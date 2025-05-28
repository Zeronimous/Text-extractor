import os
import json
import copy
# import re # No longer needed for this version

# Define constants for folder names
ORIGINALES_DIR = "Originales"
TEXTOS_DIR = "Textos"
TRADUCIDOS_DIR = "Traducidos"

def set_value_at_path(data_obj, path_list, value):
    """
    Sets a value in a nested dictionary/list structure using a list of path segments.
    Example: path_list = ['events', 0, 'list', 5, 'parameters', 0]
    Returns True on success, False on failure.
    """
    current = data_obj
    for i, key_or_index in enumerate(path_list):
        if i == len(path_list) - 1: # Last element, set the value
            if isinstance(current, list) and isinstance(key_or_index, int):
                if 0 <= key_or_index < len(current):
                    current[key_or_index] = value
                    return True
                else:
                    print(f"Error: Index {key_or_index} out of bounds for list segment in path {' -> '.join(map(str,path_list))}")
                    return False
            elif isinstance(current, dict) and key_or_index in current:
                current[key_or_index] = value
                return True
            else: # Path implies creation or type mismatch at target
                print(f"Error: Invalid path or type mismatch at final segment '{key_or_index}' for path {' -> '.join(map(str,path_list))}. Cannot set value.")
                return False
        else: # Navigate deeper
            if isinstance(current, list) and isinstance(key_or_index, int):
                if 0 <= key_or_index < len(current):
                    current = current[key_or_index]
                else:
                    print(f"Error: Index {key_or_index} out of bounds during navigation in path {' -> '.join(map(str,path_list))}")
                    return False
            elif isinstance(current, dict) and key_or_index in current:
                current = current[key_or_index]
            else:
                print(f"Error: Could not navigate path at segment '{key_or_index}' for path {' -> '.join(map(str,path_list))}")
                return False
    return False # Should be unreachable if path_list is not empty.

def parse_json_path(path_str):
    """
    Parses a JSON path string (e.g., "events[0].list[5].parameters[0]" or "name")
    into a list of keys/indices (e.g., ['events', 0, 'list', 5, 'parameters', 0]).
    """
    parts = []
    current_segment = ""
    i = 0
    while i < len(path_str):
        char = path_str[i]
        if char == '[':
            if current_segment:
                parts.append(current_segment)
            current_segment = ""
            idx_close_bracket = path_str.find(']', i)
            if idx_close_bracket == -1:
                print(f"Error: Malformed path string, missing ']' in '{path_str}'")
                return []
            index_str = path_str[i+1:idx_close_bracket]
            if index_str.isdigit():
                parts.append(int(index_str))
            else:
                parts.append(index_str) # Should ideally not happen with this project's paths
            i = idx_close_bracket
        elif char == '.':
            if current_segment:
                parts.append(current_segment)
            current_segment = ""
        else:
            current_segment += char
        i += 1
    if current_segment:
        parts.append(current_segment)
    return parts

def insert_texts():
    """
    Main function to insert translated texts from extracted_texts.json
    back into new JSON files in TRADUCIDOS_DIR, using extraction_manifest.json.
    """
    print("Starting text insertion process...")

    if not os.path.exists(TRADUCIDOS_DIR):
        os.makedirs(TRADUCIDOS_DIR)
        print(f"Created directory: {TRADUCIDOS_DIR}")

    # Load translated texts
    translated_texts_path = os.path.join(TEXTOS_DIR, "extracted_texts.json")
    try:
        with open(translated_texts_path, 'r', encoding='utf-8') as f:
            translated_texts_array = json.load(f)
        if not isinstance(translated_texts_array, list):
            print(f"Error: Content of {translated_texts_path} is not a JSON list. Exiting.")
            return
        print(f"Successfully loaded translated texts from {translated_texts_path}.")
    except FileNotFoundError:
        print(f"Error: Translated texts file not found at {translated_texts_path}. Exiting.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {translated_texts_path}. Exiting.")
        return
    except IOError:
        print(f"Error: Could not read file {translated_texts_path}. Exiting.")
        return

    # Load manifest
    manifest_path = os.path.join(TEXTOS_DIR, "extraction_manifest.json")
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        if not isinstance(manifest_data, dict):
            print(f"Error: Content of {manifest_path} is not a JSON dictionary. Exiting.")
            return
        print(f"Successfully loaded extraction manifest from {manifest_path}.")
    except FileNotFoundError:
        print(f"Error: Manifest file not found at {manifest_path}. Exiting.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {manifest_path}. Exiting.")
        return
    except IOError:
        print(f"Error: Could not read manifest file {manifest_path}. Exiting.")
        return

    # Optional: Length check
    num_texts = len(translated_texts_array)
    num_manifest_entries = len(manifest_data)
    if num_texts != num_manifest_entries:
        print(f"Warning: Number of translated texts ({num_texts}) does not match number of manifest entries ({num_manifest_entries}). Proceeding with {num_texts} texts.")
    
    if num_texts == 0:
        print("No texts found in extracted_texts.json. Nothing to insert.")
        return

    modified_json_data = {} # To store loaded and modified JSONs (deep copies)

    for i in range(num_texts):
        current_translated_text = translated_texts_array[i]
        manifest_key_str = str(i) # Manifest keys are stringified indices

        manifest_entry = manifest_data.get(manifest_key_str)
        if manifest_entry is None:
            print(f"Warning: No manifest entry for index {i}. Skipping this text.")
            continue

        original_json_filename = manifest_entry.get("original_file")
        json_path_str = manifest_entry.get("json_path")

        if not original_json_filename or not json_path_str:
            print(f"Warning: Incomplete manifest entry for index {i} (Key: '{manifest_key_str}'). Missing original_file or json_path. Skipping.")
            continue
        
        print(f"\nProcessing entry {i}: File '{original_json_filename}', Path '{json_path_str}'")

        # Load original JSON if not already loaded, using deepcopy
        if original_json_filename not in modified_json_data:
            original_json_full_path = os.path.join(ORIGINALES_DIR, original_json_filename)
            if not os.path.exists(original_json_full_path):
                print(f"Warning: Original JSON file '{original_json_full_path}' not found for manifest entry {i}. Skipping.")
                continue
            try:
                with open(original_json_full_path, 'r', encoding='utf-8') as oj_file:
                    # Using object_pairs_hook for deepcopy during load might be complex.
                    # Simpler to load then deepcopy the entire structure if it's the first time.
                    loaded_data = json.load(oj_file)
                    modified_json_data[original_json_filename] = copy.deepcopy(loaded_data)
                print(f"Loaded and deepcopied original JSON: {original_json_full_path}")
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from '{original_json_full_path}' for manifest entry {i}. Skipping.")
                if original_json_filename in modified_json_data: # Should not be, but defensive
                     del modified_json_data[original_json_filename]
                continue
            except IOError:
                print(f"Warning: Could not read '{original_json_full_path}' for manifest entry {i}. Skipping.")
                if original_json_filename in modified_json_data:
                     del modified_json_data[original_json_filename]
                continue
        
        current_json_root = modified_json_data.get(original_json_filename)
        if current_json_root is None:
            print(f"Critical Error: JSON data for '{original_json_filename}' not found in memory map for entry {i}. Skipping.")
            continue

        path_list = parse_json_path(json_path_str)
        if not path_list:
            print(f"Warning: Could not parse JSON path '{json_path_str}' for manifest entry {i}. Skipping.")
            continue
            
        print(f"  Updating text for entry {i}: '{current_translated_text[:50]}...'")
        if not set_value_at_path(current_json_root, path_list, current_translated_text):
            print(f"Warning: Failed to set value for manifest entry {i} at path '{json_path_str}' in '{original_json_filename}'.")

    # Save all modified JSON data
    print("\nSaving all modified JSON files...")
    saved_count = 0
    if not modified_json_data:
        print("No JSON data was loaded or modified (or no valid entries processed), nothing to save.")
    
    for filename, json_content in modified_json_data.items():
        output_json_path = os.path.join(TRADUCIDOS_DIR, filename)
        try:
            with open(output_json_path, 'w', encoding='utf-8') as out_file:
                json.dump(json_content, out_file, indent=4, ensure_ascii=False)
            print(f"Successfully saved: {output_json_path}")
            saved_count += 1
        except IOError:
            print(f"Error: Could not write modified JSON to {output_json_path}.")
        except TypeError as e: 
            print(f"Error: Could not serialize JSON for {output_json_path}. Issue with data structure. Error: {e}")

    if saved_count > 0:
        print(f"\nSuccessfully saved {saved_count} modified JSON file(s) to {TRADUCIDOS_DIR}.")
    elif modified_json_data:
        print("\nJSON data was processed, but no files were saved. Check for warnings above.")
    else:
        # Message for no data loaded/modified already printed
        pass

if __name__ == "__main__":
    insert_texts()
    print("\nScript finished.")
