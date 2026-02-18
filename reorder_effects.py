"""
Reorder top-level effects in effects.yaml.

Provide effect_ids as arguments to set them as top priorities.
Remaining enabled effects keep their relative order after the promoted ones.
Disabled effects are pushed to the end.

Both order: numbers and physical YAML block positions are updated.
Category/drop effects are left untouched.

Usage:
    python reorder_effects.py --list
    python reorder_effects.py cat_phone king Custom0218_03_ActionFigureBlister
    python reorder_effects.py 9 10 11 --dry-run       (use row numbers from --list)
    python reorder_effects.py 9 cat_phone 11           (mix numbers and names)
"""

import argparse
import os
import re
import sys

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EFFECTS_YAML = os.path.join(BASE_DIR, "effects.yaml")

# Matches an effect header at 2-space indent: "  effect_id:"
EFFECT_HEADER_RE = re.compile(r"^  (\S+):\s*$")
# Matches "    order: N"
ORDER_LINE_RE = re.compile(r"^(    order:\s*)\d+(.*)$")
# Matches a comment-only line (with optional leading whitespace)
COMMENT_RE = re.compile(r"^\s*#")
# Matches a blank line
BLANK_RE = re.compile(r"^\s*$")


def load_effects_data():
    """Load effects.yaml, return (parsed_yaml_data, raw_lines)."""
    with open(EFFECTS_YAML, "r", encoding="utf-8") as f:
        raw = f.read()
    data = yaml.safe_load(raw)
    return data, raw


def parse_effect_blocks(raw):
    """Split effects.yaml into: header, effect blocks list, and footer.

    Returns:
        (header_text, blocks, footer_text)

    Each block is a dict:
        effect_id: str or None (None for comment/drop group headers)
        lines: list of raw line strings
        is_category_effect: bool
    """
    lines = raw.split("\n")

    # Find "effects:" line
    effects_start = None
    for i, line in enumerate(lines):
        if line.rstrip() == "effects:":
            effects_start = i
            break

    if effects_start is None:
        print("Error: 'effects:' section not found in effects.yaml")
        sys.exit(1)

    # Find TEMPLATES marker (footer start)
    footer_start = len(lines)
    for i in range(effects_start, len(lines)):
        if lines[i].startswith("# ── TEMPLATES"):
            # Include preceding blank lines in footer
            j = i
            while j > 0 and BLANK_RE.match(lines[j - 1]):
                j -= 1
            footer_start = j
            break

    header_text = "\n".join(lines[: effects_start + 1])
    footer_text = "\n".join(lines[footer_start:])
    body_lines = lines[effects_start + 1 : footer_start]

    # Parse body into blocks. Each block starts at an effect header line.
    # Lines before the first effect header (blanks, comments) attach to the next block.
    blocks = []
    pending_prefix = []  # comment/blank lines before an effect header

    i = 0
    while i < len(body_lines):
        line = body_lines[i]
        header_match = EFFECT_HEADER_RE.match(line)

        if header_match:
            effect_id = header_match.group(1)
            block_lines = list(pending_prefix) + [line]
            pending_prefix = []
            i += 1

            # Collect all lines belonging to this effect (4-space indented fields,
            # plus any trailing blank lines)
            while i < len(body_lines):
                next_line = body_lines[i]
                # Next effect header = new block
                if EFFECT_HEADER_RE.match(next_line):
                    break
                # Comment line starting a drop section (e.g. "  # ── Avatar Drop ──")
                if COMMENT_RE.match(next_line) and not next_line.startswith("    "):
                    break
                # A field line (4-space indent) or blank line
                block_lines.append(next_line)
                i += 1

            # Strip trailing blank lines from block, keep them as separator
            trailing_blanks = []
            while block_lines and BLANK_RE.match(block_lines[-1]):
                trailing_blanks.insert(0, block_lines.pop())

            blocks.append({
                "effect_id": effect_id,
                "lines": block_lines,
                "trailing_blanks": trailing_blanks,
            })
        else:
            # Comment or blank line not yet attached to an effect
            pending_prefix.append(line)
            i += 1

    # Any remaining pending prefix (comments/blanks before footer)
    if pending_prefix:
        # Attach to a "leftover" block
        blocks.append({
            "effect_id": None,
            "lines": pending_prefix,
            "trailing_blanks": [],
        })

    return header_text, blocks, footer_text


def classify_blocks(blocks, yaml_data):
    """Classify each block as top-level or category effect.

    Returns (top_level_blocks, category_blocks).
    top_level_blocks: list of blocks with category=None
    category_blocks: list of blocks with a category (or effect_id=None for group comments)
    """
    effects = yaml_data.get("effects") or {}
    top_level = []
    category = []

    for block in blocks:
        eid = block["effect_id"]
        if eid is None:
            # Comment/separator block — check if it's a drop header
            # (lines like "  # ── Avatar Drop ──")
            category.append(block)
            continue

        edata = effects.get(eid)
        if edata and edata.get("category"):
            category.append(block)
        else:
            top_level.append(block)

    return top_level, category


def update_block_order(block, new_order):
    """Update the order: value in a block's lines."""
    for i, line in enumerate(block["lines"]):
        m = ORDER_LINE_RE.match(line)
        if m:
            block["lines"][i] = f"{m.group(1)}{new_order}{m.group(2)}"
            return
    # No order line found — shouldn't happen but just in case
    print(f"  Warning: no order: line found for {block['effect_id']}")


def reassemble(header_text, top_blocks, cat_blocks, footer_text):
    """Reassemble the full YAML from parts."""
    parts = [header_text]

    for block in top_blocks:
        parts.append("\n".join(block["lines"]))
        if block["trailing_blanks"]:
            parts.append("\n".join(block["trailing_blanks"]))
        else:
            parts.append("")  # one blank line separator

    # Blank line between top-level and category sections
    parts.append("")

    for block in cat_blocks:
        parts.append("\n".join(block["lines"]))
        if block["trailing_blanks"]:
            parts.append("\n".join(block["trailing_blanks"]))
        else:
            parts.append("")

    parts.append(footer_text)

    # Join and clean up excessive blank lines (max 2 consecutive)
    result = "\n".join(parts)
    result = re.sub(r"\n{4,}", "\n\n\n", result)
    return result


def get_block_by_id(blocks, effect_id):
    """Find a block by effect_id."""
    for b in blocks:
        if b["effect_id"] == effect_id:
            return b
    return None


def cmd_list(yaml_data, top_blocks):
    """Show current top-level effect order."""
    effects = yaml_data.get("effects") or {}

    enabled = []
    disabled = []
    for block in top_blocks:
        eid = block["effect_id"]
        edata = effects.get(eid, {})
        if edata.get("enabled", True):
            enabled.append((eid, edata))
        else:
            disabled.append((eid, edata))

    print(f"\n  Top-level effects: {len(enabled)} enabled, {len(disabled)} disabled\n")
    print(f"  {'#':<4} {'Order':<6} {'Effect ID':<42} Label")
    print(f"  {'─'*4} {'─'*6} {'─'*42} {'─'*30}")

    num = 0
    for eid, edata in enabled:
        num += 1
        order = edata.get("order", "?")
        label = edata.get("label", "")
        print(f"  {num:<4} {order:<6} {eid:<42} {label}")

    if disabled:
        print()
        for eid, edata in disabled:
            num += 1
            order = edata.get("order", "?")
            label = edata.get("label", "")
            print(f"  {num:<4} {order:<6} {eid:<42} {label}  [DISABLED]")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Reorder top-level effects in effects.yaml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python reorder_effects.py --list\n"
            "  python reorder_effects.py cat_phone king Custom0218_03_ActionFigureBlister\n"
            "  python reorder_effects.py 9 10 11 --dry-run    (row numbers from --list)\n"
            "  python reorder_effects.py cat_phone king --dry-run\n"
        ),
    )
    parser.add_argument("effect_ids", nargs="*",
                        help="Effect IDs or row numbers from --list (in desired order)")
    parser.add_argument("--list", action="store_true",
                        help="Show current top-level effect order and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without modifying files")
    args = parser.parse_args()

    if not args.list and not args.effect_ids:
        parser.print_help()
        sys.exit(0)

    # Load and parse
    yaml_data, raw = load_effects_data()
    header_text, blocks, footer_text = parse_effect_blocks(raw)
    top_blocks, cat_blocks = classify_blocks(blocks, yaml_data)

    if args.list:
        cmd_list(yaml_data, top_blocks)
        return

    # Build lookups: row # -> effect_id AND order value -> effect_id
    effects = yaml_data.get("effects") or {}
    top_ids = [b["effect_id"] for b in top_blocks]
    enabled_ids = [eid for eid in top_ids if effects.get(eid, {}).get("enabled", True)]
    row_to_id = {str(i + 1): eid for i, eid in enumerate(enabled_ids)}
    order_to_id = {}
    for eid in enabled_ids:
        order_val = str(effects[eid].get("order", ""))
        if order_val:
            order_to_id[order_val] = eid

    # Resolve: accept effect_id, row # from --list, or order value
    resolved_ids = []
    for arg in args.effect_ids:
        if arg in row_to_id:
            resolved_ids.append(row_to_id[arg])
        elif arg in order_to_id:
            resolved_ids.append(order_to_id[arg])
        elif arg in effects:
            if arg not in top_ids:
                cat = effects[arg].get("category", "")
                print(f"Error: '{arg}' belongs to category '{cat}', not top-level")
                sys.exit(1)
            if not effects[arg].get("enabled", True):
                print(f"Error: '{arg}' is disabled. Enable it in effects.yaml first.")
                sys.exit(1)
            resolved_ids.append(arg)
        else:
            print(f"Error: '{arg}' — not a valid effect ID, row #, or order value")
            sys.exit(1)

    if len(set(resolved_ids)) != len(resolved_ids):
        print("Error: duplicate effects after resolving numbers")
        sys.exit(1)

    args.effect_ids = resolved_ids

    # Split top-level blocks into: promoted, remaining enabled, disabled
    promoted_ids = args.effect_ids
    enabled_blocks = []
    disabled_blocks = []

    for block in top_blocks:
        eid = block["effect_id"]
        edata = effects.get(eid, {})
        if not edata.get("enabled", True):
            disabled_blocks.append(block)
        elif eid not in promoted_ids:
            enabled_blocks.append(block)

    # Build final order: promoted first, then rest enabled, then disabled
    promoted_blocks = [get_block_by_id(top_blocks, eid) for eid in promoted_ids]
    final_top = promoted_blocks + enabled_blocks + disabled_blocks

    # Update order: values
    for i, block in enumerate(final_top):
        update_block_order(block, i + 1)

    # Preview
    print(f"\n  Reorder: {len(promoted_ids)} promoted, "
          f"{len(enabled_blocks)} other enabled, "
          f"{len(disabled_blocks)} disabled\n")
    print(f"  {'#':<4} {'Effect ID':<42} Label")
    print(f"  {'─'*4} {'─'*42} {'─'*30}")

    for i, block in enumerate(final_top):
        eid = block["effect_id"]
        edata = effects.get(eid, {})
        label = edata.get("label", "")
        old_order = edata.get("order", "?")
        new_order = i + 1
        marker = " <--" if eid in promoted_ids else ""
        disabled_tag = "  [DISABLED]" if not edata.get("enabled", True) else ""
        changed = f" (was {old_order})" if old_order != new_order else ""
        print(f"  {new_order:<4} {eid:<42} {label}{disabled_tag}{changed}{marker}")

    print()

    if args.dry_run:
        print("  --dry-run: No files modified.")
        return

    confirm = input("  Confirm? [y/n]: ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return

    # Reassemble and write
    new_content = reassemble(header_text, final_top, cat_blocks, footer_text)

    with open(EFFECTS_YAML, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\n  Updated: effects.yaml ({len(final_top)} top-level effects reordered)")


if __name__ == "__main__":
    main()
