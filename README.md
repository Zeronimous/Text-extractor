# RPGMaker JSON Translation Tools

This repository contains two Python scripts to help with translating text in RPGMaker MV/MZ JSON files.

## Features

*   `extractor.py`: Extracts text from game data files into `.txt` files for easy translation.
*   `inserter.py`: Inserts translated text from `.txt` files back into new JSON game data files.

## Requirements

*   Python 3.x

## Folder Structure

The scripts expect the following folder structure in the root of the repository:

*   `Originales/`: Place your original game's `.json` files (e.g., `Map001.json`, `Items.json`) here.
*   `Textos/`:
    *   This folder will be automatically created by `extractor.py`.
    *   It will contain `.txt` files with the extracted text, one for each processed JSON file.
    *   It will also contain `extraction_manifest.json`, which is used by the scripts to track text locations. **Do not edit this manifest file manually unless you know what you are doing.**
*   `Traducidos/`:
    *   This folder will be automatically created by `inserter.py`.
    *   It will contain the new `.json` files with the translated text.

## Workflow

1.  **Prepare Original Files:**
    *   Create the `Originales` folder.
    *   Copy all the `.json` files you want to translate from your RPGMaker project's `data` folder into the `Originales` folder.

2.  **Extract Text:**
    *   Run the `extractor.py` script from the root of the repository:
        ```bash
        python extractor.py
        ```
    *   This will populate the `Textos` folder with `.txt` files containing the game's text and an `extraction_manifest.json`.

3.  **Translate Text:**
    *   Open the `.txt` files located in the `Textos` folder.
    *   Each line will be in the format: `[lineaX] Original Text` (e.g., `[linea1] Hello world!`).
    *   Edit these files by replacing the original text with your translation, keeping the line number and bracketed format: `[lineaX] Translated Text` (e.g., `[linea1] ¡Hola mundo!`).
    *   **Important for game codes:** If the original text contains special RPGMaker codes (like `\C[1]`, `\N[2]`, `\.`), make sure to preserve these codes exactly as they are in your translated string. For example, if the original is `[linea1] Press \C[2]OK\C[0] to continue.`, your translation might be `[linea1] Pulse \C[2]OK\C[0] para continuar.`. The scripts replace the entire string.

4.  **Insert Translations:**
    *   Once you have translated the `.txt` files, run the `inserter.py` script from the root of the repository:
        ```bash
        python inserter.py
        ```
    *   This will read your translated `.txt` files and the manifest, then create new translated `.json` files in the `Traducidos` folder.

5.  **Use Translated Files:**
    *   The `.json` files in the `Traducidos` folder can now be used to replace the original files in your game project's `data` folder. **Always back up your original game data first!**

## Notes

*   The scripts attempt to handle various text locations within RPGMaker JSON files, including item names, descriptions, and text within event commands (Show Text, Show Choices, Scrolling Text).
*   If you encounter any issues or have suggestions, please report them.
