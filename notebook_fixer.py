import os
import json
import time
import sys
import argparse
import google.generativeai as genai
import nbformat
from nbformat.validator import validate, ValidationError

def validate_notebook_structure(path):
    """
    Validates the notebook against the nbformat specification.
    Returns (is_valid, error_message).
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        validate(nb)
        return True, "Valid nbformat v4"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except ValidationError as e:
        return False, f"nbformat Validation Error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected Error: {str(e)}"

def fix_with_gemini(path, error_msg, model_name):
    """
    Reads the broken notebook, sends it to Gemini to fix structure/JSON,
    and returns the corrected content string.
    """
    print(f"   Requesting fix from {model_name}...")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        # If file can't be read normally, try reading as raw bytes/text
        with open(path, 'r', errors='ignore') as f:
            content = f.read()

    prompt = f"""
    You are an expert software engineer specializing in Jupyter Notebooks and JSON data structures.
    
    The file below is supposed to be a Jupyter Notebook (.ipynb), but it currently fails validation.
    
    VALIDATION ERROR:
    {error_msg}
    
    TASK:
    1. specific fix: Fix the invalid JSON syntax or nbformat structure issues.
    2. Do NOT change the actual code or markdown text content within the cells unless it causes the syntax error.
    3. Ensure the output is a strictly valid JSON object.
    4. Return ONLY the JSON. Do not include markdown formatting (like ```json ... ```).
    
    BROKEN CONTENT:
    {content}
    """

    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    
    # Clean up response (remove markdown fences if model adds them)
    cleaned_text = response.text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
        
    return cleaned_text.strip()

def main():
    parser = argparse.ArgumentParser(description="Fixes Jupyter Notebook formatting using Gemini API.")
    parser.add_argument("notebook_path", type=str, nargs='?',
                        default="examples/analysis/02_Core_Architecture.ipynb",
                        help="Path to the Jupyter Notebook file to fix. Defaults to examples/analysis/02_Core_Architecture.ipynb")
    parser.add_argument("--model", type=str, default="gemini-2.5-pro",
                        help="Gemini model to use for fixing. Defaults to gemini-2.5-pro")
    
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please export GEMINI_API_KEY='your_key_here'")
        sys.exit(1)

    genai.configure(api_key=api_key)
    
    print(f"Starting repair process for: {args.notebook_path} with model {args.model}")
    max_retries = 5
    
    for attempt in range(1, max_retries + 1):
        print(f"\n--- Check Cycle {attempt}/{max_retries} ---")
        
        is_valid, msg = validate_notebook_structure(args.notebook_path)
        
        if is_valid:
            print(f"✅ Success! Notebook is valid: {msg}")
            break
        else:
            print(f"❌ Validation Failed: {msg}")
            if attempt == max_retries:
                print("Max retries reached. Could not fix notebook.")
                sys.exit(1)
            
            print("Attempting to fix with Gemini...")
            try:
                fixed_content = fix_with_gemini(args.notebook_path, msg, args.model)
                
                # Verify it's at least parseable JSON before writing
                try:
                    json_obj = json.loads(fixed_content)
                    with open(args.notebook_path, 'w', encoding='utf-8') as f:
                        json.dump(json_obj, f, indent=1)
                    print("   -> Wrote potential fix to file.")
                except json.JSONDecodeError:
                    print("   -> Gemini returned invalid JSON. Retrying...")
                    
            except Exception as e:
                print(f"   -> Error during API call: {e}")
                time.sleep(1)

if __name__ == "__main__":
    main()
