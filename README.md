# Skellaprompter

This project manages Markdown prompt templates alongside YAML variable files. It aims to provide a desktop application that lets you build prompts quickly by selecting variables from dropdowns or entering text.

The repository currently includes a small backend written in Python. Run it with:

```bash
python main.py --debug
```
The script ensures required directories exist (`prompts`, `vars`, and `prompt-vars`) and then launches the GUI.

Only Markdown files within the `prompts` directory appear in the navigation tree. File extensions are stripped so, for example, "Hunters.md" is shown as "Hunters".

## Variable syntax

Template variables are marked using one of four delimiters:

- `{{name}}` for global variables
- `<<name>>` for prompt-local variables
- `[[name]]` for short free-form text
- `[[[name]]]` for long free-form text

You can specify a default value after the variable name using a pipe (`|`).
For example:

```
{{Character|John}}
<<Location|Dungeon>>
```

When the template loads, these defaults pre-fill the corresponding fields even
if they are not listed in the YAML options file.
