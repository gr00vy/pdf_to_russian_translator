# PDF Translator — English to Russian

Translate **any** PDF document from English to Russian with a single click in Windows Explorer or one command on Linux/macOS. Preserves original layout and formatting as closely as possible.

## Features

- **Batch translation** — groups multiple text pieces into each API request, avoiding Google's per-request throttling
- **Smart font sizing** — detects original font size (titles stay big), then shrinks only when Russian text is wider than the English original
- **Pixel-aware wrapping** — measures actual rendered width of Cyrillic characters to avoid text spilling into adjacent lines
- **No API key needed** — uses `googletrans` (free Google Translate)

---

## Prerequisites: Install Python

### Windows

1. Download Python 3.9 or later from <https://www.python.org/downloads/>
2. Run the installer
3. **Important:** Check the box **"Add Python to PATH"** on the first screen — this is required for everything to work
4. Click "Install Now" and wait for it to finish

To verify installation, open Command Prompt (`Win + R` → type `cmd`) and run:
```
python --version
```
You should see something like `Python 3.9.x` or higher.

### Linux / macOS

Most systems already have Python installed. Check with:
```bash
python3 --version
```
If you need to install it:

- **Ubuntu/Debian:** `sudo apt update && sudo apt install python3 python3-venv`
- **Fedora/RHEL:** `sudo dnf install python3`
- **macOS (Homebrew):** `brew install python`

---

## Quick Start

### Windows

1. **Install dependencies:** Double-click `create_virtual_environment.bat` — a window will open, wait for it to finish
2. **Run on a file:** Double-click `pdf_translate.bat`, then type the path to your PDF (or drag-and-drop the file)
3. *(Optional)* Add right-click menu: Double-click `install_pdf_context_menu.bat` — after this you can right-click any `.pdf` → **"Translate PDF to Russian"**

### Linux / macOS

1. **Install dependencies:** Run `bash create_virtual_environment.sh`
2. **Run on a file:** `./pdf_translate.sh your_document.pdf`
3. Output will be saved as `your_document_ru.pdf` (or specify custom name: `./pdf_translate.sh input.pdf output.pdf`)

---

## Uninstall Context Menu (Windows)

If you installed the right-click menu and want to remove it, double-click **`uninstall_pdf_context_menu.bat`**. This removes the "Translate PDF to Russian" entry from Windows Explorer. No files are deleted — only registry entries are cleaned up.

---

## Output Naming

If you provide only one argument (the input file), the output gets an `_ru` suffix:

```
input.pdf          →  input_ru.pdf
my_report.pdf      →  my_report_ru.pdf
```

You can also specify a custom output name:
```bash
python pdf_translate.py input.pdf translated_output.pdf
```

---

## How It Works

1. Extracts all text from the PDF along with position and font size metadata
2. Groups pieces into batches of ~20, wraps each in a unique marker (`§TX0001§Hello world`)
3. Sends each batch as **one** translation request to Google Translate
4. Unbundles translated response by marker ID
5. Redacts original English text and overlays Russian translation at the same position with adjusted font size

## Requirements

- Python 3.9+ (see installation instructions above)
- All other dependencies are installed automatically into a local `.venv` — no system-wide changes needed
