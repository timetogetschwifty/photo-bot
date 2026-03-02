"""
cleanup_inactive.py
───────────────────
Archives inactive categories and effects from the Photo Bot project.

Inactive = enabled: false in effects.yaml, OR belongs to a disabled category.

What it does:
  1. Reads effects.yaml, finds all disabled categories and effects
  2. Removes them from effects.yaml and rewrites the file
  3. Moves category images  → images/archive/
  4. Moves effect images    → images/archive/
  5. Moves effect prompts   → prompts/archive/

Usage:
  python cleanup_inactive.py           # dry run (safe preview, no changes)
  python cleanup_inactive.py --execute # actually move files and rewrite YAML
"""

import sys
import shutil
from pathlib import Path

import yaml

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE        = Path(__file__).parent
YAML_PATH   = BASE / "effects.yaml"
PROMPTS_DIR = BASE / "prompts"
IMAGES_DIR  = BASE / "images"

DRY_RUN = "--execute" not in sys.argv

# ── Load YAML ─────────────────────────────────────────────────────────────────

with open(YAML_PATH, encoding="utf-8") as f:
    config = yaml.safe_load(f)

categories = config.get("categories", {})
effects    = config.get("effects", {})

# ── Collect disabled items ─────────────────────────────────────────────────────

disabled_categories: list[str] = []
disabled_effects:    list[str] = []
cat_disabled_effects: list[str] = []  # enabled=true but category is disabled

for cat_id, cat in categories.items():
    if not cat.get("enabled", True):
        disabled_categories.append(cat_id)

for eff_id, eff in effects.items():
    own_disabled = not eff.get("enabled", True)
    cat_disabled = eff.get("category") in disabled_categories
    if own_disabled or cat_disabled:
        disabled_effects.append(eff_id)
        if cat_disabled and not own_disabled:
            cat_disabled_effects.append(eff_id)

# ── Report what will be archived ───────────────────────────────────────────────

mode_label = "[DRY RUN]" if DRY_RUN else "[EXECUTE]"
print(f"\n{mode_label} Photo Bot — Archive Inactive Effects")
print("=" * 55)

print(f"\nDisabled categories ({len(disabled_categories)}):")
for cat_id in disabled_categories:
    label = categories[cat_id].get("label", "")
    print(f"  • {cat_id}  {label}")

print(f"\nDisabled effects ({len(disabled_effects)}):")
for eff_id in disabled_effects:
    eff   = effects[eff_id]
    label = eff.get("label", "")
    note  = "  ← enabled=true, but category disabled" if eff_id in cat_disabled_effects else ""
    print(f"  • {eff_id}  {label}{note}")

# ── Find files to move ────────────────────────────────────────────────────────

IMAGE_EXTS  = [".png", ".jpg", ".webp"]

moves: list[tuple[Path, Path]] = []   # (src, dst)
missing: list[str]             = []

def queue_image(item_id: str, search_dir: Path, dst_dir: Path):
    """Find the first matching image extension and queue it, or mark as missing."""
    for ext in IMAGE_EXTS:
        src = search_dir / f"{item_id}{ext}"
        if src.exists():
            moves.append((src, dst_dir / src.name))
            return
    missing.append(str((search_dir / item_id).relative_to(BASE)) + ".[png|jpg|webp]")

def queue_prompt(eff_id: str):
    src = PROMPTS_DIR / f"{eff_id}.txt"
    if src.exists():
        moves.append((src, PROMPTS_DIR / "archive" / src.name))
    else:
        missing.append(str(src.relative_to(BASE)))

# Category images
for cat_id in disabled_categories:
    queue_image(cat_id, IMAGES_DIR, IMAGES_DIR / "archive")

# Effect prompts + images
for eff_id in disabled_effects:
    queue_prompt(eff_id)
    queue_image(eff_id, IMAGES_DIR, IMAGES_DIR / "archive")

print(f"\nFiles to move ({len(moves)}):")
for src, dst in moves:
    print(f"  {src.relative_to(BASE)}  →  {dst.relative_to(BASE)}")

if missing:
    print(f"\nFiles not found (skipped, {len(missing)}):")
    for m in missing:
        print(f"  ! {m}")

# ── Execute ───────────────────────────────────────────────────────────────────

if DRY_RUN:
    print("\n" + "─" * 55)
    print("No changes made. Run with --execute to apply.")
    print("─" * 55 + "\n")
    sys.exit(0)

# Create archive folders
(IMAGES_DIR  / "archive").mkdir(exist_ok=True)
(PROMPTS_DIR / "archive").mkdir(exist_ok=True)

# Move files
for src, dst in moves:
    shutil.move(str(src), str(dst))
    print(f"  Moved: {src.relative_to(BASE)} → {dst.relative_to(BASE)}")

# Remove disabled items from YAML data
for cat_id in disabled_categories:
    del config["categories"][cat_id]
for eff_id in disabled_effects:
    del config["effects"][eff_id]

# Rewrite effects.yaml (note: PyYAML does not preserve comments)
with open(YAML_PATH, "w", encoding="utf-8") as f:
    yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

print(f"\n  Rewrote: {YAML_PATH.relative_to(BASE)}")
print(f"  Removed {len(disabled_categories)} categories, {len(disabled_effects)} effects")

print("\n" + "─" * 55)
print("Done. Verify with: python photo_bot.py")
print("─" * 55 + "\n")
