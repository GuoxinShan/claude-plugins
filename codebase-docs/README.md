# codebase-docs

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg) ![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

English | [中文](README_CN.md)

**Automated codebase documentation with progressive disclosure for Claude Code.**

Scans your codebase with parallel subagents, generates structured docs, and maintains a lightweight index in CLAUDE.md. Agents navigate progressively — index first, specific docs on demand, source code only when needed.

## Why?

Without it, agents burn context reading source files to understand your codebase. With it, agents read a one-line-per-doc index in CLAUDE.md and load only relevant docs. Less context waste, faster answers.

## Install

In Claude Code, run these **one at a time**:

```
/plugin marketplace add https://github.com/GuoxinShan/claude-plugins
```

Then:

```
/plugin install codebase-docs
```

## Features

| Feature | Command | What it does |
|---------|---------|-------------|
| Full init | `/codebase-docs:init` | Parallel scan of all modules, architecture patterns, API endpoints |
| Incremental update | `/codebase-docs:update` | Only re-scans changed modules |
| File organization | `/codebase-docs:organize` | Reclassify misplaced docs and tests (dry-run by default) |
| Progressive reading | _auto-activating skill_ | Agents read index → load doc on demand → source code last |

### Progressive Disclosure

The core idea — agents never load everything at once:

```
Level 1: CLAUDE.md index     ← Always in context (one line per doc)
Level 2: Individual doc file ← Loaded on demand
Level 3: Source code          ← Last resort
```

### Parallel Scanning

`/codebase-docs:init` launches subagents in parallel:

```
├── module-scanner  ×N  →  docs/design/*.md       (one per module)
├── pattern-scanner     →  docs/design/architecture-overview.md
└── api-scanner         →  docs/api/api-reference.md
└── generate-index.py   →  CLAUDE.md doc index updated
```

For a medium-sized project (~10k lines), init takes 2-5 minutes.

### Incremental Updates

`/codebase-docs:update` detects changed modules via git diff and only re-scans those. Keeps `.docs-manifest.json` to track generation state.

### Auto Hooks

| Hook | When | What |
|------|------|------|
| SessionStart | Session starts | Checks doc freshness (>24h old or source newer). Suggests update. |
| Stop | Session ends | Detects which documented modules changed. Suggests sync. |

### doc-organize (repo-cleanser integrated)

Scans for misplaced docs, test files outside `tests/`, duplicate or orphaned docs. Shows dry-run preview before moving anything. Always uses `git mv` to preserve history.

## Usage

```bash
# First time
/codebase-docs:init

# After making changes
/codebase-docs:update

# Organize scattered files (dry-run first)
/codebase-docs:organize
/codebase-docs:organize --no-dry-run    # execute moves

# Force full re-scan
/codebase-docs:update --force
```

## Generated Output

```
your-project/
├── .docs-manifest.json                    # Tracks generation state
├── CLAUDE.md                              # Updated with doc index
├── docs/
│   ├── design/
│   │   ├── architecture-overview.md       # System architecture
│   │   ├── task.md                        # Module doc
│   │   └── ...
│   ├── api/
│   │   └── api-reference.md              # All endpoints
│   └── reference/
```

## Architecture

```
codebase-docs/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── module-scanner.md      # Scans individual modules
│   ├── pattern-scanner.md     # Detects architecture patterns
│   └── api-scanner.md         # Maps API endpoints
├── hooks/
│   └── hooks.json             # SessionStart + Stop hooks
├── scripts/
│   ├── generate-index.py      # Generates CLAUDE.md doc index
│   ├── detect-changes.py      # Detects changed modules
│   └── check-staleness.py     # Checks if docs are stale
└── skills/
    ├── doc-init/              # Full initialization
    ├── doc-update/            # Incremental update
    ├── doc-read/              # Progressive reading (auto-activating)
    └── doc-organize/          # File organization
```

## Requirements

- Python 3.10+
- Git (for change detection)
- Claude Code CLI

## License

MIT
