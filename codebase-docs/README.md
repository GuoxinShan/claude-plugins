# codebase-docs

Automated codebase documentation generator with progressive disclosure for Claude Code.

## Overview

This plugin scans your codebase using parallel subagents, generates structured documentation, and maintains a lightweight index in CLAUDE.md. Agents can then navigate documentation progressively — reading only what they need, when they need it.

## Features

- **Full documentation initialization** (`/codebase-docs:init`) — Parallel scan of all modules, architecture patterns, and API endpoints
- **Incremental updates** (`/codebase-docs:update`) — Only re-scan changed modules
- **Progressive reading** (`doc-read` skill) — Auto-activates when agents need to understand the codebase
- **File organization** (`/codebase-docs:organize`) — Reclassify misplaced docs and tests

## Installation

In Claude Code, run these **one at a time**:

```
/plugin marketplace add https://github.com/GuoxinShan/claude-plugins
```

Then:

```
/plugin install codebase-docs
```

## Usage

### First-time setup

```
/codebase-docs:init
```

This scans your entire codebase and generates documentation. For a medium-sized project, this takes 2-5 minutes.

### After making changes

```
/codebase-docs:update
```

Only re-scans modules that have changed since the last generation.

### Organize scattered files

```
/codebase-docs:organize --dry-run
```

Shows what would be moved. Remove `--dry-run` to execute.

### How agents use the docs

Agents automatically activate the `doc-read` skill when they need to understand the codebase. They read the lightweight index in CLAUDE.md first, then load specific docs on demand.

## Directory Structure

```
codebase-docs/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── module-scanner.md      # Scans individual modules
│   ├── pattern-scanner.md     # Detects architecture patterns
│   └── api-scanner.md         # Maps API endpoints
├── hooks/
│   ├── hooks.json             # SessionStart + Stop hooks
│   └── scripts/
├── scripts/
│   ├── generate-index.py      # Generates CLAUDE.md doc index
│   ├── detect-changes.py      # Detects changed modules
│   └── check-staleness.py     # Checks if docs are stale
├── skills/
│   ├── doc-init/              # Full initialization skill
│   ├── doc-update/            # Incremental update skill
│   ├── doc-read/              # Progressive reading skill
│   └── doc-organize/          # File organization skill
└── README.md
```

## Generated Output

After running `/codebase-docs:init`, your project will have:

```
your-project/
├── .docs-manifest.json                    # Tracks generation state
├── CLAUDE.md                              # Updated with doc index
├── docs/
│   ├── design/
│   │   ├── architecture-overview.md       # System architecture
│   │   ├── task.md                        # Module doc
│   │   ├── project.md                     # Module doc
│   │   └── ...
│   ├── api/
│   │   └── api-reference.md              # All endpoints
│   └── reference/                         # Existing reference docs
```

## Hooks

### SessionStart
Checks if documentation is stale (>24h old or source code is newer). If stale, suggests running `/codebase-docs:update`.

### Stop
Detects which source files changed during the session. If any documented modules were modified, suggests syncing documentation.

## Requirements

- Python 3.10+
- Git (for change detection)
- Claude Code CLI
