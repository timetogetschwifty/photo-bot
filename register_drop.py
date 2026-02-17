"""
Register Drop — add a completed drop's effects to effects.yaml.

Reads the original ideas file, extracts tips (Menu description RU),
prompts you for labels, then appends to effects.yaml and copies files.

Usage:
    python register_drop.py "testing/Avatar Drop/avatar 10.txt"
    python register_drop.py "testing/Avatar Drop/avatar 10.txt" --dry-run
    python register_drop.py "testing/Avatar Drop/avatar 10.txt" --enabled false
"""

import argparse
import os
import re
import shutil
import sys

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EFFECTS_YAML = os.path.join(BASE_DIR, "effects.yaml")
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
IMAGES_DIR = os.path.join(BASE_DIR, "images")

TITLE_RE = re.compile(r"=+\s*IDEA\s+(\d+)\s*:\s*(.+?)\s*=+", re.IGNORECASE)
MENU_DESC_RE = re.compile(r"Menu description \(RU\):\s*(.+)")
BEST_INPUT_RE = re.compile(r"Best input \(RU\):\s*\n((?:\s*•.*\n?)+)", re.MULTILINE)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def normalize_quotes(text):
    """Replace curly quotes with straight quotes to avoid IDE warnings."""
    replacements = {
        '"': '"',  # Left double quote
        '"': '"',  # Right double quote
        ''': "'",  # Left single quote
        ''': "'",  # Right single quote
    }
    for curly, straight in replacements.items():
        text = text.replace(curly, straight)
    return text


def parse_ideas_with_tips(filepath):
    """Parse ideas file, return list of (number, name, menu_description, best_input)."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all idea headers, then extract chunks between them
    title_matches = list(TITLE_RE.finditer(content))
    ideas = []

    for i, title_match in enumerate(title_matches):
        number = int(title_match.group(1))
        name = title_match.group(2).strip()

        # Chunk runs from this title to the next title (or end of file)
        start = title_match.start()
        end = title_matches[i + 1].start() if i + 1 < len(title_matches) else len(content)
        chunk = content[start:end]

        menu_match = MENU_DESC_RE.search(chunk)
        tips = normalize_quotes(menu_match.group(1).strip()) if menu_match else ""

        # Extract best_input bullets
        best_input_match = BEST_INPUT_RE.search(chunk)
        if best_input_match:
            # Extract bullet points and join them with newline
            bullets = best_input_match.group(1).strip()
            # Clean up: remove bullet points and extra whitespace
            best_input = bullets.replace("•", "").strip()
            # Join multiple lines into one, separated by semicolons for readability
            best_input = "; ".join(line.strip() for line in best_input.split("\n") if line.strip())
            best_input = normalize_quotes(best_input)
        else:
            best_input = ""

        ideas.append((number, name, tips, best_input))

    return ideas


def sanitize_name(name):
    """Convert 'LinkedIn Headshot Studio' -> 'LinkedInHeadshotStudio' (first 3 words only)."""
    parts = re.split(r"[^a-zA-Z0-9]+", name)
    # Take only first 3 words to keep filenames short
    parts = [p for p in parts if p][:3]
    return "".join(p.capitalize() for p in parts)


def get_folder_label(folder_path):
    """Convert folder name: 'Avatar Drop' -> 'AvatarDrop'."""
    return sanitize_name(os.path.basename(folder_path))


def build_effect_id(number, folder_label, idea_name):
    """Build effect_id matching drop_pipeline naming: AvatarDrop_01_LinkedinHeadshot."""
    return f"{folder_label}_{number:02d}_{sanitize_name(idea_name)}"


def get_max_order(yaml_data):
    """Find the highest order number in existing effects."""
    max_order = 0
    effects = yaml_data.get("effects") or {}
    for effect in effects.values():
        if isinstance(effect, dict):
            order = effect.get("order", 0)
            if order > max_order:
                max_order = order
    return max_order


def find_drop_files(folder, folder_label):
    """Find prompt .txt and .png files from the drop."""
    pattern = re.compile(rf"^{re.escape(folder_label)}_\d{{2}}_\w+\.(txt|png)$")
    files = {}
    for f in os.listdir(folder):
        if pattern.match(f):
            base = os.path.splitext(f)[0]
            ext = os.path.splitext(f)[1]
            if base not in files:
                files[base] = {}
            files[base][ext] = os.path.join(folder, f)
    return files


def main():
    parser = argparse.ArgumentParser(description="Register drop effects into effects.yaml")
    parser.add_argument("ideas_file", help="Path to the original ideas txt file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying files")
    parser.add_argument("--enabled", default="true", choices=["true", "false"],
                        help="Register effects as enabled or disabled (default: true)")
    args = parser.parse_args()

    ideas_path = os.path.abspath(args.ideas_file)
    if not os.path.exists(ideas_path):
        print(f"Error: File not found: {ideas_path}")
        sys.exit(1)

    folder = os.path.dirname(ideas_path)
    folder_label = get_folder_label(folder)
    folder_name = os.path.basename(folder)
    category = folder_name.split()[0].lower()
    enabled = args.enabled == "true"

    # Parse ideas for tips
    ideas = parse_ideas_with_tips(ideas_path)
    if not ideas:
        print("No ideas found in file.")
        sys.exit(1)

    # Find existing drop files
    drop_files = find_drop_files(folder, folder_label)

    # Load current effects.yaml
    with open(EFFECTS_YAML, "r", encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    max_order = get_max_order(yaml_data)

    # Build effect entries and collect labels interactively
    print(f"\nRegister Drop: {folder_name} ({len(ideas)} effects)")
    print(f"Category: {category}")
    print(f"Enabled: {enabled}")
    print()

    effects_to_add = []

    for i, (number, name, tips, best_input) in enumerate(ideas):
        effect_id = build_effect_id(number, folder_label, name)
        order = i + 1  # each drop/category starts from 1

        # Check if already registered
        if yaml_data.get("effects") and effect_id in yaml_data["effects"]:
            print(f"  {number}) {effect_id} — already in YAML, skipping")
            continue

        print(f"  {number}) {effect_id}")
        print(f"     Tips: {tips}")
        if best_input:
            print(f"     Best input: {best_input[:60]}...")

        label = input(f"     Label: ").strip()
        if not label:
            label = name
            print(f"     (using default: {label})")

        has_txt = effect_id in drop_files and ".txt" in drop_files[effect_id]
        has_png = effect_id in drop_files and ".png" in drop_files[effect_id]

        effects_to_add.append({
            "effect_id": effect_id,
            "order": order,
            "label": label,
            "tips": tips,
            "best_input": best_input,
            "category": category,
            "enabled": enabled,
            "has_txt": has_txt,
            "has_png": has_png,
            "txt_src": drop_files.get(effect_id, {}).get(".txt"),
            "png_src": drop_files.get(effect_id, {}).get(".png"),
        })
        print()

    if not effects_to_add:
        print("Nothing to register.")
        return

    # Preview
    print("\n══════════════════════════════════════════════════════════")
    print("  Preview")
    print("══════════════════════════════════════════════════════════")
    for e in effects_to_add:
        status = []
        if e["has_txt"]:
            status.append("txt")
        else:
            status.append("NO txt")
        if e["has_png"]:
            status.append("png")
        else:
            status.append("no png")
        print(f"  {e['effect_id']}")
        print(f"    label: {e['label']}")
        print(f"    tips:  {e['tips'][:60]}...")
        print(f"    order: {e['order']}  files: {', '.join(status)}")
    print("══════════════════════════════════════════════════════════")

    if args.dry_run:
        print("\n  --dry-run: No files modified.")
        return

    confirm = input("\nConfirm? [y/n]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    # Execute: copy files and update YAML
    print()

    with open(EFFECTS_YAML, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if category needs to be added
    need_new_category = not yaml_data.get("categories") or category not in yaml_data["categories"]
    if need_new_category:
        cat_order = len(yaml_data.get("categories") or {}) + 1
        cat_block = (
            f"\n  {category}:\n"
            f"    enabled: false\n"
            f"    order: {cat_order}\n"
            f'    label: "{folder_name}"\n'
        )
        # Insert before "# ── Effects" line
        effects_marker = "# ── Effects"
        if effects_marker in content:
            pos = content.index(effects_marker)
            content = content[:pos] + cat_block + "\n" + content[pos:]
        print(f"  Created category: {category} (enabled: false — enable manually)")

    # Copy files and build YAML block
    yaml_lines = [f"\n  # ── {folder_name} ──"]

    for e in effects_to_add:
        eid = e["effect_id"]

        # Copy prompt txt
        if e["has_txt"]:
            dst = os.path.join(PROMPTS_DIR, f"{eid}.txt")
            shutil.copy2(e["txt_src"], dst)
            print(f"  Copied: prompts/{eid}.txt")

        # Copy image png
        if e["has_png"]:
            dst = os.path.join(IMAGES_DIR, f"{eid}.png")
            shutil.copy2(e["png_src"], dst)
            print(f"  Copied: images/{eid}.png")

        # Build YAML entry
        tips_escaped = e["tips"].replace('"', '\\"')
        best_input_escaped = e["best_input"].replace('"', '\\"')
        yaml_lines.append(f"  {eid}:")
        yaml_lines.append(f"    enabled: {'true' if e['enabled'] else 'false'}")
        yaml_lines.append(f"    order: {e['order']}")
        yaml_lines.append(f'    label: "{e["label"]}"')
        yaml_lines.append(f'    tips: "{tips_escaped}"')
        yaml_lines.append(f'    best_input: "{best_input_escaped}"')
        yaml_lines.append(f"    category: {e['category']}")
        yaml_lines.append("")

    # Insert effects before the TEMPLATES comment
    templates_marker = "# ── TEMPLATES"
    effects_block = "\n".join(yaml_lines) + "\n"
    if templates_marker in content:
        insert_pos = content.index(templates_marker)
        content = content[:insert_pos] + effects_block + "\n" + content[insert_pos:]
    else:
        content = content.rstrip() + "\n" + effects_block

    with open(EFFECTS_YAML, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n  Updated: effects.yaml (+{len(effects_to_add)} effects)")
    print(f"\n  Done! {len(effects_to_add)} effects registered under category '{category}'")


if __name__ == "__main__":
    main()
