# Skellaprompter

This project manages Markdown prompt templates alongside YAML variable files. It aims to provide a desktop application that lets you build prompts quickly by selecting variables from dropdowns or entering text.

The repository currently includes a small backend written in Python. Run it with:

```bash
python main.py --debug
```
The script ensures required directories exist (`prompts`, `vars`, and `prompt-vars`) and then launches the GUI.
