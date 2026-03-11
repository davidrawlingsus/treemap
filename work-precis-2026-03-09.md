# Detailed Précis - 2026-03-09

Built from planning docs in `prompts/voc_coding_chain.md`, `prompts/step1_discover.json`, `prompts/step2_code.json`, `prompts/step3_refine.json`, plus chat history in [Lead-Gen VOC build/debug](ef9fe393-2255-4683-9a93-d3533659b066).

## 1) Strategic Direction Finalized

- Confirmed lead-gen architecture: public no-auth Trustpilot intake, transform to import-ready VoC rows, run LLM coding chain, persist lead outputs separately from client production data.
- Chose separate staging tables (`leadgen_voc_runs`, `leadgen_voc_rows`) over a `lead_gen` flag in `process_voc`, to keep onboarding/upgrade flows clean.
- Aligned implementation with the 4-step coding pipeline from planning docs: Discover -> Code -> Refine -> Re-code with batching/checkpointing.

## 2) Backend Foundation Implemented

- Added lead-gen models, schemas, services, and routers:
  - `backend/app/models/leadgen_voc.py`
  - `backend/app/services/leadgen_voc_service.py`
  - `backend/app/routers/public_leadgen.py`
  - `backend/app/routers/founder_admin/leadgen_voc.py`
  - `backend/app/routers/voc_leads.py`
  - `backend/app/schemas/leadgen_voc.py`
  - `backend/app/schemas/public_leadgen.py`
- Wired routes into app entrypoints (`backend/app/main.py`, `backend/app/routers/founder_admin/__init__.py`).
- Applied/validated migration path for lead-gen staging tables.

## 3) Public Trustpilot + LLM Processing Flow Delivered

- Built end-to-end intake flow:
  - Parse work email/domain.
  - Build/fallback company context.
  - Fetch Trustpilot reviews via Apify.
  - Normalize reviews into import-ready `process_voc`-shaped rows.
  - Run coding chain and merge coded topics/sentiment.
  - Persist run + rows for founder inspection.
- Added robustness:
  - Context extraction fallback when site crawl/context fails.
  - Retry behavior for problematic coding batches.
  - Validation for import-ready row quality.

## 4) Founder Admin + Visualization Integration Completed

- Refactored founder admin UX:
  - Moved lead runs to dedicated page `founder_leadgen_runs.html`.
  - Changed crowded menu layout to list-style.
- Added leads visibility in main visualization app:
  - New Clients | Leads toggle in `index.html`.
  - Lead-mode data loading via `js/services/api-leadgen-voc.js`.
  - Insights guarded in Leads mode to avoid invalid client-insights calls.
- Added intake progress UI:
  - `trustpilot-intake.html`
  - `styles/trustpilot-intake.css`
  - `js/controllers/trustpilot-intake-controller.js`

## 5) Major Debugging Cycles Resolved (Runtime-Evidence Driven)

- Fixed mode-toggle regressions and stale-render issues in `index.html`:
  - URL mode/state conflicts.
  - Event-handler collisions between client and lead selectors.
  - Missing reload on switch back to Clients.
  - Leads-mode insights 404 behavior.
- Fixed review count limitations in Trustpilot ingestion:
  - Removed hard cap behavior caused by one-page fetch logic in `backend/app/services/trustpilot_apify_service.py`.
  - Increased backend review cap default in `backend/app/config.py` (`apify_max_reviews` to `250`).
- Fixed client restore bug when switching Leads -> Clients:
  - Added and persisted last known Clients selection logic in `index.html`.
  - Prevented fallback to Martin Randall Travel when prior client should be restored.

## 6) Tests and Verification

- Added/updated backend tests:
  - `backend/tests/test_public_leadgen.py`
  - `backend/tests/test_leadgen_voc_routes.py`
  - `backend/tests/test_voc_coding_chain_service.py`
- Repeated instrumented reproduce/fix/verify loops and removed instrumentation after confirmation.

## 7) Git/Delivery Status

- Created and pushed major feature commit to `master`:
  - `ebe3043` - lead-gen staging workflows + leads visualization mode.
- Left unrelated/unwanted files uncommitted at push time (`backend/tmp/`, `mapthegap_prospect_list.xlsx`).
- Continued post-push fixes (review cap + client toggle restore) were implemented afterward and should be included in the next commit/push batch if not already.

## 8) Prompt Iteration Workflow (Founder Prompt Engineering + Re-run)

- Implemented founder workflow to iterate on chain prompts in Prompt Engineering and reprocess existing lead runs without creating duplicates.
- Added founder rerun endpoint:
  - `POST /api/founder-admin/leadgen-runs/{run_id}/rerun`
  - Reuses stored `leadgen_voc_rows` (no Apify refetch), re-codes, and overwrites same `run_id` via upsert.
  - Includes single-flight protection (returns `409` if same run is already being reprocessed).

### DB Prompt Source of Truth for VOC Chain

- Added DB prompt loading bridge in `backend/app/services/voc_coding_chain_service.py`.
- Chain now resolves live prompts by `prompt_purpose`:
  - `voc_discover`
  - `voc_code`
  - `voc_refine`
- Public leadgen path in `backend/app/routers/public_leadgen.py` now attempts DB prompts first with fallback to built-in prompt constants.
- Founder rerun path requires DB prompts strictly (fails fast if missing/invalid), ensuring reruns reflect prompt-engineering edits.

### Founder Lead Runs UI Updates

- Updated `founder_leadgen_runs.html`:
  - Added `Re-run` button per run.
  - Added status messaging for rerun actions.
  - Added direct link to prompt editing: `/founder_prompt_engineering.html?prompt_search=voc_`.
- Updated `styles/founder-leadgen-runs.css` with rerun action styling and row action layout.
- Updated `js/prompt-engineering/main.js` to support URL-driven filtering (`prompt_search`, `status`) so VOC prompts can be opened quickly.

### Additional API/Service Updates

- Added `delete_leadgen_run` helper in `backend/app/services/leadgen_voc_service.py`.
- Extended `backend/app/routers/founder_admin/leadgen_voc.py` with both:
  - run delete endpoint
  - run rerun endpoint

### Tests for New Workflow

- Extended `backend/tests/test_leadgen_voc_routes.py` with:
  - rerun success path
  - rerun 404 path
  - rerun prompt-config failure path
  - overwrite semantics on same `run_id`
- Extended `backend/tests/test_voc_coding_chain_service.py` with prompt bundle fallback/strict-mode tests.
- Verified with:
  - `./venv/bin/pytest tests/test_leadgen_voc_routes.py tests/test_voc_coding_chain_service.py`
  - Result: 14 passed.
