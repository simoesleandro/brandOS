# Plan 006: CMO inbox pruning and actionable recommendations

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: `plans/003-unify-cmo-briefing-weekly-pipeline.md`, `plans/005-ux-ui-convergence.md`
- **Category**: product, cmo, ux
- **Status**: DONE
- **Started at**: 2026-07-07

## Why This Matters

The CMO section was technically useful but product-confusing: it showed generated files, test duplicates, and old draft recommendations as if they were all current user decisions. For the operator, CMO should be a decision inbox, not a file archive.

## Design Direction

- Show one actionable recommendation as the next decision.
- Keep older recommendations accessible, but out of the main path.
- Deduplicate local index noise without deleting generated files.
- Mark a recommendation as used once it becomes a briefing.
- Provide a maintenance action to archive stale/duplicate recommendations.

## Done Criteria

- [x] CMO list has a single active recommendation area.
- [x] Duplicate recommendations are hidden from the primary UI.
- [x] Recommendations that become briefings move out of the active queue.
- [x] Old recommendations can be archived in one action.
- [x] Existing archive/read/create briefing flows still work.
- [x] Tests cover inbox shaping, stale archiving, and briefing-created state.
- [x] `python -m pytest -q` exits 0. Verified: 65 passed.

## Implemented

- Added `CmoService.list_recommendation_inbox()` for active recommendation, history, archived, and duplicate count.
- Added `CmoService.archive_stale_recommendations()` to keep only the newest actionable recommendation active.
- Added `CmoService.mark_recommendation_briefing_created()` and called it from briefing creation.
- Added `/cmo/recommendations/archive-stale`.
- Rebuilt `cmo_recommendation_list.html` as an actionable inbox: next decision first, history collapsed, archived collapsed.
- Added global JS handler `archiveStaleCmoRecommendations`.
- Added CMO service tests for deduplication, stale archiving, and briefing-created state.
