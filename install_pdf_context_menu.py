#!/usr/bin/env python3
"""
install_pdf_context_menu.py — Adds 'Translate PDF to Russian' entry to the
Windows Explorer right-click context menu for .pdf files.

Generates a batch wrapper that activates our venv, then writes registry keys
under HKEY_CURRENT_USER (no admin rights required).

Usage:
    python install_pdf_context_menu.py            # Install
    python install_pdf_context_menu.py --uninstall # Remove entries
"""

import sys
import os
import subprocess
import winreg


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_SCRIPT = os.path.join(SCRIPT_DIR, "pdf_translate.py")
PDF_BATCH = os.path.join(SCRIPT_DIR, "translate_pdf.bat")
VENV_ACTIVATE = os.path.join(SCRIPT_DIR, ".venv\\Scripts\\activate.bat")


def generate_batch():
    """Create a .bat wrapper that activates venv then runs the Python script."""
    content = (
        f'@echo off\r\n'
        f'cd /d "{SCRIPT_DIR}"\r\n'
        f'call "{VENV_ACTIVATE}"\r\n'
        f'python pdf_translate.py "%~1"\r\n'
        f'deactivate\r\n'
    )
    with open(PDF_BATCH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Created {PDF_BATCH}")


def run_cmd(args):
    """Run a command and return success bool."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def get_progid(ext):
    """Resolve the ProgID for a file extension."""
    # 1. Try UserChoice (modern Windows)
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\{ext}\\UserChoice"
        )
        value, _ = winreg.QueryValueEx(key, "ProgId")
        return value
    except FileNotFoundError:
        pass

    # 2. Fallback to HKCU Classes
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}")
        value, _ = winreg.QueryValueEx(key, "")
        return value
    except FileNotFoundError:
        pass

    # 3. Fallback to HKCR
    try:
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ext)
        value, _ = winreg.QueryValueEx(key, "")
        return value
    except FileNotFoundError:
        pass

    raise RuntimeError(f"Could not resolve ProgID for {ext}")


def install():
    print("Installing 'Translate PDF to Russian' context menu entry...\n")

    if not os.path.isfile(PDF_SCRIPT):
        print("Error: pdf_translate.py not found.", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(VENV_ACTIVATE):
        print(f"Error: venv not found at {VENV_ACTIVATE}", file=sys.stderr)
        print("Run create_virtual_environment.bat first.")
        sys.exit(1)

    generate_batch()

    pdf_class = get_progid(".pdf")

    subkey_path = f"Software\\Classes\\{pdf_class}\\shell\\TranslateToRussian"

    try:
        # 1. Create the menu item key
        menu_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, subkey_path)
        winreg.SetValueEx(menu_key, "MUIVerb", 0, winreg.REG_SZ, "Translate PDF to Russian")
        winreg.SetValueEx(menu_key, "", 0, winreg.REG_SZ, "")
        menu_key.Close()

        # 2. Create the required 'command' subkey
        cmd_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{subkey_path}\\command")
        cmd_line = f'"{PDF_BATCH}" "%1"'
        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd_line)
        cmd_key.Close()

        print(f"  [OK] .pdf context menu installed (ProgID: {pdf_class})")
    except Exception as e:
        print(f"  [ERROR] Failed to install: {e}", file=sys.stderr)

    print("\nDone. Right-click a .pdf file -> 'Translate PDF to Russian'.")


def uninstall():
    print("Removing context menu entry...\n")

    try:
        pdf_class = get_progid(".pdf")
        reg_path = f"HKCU\\Software\\Classes\\{pdf_class}\\shell\\TranslateToRussian"

        success, output = run_cmd(["reg", "delete", reg_path, "/f"])
        if success:
            print("  [OK] .pdf context menu removed")
        else:
            if "could not find" in (output or "").lower():
                print("  [OK] .pdf context menu removed (wasn't present)")
            else:
                print(f"  [WARN] Could not remove: {output.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}", file=sys.stderr)

    if os.path.isfile(PDF_BATCH):
        try:
            os.remove(PDF_BATCH)
            print(f"  Removed {PDF_BATCH}")
        except OSError as e:
            print(f"  [WARN] Failed to remove {PDF_BATCH}: {e}", file=sys.stderr)

    print("\nUninstall complete.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall()
    else:
        install()


if __name__ == "__main__":
    main()
