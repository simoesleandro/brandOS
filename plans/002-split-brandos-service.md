# Plan 002: Split BrandOSService into workflow services

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If any STOP condition occurs, stop and report; do not improvise.
>
> **Drift check (run first)**: `git diff --stat 852c752..HEAD -- app/core/brandos_service.py app/core/services app/web/routes tests`

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: MED
- **Depends on**: `plans/001-stabilize-publication-registry.md`
- **Category**: tech-debt, tests, dx
- **Status**: DONE on 2026-07-07
- **Planned at**: commit `852c752`, 2026-07-06

## Why This Matters

`BrandOSService` has become the system all-purpose object. It is too large for reliable feature work and makes unrelated changes risky: editing briefing generation can break publishing, dashboard metrics, or strategic memory. The goal is to create stable service boundaries that match BrandOS product workflows.

## Current State

- `app/core/brandos_service.py:9` defines `BrandOSService`.
- Function index shows responsibilities for weekly generation, history, assets, metrics, CMO recommendations, briefings, generated weeks, discard/edit/approve, scheduling, strategic memory, publication assistant, manual publishing, registry repair, and tracking.
- Existing extractions are partial: `AssetService`, `CalendarService`, and `HistoryRepository`.
- Web routes instantiate `BrandOSService()` directly at import time in many modules, including `app/web/routes/publications.py:10`, `calendar.py:8`, `publishing.py:8`, and `cmo_recommendations.py:12`.

## Commands You Will Need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Tests | `python -m pytest -q` | exit 0 |
| Route import check | `python -c "import app.web.server; print('ok')"` | prints `ok` |
| Static route check | `rg -n "service = BrandOSService\\(|brandos_service = BrandOSService\\(" app/web/routes` | no matches |

## Scope

**In scope**:
- `app/core/brandos_service.py`
- New files under `app/core/services/`
- `app/web/routes/*.py` only where dependency construction must change.
- Tests under `tests/`.

**Out of scope**:
- Changing UI behavior.
- Changing prompt text or LLM output quality.
- SQLite migration.
- Rewriting the app as async.

## Steps

### Step 1: Create a service container/factory

Create `app/core/services/service_container.py` with a function such as `create_brandos_services(base_dir: str = ".")`. Construct `HistoryRepository`, `AssetService`, `CalendarService`, and future services there. Keep `BrandOSService` as a facade temporarily.

**Status**: DONE.

**Verify**: `python -c "from app.core.services.service_container import create_brandos_services; print('ok')"` prints `ok`.

### Step 2: Extract publication operations

Create `app/core/services/publication_service.py` for item state transitions:

- `update_item_status`
- `discard_item`
- `update_item_content`
- `approve_generated_post`
- `approve_generated_week`
- `mark_manual_published`
- `mark_post_publishing_ready`
- `mark_post_published`
- `undo_post_published`
- `start_post_publish_tracking`
- `update_post_publish_tracking_status`

Use repository helpers from plan 001. Keep `BrandOSService` methods as delegates.

**Status**: DONE. Implemented in `app/core/services/publication_service.py` with direct tests in `tests/test_publication_service.py`.

**Verify**: `python -m pytest tests/test_brandos_service.py -q` exits 0.

### Step 3: Extract briefing and recommendation operations

Create:

- `app/core/services/briefing_service.py` for briefing list/read/edit/approve/archive/create/prepare.
- `app/core/services/cmo_service.py` for CMO recommendation generation/archive/list/detail.

Do not change prompt behavior in this plan.

**Status**: DONE. `BriefingService` owns briefing list/read/prepare/edit/approve/archive/create-from-CMO. `CmoService` owns recommendation index listing, markdown reading, archive, and recommendation generation paths, including the memory-aware flow.

**Verify**: `python -m pytest tests/test_brandos_service.py -q` exits 0.

### Step 4: Extract learning and ops operations

Create:

- `app/core/services/learning_service.py` for editorial learning and strategic memory.
- `app/core/services/ops_service.py` for dashboard metrics, invalid item preview, registry cleanup delegates, and operational dashboard data.

**Status**: DONE. `LearningService` owns editorial learning and strategic memory. `OpsService` owns dashboard metrics, operational dashboard data, invalid item preview, and registry cleanup helpers, with direct tests.

**Verify**: `python -m pytest -q` exits 0.

### Step 5: Replace direct route construction with dependency access

Introduce `app/web/dependencies.py` returning the facade or service container. Update routes so they no longer instantiate `BrandOSService()` at module import time.

**Verify**: `rg -n "service = BrandOSService\\(|brandos_service = BrandOSService\\(" app/web/routes` returns no matches.

## Done Criteria

- [x] `python -m pytest -q` exits 0. Verified: 52 passed.
- [x] `BrandOSService` is a thin facade, not the owner of all domain logic.
- [x] Web routes no longer instantiate `BrandOSService` at import time.
- [x] New services have focused tests.
- [x] `plans/README.md` marks plan 002 as DONE.

## STOP Conditions

Stop and report if plan 001 is incomplete, templates must change to complete extraction, or a moved method requires prompt/output schema changes.
