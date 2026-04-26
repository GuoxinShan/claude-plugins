---
name: doc-update
description: |
  Incremental documentation update. Detects source code changes since the last
  doc generation and only updates affected documentation files.
  Triggers: "update docs", "sync docs", "refresh documentation",
  "/codebase-docs:update", "docs are outdated".
version: 0.1.0
user-invoked: true
description-text: Incrementally update documentation for changed modules only
argument-hint: "[--force] [--module MODULE]"
allowed-tools:
  - Agent
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# doc-update: Incremental Documentation Update

You are performing an incremental documentation update. Only changed modules are re-scanned and re-documented.

## Step 1: Load Manifest

Read `.docs-manifest.json` to get:
- `last_generated`: When docs were last generated
- `doc_map`: Mapping of module paths to doc file paths
- `source_hash`: Git commit hash at generation time

If no manifest exists, tell the user to run `/codebase-docs:init` first.

## Step 2: Detect Changes

### Option A: Git-based detection (preferred)
```bash
python CLAUDE_PLUGIN_ROOT/scripts/detect-changes.py --source-dir src/openturtle_os --manifest .docs-manifest.json
```

This returns a JSON object with `changed_modules` and `modules_with_docs`.

### Option B: User-specified module
If the user passes `--module core/task`, only update that specific module.

### Option C: Force full update
If the user passes `--force`, treat all modules as changed (same as re-running init, but preserves existing docs that haven't changed).

## Step 3: Targeted Re-scan

For each changed module that has existing documentation:

1. Read the current doc to understand what exists
2. Spawn a module-scanner agent for just that module:
   ```
   Agent({
     subagent_type: "general-purpose",
     description: "Re-scan module: {module_name}",
     prompt: "Read CLAUDE_PLUGIN_ROOT/agents/module-scanner.md. Update the existing doc at {doc_path}. Preserve the structure but update content to match current code."
   })
   ```

**Parallelism**: Spawn up to 5 scanners in parallel for multiple changed modules.

For modules that changed but DON'T have existing docs — these are new modules. Spawn scanners to create fresh docs.

## Step 4: Update Index

After all re-scans complete:

```bash
python CLAUDE_PLUGIN_ROOT/scripts/generate-index.py --docs-dir docs --claude-md CLAUDE.md
```

## Step 5: Update Manifest

Update `.docs-manifest.json`:
- `last_generated`: Current timestamp
- `source_hash`: Current git HEAD
- `modules_documented`: Updated list
- `doc_map`: Updated mapping

## Output

```
Documentation updated:
- X modules re-scanned: [list]
- Y new modules documented: [list]
- Z modules unchanged: skipped
- CLAUDE.md index refreshed
- .docs-manifest.json updated

Changed modules not yet documented: [list, if any]
```

## Edge Cases

- **Deleted modules**: If a source module no longer exists but has a doc, ask user whether to archive or delete the doc
- **Renamed modules**: Detect by checking if a doc references files that no longer exist
- **Merge conflicts in docs**: Preserve user hand-edits by reading existing doc before overwriting
- **No changes detected**: Tell user docs are up to date, no action needed
