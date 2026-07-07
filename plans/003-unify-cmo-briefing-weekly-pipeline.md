# Plan 003: Rebuild CMO to briefing to weekly generation as one pipeline

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If any STOP condition occurs, stop and report; do not improvise.
>
> **Drift check (run first)**: `git diff --stat 852c752..HEAD -- app/core/brandos_service.py app/workflows/weekly_workflow.py app/agents app/prompts app/web/routes/briefings.py app/web/routes/cmo_recommendations.py tests`

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: `plans/001-stabilize-publication-registry.md`, `plans/002-split-brandos-service.md`
- **Category**: bug, tech-debt, direction
- **Status**: DONE on 2026-07-07
- **Planned at**: commit `852c752`, 2026-07-06

## Why This Matters

The intended core loop is strategic: CMO recommends a week, the user approves a briefing, then BrandOS generates posts and publication assets. Today that loop is split between the original `weekly_workflow.py` and a second one-shot generation path inside `BrandOSService.generate_week_from_briefing`. That creates duplicated prompts, duplicated file writing, inconsistent output files, and registry drift.

## Current State

- `docs/01-product-vision.md` says the MVP flow is briefing, weekly generation, 3 LinkedIn posts, carousel, prompts, networking, checklist, manual publication, metrics, and recommendations.
- `app/workflows/weekly_workflow.py` runs specialized agents and writes files `01` through `11`.
- `app/core/brandos_service.py:626` has another generation path that prompts one LLM call to produce blocks.
- `app/core/brandos_service.py:601` prepares a week from a briefing but returns hardcoded defaults such as "Sentinela RJ".
- `app/core/brandos_service.py:344` generates CMO recommendations and writes them to `data/generated/cmo-recommendations`.

## Commands You Will Need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Tests | `python -m pytest -q` | exit 0 |
| Targeted workflow tests | `python -m pytest tests/test_brandos_service.py -q` | exit 0 |
| Static search | `rg -n "Gere uma semana editorial a partir do briefing aprovado" app` | no match outside a named prompt constant or fallback |

## Scope

**In scope**:
- `app/workflows/weekly_workflow.py`
- briefing/CMO services from plan 002
- `app/prompts/workflow_prompts.py`
- existing agent files under `app/agents/`
- tests under `tests/`

**Out of scope**:
- Visual templates.
- New channels beyond LinkedIn.
- Automatic publishing.
- Real API calls in tests.

## Steps

### Step 1: Define a WeeklyGenerationRequest

Create a dataclass or typed dict representing `briefing_content`, `project`, `theme`, `start_date`, `frequency`, `source_briefing_file`, and `source_recommendation_id`.

**Status**: DONE. Implemented as `WeeklyGenerationRequest` in `app/workflows/weekly_workflow.py`.

**Verify**: `python -m pytest -q` still passes.

### Step 2: Teach `weekly_workflow.py` to accept approved briefing context

Refactor `run_weekly_workflow` so it can run in legacy mode or approved briefing mode. Keep the specialized multi-agent pipeline. Do not use a single "generate all blocks" prompt as the main path.

**Status**: DONE. `run_weekly_workflow` now accepts approved briefing context while preserving legacy mode.

**Verify**: add tests with a fake LLM or monkeypatch agents; no network calls.

### Step 3: Replace `generate_week_from_briefing` internals

Make `generate_week_from_briefing` validate the briefing, build `WeeklyGenerationRequest`, then call the unified workflow. Return a structured result with folder name, files, item IDs, and warnings.

**Status**: DONE. `BrandOSService` delegates to `BriefingService`, which validates status, builds the request, calls the workflow, and marks the briefing generated.

**Verify**: `rg -n "Gere uma semana editorial a partir do briefing aprovado" app/core app/workflows` returns no match unless it is an explicit fallback.

### Step 4: Centralize output registration

Move registry writing for generated posts into one function. It should create a week entry with nested `items` using the contract from plan 001.

Expected files:

- `01-diagnostico-cmo.md`
- `02-plano-semanal.md`
- `03-post-segunda.md`
- `04-post-quarta.md`
- `05-post-sexta.md`
- `06-carrossel.md`
- `07-prompts-imagem.md`
- `08-plano-networking.md`
- `09-checklist-publicacao.md`
- `10-comentario-linkedin.md`
- `11-instrucoes-publicacao.md`

**Verify**: a new test asserts all expected files are registered without touching real `data/`.

**Status**: DONE. `register_generated_week` creates nested registry items for segunda, quarta, and sexta using the plan 001 contract.

### Step 5: Remove hardcoded briefing defaults

Replace hardcoded defaults in `prepare_week_from_briefing` with parsing from approved briefing content. If a field is absent, return an explicit warning and a safe default.

**Status**: DONE. Metadata is parsed from briefing content; missing project/theme now returns explicit warnings and safe defaults.

**Verify**: tests for a briefing with metadata and one missing metadata.

## Done Criteria

- [x] `python -m pytest -q` exits 0. Verified: 55 passed.
- [x] There is one weekly generation path shared by CLI and approved briefing flow.
- [x] The single-call block parser is removed from the approved briefing path.
- [x] Generated week files and registry entries are consistent across entry points.
- [x] `plans/README.md` marks plan 003 as DONE.

## STOP Conditions

Stop and report if plans 001 or 002 are incomplete, tests require live Gemini, or the UI depends on the old reduced file set.
