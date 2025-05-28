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

def find_texts_in_json_recursive(data, current_path_stack, original_filename_str, 
                                 global_texts_list, global_manifest_dict, global_index_list):
    """
    Recursively searches for text strings in JSON data and populates global lists/dicts.
    - data: current JSON node (dict or list)
    - current_path_stack: list representing the path to the current node
    - original_filename_str: filename of the original JSON (e.g., "Map001.json")
    - global_texts_list: list to append all found texts
    - global_manifest_dict: dictionary to store metadata for each extracted text, keyed by global index
    - global_index_list: a list containing the current global_text_index (e.g., [0]) to allow modification
    """
    if isinstance(data, dict):
        for key, value in data.items():
            current_path_stack.append(key)
            if key in ("name", "description") and isinstance(value, str) and value.strip():
                found_text = value
                global_texts_list.append(found_text)
                global_manifest_dict[str(global_index_list[0])] = {
                    "original_file": original_filename_str,
                    "json_path": get_json_path(current_path_stack),
                    "original_text": found_text
                }
                global_index_list[0] += 1
            elif key == "list" and isinstance(value, list): # Typically for event commands
                for index, item in enumerate(value):
                    current_path_stack.append(index)
                    if isinstance(item, dict) and "code" in item:
                        code = item.get("code")
                        parameters = item.get("parameters", [])
                        if code in (101, 401, 105): # Show Text, Show Text with Face, Show Scrolling Text
                            current_path_stack.append("parameters")
                            current_path_stack.append(0) # Text is usually the first parameter
                            if len(parameters) > 0 and isinstance(parameters[0], str) and parameters[0].strip():
                                text_content = parameters[0]
                                global_texts_list.append(text_content)
                                global_manifest_dict[str(global_index_list[0])] = {
                                    "original_file": original_filename_str,
                                    "json_path": get_json_path(current_path_stack),
                                    "original_text": text_content
                                }
                                global_index_list[0] += 1
                            current_path_stack.pop() # Pop 0
                            current_path_stack.pop() # Pop "parameters"
                        elif code == 102: # Show Choices
                            current_path_stack.append("parameters")
                            current_path_stack.append(0) # Path to the array of choices
                            if len(parameters) > 0 and isinstance(parameters[0], list):
                                for choice_idx, choice_text in enumerate(parameters[0]):
                                    if isinstance(choice_text, str) and choice_text.strip():
                                        current_path_stack.append(choice_idx)
                                        global_texts_list.append(choice_text)
                                        global_manifest_dict[str(global_index_list[0])] = {
                                            "original_file": original_filename_str,
                                            "json_path": get_json_path(current_path_stack),
                                            "original_text": choice_text
                                        }
                                        global_index_list[0] += 1
                                        current_path_stack.pop() # Pop choice_idx
                            current_path_stack.pop() # Pop 0
                            current_path_stack.pop() # Pop "parameters"
                    # Recursive call for other elements within the list item (e.g. nested structures)
                    find_texts_in_json_recursive(item, current_path_stack, original_filename_str, 
                                                 global_texts_list, global_manifest_dict, global_index_list)
                    current_path_stack.pop() # Pop index
            else: # Regular recursive call for other dictionary values
                find_texts_in_json_recursive(value, current_path_stack, original_filename_str, 
                                             global_texts_list, global_manifest_dict, global_index_list)
            current_path_stack.pop() # Pop key
    elif isinstance(data, list):
        for index, item in enumerate(data):
            current_path_stack.append(index)
            find_texts_in_json_recursive(item, current_path_stack, original_filename_str, 
                                         global_texts_list, global_manifest_dict, global_index_list)
            current_path_stack.pop() # Pop index

def extract_texts():
    """
    Main function to extract texts from JSON files in ORIGINALES_DIR,
    creates a global list of texts and an index-based manifest.
    """
    if not os.path.exists(TEXTOS_DIR):
        os.makedirs(TEXTOS_DIR)
        print(f"Created directory: {TEXTOS_DIR}")

    all_extracted_texts = []
    manifest_data = {}
    global_text_index_list = [0] # Use a list to pass by reference for modification

    json_files = sorted([f for f in os.listdir(ORIGINALES_DIR) if f.endswith(".json")])

    if not json_files:
        print(f"No JSON files found in {ORIGINALES_DIR}. Nothing to process.")
        # Create empty files as per desired output for no texts
        output_texts_filepath = os.path.join(TEXTOS_DIR, "extracted_texts.json")
        output_manifest_filepath = os.path.join(TEXTOS_DIR, "extraction_manifest.json")
        try:
            with open(output_texts_filepath, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            print(f"Saved empty list to {output_texts_filepath}")
            with open(output_manifest_filepath, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            print(f"Saved empty manifest to {output_manifest_filepath}")
        except IOError as e:
            print(f"Error writing empty files: {e}")
        return

    for filename in json_files:
        original_filepath = os.path.join(ORIGINALES_DIR, filename)
        print(f"Processing {original_filepath}...")

        try:
            with open(original_filepath, 'r', encoding='utf-8') as f:
                json_content = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {original_filepath}. Skipping file.")
            continue
        except FileNotFoundError: # Should not happen if os.listdir is used and files not deleted mid-script
            print(f"Error: File not found {original_filepath}. Skipping file.")
            continue
        
        find_texts_in_json_recursive(json_content, [], filename, 
                                     all_extracted_texts, manifest_data, global_text_index_list)

    # Save the global list of texts
    output_texts_filepath = os.path.join(TEXTOS_DIR, "extracted_texts.json")
    try:
        with open(output_texts_filepath, 'w', encoding='utf-8') as f:
            json.dump(all_extracted_texts, f, ensure_ascii=False, indent=4)
        print(f"All extracted texts saved to {output_texts_filepath}")
    except IOError:
        print(f"Error: Could not write extracted texts to {output_texts_filepath}")

    # Save the global manifest data
    output_manifest_filepath = os.path.join(TEXTOS_DIR, "extraction_manifest.json")
    try:
        with open(output_manifest_filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=4)
        print(f"Extraction manifest saved to {output_manifest_filepath}")
    except IOError:
        print(f"Error: Could not write manifest file to {output_manifest_filepath}")

if __name__ == "__main__":
    print("Script execution started.")
    extract_texts()
    print("Script finished successfully.")
