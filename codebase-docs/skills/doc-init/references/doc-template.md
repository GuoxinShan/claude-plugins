# Document Template Reference

## Module Doc Template

Each generated module document follows this structure:

```markdown
---
title: Module Name
description: One-line description
category: design
generated: 2026-04-26T10:00:00
source_path: src/module/path/
---

# Module Name

> One-line summary.

## Architecture

- **Layer**: [core / infrastructure / api / shared]
- **Pattern**: [design pattern name]
- **Dependencies**: [internal module dependencies]
- **Dependents**: [modules that depend on this one]

## Public API

### Classes

#### `ClassName`
- **Purpose**: One-line description
- **Key Methods**: `method()` — description

### Functions

#### `function_name()`
- **Purpose**: One-line description

## Data Models

| Model | Table | Key Fields | Relationships |
|-------|-------|------------|---------------|

## Internal Flow

Brief description of execution flow.

## Configuration

Env vars, settings, config files used by this module.
```

## Architecture Overview Template

```markdown
# System Architecture

## Layer Map

```
API → Core → Infrastructure
```

## Cross-Cutting Concerns

### Dependency Injection
### Event System
### Authentication
### Error Handling
### State Machines
### Background Processing

## Module Dependency Graph

## Shared Utilities
```

## API Reference Template

```markdown
# API Reference

## Overview

| Domain | Endpoints | Auth |
|--------|-----------|------|

## Domain Name API

### Endpoint Name

`METHOD /path`

- **Auth**: Required/None
- **Description**: One-line
- **Params**: ...
- **Response**: ...
- **Status Codes**: ...
```
