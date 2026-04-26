---
name: doc-organize
description: |
  Organize scattered documentation and test files, reclassify misplaced docs,
  and maintain a clean documentation directory structure. Integrates repo-cleanser
  functionality for documentation-specific cleanup.
  Triggers: "organize docs", "clean up documentation", "reorganize docs folder",
  "/codebase-docs:organize", "docs are messy", "reclassify docs".
version: 0.1.0
user-invoked: true
description-text: Organize and reclassify scattered documentation files into proper categories
argument-hint: "[--dry-run] [--docs-dir DOCS]"
allowed-tools:
  - Agent
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# doc-organize: Documentation Organization & Cleanup

You are organizing the project's documentation. Find misplaced files, reclassify them, and maintain a clean directory structure.

## Classification Rules

Docs should be organized by category:

| Directory | Contents |
|-----------|----------|
| `docs/design/` | Architecture, design decisions, module docs, state machines, flow diagrams |
| `docs/api/` | API endpoint references, request/response schemas, authentication docs |
| `docs/reference/` | Configuration, migration guides, SDK references, integration guides |
| `docs/business/` | Product specs, planning docs, feature requirements, roadmap |
| `docs/archive/` | Historical specs and plans (frozen, read-only) |
| `tests/` | Test files (NOT in docs/) |

## Step 1: Scan for Misplaced Files

### Check for docs in wrong locations
```bash
# Find markdown files outside docs/ that look like documentation
Glob: *.md          (root level — should these be in docs/?)
Glob: **/*.md       (scan all .md files, filter out node_modules, .git, etc.)
```

### Check for test files in wrong locations
```bash
# Find test files outside tests/
Grep: "def test_|class Test|describe\(|it\(" in non-test directories
```

### Read the doc index
Read the `### Documentation Index (auto-generated)` section in CLAUDE.md to understand the expected structure.

## Step 2: Classify and Plan

For each misplaced file, determine:

1. **File type** — Is it documentation, a test, or something else (README, config)?
2. **Target location** — Where should it go based on the classification rules?
3. **Action** — Move, archive, or delete?
4. **Dependencies** — Does anything reference this file? (Grep for the filename)

### Action Rules

- **Active design docs in root or wrong subdir** → Move to `docs/design/`
- **API docs in design/** → Move to `docs/api/`
- **Historical/frozen plans** → Move to `docs/archive/`
- **Test files outside tests/** → Move to appropriate `tests/` subdirectory
- **Duplicate docs** → Keep the newer/canonical one, archive the other
- **Orphaned docs** (no references, outdated) → Move to `docs/archive/`

## Step 3: Execute (with dry-run support)

**If `--dry-run`** (default behavior):
- Print the planned moves without executing
- Present a summary table:

```
| Current Location | Target Location | Action | Reason |
|-----------------|-----------------|--------|--------|
| docs/design/api-stt.md | docs/api/api-stt.md | Move | API reference misplaced in design/ |
| root-plan.md | docs/archive/plans/ | Archive | Historical plan, no longer active |
```

- Ask user to confirm before executing

**If user confirms** (or `--dry-run` is false):
- Move files using `git mv` to preserve history
- Update any internal cross-references in moved files
- Update the CLAUDE.md doc index

## Step 4: Update Index and References

After moving files:

1. **Update cross-references** — Grep for old paths and update them
2. **Regenerate the index**:
   ```bash
   python CLAUDE_PLUGIN_ROOT/scripts/generate-index.py --docs-dir docs --claude-md CLAUDE.md
   ```
3. **Update CLAUDE.md** doc section if paths changed

## Step 5: Report

```
Documentation organized:
- X files moved to correct categories
- Y files archived
- Z cross-references updated
- CLAUDE.md index refreshed

Remaining issues:
- [list any files that couldn't be auto-classified]
```

## Safety Rules

- NEVER delete files — always move or archive
- ALWAYS use `git mv` to preserve history
- ALWAYS update references after moving
- ALWAYS show dry-run results before executing
- SKIP files in `.git/`, `node_modules/`, `__pycache__/`, `.venv/`
