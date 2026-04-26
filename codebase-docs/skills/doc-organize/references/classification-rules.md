# Classification Rules Reference

## File Classification Matrix

| File Pattern | Target Directory | Examples |
|-------------|-----------------|----------|
| `*-design.md`, `*-architecture.md` | `docs/design/` | Agent network design, DI infrastructure |
| `*-api.md`, `api-*.md` | `docs/api/` | API pagination, STT API |
| `*-config.md`, `CONFIG.md`, `*-reference.md` | `docs/reference/` | Configuration reference, SDK reference |
| `*-spec.md`, `*-产品*.md`, `*-方案*.md` | `docs/business/` | Product definition, interaction design |
| `*-plan.md`, `*-计划*.md` (historical) | `docs/archive/plans/` | Phase 1-5 implementation plans |
| `*-spec.md` (historical) | `docs/archive/specs/` | Historical design specifications |
| `test_*.py`, `*_test.py` | `tests/unit/` or `tests/integration/` | Unit and integration tests |

## Detection Heuristics

### Documentation Detection
A file is likely documentation if:
- Extension is `.md` and it's not a README
- Contains `#` headings (H1-H3)
- Contains structured content (tables, code blocks, lists)
- Is not a config file (`.github/`, `.claude/`)

### Test File Detection
A file is a test if:
- Filename matches `test_*.py` or `*_test.py`
- Contains `def test_` or `class Test`
- Imports `pytest` or `unittest`

### Orphan Detection
A doc is orphaned if:
- No other file references it (Grep returns 0 results for the filename)
- Not listed in CLAUDE.md
- Older than 30 days with no recent modifications

## Priority Actions

1. **HIGH**: Active design docs in wrong directory → move immediately
2. **MEDIUM**: Test files outside tests/ → move with reference updates
3. **LOW**: Historical docs already in archive/ → no action needed
4. **SKIP**: README.md, CHANGELOG.md, LICENSE → these belong in root
