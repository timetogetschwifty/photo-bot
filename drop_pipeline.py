"""
Drop Pipeline — split a multi-idea file into prompt files and batch-generate images.

Usage:
    python drop_pipeline.py "testing/Avatar Drop/avatar 10.txt"
    python drop_pipeline.py "testing/Avatar Drop/avatar 10.txt" --split-only
    python drop_pipeline.py "testing/Avatar Drop/avatar 10.txt" --generate-only
    python drop_pipeline.py "testing/Avatar Drop/avatar 10.txt" --force
"""

import argparse
import io
import os
import re
import sys
import time

from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEMINI_MODEL = "gemini-3-pro-image-preview"
SAFETY_SETTINGS = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

TITLE_RE = re.compile(r"Idea\s+(\d+)\s*[—\-–]\s*(.+)", re.IGNORECASE)
PROMPT_RE = re.compile(r"(===PROMPT===.*?===END PROMPT===)", re.DOTALL)


# ── Step 1: Parsing & Splitting ─────────────────────────────────────────────


def parse_ideas(filepath):
    """Parse multi-idea file. Returns list of (number, name, prompt_text)."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on THREE-EM DASH (⸻) or similar long dashes
    chunks = re.split(r"\u2E3B+", content)

    ideas = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        title_match = TITLE_RE.search(chunk)
        if not title_match:
            continue

        number = int(title_match.group(1))
        name = title_match.group(2).strip()

        prompt_match = PROMPT_RE.search(chunk)
        if not prompt_match:
            print(f"  Warning: No ===PROMPT=== block found for Idea {number} — {name}, skipping.")
            continue

        prompt_text = prompt_match.group(1).strip()
        ideas.append((number, name, prompt_text))

    return ideas


def sanitize_name(name):
    """Convert 'LinkedIn Headshot' -> 'LinkedInHeadshot'."""
    # Split on non-alphanumeric, capitalize each part, join
    parts = re.split(r"[^a-zA-Z0-9]+", name)
    return "".join(p.capitalize() for p in parts if p)


def get_folder_label(folder_path):
    """Convert folder name to label: 'Avatar Drop' -> 'AvatarDrop'."""
    folder_name = os.path.basename(folder_path)
    return sanitize_name(folder_name)


def build_filename(number, folder_label, idea_name):
    """Build e.g. 'AvatarDrop_01_LinkedInHeadshot'."""
    return f"{folder_label}_{number:02d}_{sanitize_name(idea_name)}"


def split_ideas(filepath, force=False):
    """Parse and save individual prompt files. Returns list of saved paths."""
    folder = os.path.dirname(os.path.abspath(filepath))
    folder_label = get_folder_label(folder)

    ideas = parse_ideas(filepath)
    if not ideas:
        print("No ideas found in the file.")
        return []

    print(f"Found {len(ideas)} ideas in {os.path.basename(filepath)}")
    print()

    saved = []
    for number, name, prompt_text in ideas:
        base = build_filename(number, folder_label, name)
        out_path = os.path.join(folder, f"{base}.txt")

        if os.path.exists(out_path) and not force:
            print(f"  Exists (skip): {base}.txt")
            saved.append(out_path)
            continue

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(prompt_text + "\n")

        print(f"  Saved: {base}.txt")
        saved.append(out_path)

    print(f"\n{len(saved)} prompt files ready.")
    return saved


# ── Step 2: Batch Generation ────────────────────────────────────────────────


def find_photos(folder):
    """Find test photos in {folder}/photos/ subfolder."""
    photos_dir = os.path.join(folder, "photos")

    if not os.path.isdir(photos_dir):
        print(f"Error: No photos/ subfolder found at {photos_dir}")
        print(f"Create it and add your test photos there.")
        sys.exit(1)

    photos = sorted(
        f
        for f in os.listdir(photos_dir)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
    )

    if not photos:
        print(f"Error: No images found in {photos_dir}")
        print(f"Add .jpg/.png/.webp photos to the photos/ subfolder.")
        sys.exit(1)

    return [os.path.join(photos_dir, p) for p in photos]


def find_prompt_files(folder, folder_label):
    """Find generated prompt files matching FolderLabel_NN_*.txt pattern."""
    pattern = re.compile(rf"^{re.escape(folder_label)}_\d{{2}}_\w+\.txt$")
    files = sorted(
        f for f in os.listdir(folder)
        if pattern.match(f)
    )
    return [os.path.join(folder, f) for f in files]


def load_image(photo_path):
    """Load and resize image (max 1280px), matching test_prompt.py logic."""
    image = Image.open(photo_path)
    max_side = 1280
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.LANCZOS)
    return image


def generate_image(client, prompt, image):
    """Call Gemini API once. Returns PIL Image or None."""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt, image],
        config=types.GenerateContentConfig(
            response_modalities=["Text", "Image"],
            safety_settings=SAFETY_SETTINGS,
        ),
    )

    if not response.parts:
        return None

    for part in response.parts:
        if part.inline_data is not None:
            return Image.open(io.BytesIO(part.inline_data.data))

    return None


def batch_generate(folder, folder_label, force=False):
    """For each prompt file in folder, generate image with photo cycling."""
    photos = find_photos(folder)
    prompt_files = find_prompt_files(folder, folder_label)

    if not prompt_files:
        print("No prompt files found. Run without --generate-only first.")
        return []

    print(f"Found {len(prompt_files)} prompt files and {len(photos)} test photos")
    print(f"Photos: {', '.join(os.path.basename(p) for p in photos)}")
    print()

    # Load .env and create Gemini client
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    if "GEMINI_API_KEY" not in os.environ:
        print("Error: GEMINI_API_KEY not found in .env")
        sys.exit(1)

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    results = []  # list of (base_name, photo_name, status, error_msg)

    try:
        for i, prompt_path in enumerate(prompt_files):
            base_name = os.path.splitext(os.path.basename(prompt_path))[0]
            image_path = os.path.join(folder, f"{base_name}.png")
            photo_path = photos[i % len(photos)]
            photo_name = os.path.basename(photo_path)

            # Skip existing
            if os.path.exists(image_path) and not force:
                print(f"  [{i+1}/{len(prompt_files)}] {base_name} — exists (skip)")
                results.append((base_name, photo_name, "skipped", None))
                continue

            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt = f.read().strip()

            image = load_image(photo_path)

            print(f"  [{i+1}/{len(prompt_files)}] {base_name} + {photo_name} — generating...", end=" ", flush=True)

            success = False
            error_msg = None

            for attempt in range(2):  # max 2 attempts (1 retry)
                try:
                    result_image = generate_image(client, prompt, image)
                    if result_image:
                        result_image.save(image_path, format="PNG")
                        print("OK")
                        results.append((base_name, photo_name, "success", None))
                        success = True
                        break
                    else:
                        error_msg = "No image in response (possible safety block)"
                        print(f"FAILED: {error_msg}")
                        results.append((base_name, photo_name, "failed", error_msg))
                        success = True  # don't retry on empty response (deterministic)
                        break
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {e}"
                    if attempt == 0:
                        print(f"error, retrying in 3s...", end=" ", flush=True)
                        time.sleep(3)
                    else:
                        print(f"FAILED: {error_msg}")
                        results.append((base_name, photo_name, "failed", error_msg))

            if not success and error_msg:
                pass  # already appended in the loop

            # Pause between API calls
            if i < len(prompt_files) - 1:
                time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n  Stopped by user (Ctrl+C)")

    return results


# ── Summary ──────────────────────────────────────────────────────────────────


def print_summary(folder_name, photo_count, results):
    """Print the pipeline summary."""
    success = sum(1 for _, _, s, _ in results if s == "success")
    failed = sum(1 for _, _, s, _ in results if s == "failed")
    skipped = sum(1 for _, _, s, _ in results if s == "skipped")

    print()
    print("══════════════════════════════════════════════════════════")
    print("  Drop Pipeline Summary")
    print("══════════════════════════════════════════════════════════")
    print(f"  Folder:    {folder_name}")
    print(f"  Photos:    {photo_count} test photo(s) (cycling)")
    print(f"  Total:     {len(results)} prompts")
    print(f"  Success:   {success} images generated")
    if failed:
        print(f"  Failed:    {failed}")
    if skipped:
        print(f"  Skipped:   {skipped} (already existed)")
    print("══════════════════════════════════════════════════════════")

    if any(s in ("failed",) for _, _, s, _ in results):
        print("  Failed prompts:")
        for base, photo, status, err in results:
            if status == "failed":
                print(f"    - {base}: {err}")
        print("══════════════════════════════════════════════════════════")

    print(f"\n  {success} out of {len(results)} success")


# ── CLI ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Split prompts and batch-generate images for a drop."
    )
    parser.add_argument("ideas_file", help="Path to the multi-idea txt file")
    parser.add_argument("--split-only", action="store_true", help="Only split, skip generation")
    parser.add_argument("--generate-only", action="store_true", help="Only generate from existing prompt files")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    ideas_path = os.path.abspath(args.ideas_file)
    if not os.path.exists(ideas_path):
        print(f"Error: File not found: {ideas_path}")
        sys.exit(1)

    folder = os.path.dirname(ideas_path)
    folder_label = get_folder_label(folder)
    folder_name = os.path.basename(folder)

    print(f"Drop Pipeline: {folder_name}")
    print(f"Source: {os.path.basename(ideas_path)}")
    print()

    # Step 1: Split
    if not args.generate_only:
        print("── Step 1: Splitting prompts ──────────────────────────────")
        split_ideas(ideas_path, force=args.force)
        print()

    # Step 2: Generate
    if not args.split_only:
        print("── Step 2: Generating images ──────────────────────────────")
        photos = find_photos(folder)
        results = batch_generate(folder, folder_label, force=args.force)
        print_summary(folder_name, len(photos), results)


if __name__ == "__main__":
    main()
