#!/usr/bin/env python3
"""
pdf_translate.py — Translate English PDFs to Russian using googletrans.

Groups text pieces with unique markers, sends translation in batches of
multiple pieces per request (not one-by-one), then unbundles by ID. This
avoids per-paragraph API throttling from Google while staying within
Google's request size limits.

Usage:  source .venv/bin/activate && python3 pdf_translate.py input.pdf [output_ru.pdf]
"""

import sys
import os
import re
import time
import fitz  # PyMuPDF
from googletrans import Translator

# ── Configuration ────────────────────────────────────────────────────────
SRC_LANG = "en"
DST_LANG = "ru"
MARKER_PREFIX = "§TX"   # unlikely to appear in real text / be translated
CHUNK_THRESHOLD = 150   # max chars per chunk before we split
MIN_PIECE_LEN = 10      # skip very short fragments (noise, punctuation)

# ── Helpers ──────────────────────────────────────────────────────────────

def make_marker(index: int) -> str:
    """Return a unique marker like §TX0001§."""
    return f"{MARKER_PREFIX}{index:04d}§"


def extract_text_blocks(doc: fitz.Document) -> list[dict]:
    """Extract text blocks from every page with position metadata.

    Returns a list of dicts:
        {page, block_id, line_idx, bbox, original, marker, fontsize}
    """
    blocks = []
    idx = 0
    for page_num in range(len(doc)):
        page = doc[page_num]
        full = page.get_text("dict")
        for block_idx, block in enumerate(full["blocks"]):
            if block.get("type", 0) != 0:
                continue
            for line_idx, line in enumerate(block.get("lines", [])):
                spans = line.get("spans", [])
                text = " ".join(s["text"] for s in spans)
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) < MIN_PIECE_LEN:
                    continue

                bbox = tuple(line["bbox"])
                # Use max font size across all spans in this line
                fontsize = max((s.get("size", 10) for s in spans), default=10)

                marker = make_marker(idx)
                blocks.append({
                    "page": page_num,
                    "block_idx": block_idx,
                    "line_idx": line_idx,
                    "bbox": bbox,
                    "original": text,
                    "marker": marker,
                    "fontsize": fontsize,
                })
                idx += 1
    return blocks


def build_batch_string(blocks: list[dict]) -> str:
    """Join all pieces into one string wrapped in markers.

        §TX0001§Hello world§TX0002§How are you…
    """
    parts = []
    for b in blocks:
        parts.append(f"{b['marker']}{b['original']}")
    return "\n".join(parts)


def parse_translated(text: str, blocks: list[dict]) -> dict[str, str]:
    """Split translated text back into pieces using markers.

    Returns {marker: translated_text}.
    """
    mapping = {}
    # Build regex that matches any of our markers
    pattern = re.compile(
        r"(§TX\d{4}§)(.*?)(?=§TX\d{4}§|$)",
        re.DOTALL,
    )
    for m in pattern.finditer(text):
        marker = m.group(1)
        translated = m.group(2).strip()
        # Clean up: remove any trailing markers or newlines that leaked through
        translated = re.sub(r"§TX\d{4}§", "", translated).strip()
        mapping[marker] = translated

    return mapping


def translate_batch(translator: Translator, text: str) -> str:
    """Send the entire batch string as one translation request."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = translator.translate(text, src=SRC_LANG, dest=DST_LANG)
            return result.text
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 5
                print(f"  Translation error (retry {attempt+1}/{max_retries}): {e}")
                print(f"  Waiting {wait}s…")
                time.sleep(wait)
            else:
                raise


def replace_text_in_pdf(
    doc: fitz.Document,
    blocks: list[dict],
    mapping: dict[str, str],
):
    """Replace original text with translated text in-place.

    Redacts original English text, then overlays Russian translation using
    a Cyrillic-capable font loaded from the system. Uses pixel-width-based
    word wrapping and iteratively finds the largest fontsize that fits both
    the bbox width AND height constraints.
    """
    from collections import defaultdict

    # Load a system font that supports Cyrillic
    FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        cyrillic_font = fitz.Font(fontfile=FONT_FILE)
    except Exception:
        cyrillic_font = None

    DEFAULT_FONTSIZE = 10
    MIN_FONTSIZE = 2
    LINE_SPACING = 1.05   # tight vertical spacing to fit more lines

    def text_width(text, fontsize):
        """Measure rendered pixel width of text at given fontsize."""
        if cyrillic_font is not None:
            return sum(cyrillic_font.char_lengths(text, fontsize=fontsize))
        return len(text) * fontsize * 0.5

    def wrap_by_pixel_width(text, max_width_px, fontsize):
        """Word-wrap text so each line fits within max_width pixels."""
        words = text.split()
        lines = []
        current_words = []
        current_width = 0.0
        for word in words:
            w = text_width(word, fontsize)
            space_w = text_width(" ", fontsize) if current_words else 0.0
            if current_width + space_w + w > max_width_px and current_words:
                lines.append(" ".join(current_words))
                current_words = [word]
                current_width = w
            else:
                current_words.append(word)
                current_width += space_w + w
        if current_words:
            lines.append(" ".join(current_words))
        return lines

    def fit_text(text, max_width_px, max_height_px, base_size):
        """Compute fontsize and line breaks so text fits the bbox.

        For single-line regions (narrow height) — shrink only, no wrapping.
        For multi-line regions — wrap + shrink until all lines fit vertically.
        """
        SINGLE_LINE_THRESHOLD = 15  # px — bboxes shorter than this are one row

        if max_height_px < SINGLE_LINE_THRESHOLD:
            # Single line: just shrink font to fit width
            w_at_base = text_width(text, base_size)
            if w_at_base <= max_width_px:
                return base_size, [text]
            fs = max(base_size * (max_width_px / w_at_base), MIN_FONTSIZE)
            return fs, [text]

        # Multi-line region: wrap + shrink until height fits
        fs = base_size
        for _ in range(30):
            lines = wrap_by_pixel_width(text, max_width_px, fs)
            total_height = len(lines) * fs * LINE_SPACING
            if total_height <= max_height_px:
                return fs, lines
            fs *= 0.85
            if fs < MIN_FONTSIZE:
                break

        # Last resort: force single line at min size (will overflow but readable)
        w_at_min = text_width(text, MIN_FONTSIZE)
        if w_at_min <= max_width_px:
            return MIN_FONTSIZE, [text]
        # Even one word won't fit — use min size anyway
        return MIN_FONTSIZE, [text]

    pages = defaultdict(list)
    for b in blocks:
        pages[b["page"]].append(b)

    for page_num, page_blocks in pages.items():
        page = doc[page_num]

        # Add redaction annotations for all translated regions
        for b in page_blocks:
            bbox = fitz.Rect(b["bbox"])
            page.add_redact_annot(bbox)

        # Apply redactions — removes original text and fills with white
        page.apply_redactions()

        # Overlay translated text using TextWriter
        tw = fitz.TextWriter(page.rect)
        for b in page_blocks:
            translated = mapping.get(b["marker"], b["original"])
            x0, y0, x1, y1 = b["bbox"]
            max_width = x1 - x0
            max_height = y1 - y0

            # Pre-scale down by ~20% to account for Russian text being wider than English
            orig_sz = b.get("fontsize", DEFAULT_FONTSIZE)
            base_size = min(orig_sz * 0.8, 36)
            fs, lines = fit_text(
                translated, max_width, max_height, base_size
            )
            for i, line in enumerate(lines):
                tw.append(
                    (x0, y0 + i * fs * LINE_SPACING),
                    line,
                    font=cyrillic_font,
                    fontsize=fs,
                )

        tw.write_text(page)


# ── Main ─────────────────────────────────────────────────────────────────

def translate_pdf(input_path: str, output_path: str):
    print(f"Opening {input_path} …")
    doc = fitz.open(input_path)
    print(f"  Pages: {doc.page_count}")

    print("Extracting text blocks …")
    blocks = extract_text_blocks(doc)
    print(f"  Found {len(blocks)} translatable pieces")

    if not blocks:
        print("No text found — nothing to translate.")
        return

    BATCH_SIZE = 20  # pieces per batch — stays within Google's limits

    translator = Translator()
    mapping: dict[str, str] = {}

    total_batches = (len(blocks) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(blocks), BATCH_SIZE):
        chunk = blocks[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"  Batch {batch_num}/{total_batches} ({len(chunk)} pieces) …")

        batch_str = build_batch_string(chunk)
        translated_text = translate_batch(translator, batch_str)

        chunk_mapping = parse_translated(translated_text, chunk)
        mapping.update(chunk_mapping)

        # Brief pause between batches to avoid throttling
        if i + BATCH_SIZE < len(blocks):
            time.sleep(1.5)

    missing = [b["marker"] for b in blocks if b["marker"] not in mapping]
    if missing:
        print(f"  WARNING: {len(missing)} markers not found — keeping originals")

    # Reload original doc for replacement (redact is destructive)
    doc = fitz.open(input_path)
    blocks = extract_text_blocks(doc)  # re-extract on clean copy

    print("Replacing text in document …")
    replace_text_in_pdf(doc, blocks, mapping)

    print(f"Saving to {output_path} …")
    doc.save(output_path)
    doc.close()
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.pdf> [output.pdf]")
        print("  If output is omitted, input name gets '_ru' suffix.")
        sys.exit(1)

    input_path = sys.argv[1]
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_ru{ext}"

    translate_pdf(input_path, output_path)
