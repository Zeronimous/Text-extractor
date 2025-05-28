import os
import json
import copy
import csv

# Define constants for folder names
ORIGINALES_DIR = "Originales"
TEXTOS_DIR = "Textos"
TRADUCIDOS_DIR = "Traducidos"

def set_value_at_path(data_obj, path_list, value):
    current = data_obj
    for i, key_or_index in enumerate(path_list):
        if i == len(path_list) - 1:
            if isinstance(current, list) and isinstance(key_or_index, int):
                if 0 <= key_or_index < len(current):
                    current[key_or_index] = value
                    return True
                else:
                    # print(f"Error: Index {key_or_index} out of bounds for list segment in path {' -> '.join(map(str,path_list))}")
                    return False
            elif isinstance(current, dict) and (key_or_index in current or isinstance(key_or_index, str)):
                current[key_or_index] = value
                return True
            else:
                # print(f"Error: Invalid path or type mismatch at final segment '{key_or_index}' for path {' -> '.join(map(str,path_list))}. Cannot set value.")
                return False
        else:
            if isinstance(current, list) and isinstance(key_or_index, int):
                if 0 <= key_or_index < len(current):
                    current = current[key_or_index]
                else:
                    # print(f"Error: Index {key_or_index} out of bounds during navigation in path {' -> '.join(map(str,path_list))}")
                    return False
            elif isinstance(current, dict) and key_or_index in current:
                current = current[key_or_index]
            else:
                # print(f"Error: Could not navigate path at segment '{key_or_index}' for path {' -> '.join(map(str,path_list))}")
                return False
    return False

def parse_json_path(path_str):
    parts = []
    current_segment = ""
    i = 0
    while i < len(path_str):
        char = path_str[i]
        if char == '[':
            if current_segment: parts.append(current_segment)
            current_segment = ""
            idx_close_bracket = path_str.find(']', i)
            if idx_close_bracket == -1:
                print(f"Error: Malformed path string, missing ']' in '{path_str}'")
                return []
            index_str = path_str[i+1:idx_close_bracket]
            if index_str.isdigit(): parts.append(int(index_str))
            else: parts.append(index_str)
            i = idx_close_bracket
        elif char == '.':
            if current_segment: parts.append(current_segment)
            current_segment = ""
        else:
            current_segment += char
        i += 1
    if current_segment: parts.append(current_segment)
    return parts

def process_translated_files():
    print("Starting translated text insertion process from TSV files...")

    if not os.path.exists(TRADUCIDOS_DIR):
        os.makedirs(TRADUCIDOS_DIR)
        print(f"Created directory: {TRADUCIDOS_DIR}")

    modified_json_data = {} # Cache for loaded and modified original JSONs
    failed_to_load_originals = set() # Keep track of original files that couldn't be loaded

    for tsv_filename in os.listdir(TEXTOS_DIR):
        if not tsv_filename.lower().endswith(".tsv"):
            continue

        basename = tsv_filename[:-4] # e.g., "Map001"
        original_game_filename = f"{basename}.json"
        manifest_filename = f"{basename}_manifest.json"
        
        tsv_filepath = os.path.join(TEXTOS_DIR, tsv_filename)
        manifest_filepath = os.path.join(TEXTOS_DIR, manifest_filename)

        print(f"\nProcessing TSV file: {tsv_filepath}")

        # Load Manifest
        if not os.path.exists(manifest_filepath):
            print(f"Warning: Manifest file '{manifest_filename}' not found for '{tsv_filename}'. Skipping.")
            continue
        try:
            with open(manifest_filepath, 'r', encoding='utf-8') as f:
                manifest_array = json.load(f)
            if not isinstance(manifest_array, list):
                print(f"Warning: Manifest content in '{manifest_filename}' is not a JSON list. Skipping '{tsv_filename}'.")
                continue
            print(f"Successfully loaded manifest: {manifest_filename}")
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from '{manifest_filename}'. Skipping '{tsv_filename}'.")
            continue
        except IOError as e:
            print(f"Warning: Could not read manifest file '{manifest_filename}': {e}. Skipping '{tsv_filename}'.")
            continue

        # Process TSV
        try:
            with open(tsv_filepath, 'r', encoding='utf-8', newline='') as tsvfile:
                reader = csv.reader(tsvfile, delimiter='\t')
                header_row = next(reader, None)
                if not header_row:
                    print(f"Warning: TSV file '{tsv_filename}' is empty or header row is missing. Skipping.")
                    continue
                
                try:
                    # The extractor writes "original_text". User translates this column. Inserter reads from it.
                    text_column_name = "original_text" 
                    text_column_idx = header_row.index(text_column_name)
                except ValueError:
                    print(f"Warning: Column '{text_column_name}' not found in header of '{tsv_filename}'. Skipping.")
                    continue

                for row_idx, tsv_row_list in enumerate(reader):
                    if row_idx >= len(manifest_array):
                        print(f"Warning: TSV file '{tsv_filename}' has more data rows ({row_idx+1}) than manifest entries ({len(manifest_array)}). Stopping processing for this file.")
                        break
                    
                    manifest_entry = manifest_array[row_idx]
                    json_path_str = manifest_entry.get("json_path_to_parameter")
                    if not json_path_str:
                        print(f"Warning: 'json_path_to_parameter' missing in manifest entry {row_idx} of '{manifest_filename}'. Skipping row.")
                        continue

                    if text_column_idx >= len(tsv_row_list):
                        print(f"Warning: Malformed row {row_idx+1} in '{tsv_filename}' (not enough columns for '{text_column_name}'). Skipping row.")
                        continue
                    translated_text_from_tsv = tsv_row_list[text_column_idx]

                    # Load Original JSON (if not already loaded or failed)
                    if original_game_filename in failed_to_load_originals:
                        # print(f"Skipping entry for {original_game_filename} as it previously failed to load.") # Optional: too verbose
                        continue 

                    if original_game_filename not in modified_json_data:
                        original_json_full_path = os.path.join(ORIGINALES_DIR, original_game_filename)
                        if not os.path.exists(original_json_full_path):
                            print(f"Warning: Original game file '{original_json_full_path}' not found. Skipping all entries for this file.")
                            failed_to_load_originals.add(original_game_filename)
                            continue # Skips this row, and subsequent rows for this file will also hit the failed_to_load_originals check
                        try:
                            with open(original_json_full_path, 'r', encoding='utf-8') as oj_file:
                                loaded_data = json.load(oj_file)
                                modified_json_data[original_game_filename] = copy.deepcopy(loaded_data)
                            print(f"Loaded and deepcopied original JSON: {original_json_full_path}")
                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode JSON from '{original_json_full_path}'. Skipping all entries for this file.")
                            failed_to_load_originals.add(original_game_filename)
                            continue
                        except IOError as e:
                            print(f"Warning: Could not read '{original_json_full_path}': {e}. Skipping all entries for this file.")
                            failed_to_load_originals.add(original_game_filename)
                            continue
                    
                    current_json_root = modified_json_data[original_game_filename] # Should exist if not failed
                    
                    parsed_path = parse_json_path(json_path_str)
                    if not parsed_path:
                        print(f"Warning: Could not parse JSON path '{json_path_str}' from manifest entry {row_idx} of '{manifest_filename}'. Skipping row.")
                        continue
                    
                    print(f"  Updating '{original_game_filename}' at path '{json_path_str}' with text: '{translated_text_from_tsv[:50]}...'")
                    if not set_value_at_path(current_json_root, parsed_path, translated_text_from_tsv):
                        print(f"Warning: Failed to set value for path '{json_path_str}' in '{original_game_filename}' (Manifest entry {row_idx}).")

        except IOError as e:
            print(f"Warning: Could not read TSV file '{tsv_filename}': {e}. Skipping.")
            continue
        except Exception as e: # Catch any other unexpected errors during TSV processing
            print(f"An unexpected error occurred while processing TSV '{tsv_filename}': {e}. Skipping.")
            continue

    # Save all modified JSON data
    print("\nSaving all modified JSON files...")
    saved_count = 0
    if not modified_json_data:
        print("No JSON data was loaded or modified. Nothing to save.")
    
    for filename, json_content in modified_json_data.items():
        # filename here is original_game_filename like "Map001.json"
        if filename in failed_to_load_originals: # Should not happen if logic is correct, but defensive
            continue
        output_json_path = os.path.join(TRADUCIDOS_DIR, filename)
        try:
            with open(output_json_path, 'w', encoding='utf-8') as out_file:
                json.dump(json_content, out_file, indent=4, ensure_ascii=False)
            print(f"Successfully saved: {output_json_path}")
            saved_count += 1
        except IOError as e:
            print(f"Error: Could not write modified JSON to {output_json_path}: {e}.")
        except TypeError as e: 
            print(f"Error: Could not serialize JSON for {output_json_path}. Error: {e}")

    if saved_count > 0:
        print(f"\nSuccessfully saved {saved_count} modified JSON file(s) to {TRADUCIDOS_DIR}.")
    elif modified_json_data: # Data was loaded but nothing saved (perhaps all were for failed original files)
        print("\nJSON data was processed, but no files were saved. Check for warnings above.")

if __name__ == "__main__":
    process_translated_files()
    print("\nScript finished.")
