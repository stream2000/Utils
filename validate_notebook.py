import json
import ast
import sys

def validate_notebook(file_path):
    """
    Validates a Jupyter Notebook file for JSON format, basic structure,
    and Python syntax in code cells.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}.")
        print(f"Details: {e}")
        return False

    if "cells" not in notebook or not isinstance(notebook["cells"], list):
        print(f"Error: Missing or invalid 'cells' list in {file_path}.")
        return False

    is_valid = True
    for i, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            # Skip empty code cells
            if not source.strip():
                continue
            try:
                ast.parse(source)
            except SyntaxError as e:
                print(f"--- Syntax Error Found in {file_path}, Cell {i+1} ---")
                print(f"Line {e.lineno}, Offset {e.offset}: {e.msg}")
                print("```python")
                print(e.text.strip())
                print(" " * (e.offset - 1) + "^")
                print("```")
                is_valid = False
    
    return is_valid

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_notebook.py <notebook_file.ipynb>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if validate_notebook(file_path):
        print(f"Validation successful: {file_path} is a valid notebook with correct Python syntax.")
    else:
        print(f"Validation failed for {file_path}.")
        sys.exit(1)
