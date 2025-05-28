# RPGMaker JSON Translation Tools

This repository contains two Python scripts to help with translating text in RPGMaker MV/MZ JSON files, supporting a mix of direct string and in-object translations.

## Features

*   `extractor.py`: Extracts translatable items from your game data files into a single JSON file (`extracted_text_objects.json`). These items can be either complete JSON objects (like game event commands) or simple JSON strings (like item names). It also creates a manifest file (`extraction_manifest.json`) to track the origin and type of each item.
*   `inserter.py`: Inserts translated items from the modified `extracted_text_objects.json` file back into new JSON game data files, using the manifest to ensure correct placement and handling based on item type.

## Requirements

*   Python 3.x

## Folder Structure

The scripts expect the following folder structure in the root of the repository:

*   `Originales/`: Place your original game's `.json` files (e.g., `Map001.json`, `Items.json`, `CommonEvents.json`) here.
*   `Textos/`:
    *   This folder will be automatically created by `extractor.py`. It will contain:
        *   `extracted_text_objects.json`: A single JSON file containing an array of items to be translated. **These items can be either complete JSON objects (like game event commands) or simple JSON strings (like item names or descriptions).** This is the primary file you will edit.
        *   `extraction_manifest.json`: A JSON file used by the scripts to map each item in `extracted_text_objects.json` (by its array index) back to its original location (file and path within the file). It also contains a `type` field (e.g., `event_command_object` or `string_value`) for each entry, indicating how the corresponding item in `extracted_text_objects.json` should be treated. **Do not edit this manifest file manually unless you know what you are doing.**
*   `Traducidos/`:
    *   This folder will be automatically created by `inserter.py`.
    *   It will contain the new `.json` files with the translated text, mirroring the structure of your `Originales/` directory.

## Workflow

1.  **Prepare Original Files:**
    *   Create the `Originales/` folder if it doesn't exist.
    *   Copy all the `.json` files you want to translate from your RPGMaker project's `data` folder (or relevant subfolders) into the `Originales/` folder.

2.  **Extract Text Objects and Strings:**
    *   Run the `extractor.py` script from the root of the repository:
        ```bash
        python extractor.py
        ```
    *   This will populate the `Textos/` folder with two files:
        *   `extracted_text_objects.json`: Contains a JSON array of all translatable items (objects or strings).
        *   `extraction_manifest.json`: The manifest file linking these items to their origins and specifying their type.

3.  **Translate Text Items:**
    *   Open `Textos/extracted_text_objects.json` with a text editor that handles JSON well (e.g., VS Code, Sublime Text, Notepad++) or a specialized JSON editor.
    *   This file contains a JSON array of mixed items. Each item is either a complete JSON object (usually an event command from the game) or a simple JSON string (like a name or description).

    **How to Translate:**

    *   **If the item is a JSON string (e.g., a name):**
        This is common for item names, descriptions, skill names, etc. The manifest type for these is typically `string_value`.
        ```json
        // Example item in extracted_text_objects.json:
        "Potion" 
        // Translate it directly by replacing the string:
        "Poción"
        ```

    *   **If the item is a JSON object (e.g., an event command):**
        This is common for dialog, choices, scrolling text, etc. The manifest type for these is typically `event_command_object` or similar.
        ```json
        // Example item in extracted_text_objects.json:
        {
            "code": 401,
            "indent": 0,
            "parameters": [
                "Hello, adventurer!"
            ]
        }
        // You need to find the text within this object and translate it IN PLACE:
        {
            "code": 401,
            "indent": 0,
            "parameters": [
                "¡Hola, aventurero!"
            ]
        }
        ```
        Common places for text in event commands are within the `parameters` array:
        *   **Show Text (code 401):** Text is typically `parameters[0]`.
        *   **Show Text (code 101, with face/speaker):** Text can be in `parameters[4]` or `parameters[5]` depending on RPGMaker version and if a speaker name is used. You'll need to identify the correct string.
        *   **Show Choices (code 102):** `parameters[0]` is an array of choice strings, e.g., `["Yes", "No"]`. Translate each string in that inner array.
        *   **Show Scrolling Text (code 105):** Text is typically `parameters[0]`.
        *   Other commands like changing actor names (code 320), nicknames (code 324), or profiles (code 325) will have text in `parameters[1]`.

        **Crucially, when editing an object, only change the text values. Do NOT alter the object's structure (keys like `code`, `indent`), numerical values, boolean flags, or the order of parameters unless you are certain of the effect on the game engine.** Modifying the structure can easily lead to game errors.

    **General Rules for Translation:**
    *   You MUST preserve the order and number of items in the main `extracted_text_objects.json` array. Each item's position (index) is vital for placing the translation back correctly. Do not add, remove, or reorder items within the main array.
    *   If an original string (whether standalone or within an object) contains special RPGMaker codes (like `\C[1]`, `\N[2]`, `\.`), preserve these codes in your translation.
    *   The `extraction_manifest.json` contains a `type` field for each entry, which helps the `inserter.py` script understand whether to replace a whole object or just a string value at a specific path. You don't typically need to interact with the manifest, but it explains why `extracted_text_objects.json` has mixed types and how the inserter works.

4.  **Insert Translations:**
    *   Once you have translated the items in `Textos/extracted_text_objects.json`, run the `inserter.py` script from the root of the repository:
        ```bash
        python inserter.py
        ```
    *   This will read your translated items from `Textos/extracted_text_objects.json` and use `Textos/extraction_manifest.json` to create new translated `.json` files in the `Traducidos/` folder.

5.  **Use Translated Files:**
    *   The `.json` files in the `Traducidos/` folder can now be used to replace the original files in your game project's `data` folder. **Always back up your original game data first!**

## Notes

*   The scripts attempt to handle various text locations and structures within RPGMaker JSON files.
*   The order of items in `extracted_text_objects.json` is deterministic: files in `Originales/` are processed alphabetically, and items within each file are extracted based on the script's traversal order.
*   If you encounter any issues or have suggestions, please report them.
