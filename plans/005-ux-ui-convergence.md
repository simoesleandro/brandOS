# Plan 005: UX/UI convergence for the operating loop

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: `plans/001-stabilize-publication-registry.md`, `plans/002-split-brandos-service.md`, `plans/003-unify-cmo-briefing-weekly-pipeline.md`, `plans/004-product-operating-loop.md`
- **Category**: ux, ui, product
- **Status**: DONE
- **Started at**: 2026-07-07

## Why This Matters

The backend flow now converges, but the interface still feels like several dashboards sharing a theme. This plan makes the UI communicate one product loop: decide, create, review, publish, measure, learn.

## Design Direction

- **Subject**: a solo marketing operations cockpit for Leandro's LinkedIn routine.
- **Audience**: one operator who needs clarity, not decoration.
- **Single job**: answer what to do next and where each artifact sits in the content loop.
- **Signature element**: an `Operating Runway` showing CMO → briefing → week → publication → metrics → learning.

## Scope

- Design tokens and shared CSS in `app/web/static/css/brandos.css`.
- Dashboard/home hierarchy.
- CMO recommendations, briefings, generated week, and ops pages where convergence improves navigation.
- No new backend behavior unless needed to support display.

## Done Criteria

- [x] The home page leads with action, not vanity metrics.
- [x] Main workflow pages share the same section language and component style.
- [x] Cards/buttons/badges use consistent classes on the updated workflow pages.
- [x] The visual style is calmer and more operational.
- [x] `python -m pytest -q` exits 0. Verified: 62 passed.
- [x] `python -c "import app.web.server; print('ok')"` prints `ok`.

## Implemented

- Added operating UI tokens and components in `app/web/static/css/brandos.css`.
- Replaced the home hero with a focused operating-loop header and runway.
- Aligned CMO recommendations, briefings, and generated-week review pages with the same workflow language.
- Aligned Ops Dashboard as the daily operating panel instead of a separate technical board.
- Aligned Publish Assistant as step 04 of the loop: content, assets, directions, confirmation.
- Aligned Publications, Publication Detail, and Editorial Calendar with the same operational header, action buttons, and list/card language.
- Aligned deep workflow screens: Item Detail, Briefing Detail, CMO Recommendation Detail, Strategic Memory List, and Strategic Memory Detail.
- Aligned support screens: Manual Generation, History, Briefing Edit, Editorial Learning, Projects, Settings, and Error state.
- Preserved the existing backend behavior and added no LLM calls.
- Render-checked the updated templates with representative data.
