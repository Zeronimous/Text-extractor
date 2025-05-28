import os
import json
import copy
import re # For parsing text lines

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
            elif isinstance(current, dict) and isinstance(key_or_index, str): # Allow creating new key if it's the target
                 # This case might be needed if a text was optional and not present in original,
                 # but this script assumes replacement of existing text.
                 # For safety, we only modify existing paths. If a path implies creation, it's an issue.
                print(f"Error: Key '{key_or_index}' not found in dict segment for path {' -> '.join(map(str,path_list))}. Cannot create new keys.")
                return False
            else:
                print(f"Error: Invalid path or type mismatch at final segment '{key_or_index}' for path {' -> '.join(map(str,path_list))}")
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
    return False # Should be unreachable if path_list is not empty, but as a fallback.

def parse_json_path(path_str):
    """
    Parses a JSON path string (e.g., "events[0].list[5].parameters[0]" or "name" or "system.boat.vehicleName")
    into a list of keys/indices (e.g., ['events', 0, 'list', 5, 'parameters', 0]).
    """
    parts = []
    current_segment = ""
    i = 0
    while i < len(path_str):
        char = path_str[i]
        if char == '[':
            if current_segment: # Segment before '[' (e.g. 'events' in 'events[0]')
                parts.append(current_segment)
            current_segment = ""
            # Find closing ']'
            idx_close_bracket = path_str.find(']', i)
            if idx_close_bracket == -1:
                # Malformed path
                print(f"Error: Malformed path string, missing ']' in '{path_str}'")
                return [] # Return empty list for error
            index_str = path_str[i+1:idx_close_bracket]
            if index_str.isdigit():
                parts.append(int(index_str))
            else: # Should not happen for valid paths from extractor
                parts.append(index_str) # Store as string if not digit, though unlikely for RPGMaker
            i = idx_close_bracket # Move past ']'
        elif char == '.':
            if current_segment: # Segment before '.'
                parts.append(current_segment)
            current_segment = ""
        else:
            current_segment += char
        i += 1
    if current_segment: # Add the last segment
        parts.append(current_segment)
    return parts

def insert_texts():
    """
    Main function to insert translated texts back into JSON files.
    """
    print("Starting text insertion process...")

    if not os.path.exists(TRADUCIDOS_DIR):
        os.makedirs(TRADUCIDOS_DIR)
        print(f"Created directory: {TRADUCIDOS_DIR}")

    manifest_path = os.path.join(TEXTOS_DIR, "extraction_manifest.json")
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest file not found at {manifest_path}. Exiting.")
        return

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        print("Successfully loaded extraction_manifest.json.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {manifest_path}. Exiting.")
        return
    except IOError:
        print(f"Error: Could not read manifest file {manifest_path}. Exiting.")
        return

    modified_json_data = {} # To store loaded and modified JSONs

    # Define the regex for the new format "LINEA_X: Text |"
    line_parser_new_format = re.compile(r"^LINEA_(\d+): (.*?) \|$", re.UNICODE)

    for text_filename_in_textos_dir in os.listdir(TEXTOS_DIR):
        if not text_filename_in_textos_dir.endswith(".txt") or text_filename_in_textos_dir == "extraction_manifest.json":
            continue

        # This is the name of the .txt file, e.g. "Map001.txt"
        translated_txt_filepath = os.path.join(TEXTOS_DIR, text_filename_in_textos_dir)
        print(f"\nProcessing translated file: {translated_txt_filepath}")

        try:
            with open(translated_txt_filepath, 'r', encoding='utf-8') as txt_file:
                for line_number_in_file, line_content in enumerate(txt_file, 1): # file line numbers are 1-based
                    line_content = line_content.strip() # Strip leading/trailing whitespace, including newline

                    if not line_content: # Skip empty lines
                        continue

                    match = line_parser_new_format.match(line_content)
                    if match:
                        code_str = match.group(1)
                        translated_text = match.group(2) # Content between "LINEA_X: " and " |"
                        try:
                            parsed_id_from_line = int(code_str)
                        except ValueError:
                            print(f"Warning: Could not parse code '{code_str}' as a number in line {line_number_in_file} of {text_filename_in_textos_dir}: '{line_content[:50]}...'. Skipping.")
                            continue
                    else:
                        print(f"Warning: Line {line_number_in_file} in {text_filename_in_textos_dir} does not match 'LINEA_X: Text |' format: '{line_content[:50]}...'. Skipping.")
                        continue
                    
                    # Construct manifest key (e.g., Map001.txt#1)
                    manifest_key = f"{text_filename_in_textos_dir}#{parsed_id_from_line}"

                    if manifest_key not in manifest_data:
                        print(f"Warning: Key '{manifest_key}' not found in manifest. Skipping line {line_number_in_file} ('LINEA_{parsed_id_from_line}: ...') from {text_filename_in_textos_dir}.")
                        continue

                    entry = manifest_data[manifest_key]
                    original_json_filename = entry.get("original_file") # e.g., "Map001.json"
                    json_path_str = entry.get("json_path")

                    if not original_json_filename or not json_path_str:
                        print(f"Warning: Incomplete manifest entry for '{manifest_key}'. Missing original_file or json_path. Skipping.")
                        continue

                    # Load original JSON if not already loaded, using deepcopy
                    if original_json_filename not in modified_json_data:
                        original_json_full_path = os.path.join(ORIGINALES_DIR, original_json_filename)
                        if not os.path.exists(original_json_full_path):
                            print(f"Warning: Original JSON file '{original_json_full_path}' not found for key '{manifest_key}'. Skipping processing for this key.")
                            continue
                        try:
                            with open(original_json_full_path, 'r', encoding='utf-8') as oj_file:
                                # Use deepcopy here
                                modified_json_data[original_json_filename] = json.load(oj_file, object_pairs_hook=lambda pairs: copy.deepcopy(dict(pairs)))
                            print(f"Loaded and deepcopied original JSON: {original_json_full_path}")
                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode JSON from '{original_json_full_path}' for key '{manifest_key}'. Skipping processing for this key.")
                            # Remove placeholder if file load failed to prevent trying to save it later
                            if original_json_filename in modified_json_data:
                                del modified_json_data[original_json_filename]
                            continue
                        except IOError:
                            print(f"Warning: Could not read '{original_json_full_path}' for key '{manifest_key}'. Skipping processing for this key.")
                            if original_json_filename in modified_json_data:
                                del modified_json_data[original_json_filename]
                            continue
                    
                    # Get the root of the JSON object to modify for this specific original_json_filename
                    current_json_root = modified_json_data.get(original_json_filename)
                    if current_json_root is None: # Should not happen if loading logic is correct
                        print(f"Critical Error: JSON data for '{original_json_filename}' not found in memory map, though it should be. Skipping '{manifest_key}'.")
                        continue

                    path_list = parse_json_path(json_path_str)
                    if not path_list:
                        print(f"Warning: Could not parse JSON path '{json_path_str}' for key '{manifest_key}'. Skipping.")
                        continue
                        
                    print(f"  Updating: '{manifest_key}' (Path: {json_path_str}, Text: '{translated_text[:30]}...')")
                    if not set_value_at_path(current_json_root, path_list, translated_text):
                        print(f"Warning: Failed to set value for key '{manifest_key}' at path '{json_path_str}' in '{original_json_filename}'.")

        except IOError:
            print(f"Error: Could not read translated file '{translated_txt_filepath}'. Skipping this file.")
            continue
        except Exception as e:
            print(f"An unexpected error occurred while processing file '{translated_txt_filepath}': {e}. Skipping this file.")
            continue


    # After processing all .txt files, save modified JSON data
    print("\nSaving all modified JSON files...")
    saved_count = 0
    if not modified_json_data:
        print("No JSON data was loaded or modified, nothing to save.")
    
    for original_filename, json_content in modified_json_data.items():
        # original_filename is like "Map001.json"
        output_json_path = os.path.join(TRADUCIDOS_DIR, original_filename)
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
    elif modified_json_data: # Some data was loaded but nothing saved
        print("\nJSON data was processed, but no files were saved. Check for warnings above.")
    else: # No data loaded and nothing saved
        pass # Already printed "No JSON data was loaded..."


if __name__ == "__main__":
    insert_texts()
    print("\nScript finished.")
