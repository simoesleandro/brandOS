# Plan 001: Stabilize the publication registry contract

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If any STOP condition occurs, stop and report; do not improvise.
>
> **Drift check (run first)**: `git diff --stat 852c752..HEAD -- app/core/repositories/history_repository.py app/core/brandos_service.py app/core/services/calendar_service.py tests/conftest.py tests/test_brandos_service.py tests/test_history_repository.py`

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: bug, tests, tech-debt
- **Planned at**: commit `852c752`, 2026-07-06

## Why This Matters

BrandOS features do not connect cleanly because the central registry has no enforced contract. The real `data/registry/publication-log.json` is mostly a list of week entries with nested `items`, but it also contains loose root-level test items. Some methods treat it as a dict with an `items` key, and other methods iterate the top-level list as if it were a flat item list. This causes detail screens, approvals, dashboard counts, generated-week views, and cleanup operations to disagree about what exists.

## Current State

- `app/core/repositories/history_repository.py` is the only registry repository, but it simply loads raw JSON and returns `[]` on any error.
- `app/core/brandos_service.py:626` implements `generate_week_from_briefing` and writes directly to `publication-log.json`.
- `app/core/brandos_service.py:931` appends `new_week` to `log_data`, confirming the dominant shape is a list of week entries.
- `app/core/brandos_service.py:1006` calls `log_data.get("items", [])`, which only works if the registry is a dict. The real registry is a list, so this path catches an exception and silently degrades.
- `app/core/brandos_service.py:1285`, `1345`, `1422`, `1499`, and `1558` iterate `for item in log_data:`, treating the top-level list as flat items.
- `app/core/brandos_service.py:3309`, `3350`, and `3390` contain registry repair/cleanup helpers inside the service instead of the repository.
- `tests/conftest.py:18` creates a list-of-weeks fixture.
- `tests/test_brandos_service.py:22` has the currently failing dashboard test; `tests/test_brandos_service.py:25` expects `total_items == 3` even though current dashboard logic excludes linked carousel assets.

## Commands You Will Need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Tests | `python -m pytest -q` | exit 0, all tests pass |
| Targeted tests | `python -m pytest tests/test_history_repository.py tests/test_brandos_service.py -q` | exit 0 |
| Git status | `git status --short` | only in-scope files modified |

## Scope

**In scope**:
- `app/core/repositories/history_repository.py`
- `app/core/brandos_service.py`
- `app/core/services/calendar_service.py`
- `tests/conftest.py`
- `tests/test_history_repository.py`
- `tests/test_brandos_service.py`

**Out of scope**:
- Migrating to SQLite.
- Changing UI templates.
- Changing generated content files under `data/generated`.
- Editing real `data/registry/publication-log.json` except in a separate manual migration after code and tests are ready.

## Steps

### Step 1: Define the registry contract in HistoryRepository

Update `HistoryRepository` so its public contract is explicit:

- `load()` returns `list[dict]` of week-like entries.
- Add `iter_items(history=None)` that yields `(entry, item)` pairs for nested items only.
- Add `find_item(item_id, history=None)` that uses both `item["item_id"]` and `item["id"]`.
- Add save validation that rejects non-list history and rejects root-level entries that are item-like but have no `items` list, unless a migration/preview function handles them.
- Stop swallowing JSON parse errors silently. Prefer raising `ValueError("Invalid publication-log.json")` with the path.

**Verify**: `python -m pytest tests/test_history_repository.py -q` exits 0.

### Step 2: Move registry shape repair out of BrandOSService

Move the concepts currently in `BrandOSService.normalize_registry_item_ids`, `preview_invalid_items`, and `discard_items_bulk` into repository-level methods or a dedicated helper under `app/core/repositories/`.

Keep route-facing methods in `BrandOSService` temporarily as thin delegates.

**Verify**: `python -m pytest tests/test_history_repository.py tests/test_brandos_service.py -q` exits 0.

### Step 3: Replace dict/flat-list registry reads

In `BrandOSService`, replace code paths that assume `log_data.get("items", [])` or `for item in log_data:` for registry items.

Targets:

- `get_generated_week_details`
- `approve_generated_post`
- `approve_generated_week`
- `schedule_post`
- `reschedule_post`
- `unschedule_post`

Use repository helpers to locate entries/items. Preserve existing response shapes.

**Verify**: `rg -n "log_data\\.get\\(\"items\"|for item in log_data:" app/core/brandos_service.py` returns no matches.

### Step 4: Decide and test dashboard item semantics

Resolve the failing test intentionally. Recommended semantics:

- `total_items`: count only main publishable items.
- `linked_assets_items`: count assets linked to publications.

Update `tests/test_brandos_service.py::test_get_dashboard_metrics` to expect `total_items == 2` and `linked_assets_items == 1`, or change `get_dashboard_metrics` if the product owner explicitly wants assets counted in total items. Document the decision in a short test comment.

**Verify**: `python -m pytest tests/test_brandos_service.py -q` exits 0.

### Step 5: Add regression fixtures for mixed legacy registry entries

Add tests that include root-level loose item entries like the real registry currently has. The expected behavior should be explicit: either `preview_invalid_items` reports them for cleanup, or repository load rejects them before save.

**Verify**: `python -m pytest -q` exits 0.

## Done Criteria

- [x] `python -m pytest -q` exits 0.
- [x] No production code path treats the registry as both dict-with-items and flat item list.
- [x] `BrandOSService` uses repository helpers for item lookup in the targeted methods.
- [x] The dashboard test documents whether linked carousel assets count as main items.
- [x] `plans/README.md` marks plan 001 as DONE.

## STOP Conditions

Stop and report if the real registry changes during implementation, if fixing lookup requires generated data edits, or if loose root-level items turn out to be an intentional active feature.
