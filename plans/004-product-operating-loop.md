# Plan 004: Turn BrandOS into a useful marketing operating loop

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If any STOP condition occurs, stop and report; do not improvise.
>
> **Drift check (run first)**: `git diff --stat 852c752..HEAD -- docs app/core/services app/web/routes app/web/templates tests`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: `plans/001-stabilize-publication-registry.md`, `plans/002-split-brandos-service.md`, `plans/003-unify-cmo-briefing-weekly-pipeline.md`
- **Category**: direction, docs, tech-debt
- **Status**: DONE on 2026-07-07
- **Planned at**: commit `852c752`, 2026-07-06

## Why This Matters

BrandOS already has CMO recommendations, briefings, calendar, generated posts, assets, publication assistant, metrics, editorial learning, and strategic memory. The user problem is that these do not yet feel like one daily workflow. This plan adds a thin orchestration layer for the product experience before adding more features.

## Current State

- `README.md` advertises a Web Console, Asset Manager, metrics, dashboard, agenda, and full publication workflow.
- `docs/01-product-vision.md` says the rule of gold is whether a feature helps Leandro build networking, authority, portfolio, or opportunities.
- `docs/04-roadmap.md` warns against jumping too early into dashboard/interface complexity.
- The app already has routes for dashboard, calendar, briefings, CMO recommendations, generated weeks, publications, publishing, ops, history, settings, strategic memory, and projects.

## Commands You Will Need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Tests | `python -m pytest -q` | exit 0 |
| Route import check | `python -c "import app.web.server; print('ok')"` | prints `ok` |

## Scope

**In scope**:
- New `app/core/services/operating_loop_service.py`
- Dashboard route/template or a new home route/template.
- Tests for the new service.
- Optional docs update in `docs/04-roadmap.md` or a new prioritization doc.

**Out of scope**:
- New LLM agents.
- LinkedIn API.
- Scraping.
- A full analytics dashboard rewrite.
- Multi-user/login.

## Steps

### Step 1: Define the operating loop states

Create `get_today_operating_loop()` returning:

- `next_action`: one of `publish_due`, `capture_metrics`, `review_generated`, `approve_briefing`, `generate_cmo_recommendation`, `create_next_briefing`, `write_new_post`, or `idle`.
- `reason`
- `primary_item`
- `secondary_actions`
- `warnings`

Use existing services and repository data. Do not make LLM calls.

**Status**: DONE. Implemented in `app/core/services/operating_loop_service.py`.

**Verify**: unit tests cover at least four states.

### Step 2: Add a focused home/dashboard section

Display today's next action, due publications, due metrics captures, approved briefing waiting for generation, last CMO recommendation, and last editorial learning.

Keep the UI restrained and operational.

**Status**: DONE. Dashboard now shows today's next action, shortcuts, due publications, due metrics, approved briefings, latest CMO recommendation, and latest editorial learning.

**Verify**: `python -c "import app.web.server; print('ok')"` prints `ok`.

### Step 3: Add metric reminder logic

Use existing fields such as `published_at`, `post_publish_tracking_status`, `metrics_due_24h_at`, `metrics_due_48h_at`, `metrics_due_7d_at`, and `last_metrics_imported_at`.

Return links to existing item detail or publication assistant instead of creating a new metrics flow.

**Status**: DONE. Metric reminders use existing tracking fields and link back to existing publication detail.

**Verify**: tests cover posts due now, not due yet, and completed tracking.

### Step 4: Add a small feature decision doc

Document that every proposed feature is classified as `Now`, `Next`, `Later`, or `No`.

- `Now`: improves the operating loop directly.
- `Next`: improves quality or reduces manual work.
- `Later`: portfolio/product expansion.
- `No`: adds complexity without improving publishing, reputation, portfolio, or networking.

**Verify**: `git diff -- docs` shows the intentional docs change.

**Status**: DONE. `docs/04-roadmap.md` now classifies ideas as `Now`, `Next`, `Later`, or `No`.

## Suggested Feature Backlog After This Plan

- Campaign mode: a 30-day campaign around one project.
- Post quality score: clarity, specificity, proof, CTA, tone, and "AI smell".
- Project-to-content importer from local README/commits.
- Manual LinkedIn metrics assistant with 24h, 48h, and 7d reminders.
- Publication bundle export: post text, first comment, assets, hashtags, links, and checklist.

## Done Criteria

- [x] `python -m pytest -q` exits 0. Verified: 62 passed.
- [x] The dashboard/home experience clearly tells the user what to do next.
- [x] No new LLM calls are added.
- [x] The backlog is classified by product value, not by excitement.
- [x] `plans/README.md` marks plan 004 as DONE.

## STOP Conditions

Stop and report if plans 001 through 003 are incomplete, the operating loop requires another registry schema change, or the UI work expands into a broad dashboard redesign.
