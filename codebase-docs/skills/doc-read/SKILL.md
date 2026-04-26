---
name: doc-read
description: |
  Progressive documentation navigation skill. Activates automatically when an agent
  needs to understand the codebase, find where something is implemented, or look up
  architectural decisions. Provides lightweight index-based navigation so agents
  can find relevant docs without loading everything into context.
  Triggers: "where is X implemented", "how does X work", "find the module that handles X",
  "show me the architecture of X", "what module handles X", "look up X in docs",
  "navigate docs", "read the documentation for X".
version: 0.1.0
allowed-tools:
  - Read
  - Glob
  - Grep
---

# doc-read: Progressive Documentation Navigation

You are a documentation navigator. Help the agent find and read relevant documentation using progressive disclosure — start with the index, then load only what's needed.

## How Progressive Disclosure Works

The documentation system has 3 levels:

```
Level 1: CLAUDE.md Index        ← Always in context, lightweight (path + 1-line summary per doc)
Level 2: Individual Doc Files   ← Loaded on demand, one at a time
Level 3: Source Code            ← Only if docs don't answer the question
```

**Never load more than 2 doc files into context at once.** If you need more, summarize what you've read and free context before loading the next.

## Navigation Protocol

### When the agent asks "where is X?" or "how does X work?":

1. **Read the index** — The `### Documentation Index (auto-generated)` section in CLAUDE.md lists all docs by category with one-line descriptions.

2. **Identify relevant docs** — Match the query against index entries:
   - For module-specific questions → look in `docs/design/`
   - For API questions → look in `docs/api/`
   - For architecture questions → `docs/design/architecture-overview.md`
   - For configuration → `docs/reference/`

3. **Load the most relevant doc** — Read a single doc file that best matches the query.

4. **If the doc doesn't fully answer** — Check its cross-references or related docs, but load only ONE more.

5. **If docs are insufficient** — Fall back to source code using Glob/Grep, but tell the user that the docs may need updating.

### When the agent asks "show me the full picture of X":

This implies a multi-doc exploration. Use this approach:

1. Read the index to identify ALL docs related to X
2. Read the primary doc first
3. Summarize what you found
4. Ask if the agent wants you to read additional related docs

### When the agent asks for a quick lookup:

For simple factual questions ("what's the Task status enum?", "what API endpoint creates a workflow?"):
1. Search the index for keywords
2. Read only the relevant section of the matching doc
3. Answer directly without loading the full doc if possible

## File Locations

| Item | Path |
|------|------|
| Index | CLAUDE.md → `### Documentation Index (auto-generated)` section |
| Design docs | `docs/design/*.md` |
| API docs | `docs/api/*.md` |
| Reference | `docs/reference/*.md` |
| Architecture | `docs/design/architecture-overview.md` |
| Manifest | `.docs-manifest.json` |

## Context Budget Guidelines

- **Index scan**: Always OK (it's already in CLAUDE.md)
- **Single doc read**: OK for any query
- **Two doc reads**: OK for cross-cutting questions
- **Three+ doc reads**: Summarize and free context first, then continue
- **Source code fallback**: Last resort, tell user docs may be stale

## Quality Check

If you notice the index is missing or the `### Documentation Index (auto-generated)` section doesn't exist in CLAUDE.md, suggest the user run `/codebase-docs:init` to generate documentation.
