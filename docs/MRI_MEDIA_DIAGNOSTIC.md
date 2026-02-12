# MRI Media Diagnostic Instrumentation

Diagnostic logging for diagnosing why images and videos are not scraped, saved, or rendered in Creative MRI reports.

## Log file

After running an import and/or MRI report, check:

```
.cursor/mri_media_diagnostic.log
```

Each line is a JSON object. Phases:

| Phase | Events | What it tells you |
|-------|--------|-------------------|
| **scrape** | start, extract, done | Whether the scraper found ad cards and media URLs. `extract` shows per-ad media counts and sample URLs. |
| **import** | save_ad, done, error | Whether media was saved to DB per ad. `save_ad` shows ad_id, media_count, sample URLs. |
| **mri** | path, video_phase_start, video_phase_skipped, video_item_before, video_item_after, ads_built, load_ads, ad_to_dict, report_serialized | path: stream vs background. video_phase_*: analysis phase. video_item_*: per-video before/after Gemini. ads_built: sample of media_items when building for pipeline. |
| **gemini** | video_download, image_download, video_analysis | video_download/image_download: HTTP status, content length, errors. video_analysis: has_transcript, transcript_len when Gemini returns analysis. |
| **mri** | report_fetched | When a stored report is fetched (GET). Shows ads_count, ads_with_media, sample (with vid_has_analysis, vid_has_transcript per ad). Use for diagnosing old reports. |

## How to trace a failure

1. **No media at all**
   - Check `scrape/extract`: `ad_cards_with_media`, `total_media_items`. If 0, the scraper isn't finding media (Meta DOM may have changed).
   - Check `scrape/extract` → `media_summary`: per-ad `videos`, `images`, `media_thumbnail_url`. If all empty, `findMediaInContainer` isn't matching.

2. **Media scraped but not saved**
   - Check `import/save_ad`: `media_count` and `media_urls_sample`. If save_ad has media but mri/load_ads shows 0, something failed between import and MRI load.

3. **Media saved but not in report**
   - Check `mri/load_ads`: `ads_media_summary` shows what each ad had when loaded.
   - Check `mri/ad_to_dict`: `media_items_count` per ad.
   - Check `mri/report_serialized`: `ads_with_media` vs `ads_count`.

4. **Media in report but not rendering**
   - Add `?mri_debug=1` to the URL when viewing the report.
   - Open browser console: each ad logs `ad_id`, `media_items_count`, `resolved_url`, `source`. If `source: 'none'`, the report has no URL for that ad.

5. **Gemini analysis failing**
   - Check `gemini/video_download` and `gemini/image_download`: `status`, `content_length`, `error`. Status 403/404 or connection errors mean Meta CDN URLs may be expired or blocked.

6. **Video transcripts not showing**
   - Check `gemini/video_analysis`: `has_transcript`, `transcript_len` when Gemini returns. If has_transcript=false for all, Gemini may be returning null (silent/music-only videos).
   - Check `mri/report_serialized`: `videos_with_analysis`, `videos_with_transcript`. If both 0, Gemini wasn't run or failed.
   - Check `mri/report_fetched` when loading a stored report: `sample_ads_media` → `vid_has_analysis`, `vid_has_transcript`. If false, report was created before video analysis or analysis failed.
   - Add `?mri_debug=1` to the URL and open browser console: `[MRI transcript]` logs show per-ad `has_video`, `has_analysis`, `has_transcript`, `analysis_keys`.

## Clearing the log

To start fresh before a new run:

```bash
rm -f .cursor/mri_media_diagnostic.log
```

## Example flow

1. Clear log: `rm -f .cursor/mri_media_diagnostic.log`
2. Run a new Ad Library import (or use existing).
3. Run a Creative MRI report.
4. Inspect `.cursor/mri_media_diagnostic.log`.
5. If viewing an existing report: add `?mri_debug=1` and check browser console.
