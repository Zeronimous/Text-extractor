import os
import json

# Define constants for folder names
ORIGINALES_DIR = "Originales"
TEXTOS_DIR = "Textos"

def get_json_path(context_stack):
    """
    Generates a string representation of the JSON path from a context stack.
    Example: ['events', 0, 'list', 5, 'parameters', 0] -> "events[0].list[5].parameters[0]"
    """
    if not context_stack:
        return ""
    path_str = str(context_stack[0])
    for item in context_stack[1:]:
        if isinstance(item, int):
            path_str += f"[{item}]"
        else:
            path_str += f".{item}"
    return path_str

def find_texts_in_json(data, current_path_stack, file_id, extracted_texts_for_file, manifest_data, original_filename_no_ext):
    """
    Recursively searches for text strings in JSON data.
    - data: current JSON node (dict or list)
    - current_path_stack: list representing the path to the current node
    - file_id: unique ID for the current file (e.g., Map001) - this is not used for manifest key generation anymore
    - extracted_texts_for_file: list to append found texts for the current file
    - manifest_data: dictionary to store metadata for each extracted text
    - original_filename_no_ext: original filename without .json extension (e.g., Map001)
    """
    if isinstance(data, dict):
        for key, value in data.items():
            current_path_stack.append(key)
            if key in ("name", "description") and isinstance(value, str) and value.strip():
                extracted_texts_for_file.append(value)
                manifest_key = f"{original_filename_no_ext}.txt#{len(extracted_texts_for_file)}"
                manifest_data[manifest_key] = {
                    "original_file": f"{original_filename_no_ext}.json",
                    "json_path": get_json_path(current_path_stack),
                    "original_text": value
                }
            elif key == "list" and isinstance(value, list): # Typically for event commands
                for index, item in enumerate(value):
                    current_path_stack.append(index)
                    if isinstance(item, dict) and "code" in item:
                        code = item.get("code")
                        parameters = item.get("parameters", [])
                        if code in (101, 401, 105): # Show Text, Show Text with Face, Show Scrolling Text
                            current_path_stack.append("parameters")
                            current_path_stack.append(0)
                            if len(parameters) > 0 and isinstance(parameters[0], str) and parameters[0].strip():
                                text_content = parameters[0]
                                extracted_texts_for_file.append(text_content)
                                manifest_key = f"{original_filename_no_ext}.txt#{len(extracted_texts_for_file)}"
                                manifest_data[manifest_key] = {
                                    "original_file": f"{original_filename_no_ext}.json",
                                    "json_path": get_json_path(current_path_stack),
                                    "original_text": text_content
                                }
                            current_path_stack.pop() # Pop 0
                            current_path_stack.pop() # Pop "parameters"
                        elif code == 102: # Show Choices
                            current_path_stack.append("parameters")
                            current_path_stack.append(0) # Path to the array of choices
                            if len(parameters) > 0 and isinstance(parameters[0], list):
                                for choice_idx, choice_text in enumerate(parameters[0]):
                                    if isinstance(choice_text, str) and choice_text.strip():
                                        current_path_stack.append(choice_idx)
                                        extracted_texts_for_file.append(choice_text)
                                        manifest_key = f"{original_filename_no_ext}.txt#{len(extracted_texts_for_file)}"
                                        manifest_data[manifest_key] = {
                                            "original_file": f"{original_filename_no_ext}.json",
                                            "json_path": get_json_path(current_path_stack),
                                            "original_text": choice_text
                                        }
                                        current_path_stack.pop() # Pop choice_idx
                            current_path_stack.pop() # Pop 0
                            current_path_stack.pop() # Pop "parameters"
                    # Recursive call for other elements within the list item (e.g. nested structures)
                    find_texts_in_json(item, current_path_stack, file_id, extracted_texts_for_file, manifest_data, original_filename_no_ext)
                    current_path_stack.pop() # Pop index
            else: # Regular recursive call for other dictionary values
                find_texts_in_json(value, current_path_stack, file_id, extracted_texts_for_file, manifest_data, original_filename_no_ext)
            current_path_stack.pop() # Pop key
    elif isinstance(data, list):
        for index, item in enumerate(data):
            current_path_stack.append(index)
            find_texts_in_json(item, current_path_stack, file_id, extracted_texts_for_file, manifest_data, original_filename_no_ext)
            current_path_stack.pop() # Pop index

def extract_texts():
    """
    Main function to extract texts from JSON files in ORIGINALES_DIR
    and save them to TEXTOS_DIR.
    """
    if not os.path.exists(TEXTOS_DIR):
        os.makedirs(TEXTOS_DIR)
        print(f"Created directory: {TEXTOS_DIR}")

    manifest_data = {}

    for filename in os.listdir(ORIGINALES_DIR):
        if filename.endswith(".json"):
            original_filepath = os.path.join(ORIGINALES_DIR, filename)
            print(f"Processing {original_filepath}...")

            try:
                with open(original_filepath, 'r', encoding='utf-8') as f:
                    json_content = json.load(f)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in {original_filepath}. Skipping file.")
                continue
            except FileNotFoundError:
                print(f"Error: File not found {original_filepath}. Skipping file.") # Should not happen if os.listdir is used
                continue

            extracted_texts_for_file = []
            original_filename_no_ext = filename[:-5] # Remove .json (e.g., Map001)
            
            # Pass original_filename_no_ext for manifest key generation
            find_texts_in_json(json_content, [], original_filename_no_ext, extracted_texts_for_file, manifest_data, original_filename_no_ext)

            if extracted_texts_for_file:
                txt_output_filename = os.path.join(TEXTOS_DIR, f"{original_filename_no_ext}.txt")
                with open(txt_output_filename, 'w', encoding='utf-8') as txt_file:
                    for i, text_content in enumerate(extracted_texts_for_file):
                        txt_file.write(f"[linea{i+1}] {text_content}\n")
                print(f"Extracted texts saved to {txt_output_filename}")
            else:
                print(f"No texts found in {original_filepath}.")

    # Save manifest data
    manifest_filepath = os.path.join(TEXTOS_DIR, "extraction_manifest.json")
    try:
        with open(manifest_filepath, 'w', encoding='utf-8') as manifest_file:
            json.dump(manifest_data, manifest_file, indent=4, ensure_ascii=False)
        print(f"Manifest file saved to {manifest_filepath}")
    except IOError:
        print(f"Error: Could not write manifest file to {manifest_filepath}")


if __name__ == "__main__":
    print("Script execution started.")
    extract_texts()
    print("Script finished successfully.")
