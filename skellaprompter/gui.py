"""PyQt based GUI implementation for Skellaprompter."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)


TOKEN_RE = re.compile(
    r"\{\{(?P<gd>[^{}]+)\}\}|<<(?P<ld>[^<>]+)>>|\[\[\[(?P<long>[^\]]+)\]\]\]|\[\[(?P<short>[^\]]+)\]\]"
)


class Variable:
    """Representation of a template variable."""

    def __init__(
        self, kind: str, name: str, file_path: Path | None, default: str | None = None
    ) -> None:
        self.kind = kind
        self.name = name
        self.file_path = file_path
        self.default = default
        self.widget: QWidget | None = None


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, base_path: Path) -> None:
        super().__init__()
        self.base_path = base_path
        self.setWindowTitle("Skellaprompter")
        self.resize(1000, 600)

        self.prompt_tree = QTreeWidget()
        self.prompt_tree.setHeaderHidden(True)
        self.prompt_tree.itemClicked.connect(self.on_tree_clicked)

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setReadOnly(True)
        self.template_edit = QPlainTextEdit()
        self.template_edit.setReadOnly(True)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.prompt_edit, "Prompt")
        self.tabs.addTab(self.template_edit, "Template")

        self.vars_form = QFormLayout()
        vars_widget = QWidget()
        vars_widget.setLayout(self.vars_form)
        self.vars_scroll = QScrollArea()
        self.vars_scroll.setWidget(vars_widget)
        self.vars_scroll.setWidgetResizable(True)

        self.copy_button = QPushButton("Copy")
        self.copy_button.clicked.connect(self.copy_prompt)

        right_column = QWidget()
        right_layout = QFormLayout(right_column)
        right_layout.addRow(self.vars_scroll)
        right_layout.addRow(self.copy_button)

        splitter = QSplitter()
        splitter.addWidget(self.prompt_tree)
        splitter.addWidget(self.tabs)
        splitter.addWidget(right_column)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)
        self.setStatusBar(QStatusBar())

        self.variables: dict[str, Variable] = {}
        self.template_text: str = ""
        self.template_path: Path | None = None

        self.build_menu()
        self.resync()

    # ------------------------------------------------------------------
    # Menu and actions

    def build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        resync_action = file_menu.addAction("Resync")
        resync_action.triggered.connect(self.resync)
        file_menu.addSeparator()
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

        help_menu = self.menuBar().addMenu("Help")
        vars_action = help_menu.addAction("Variables")
        vars_action.triggered.connect(self.show_variable_help)

    def show_variable_help(self) -> None:
        """Display a dialog describing variable syntax."""
        text = (
            "Template variable syntax:\n\n"
            "{{name}}  - global variable from vars/<name>.yaml\n"
            "<<name>>  - prompt-local variable from prompt-vars/<prompt>/<name>.yaml\n"
            "[[name]]  - short free text\n"
            "[[[name]]] - long free text\n\n"
            "A default value can be specified with a pipe, e.g. {{Character|John}}"
        )
        QMessageBox.information(self, "Variable Syntax", text)

    def resync(self) -> None:
        """Rebuild the navigation tree from the prompts directory."""
        self.prompt_tree.clear()
        prompts_root = self.base_path / "prompts"
        for path in sorted(prompts_root.rglob("*.md")):
            if path.is_file():
                rel = path.relative_to(prompts_root)
                parent = self._ensure_parents(rel.parts[:-1])
                item = QTreeWidgetItem([rel.stem])
                item.setData(0, Qt.UserRole, path)
                parent.addChild(item)

    def _ensure_parents(self, parts: tuple[str, ...]) -> QTreeWidgetItem:
        parent = self.prompt_tree.invisibleRootItem()
        for part in parts:
            found = None
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.text(0) == part:
                    found = child
                    break
            if found is None:
                found = QTreeWidgetItem([part])
                parent.addChild(found)
            parent = found
        return parent

    # ------------------------------------------------------------------
    # Template loading and variable parsing

    def on_tree_clicked(self, item: QTreeWidgetItem) -> None:
        path = item.data(0, Qt.UserRole)
        if not path:
            return
        self.template_path = Path(path)
        self.template_text = self.template_path.read_text(encoding="utf-8")
        self.template_edit.setPlainText(self.template_text)
        self.build_variables()
        self.render_prompt()

    def build_variables(self) -> None:
        # clear existing
        while self.vars_form.rowCount():
            self.vars_form.removeRow(0)
        self.variables.clear()

        if not self.template_text:
            return

        template_rel = self.template_path.relative_to(self.base_path / "prompts")
        local_base = self.base_path / "prompt-vars" / template_rel.with_suffix("")

        for match in TOKEN_RE.finditer(self.template_text):
            kind: str
            raw: str
            if match.group("gd"):
                kind = "global"
                raw = match.group("gd")
            elif match.group("ld"):
                kind = "local"
                raw = match.group("ld")
            elif match.group("short"):
                kind = "short"
                raw = match.group("short")
            else:
                kind = "long"
                raw = match.group("long")

            name, default = (raw.split("|", 1) + [None])[:2]

            file_path: Path | None = None
            if kind == "global":
                file_path = self.base_path / "vars" / f"{name}.yaml"
            elif kind == "local":
                file_path = local_base / f"{name}.yaml"

            if name in self.variables:
                continue

            var = Variable(kind, name, file_path, default)
            self.variables[name] = var

            if kind in {"global", "local"}:
                combo = QComboBox()
                options = self._load_options(file_path, default)
                if options:
                    combo.addItems([t for t, _ in options])
                    if default:
                        values = [v for _, v in options]
                        if default in values:
                            combo.setCurrentIndex(values.index(default))
                    combo.currentIndexChanged.connect(self.render_prompt)
                else:
                    combo.addItem("Missing file")
                    combo.setEnabled(False)
                var.widget = combo
                self.vars_form.addRow(name, combo)
            elif kind == "short":
                line = QLineEdit()
                if default:
                    line.setText(default)
                line.textChanged.connect(self.render_prompt)
                var.widget = line
                self.vars_form.addRow(name, line)
            else:
                text = QTextEdit()
                text.setFixedHeight(80)
                if default:
                    text.setPlainText(default)
                text.textChanged.connect(self.render_prompt)
                var.widget = text
                self.vars_form.addRow(name, text)

    def _load_options(
        self, file_path: Path | None, default: str | None = None
    ) -> list[tuple[str, str]]:
        if not file_path or not file_path.exists():
            return []
        try:
            data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return []
        result = []
        for item in data.get("options", []):
            title = str(item.get("title", ""))
            value = str(item.get("value", title))
            result.append((title, value))
        if default and default not in [v for _, v in result]:
            result.insert(0, (default, default))
        return result

    # ------------------------------------------------------------------
    # Rendering and actions

    def render_prompt(self) -> None:
        if not self.template_text:
            self.prompt_edit.clear()
            return

        rendered: list[str] = []
        pos = 0
        for match in TOKEN_RE.finditer(self.template_text):
            rendered.append(self.template_text[pos:match.start()])
            name = match.group("gd") or match.group("ld") or match.group("short") or match.group("long")
            value = self._var_value(name)
            rendered.append(value)
            pos = match.end()
        rendered.append(self.template_text[pos:])
        self.prompt_edit.setPlainText("".join(rendered))

    def _var_value(self, name: str) -> str:
        var = self.variables.get(name)
        if not var or not var.widget:
            return ""
        if isinstance(var.widget, QComboBox):
            options = self._load_options(var.file_path, var.default)
            idx = var.widget.currentIndex()
            if 0 <= idx < len(options):
                return options[idx][1]
            return var.default or ""
        if isinstance(var.widget, QLineEdit):
            text = var.widget.text()
            return text if text else (var.default or "")
        if isinstance(var.widget, QTextEdit):
            text = var.widget.toPlainText()
            return text if text else (var.default or "")
        return ""

    def copy_prompt(self) -> None:
        text = self.prompt_edit.toPlainText()
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(f"Copied {len(text)} chars", 2000)

    def closeEvent(self, event: QCloseEvent) -> None:  # pragma: no cover - GUI
        event.accept()


def run(base_path: Path) -> None:
    """Launch the GUI application."""
    app = QApplication([])
    window = MainWindow(base_path)
    window.show()
    app.exec_()

