#!/usr/bin/env python3
"""Check if documentation is stale by comparing modification times.

Compares source file mtimes against the last documentation generation timestamp.
Exit codes:
    0 = docs are fresh
    1 = docs are stale (prints staleness info to stdout)

Usage:
    python check-staleness.py [--manifest .docs-manifest.json] [--threshold-hours 24]
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def load_manifest(path: Path) -> dict:
    """Load the documentation manifest."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def find_latest_source_mtime(source_dir: Path) -> datetime | None:
    """Find the most recent modification time among source files."""
    latest = None
    for f in source_dir.rglob("*.py"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if latest is None or mtime > latest:
                latest = mtime
        except OSError:
            continue
    return latest


def main():
    parser = argparse.ArgumentParser(description="Check documentation staleness")
    parser.add_argument("--manifest", default=".docs-manifest.json", help="Manifest file path")
    parser.add_argument("--source-dir", default="src", help="Source directory")
    parser.add_argument("--threshold-hours", type=int, default=24, help="Staleness threshold in hours")
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    last_generated = manifest.get("last_generated")

    if not last_generated:
        print(json.dumps({
            "status": "never_generated",
            "message": "Documentation has never been generated. Run /codebase-docs:init to initialize.",
        }))
        sys.exit(1)

    gen_time = datetime.fromisoformat(last_generated)
    threshold = timedelta(hours=args.threshold_hours)
    now = datetime.now()

    age = now - gen_time
    is_stale = age > threshold

    # Also check if source files are newer than docs
    source_dir = Path(args.source_dir)
    latest_source = find_latest_source_mtime(source_dir) if source_dir.exists() else None

    source_newer = False
    if latest_source and latest_source > gen_time:
        source_newer = True
        is_stale = True

    result = {
        "status": "stale" if is_stale else "fresh",
        "age_hours": round(age.total_seconds() / 3600, 1),
        "threshold_hours": args.threshold_hours,
        "last_generated": last_generated,
        "source_newer_than_docs": source_newer,
    }

    if is_stale:
        if source_newer:
            result["message"] = f"Source code has changed since docs were generated ({round(age.total_seconds() / 3600, 1)}h ago). Run /codebase-docs:update to sync."
        else:
            result["message"] = f"Documentation is {round(age.total_seconds() / 3600, 1)}h old (threshold: {args.threshold_hours}h). Consider running /codebase-docs:update."
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)
    else:
        result["message"] = "Documentation is up to date."
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0)


if __name__ == "__main__":
    main()
