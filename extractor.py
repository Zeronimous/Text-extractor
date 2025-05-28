import os
import json
import copy

# Define constants for folder names
ORIGINALES_DIR = "Originales"
TEXTOS_DIR = "Textos"

# Event codes for which the entire command object should be extracted
# 101: Show Text (params[4] or params[5] is text depending on speaker)
# 401: Show Text (params[0] is text)
# 102: Show Choices (params[0] is a list of choice strings)
# 402: Show Choices Cancel option (params[1] can be custom cancel text if params[0] is type 'branch')
# 105: Show Scrolling Text (params[0] is text)
# 108: Comment (params[0] is comment text)
# 408: Comment (continuation) (params[0] is comment text)
# 320: Change Actor Name (params[1] is name)
# 324: Change Actor Nickname (params[1] is nickname)
# 325: Change Actor Profile (params[1] is profile text)
# System strings:
# gameTitle, terms.messages (various), terms.commands (various), terms.basic (various)
# armors.name, armors.description
# items.name, items.description
# weapons.name, weapons.description
# skills.name, skills.description, skills.message1, skills.message2
# states.name, states.message1, states.message2, states.message3, states.message4
# mapInfos.name (for map display names)
# troops.name (for troop names, although usually not shown to player)
# animations.name

EVENT_CODES_FOR_OBJECT_EXTRACTION = {
    101, 401, 102, 105, 108, 408, 320, 324, 325
}
# Code 402 is handled specially as its text parameter depends on another parameter.

def get_json_path(context_stack):
    if not context_stack:
        return ""
    path_str = str(context_stack[0])
    for item in context_stack[1:]:
        if isinstance(item, int):
            path_str += f"[{item}]"
        else:
            path_str += f".{item}"
    return path_str

def is_valid_text_event(data_dict):
    """
    Heuristic to check if an event command object likely contains translatable text.
    This is a simplified check.
    """
    code = data_dict.get("code")
    parameters = data_dict.get("parameters")
    if not isinstance(parameters, list): return False

    if code == 101: # Show Text (complex)
        # Text is often params[4] if speaker is used, or params[5] if new RPGMaker MV/MZ format for speaker name
        # Or if parameters are ["", 0, 0, X, "Text"], text is params[4]
        # This heuristic is tricky. Let's assume if it's 101, it's likely a text object.
        return True # Broadly accept 101
    if code == 401 and len(parameters) > 0 and isinstance(parameters[0], str): # Show Text (simple)
        return True
    if code == 102 and len(parameters) > 0 and isinstance(parameters[0], list): # Show Choices
        return True # The choices themselves are strings in parameters[0]
    if code == 105 and len(parameters) > 0 and isinstance(parameters[0], str): # Scrolling Text
        return True
    if code in (108, 408) and len(parameters) > 0 and isinstance(parameters[0], str): # Comment
        return True
    if code == 320 and len(parameters) > 1 and isinstance(parameters[1], str): # Change Actor Name
        return True
    if code == 324 and len(parameters) > 1 and isinstance(parameters[1], str): # Change Actor Nickname
        return True
    if code == 325 and len(parameters) > 1 and isinstance(parameters[1], str): # Change Actor Profile
        return True
    return False


def find_extractable_items_recursive(data, current_path_stack, original_filename_str,
                                     global_items_list, global_manifest_dict, global_index_list):
    if isinstance(data, dict):
        # Rule 1: Event Command Object Extraction
        current_code = data.get("code")
        if current_code in EVENT_CODES_FOR_OBJECT_EXTRACTION and is_valid_text_event(data):
            global_items_list.append(copy.deepcopy(data))
            global_manifest_dict[str(global_index_list[0])] = {
                "original_file": original_filename_str,
                "json_path": get_json_path(current_path_stack),
                "type": "event_command_object",
                "original_object_preview": str(data.get("parameters", ""))[:150]
            }
            global_index_list[0] += 1
            return # Stop recursion for this branch

        # Special handling for code 402 (Show Choices - Cancel)
        # Parameter index 0: choice index for cancel type (0-3 for choice, 4 for branch, 5 for disallow)
        # Parameter index 1: custom cancel text if cancel type is 'branch' (index 4)
        if current_code == 402:
            params = data.get("parameters", [])
            if len(params) >= 2 and params[0] == 4 and isinstance(params[1], str) and params[1].strip():
                 # Extract the whole command object if it has custom cancel text for branch
                global_items_list.append(copy.deepcopy(data))
                global_manifest_dict[str(global_index_list[0])] = {
                    "original_file": original_filename_str,
                    "json_path": get_json_path(current_path_stack),
                    "type": "event_command_object_cancel_choice", # Specific type
                    "original_object_preview": str(data.get("parameters", ""))[:150]
                }
                global_index_list[0] += 1
                return # Stop recursion

        # Rule 2: Name/Description String Value Extraction & General Recursion
        for key, value in data.items():
            current_path_stack.append(key)
            if key in ("name", "description", "message1", "message2", "message3", "message4", "profile", "text", "title", "nickname", "message") and \
               isinstance(value, str) and value.strip():
                # Check if the parent is an event command that would have been extracted
                # This prevents extracting text from already extracted command objects.
                # This check is basic. A more robust way would be to pass a flag if parent was extracted.
                # However, since we return early for extracted event commands, this check is mostly for safety.
                
                # A more targeted approach for specific system strings:
                is_system_terms_message = "terms" in current_path_stack and "messages" in current_path_stack
                
                if not (current_path_stack[-2] == "parameters" and data.get("code") in EVENT_CODES_FOR_OBJECT_EXTRACTION): # Avoid re-extracting from params of already handled events
                    global_items_list.append(value) # Append the string value
                    global_manifest_dict[str(global_index_list[0])] = {
                        "original_file": original_filename_str,
                        "json_path": get_json_path(current_path_stack),
                        "type": "string_value",
                        "original_object_preview": value[:150]
                    }
                    global_index_list[0] += 1
                # Continue recursion for the value even if we extracted the string,
                # unless the value is not a dict or list.
                if isinstance(value, (dict, list)):
                     find_extractable_items_recursive(value, current_path_stack, original_filename_str,
                                                 global_items_list, global_manifest_dict, global_index_list)
            elif key == "list" and isinstance(value, list) and "events" in current_path_stack: # Common structure for event lists
                # Recursively process items in an event list
                 for index_in_list, item_in_list in enumerate(value):
                    current_path_stack.append(index_in_list)
                    find_extractable_items_recursive(item_in_list, current_path_stack, original_filename_str,
                                                     global_items_list, global_manifest_dict, global_index_list)
                    current_path_stack.pop()
            elif isinstance(value, (dict, list)): # General recursion for other dicts/lists
                 find_extractable_items_recursive(value, current_path_stack, original_filename_str,
                                                 global_items_list, global_manifest_dict, global_index_list)
            current_path_stack.pop()

    elif isinstance(data, list):
        for index, item in enumerate(data):
            current_path_stack.append(index)
            find_extractable_items_recursive(item, current_path_stack, original_filename_str,
                                             global_items_list, global_manifest_dict, global_index_list)
            current_path_stack.pop()

def extract_objects_globally():
    if not os.path.exists(TEXTOS_DIR):
        os.makedirs(TEXTOS_DIR)
        print(f"Created directory: {TEXTOS_DIR}")

    all_extracted_items = []
    manifest_data = {}
    global_item_index_list = [0]

    json_files = sorted([f for f in os.listdir(ORIGINALES_DIR) if f.endswith(".json")])

    if not json_files:
        print(f"No JSON files found in {ORIGINALES_DIR}. Nothing to process.")
        # Create empty files
        output_objects_filepath = os.path.join(TEXTOS_DIR, "extracted_text_objects.json")
        output_manifest_filepath = os.path.join(TEXTOS_DIR, "extraction_manifest.json")
        try:
            with open(output_objects_filepath, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            print(f"Saved empty list to {output_objects_filepath}")
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
        except FileNotFoundError:
            print(f"Error: File not found {original_filepath}. Skipping file.")
            continue
        
        find_extractable_items_recursive(json_content, [], filename,
                                         all_extracted_items, manifest_data, global_item_index_list)

    output_objects_filepath = os.path.join(TEXTOS_DIR, "extracted_text_objects.json")
    try:
        with open(output_objects_filepath, 'w', encoding='utf-8') as f:
            json.dump(all_extracted_items, f, ensure_ascii=False, indent=4)
        print(f"All extracted items saved to {output_objects_filepath}")
    except IOError:
        print(f"Error: Could not write extracted items to {output_objects_filepath}")
    except TypeError as e: # For potential non-serializable data if deepcopy fails or other issues
        print(f"Error: Could not serialize extracted items to JSON. {e}")


    output_manifest_filepath = os.path.join(TEXTOS_DIR, "extraction_manifest.json")
    try:
        with open(output_manifest_filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=4)
        print(f"Extraction manifest saved to {output_manifest_filepath}")
    except IOError:
        print(f"Error: Could not write manifest file to {output_manifest_filepath}")

if __name__ == "__main__":
    print("Script execution started.")
    extract_objects_globally()
    print("Script finished successfully.")
