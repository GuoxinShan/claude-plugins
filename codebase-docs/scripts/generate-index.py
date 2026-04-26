#!/usr/bin/env python3
"""Generate a lightweight documentation index for CLAUDE.md.

Scans the docs/ directory, reads frontmatter from each .md file,
and produces a formatted index section that can be injected into CLAUDE.md.

Usage:
    python generate-index.py [--docs-dir DOCS_DIR] [--output OUTPUT]

If --output is omitted, prints to stdout.
The index format is optimized for progressive disclosure:
- Category headers for quick scanning
- One line per doc: path + one-line description
- No content loaded — agent reads on demand
"""

import argparse
import os
import re
import sys
from pathlib import Path


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    fm_text = match.group(1)
    result = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def extract_title(content: str) -> str:
    """Extract first H1 title from markdown."""
    for line in content.split("\n"):
        if line.startswith("# ") and not line.startswith("## "):
            return line[2:].strip()
    return ""


def extract_first_paragraph(content: str) -> str:
    """Extract the first non-empty, non-heading paragraph (as one-line summary)."""
    lines = content.split("\n")
    in_frontmatter = False
    fm_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            fm_count += 1
            if fm_count == 1:
                in_frontmatter = True
                continue
            elif fm_count == 2:
                in_frontmatter = False
                continue
        if in_frontmatter:
            continue
        if not stripped or stripped.startswith("#") or stripped.startswith("```"):
            continue
        if stripped.startswith(">"):
            stripped = stripped[1:].strip()
        return stripped[:120]
    return ""


def scan_docs(docs_dir: Path) -> dict[str, list[dict]]:
    """Scan docs directory and categorize all .md files."""
    categories = {}
    for md_file in sorted(docs_dir.rglob("*.md")):
        rel_path = md_file.relative_to(docs_dir)
        parts = rel_path.parts

        # Determine category from directory structure
        if len(parts) > 1:
            category = parts[0]
        else:
            category = "general"

        # Skip archive directories
        if category in ("archive",):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        fm = extract_frontmatter(content)
        title = fm.get("title", "") or extract_title(content)
        summary = fm.get("description", "") or extract_first_paragraph(content)

        path_str = str(rel_path).replace("\\", "/")
        categories.setdefault(category, []).append({
            "path": f"docs/{path_str}",
            "title": title,
            "summary": summary,
        })

    return categories


def generate_index(categories: dict[str, list[dict]]) -> str:
    """Generate formatted index text for CLAUDE.md."""
    lines = ["### Documentation Index (auto-generated)", ""]

    category_labels = {
        "design": "Architecture & Design",
        "api": "API Reference",
        "reference": "Reference",
        "business": "Business & Planning",
        "general": "General",
    }

    for cat in sorted(categories.keys()):
        docs = categories[cat]
        label = category_labels.get(cat, cat.replace("-", " ").title())
        lines.append(f"#### {label}")
        for doc in docs:
            summary = doc["summary"] or doc["title"] or "No description"
            # Keep one-line, truncate if needed
            if len(summary) > 100:
                summary = summary[:97] + "..."
            lines.append(f"- [{doc['path']}]({doc['path']}) — {summary}")
        lines.append("")

    return "\n".join(lines)


def update_claude_md(claude_md_path: Path, index_content: str) -> None:
    """Replace or insert the auto-generated index section in CLAUDE.md."""
    if not claude_md_path.exists():
        print(f"Warning: {claude_md_path} not found. Index printed to stdout instead.", file=sys.stderr)
        print(index_content)
        return

    content = claude_md_path.read_text(encoding="utf-8")
    marker_start = "### Documentation Index (auto-generated)"
    marker_end = "<!-- /doc-index -->"

    new_section = f"{index_content.rstrip()}\n{marker_end}\n"

    if marker_start in content:
        # Replace existing section
        start_idx = content.index(marker_start)
        if marker_end in content:
            end_idx = content.index(marker_end) + len(marker_end)
            content = content[:start_idx] + new_section + content[end_idx:]
        else:
            content = content[:start_idx] + new_section + content[start_idx + len(marker_start):]
    else:
        # Append to end
        content = content.rstrip() + "\n\n" + new_section

    claude_md_path.write_text(content, encoding="utf-8")
    print(f"Updated {claude_md_path} with {index_content.count(chr(10))} index entries.")


def main():
    parser = argparse.ArgumentParser(description="Generate docs index for CLAUDE.md")
    parser.add_argument("--docs-dir", default="docs", help="Documentation directory")
    parser.add_argument("--output", help="Output file (default: update CLAUDE.md)")
    parser.add_argument("--claude-md", default="CLAUDE.md", help="Path to CLAUDE.md")
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    if not docs_dir.exists():
        print(f"Error: {docs_dir} not found.", file=sys.stderr)
        sys.exit(1)

    categories = scan_docs(docs_dir)
    if not categories:
        print("No documentation files found.", file=sys.stderr)
        sys.exit(0)

    index_content = generate_index(categories)

    if args.output:
        Path(args.output).write_text(index_content, encoding="utf-8")
        print(f"Index written to {args.output}")
    else:
        update_claude_md(Path(args.claude_md), index_content)


if __name__ == "__main__":
    main()
