# RPGMaker JSON Translation Tools

This repository contains two Python scripts to help with translating text in RPGMaker MV/MZ JSON files using a JSON-array-based workflow.

## Features

*   `extractor.py`: Extracts all translatable text strings from your game data files into a single JSON file (`extracted_texts.json`) for easy translation. It also creates a manifest file to track the origin of each text.
*   `inserter.py`: Inserts translated text strings from the modified `extracted_texts.json` file back into new JSON game data files, using the manifest to ensure correct placement.

## Requirements

*   Python 3.x

## Folder Structure

The scripts expect the following folder structure in the root of the repository:

*   `Originales/`: Place your original game's `.json` files (e.g., `Map001.json`, `Items.json`, `CommonEvents.json`) here.
*   `Textos/`:
    *   This folder will be automatically created by `extractor.py`. It will contain:
        *   `extracted_texts.json`: A single JSON file containing an array of all text strings extracted from your game files, in a deterministic (alphabetical by original filename, then by order of appearance) order. **This is the file you will edit to add translations.**
        *   `extraction_manifest.json`: A JSON file used by the scripts to map each text string in `extracted_texts.json` (by its array index) back to its original location (file and path within the file). **Do not edit this manifest file manually unless you know what you are doing.**
*   `Traducidos/`:
    *   This folder will be automatically created by `inserter.py`.
    *   It will contain the new `.json` files with the translated text, mirroring the structure of your `Originales/` directory.

## Workflow

1.  **Prepare Original Files:**
    *   Create the `Originales/` folder if it doesn't exist.
    *   Copy all the `.json` files you want to translate from your RPGMaker project's `data` folder (or relevant subfolders) into the `Originales/` folder.

2.  **Extract Text:**
    *   Run the `extractor.py` script from the root of the repository:
        ```bash
        python extractor.py
        ```
    *   This will populate the `Textos/` folder with two files:
        *   `extracted_texts.json`: Contains a JSON array of all translatable strings found in your original files.
        *   `extraction_manifest.json`: The manifest file linking these strings (by their array index) to their origins.

3.  **Translate Text:**
    *   Open `Textos/extracted_texts.json` with a text editor that handles JSON well (e.g., VS Code, Sublime Text, Notepad++) or a specialized JSON editor.
    *   This file contains a single JSON array. Each string in this array is a piece of text from your game.
    *   **Example `extracted_texts.json`:**
        ```json
        [
            "Hello, world!",
            "This is a game.",
            "Another message with \\C[1]color\\C[0]."
        ]
        ```
    *   To translate, directly edit the strings within this array:
        ```json
        [
            "¡Hola, mundo!",
            "Este es un juego.",
            "Otro mensaje con \\C[1]color\\C[0]."
        ]
        ```
    *   **Crucial:** You MUST preserve the order and number of strings in this array. Each string's position (index) is vital for placing the translation back correctly. Do not add, remove, or reorder strings within the array.
    *   **Important for game codes:** If an original string contains special RPGMaker codes (like `\C[1]`, `\N[2]`, `\.`, etc.), make sure to preserve these codes exactly as they are within your translated string. The scripts replace the entire string.

4.  **Insert Translations:**
    *   Once you have translated the strings in `Textos/extracted_texts.json`, run the `inserter.py` script from the root of the repository:
        ```bash
        python inserter.py
        ```
    *   This will read your translated array from `Textos/extracted_texts.json` and use `Textos/extraction_manifest.json` to create new translated `.json` files in the `Traducidos/` folder.

5.  **Use Translated Files:**
    *   The `.json` files in the `Traducidos/` folder can now be used to replace the original files in your game project's `data` folder. **Always back up your original game data first!**

## Notes

*   The scripts attempt to handle various text locations within RPGMaker JSON files, including item names, descriptions, and text within event commands (Show Text, Show Choices, Scrolling Text).
*   The order of texts in `extracted_texts.json` is deterministic: files in `Originales/` are processed alphabetically, and texts within each file are extracted in the order they appear.
*   If you encounter any issues or have suggestions, please report them.
