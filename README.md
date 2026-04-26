# Claude Plugins

Personal Claude Code plugins and skills collection by [GuoxinShan](https://github.com/GuoxinShan).

## Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [codebase-docs](codebase-docs/) | Automated codebase documentation with progressive disclosure | v0.1.0 |

## Install

Add to your `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "rocks-plugins": {
      "source": {
        "source": "github",
        "repo": "GuoxinShan/claude-plugins"
      },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "codebase-docs@rocks-plugins": true
  }
}
```

Restart Claude Code, then verify with `/plugins`.

## codebase-docs

Automated codebase documentation generator with progressive disclosure.

**Features:**
- **Full documentation initialization** (`/codebase-docs:init`) — Parallel scan of all modules, architecture patterns, and API endpoints
- **Incremental updates** (`/codebase-docs:update`) — Only re-scan changed modules
- **Progressive reading** (auto-activating skill) — Agents read lightweight index first, load docs on demand
- **File organization** (`/codebase-docs:organize`) — Reclassify misplaced docs and tests

**Quick start:**

```
/codebase-docs:init          # Full scan, generate docs + update CLAUDE.md index
/codebase-docs:update        # Incremental update (changed modules only)
/codebase-docs:organize      # Organize scattered documentation files
```

**How it works:**

```
User runs /codebase-docs:init
    ├── Agent: module-scanner  → docs/design/*.md
    ├── Agent: pattern-scanner → docs/design/architecture-overview.md
    └── Agent: api-scanner     → docs/api/api-reference.md
    └── generate-index.py      → CLAUDE.md doc index updated
```

Agents navigate docs progressively — CLAUDE.md index → specific doc → source code (if needed).
