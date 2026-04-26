---
name: doc-init
description: |
  Full codebase documentation initialization. User invokes this to scan the entire
  source tree, generate structured documentation, and create a lightweight index
  in CLAUDE.md. Use when: setting up docs for a new project, after major refactors,
  or when documentation is missing/outdated and needs a complete rebuild.
  Triggers: "initialize docs", "generate documentation", "rebuild docs",
  "/codebase-docs:init", "scan codebase and generate docs".
version: 0.1.0
user-invoked: true
description-text: Initialize full codebase documentation — scan all modules, generate structured docs, and update CLAUDE.md index
argument-hint: "[--source-dir SRC] [--docs-dir DOCS] [--skip-api] [--skip-patterns]"
allowed-tools:
  - Agent
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# doc-init: Full Codebase Documentation Initialization

You are performing a full documentation initialization. This scans the entire codebase using parallel subagents and generates a structured documentation library.

## Pre-flight

1. **Detect project structure** — Read the top-level directory to identify:
   - Source code root (default: `src/`)
   - Existing docs directory (default: `docs/`)
   - Main language and framework (check `pyproject.toml`, `package.json`, etc.)
   - Any existing documentation to preserve

2. **Create `.docs-manifest.json`** if it doesn't exist — this tracks generation state.

## Phase 1: Module Discovery

Use Glob to find all source modules:

```
Glob: src/**/__init__.py     → identify module boundaries
Glob: src/**/                → list all module directories
```

Build a module list with categories:
- **Core modules**: Business logic, domain models
- **API modules**: Routes, controllers
- **Infrastructure**: Database, cache, storage, external services
- **Shared**: Utilities, types, constants
- **Background**: Workers, workflows, scheduled tasks

## Phase 2: Parallel Scanning

Launch 3 scanner agents IN PARALLEL using the Agent tool. Each agent generates docs independently.

### Agent 1: module-scanner (per module)
For EACH core module, spawn a module-scanner agent:
```
Agent({
  subagent_type: "general-purpose",
  description: "Scan module: {module_name}",
  prompt: "Read agent definition at CLAUDE_PLUGIN_ROOT/agents/module-scanner.md. Then scan the module at {module_path}. Write output to docs/design/{module-slug}.md"
})
```

**Batch strategy**: Group modules by category. Spawn up to 5 module scanners in parallel per batch. Wait for each batch to complete before spawning the next.

### Agent 2: pattern-scanner (singleton)
```
Agent({
  subagent_type: "general-purpose",
  description: "Scan architecture patterns",
  prompt: "Read agent definition at CLAUDE_PLUGIN_ROOT/agents/pattern-scanner.md. Scan source root at {source_root}. Write output to docs/design/architecture-overview.md"
})
```

### Agent 3: api-scanner (singleton)
```
Agent({
  subagent_type: "general-purpose",
  description: "Scan API endpoints",
  prompt: "Read agent definition at CLAUDE_PLUGIN_ROOT/agents/api-scanner.md. Scan source root at {source_root}. Write output to docs/api/api-reference.md"
})
```

## Phase 3: Index Generation

After all agents complete:

1. **Run the index generator**:
   ```bash
   python CLAUDE_PLUGIN_ROOT/scripts/generate-index.py --docs-dir docs --claude-md CLAUDE.md
   ```

2. **Verify the index** was inserted into CLAUDE.md — read CLAUDE.md and check for the `### Documentation Index (auto-generated)` section.

3. **Update the manifest**:
   Write to `.docs-manifest.json`:
   ```json
   {
     "last_generated": "<ISO timestamp>",
     "version": "0.1.0",
     "modules_documented": ["list", "of", "module", "slugs"],
     "doc_map": {
       "core/task": "docs/design/task.md",
       "core/project": "docs/design/project.md"
     },
     "source_hash": "<git HEAD commit>"
   }
   ```

## Phase 4: Validation

1. Count generated docs vs. discovered modules — report any gaps
2. Verify each generated doc has a title and at least one section
3. Check that the CLAUDE.md index references all generated docs

## Output

Report to the user:
```
Documentation initialized:
- X module docs generated in docs/design/
- 1 architecture overview in docs/design/architecture-overview.md
- 1 API reference in docs/api/api-reference.md
- CLAUDE.md index updated with Y entries
- .docs-manifest.json created for incremental updates

Next steps:
- Run /codebase-docs:update after making changes
- Run /codebase-docs:organize to clean up scattered files
```

## Error Handling

- If a scanner agent fails: log the failure, continue with other agents, report which modules failed at the end
- If CLAUDE.md doesn't exist: create it with just the index section
- If docs/ doesn't exist: create it with standard subdirectories (design/, api/, reference/)
- If `.docs-manifest.json` exists: warn user this will be overwritten, ask for confirmation
