import os
import json
import re
import csv # For TSV writing

ORIGINALES_DIR = "Originales"
TEXTOS_DIR = "Textos"

# Configuration for text extraction from event commands
# Each key is an event code. The value is a list of dictionaries,
# where each dictionary defines how to extract a specific text from that command.
TEXT_PARAM_CONFIG = {
    401: [{"param_idx": 0, "text_type": "simple_text"}],  # Show Text
    101: [  # Show Text (with options)
        # Try parameters[4] first (common for main text when face/name might be params[0-3])
        # Then try parameters[5] (sometimes used if params[4] is speaker name or for different structures)
        # Finally, parameters[0] if others fail (older RPG Maker versions or very simple Show Text via 101)
        {"param_idx": 4, "text_type": "message_text_p4"}, 
        {"param_idx": 5, "text_type": "message_text_p5"},
        {"param_idx": 0, "text_type": "message_text_p0_fallback"} # Fallback for older/simpler 101s
    ],
    102: [  # Show Choices
        {"param_idx": 0, "text_type": "choices_array"}, # The array of choice strings
        {"param_idx": 4, "text_type": "choice_cancel_label", # Text for cancel branch if type is 'Branch'
         "condition_param_idx": 3, "condition_value": 2} 
    ],
    105: [{"param_idx": 0, "text_type": "scrolling_text"}], # Show Scrolling Text
    320: [{"param_idx": 1, "text_type": "actor_name"}],      # Change Actor Name
    324: [{"param_idx": 1, "text_type": "actor_nickname"}]  # Change Actor Nickname
}

def get_json_path(path_stack):
    if not path_stack: return ""
    return "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in path_stack).lstrip('.')

def process_event_command_list(command_list, base_path_stack, extracted_data_list, 
                               file_type, primary_id, page_id_for_sort_and_tsv):
    if not isinstance(command_list, list):
        return

    for cmd_array_idx, command_obj in enumerate(command_list):
        if not command_obj or not isinstance(command_obj, dict):
            continue

        code = command_obj.get("code")
        parameters = command_obj.get("parameters", [])

        if code in TEXT_PARAM_CONFIG:
            config_entries = TEXT_PARAM_CONFIG[code]
            path_to_command_obj = base_path_stack + [cmd_array_idx]
            
            extracted_texts_for_this_command = set() # Avoid duplicate extraction from same command (e.g. 101 fallback)

            for config_entry in config_entries:
                param_idx = config_entry["param_idx"]
                text_type = config_entry["text_type"]

                # Conditional extraction (e.g., for choice cancel label)
                cond_param_idx = config_entry.get("condition_param_idx")
                if cond_param_idx is not None:
                    if not (len(parameters) > cond_param_idx and parameters[cond_param_idx] == config_entry["condition_value"]):
                        continue # Condition not met

                path_to_parameters_array = path_to_command_obj + ["parameters"]

                if text_type == "choices_array":
                    if len(parameters) > param_idx and isinstance(parameters[param_idx], list):
                        choices = parameters[param_idx]
                        for choice_idx, choice_text in enumerate(choices):
                            if isinstance(choice_text, str) and choice_text.strip():
                                if (param_idx, choice_idx, choice_text) in extracted_texts_for_this_command: continue
                                extracted_texts_for_this_command.add((param_idx, choice_idx, choice_text))

                                sort_keys = (primary_id, page_id_for_sort_and_tsv or 0, cmd_array_idx, code, 1, choice_idx) # 1 for choice
                                tsv_row = {
                                    "primary_id": primary_id, "page_id": page_id_for_sort_and_tsv, 
                                    "cmd_idx": cmd_array_idx, "code": code, "original_text": choice_text
                                }
                                manifest_entry = {
                                    "json_path_to_parameter": get_json_path(path_to_parameters_array + [param_idx, choice_idx]),
                                    "original_text": choice_text, "text_param_index": param_idx,
                                    "is_choice": True, "choice_index": choice_idx, "text_type": "choice_text_option"
                                }
                                extracted_data_list.append((sort_keys, tsv_row, manifest_entry))
                else: # Simple text, message text, scrolling text, actor name, nickname, cancel label
                    if len(parameters) > param_idx and isinstance(parameters[param_idx], str):
                        text = parameters[param_idx]
                        if text.strip():
                            if (param_idx, text) in extracted_texts_for_this_command: continue
                            extracted_texts_for_this_command.add((param_idx, text))
                            
                            sort_sub_key = 0 # Main text
                            if text_type == "choice_cancel_label": sort_sub_key = 2 
                            elif "fallback" in text_type : sort_sub_key = 3 # Ensure fallback is last if others extracted

                            sort_keys = (primary_id, page_id_for_sort_and_tsv or 0, cmd_array_idx, code, sort_sub_key, 0)
                            tsv_row = {
                                "primary_id": primary_id, "page_id": page_id_for_sort_and_tsv,
                                "cmd_idx": cmd_array_idx, "code": code, "original_text": text
                            }
                            manifest_entry = {
                                "json_path_to_parameter": get_json_path(path_to_parameters_array + [param_idx]),
                                "original_text": text, "text_param_index": param_idx,
                                "is_choice": False, "choice_index": None, "text_type": text_type,
                                "is_cancel_branch_label": text_type == "choice_cancel_label"
                            }
                            extracted_data_list.append((sort_keys, tsv_row, manifest_entry))


def extract_texts_from_json_structure(json_data, file_type, top_level_id_num, extracted_data_list):
    if file_type == "map":
        events_data = json_data.get("events")
        if not isinstance(events_data, list): return

        for event_array_idx, event_obj in enumerate(events_data):
            if not event_obj or not isinstance(event_obj, dict): continue
            
            event_id = event_obj.get("id", event_array_idx) # Use actual ID if present, else array index
            for page_array_idx, page_obj in enumerate(event_obj.get("pages", [])):
                if not page_obj or not isinstance(page_obj, dict): continue
                
                page_id_for_sort = page_array_idx + 1 # 1-based for sorting/display
                path_to_page_list = ['events', event_array_idx, 'pages', page_array_idx, 'list']
                process_event_command_list(page_obj.get("list", []), path_to_page_list, extracted_data_list,
                                           file_type, event_id, page_id_for_sort)
    
    elif file_type == "common_event":
        if not isinstance(json_data, list): return

        for ce_array_idx, ce_obj in enumerate(json_data):
            if not ce_obj or not isinstance(ce_obj, dict): continue

            common_event_id = ce_obj.get("id", ce_array_idx) # Use actual ID if present
            path_to_ce_list = [ce_array_idx, 'list']
            process_event_command_list(ce_obj.get("list", []), path_to_ce_list, extracted_data_list,
                                       file_type, common_event_id, None) # No page_id for common events


def write_output_files(basename, sorted_extracted_data, file_type):
    if not sorted_extracted_data:
        print(f"No text extracted for {basename}. No files will be created.")
        return

    tsv_filepath = os.path.join(TEXTOS_DIR, f"{basename}.tsv")
    manifest_filepath = os.path.join(TEXTOS_DIR, f"{basename}_manifest.json")

    tsv_rows_to_write = []
    manifest_entries_to_write = []

    for _, tsv_dict, manifest_dict in sorted_extracted_data:
        manifest_entries_to_write.append(manifest_dict)
        if file_type == "map":
            tsv_rows_to_write.append([
                tsv_dict["primary_id"], tsv_dict["page_id"], tsv_dict["cmd_idx"],
                tsv_dict["code"], tsv_dict["original_text"]
            ])
        else: # common_event
             tsv_rows_to_write.append([
                tsv_dict["primary_id"], tsv_dict["cmd_idx"],
                tsv_dict["code"], tsv_dict["original_text"]
            ])

    # Write TSV
    try:
        with open(tsv_filepath, 'w', newline='', encoding='utf-8') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t')
            if file_type == "map":
                writer.writerow(["event_id", "page_id", "command_idx", "code", "original_text"])
            else: # common_event
                writer.writerow(["common_event_id", "command_idx", "code", "original_text"])
            writer.writerows(tsv_rows_to_write)
        print(f"Successfully wrote TSV to {tsv_filepath}")
    except IOError as e:
        print(f"Error writing TSV file {tsv_filepath}: {e}")

    # Write Manifest
    try:
        with open(manifest_filepath, 'w', encoding='utf-8') as manifestfile:
            json.dump(manifest_entries_to_write, manifestfile, indent=4, ensure_ascii=False)
        print(f"Successfully wrote Manifest to {manifest_filepath}")
    except IOError as e:
        print(f"Error writing Manifest file {manifest_filepath}: {e}")


def process_game_files():
    if not os.path.exists(TEXTOS_DIR):
        os.makedirs(TEXTOS_DIR)
        print(f"Created directory: {TEXTOS_DIR}")

    processed_files_count = 0
    for filename in os.listdir(ORIGINALES_DIR):
        map_match = re.fullmatch(r"Map(\d{3})\.json", filename, re.IGNORECASE)
        is_common_events = (filename.lower() == "commonevents.json")

        if map_match or is_common_events:
            processed_files_count +=1
            print(f"\nProcessing file: {filename}...")
            basename = filename[:-5] # Remove .json
            file_type = "map" if map_match else "common_event"
            
            # For maps, map_id from filename (MapXXX) is usually not the same as event_id inside.
            # The top_level_id passed to recursive functions will be event_id or common_event_id.
            # map_id_from_filename is not directly used as primary_id in processing functions.

            original_filepath = os.path.join(ORIGINALES_DIR, filename)
            try:
                with open(original_filepath, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in {original_filepath}. Skipping file.")
                continue
            except FileNotFoundError:
                print(f"Error: File not found {original_filepath}. Skipping file.")
                continue
            except Exception as e:
                print(f"An unexpected error occurred loading {original_filepath}: {e}")
                continue

            current_file_extracted_data = [] # List of (sort_keys, tsv_row_dict, manifest_entry_dict)
            
            # top_level_id_num is not directly passed here, it's determined inside the next layer
            extract_texts_from_json_structure(json_data, file_type, None, current_file_extracted_data)
            
            # Sort data: primary_id, page_id (or 0), cmd_idx, code, type_prio (main/choice/cancel), choice_idx
            current_file_extracted_data.sort(key=lambda x: x[0])
            
            write_output_files(basename, current_file_extracted_data, file_type)
        
    if processed_files_count == 0:
        print("No MapXXX.json or CommonEvents.json files found in ORIGINALES_DIR.")

if __name__ == "__main__":
    print("Script execution started.")
    process_game_files()
    print("Script finished successfully.")
