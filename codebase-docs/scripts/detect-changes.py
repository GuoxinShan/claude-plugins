#!/usr/bin/env python3
"""Detect source code changes since last documentation generation.

Compares current git state against a stored manifest to find which modules
have changed and need documentation updates.

Usage:
    python detect-changes.py [--manifest .docs-manifest.json] [--source-dir src/]

Output (JSON to stdout):
    {
        "changed_modules": ["core/task", "api/workflow"],
        "changed_files": ["src/openturtle_os/core/task/service.py", ...],
        "total_changes": 5,
        "last_generated": "2026-04-26T10:30:00"
    }
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_git_changes(since_ref: str = None) -> list[str]:
    """Get list of changed files from git."""
    try:
        if since_ref:
            result = subprocess.run(
                ["git", "diff", "--name-only", since_ref],
                capture_output=True, text=True, cwd=os.getcwd()
            )
        else:
            # Check unstaged + staged changes
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True, text=True, cwd=os.getcwd()
            )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception:
        pass
    return []


def load_manifest(path: Path) -> dict:
    """Load the documentation manifest."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_manifest(path: Path, data: dict) -> None:
    """Save the documentation manifest."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def extract_modules(files: list[str], source_prefix: str) -> list[str]:
    """Extract unique module paths from file paths."""
    modules = set()
    for f in files:
        # Convert file path to module path
        # e.g., src/openturtle_os/core/task/service.py -> core/task
        parts = Path(f).parts
        if source_prefix in parts:
            idx = parts.index(source_prefix)
            if idx + 1 < len(parts):
                module_parts = parts[idx + 1:]
                if len(module_parts) > 1:
                    modules.add("/".join(module_parts[:-1]))  # Exclude filename
                else:
                    modules.add(module_parts[0])
    return sorted(modules)


def main():
    parser = argparse.ArgumentParser(description="Detect changes since last doc generation")
    parser.add_argument("--manifest", default=".docs-manifest.json", help="Manifest file path")
    parser.add_argument("--source-dir", default="src/openturtle_os", help="Source directory prefix")
    parser.add_argument("--since", help="Git ref to compare against (default: HEAD)")
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    last_generated = manifest.get("last_generated", None)

    changed_files = get_git_changes(args.since)
    source_name = Path(args.source_dir).name
    source_files = [f for f in changed_files if source_name in f]

    changed_modules = extract_modules(source_files, source_name)

    # Check which modules have existing docs
    doc_map = manifest.get("doc_map", {})
    modules_with_docs = [m for m in changed_modules if m in doc_map]

    result = {
        "changed_modules": changed_modules,
        "changed_files": source_files,
        "modules_with_docs": modules_with_docs,
        "total_changes": len(source_files),
        "last_generated": last_generated,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
