# Meta Import Performance Strategy

This document captures the strategy and observed behavior for high-volume Meta accounts (e.g. Ancient & Brave) so we can build the final system around proven patterns.

## Goals

- Keep UX as a single import flow.
- Maximize imported media coverage.
- Maximize performance-data coverage without stalling media ingestion.
- Be resilient to Meta throttling and intermittent DB/network failures.

## Working Strategy

1. **Media ingest first (missing-only)**
   - Import job dedupes by `library_id` for `(client_id, meta_ad_account_id)`.
   - Existing media rows are skipped, not re-downloaded.
   - This is faster and avoids unnecessary IO.

2. **Performance enrichment second (targeted)**
   - Enrich only rows missing `AdImagePerformance`.
   - Use media keys from unresolved rows (`library_id`) and query targeted lookup.
   - Persist best-ad row (highest revenue, then clicks, then recency).

3. **Backfill passes for coverage**
   - Run one large targeted pass first.
   - If useful coverage remains, run chunked deeper passes.
   - Stop when coverage plateaus (no progress for consecutive passes).

## Phase Model (current implementation)

- `media_ingest`
- `performance_enrichment`
- `finalizing`

Tracked in `ImportJob.progress_payload` and surfaced to UI polling.

## Adset Data Added

Performance rows now include:

- `meta_adset_id`
- `meta_adset_name`

So UI can show adset context per creative/perf match.

## Observed Results (Ancient & Brave)

- Media ingest completed with strong dedupe behavior (large skip counts, high net-new videos).
- Initial enrichment matched a subset only; additional backfill pass significantly improved perf coverage.
- Remaining unmatched rows likely include media not linked to ads/creatives with usable insights.

## Operational Guidance

- Prefer larger enrichment page budgets for high-volume accounts.
- Use chunked passes to squeeze additional matches after initial pass.
- Keep cooldown/backoff handling for Meta rate limits.
- Treat DB connection drops as recoverable and resume from persisted checkpoint/job state.

## Productization To-Do

- Add a first-class **performance-only async job type** (start/poll/cancel/resume).
- Let UI trigger or auto-chain this after `Import all` completion.
- Show coverage metrics directly in UI:
  - total with perf
  - missing perf
  - newly matched this pass
- Add stale-job detection (heartbeat timeout) and safe resume controls.
