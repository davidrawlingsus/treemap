"""
VoC coding chain orchestration for Trustpilot process_voc rows.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from json import JSONDecodeError
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

import httpx
from json_repair import repair_json
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.prompt import Prompt

from app.services.voc_coding_chain_prompts import (
    CODE_SCHEMA,
    CODE_SYSTEM_PROMPT,
    CODE_USER_PROMPT,
    DISCOVER_SCHEMA,
    DISCOVER_SYSTEM_PROMPT,
    DISCOVER_USER_PROMPT,
    REFINE_SCHEMA,
    REFINE_SYSTEM_PROMPT,
    REFINE_USER_PROMPT,
)

logger = logging.getLogger(__name__)

VOC_DISCOVER_PROMPT_PURPOSE = "voc_discover"
VOC_CODE_PROMPT_PURPOSE = "voc_code"
VOC_REFINE_PROMPT_PURPOSE = "voc_refine"


class VocCodingChainError(RuntimeError):
    """Raised for step-aware coding-chain failures."""

    def __init__(self, step: str, message: str):
        self.step = step
        super().__init__(message)


def determine_batch_strategy(total_reviews: int, batch_size: int, discovery_cap: int) -> Dict[str, int]:
    discovery_size = min(total_reviews, max(discovery_cap, 1))
    safe_batch_size = max(batch_size, 1)
    return {
        "discovery_sample_size": discovery_size,
        "coding_batch_size": safe_batch_size,
        "total_coding_batches": (total_reviews + safe_batch_size - 1) // safe_batch_size,
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_checkpoint_dir(settings: Any) -> Path:
    configured = (getattr(settings, "voc_coding_checkpoint_dir", "") or "").strip()
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = Path.cwd() / path
    else:
        path = Path.cwd() / "tmp" / "voc-coding-checkpoints"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_checkpoint_path(settings: Any, run_id: str) -> Path:
    return _get_checkpoint_dir(settings) / f"{run_id}.json"


def _init_checkpoint_state(run_id: str, total_reviews: int, strategy: Dict[str, int]) -> Dict[str, Any]:
    now = _utc_now_iso()
    return {
        "run_id": run_id,
        "status": "in_progress",
        "started_at": now,
        "updated_at": now,
        "input_total_reviews": total_reviews,
        "batch_size": strategy["coding_batch_size"],
        "total_batches": strategy["total_coding_batches"],
        "completed_batches": [],
        "failed_batches": [],
        "codebook_v1": None,
        "codebook_v1_1": None,
        "coded_reviews_by_id": {},
        "stats": {},
        "last_error": None,
        "passes": {
            "code_v1": {"completed_batches": [], "failed_batches": [], "coded_reviews_by_id": {}},
            "recode_final": {"completed_batches": [], "failed_batches": [], "coded_reviews_by_id": {}},
        },
    }


def save_checkpoint(settings: Any, state: Dict[str, Any]) -> Path:
    state["updated_at"] = _utc_now_iso()
    path = build_checkpoint_path(settings, state["run_id"])
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return path


def load_checkpoint(settings: Any, run_id: str) -> Optional[Dict[str, Any]]:
    path = build_checkpoint_path(settings, run_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def finalize_checkpoint(settings: Any, state: Dict[str, Any]) -> Path:
    state["status"] = "completed"
    return save_checkpoint(settings, state)


def _format_reviews_for_discovery(reviews: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for row in reviews:
        meta = row.get("survey_metadata") or {}
        rating = meta.get("rating")
        reviewer = meta.get("reviewer_name", "")
        date = meta.get("review_date") or row.get("created", "")
        date_str = str(date)[:10] if date else ""
        text = (row.get("value") or "").strip()
        rid = row.get("respondent_id")
        if reviewer:
            header = f"Reviewer: {reviewer}"
        else:
            header = f"ID: {rid}"
        if date_str:
            header += f"\nDate: {date_str}"
        header += f"\nRating: {rating}"
        lines.append(f'{header}\nReview: "{text}"')
    return "\n\n---\n\n".join(lines)


def _format_reviews_for_coding(reviews: List[Dict[str, Any]]) -> str:
    """Format reviews for the classify step.

    Always includes respondent_id so the LLM can echo it back for matching.
    """
    lines: List[str] = []
    for row in reviews:
        meta = row.get("survey_metadata") or {}
        rating = meta.get("rating")
        date = meta.get("review_date") or row.get("created", "")
        date_str = str(date)[:10] if date else ""
        text = (row.get("value") or "").strip()
        rid = row.get("respondent_id")
        header = f"respondent_id: {rid}"
        reviewer = meta.get("reviewer_name", "")
        if reviewer:
            header += f"\nReviewer: {reviewer}"
        if date_str:
            header += f"\nDate: {date_str}"
        header += f"\nRating: {rating}"
        lines.append(f'{header}\nReview: "{text}"')
    return "\n\n---\n\n".join(lines)


def _extract_json_or_text_content(response: Any) -> Dict[str, Any] | str:
    """
    Extract structured JSON from Anthropic response blocks when available,
    otherwise return concatenated text content.
    """
    content_blocks = getattr(response, "content", []) or []
    chunks: List[str] = []
    for block in content_blocks:
        if isinstance(block, dict):
            maybe_json = block.get("json") or block.get("input")
            if isinstance(maybe_json, dict):
                return maybe_json
            maybe_text = block.get("text")
            if isinstance(maybe_text, str):
                chunks.append(maybe_text)
                continue

        # Anthropic structured output may arrive as output_json blocks.
        json_payload = getattr(block, "json", None)
        if isinstance(json_payload, dict):
            return json_payload

        input_payload = getattr(block, "input", None)
        if isinstance(input_payload, dict):
            return input_payload

        text = getattr(block, "text", None)
        if text:
            chunks.append(text)
            continue

        # Last-resort extraction from model dump shape.
        try:
            as_dict = block.model_dump() if hasattr(block, "model_dump") else None
            if isinstance(as_dict, dict):
                maybe_json = as_dict.get("json") or as_dict.get("input")
                if isinstance(maybe_json, dict):
                    return maybe_json
                maybe_text = as_dict.get("text")
                if isinstance(maybe_text, str):
                    chunks.append(maybe_text)
        except Exception:
            continue

    # Last fallback: inspect top-level response dump.
    try:
        response_dump = response.model_dump() if hasattr(response, "model_dump") else None
        if isinstance(response_dump, dict):
            for block in response_dump.get("content", []):
                if isinstance(block, dict):
                    maybe_json = block.get("json") or block.get("input")
                    if isinstance(maybe_json, dict):
                        return maybe_json
                    maybe_text = block.get("text")
                    if isinstance(maybe_text, str):
                        chunks.append(maybe_text)
    except Exception:
        pass
    return "".join(chunks).strip()


def call_claude_json_schema(
    *,
    settings: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    api_key = (getattr(settings, "anthropic_api_key", None) or "").strip()
    if not api_key:
        raise VocCodingChainError("config", "ANTHROPIC_API_KEY is required for voc coding chain")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key, http_client=httpx.Client(timeout=600.0))
    request_params = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "output_config": {"format": {"type": "json_schema", "schema": schema}},
    }

    try:
        response = client.messages.create(**request_params)
        parsed = _extract_json_or_text_content(response)
        if isinstance(parsed, dict):
            return parsed
        if not parsed.strip():
            raise VocCodingChainError("llm_call", "Claude returned empty content for JSON parsing")
        try:
            return json.loads(parsed)
        except JSONDecodeError as exc:
            raise VocCodingChainError(
                "llm_call",
                f"Claude returned non-JSON content (first 200 chars): {parsed[:200]}",
            ) from exc
    except TypeError:
        # Some SDK versions may not support output_config. Use tool forcing.
        tool_params = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "tools": [
                {
                    "name": "emit_json",
                    "description": "Return the final JSON output matching the schema.",
                    "input_schema": schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": "emit_json"},
        }
        response = client.messages.create(**tool_params)
        parsed = _extract_json_or_text_content(response)
        if isinstance(parsed, dict):
            return parsed

        # Last fallback: try to repair textual JSON if model ignored tool choice.
        if not parsed.strip():
            raise VocCodingChainError("llm_call", "Claude returned empty content for JSON parsing")
        repaired = repair_json(parsed)
        if not isinstance(repaired, str) or not repaired.strip():
            raise VocCodingChainError(
                "llm_call",
                f"Claude returned unparsable content (first 200 chars): {parsed[:200]}",
            )
        try:
            return json.loads(repaired)
        except JSONDecodeError as exc:
            raise VocCodingChainError(
                "llm_call",
                f"Claude repaired output still non-JSON (first 200 chars): {repaired[:200]}",
            ) from exc
    except Exception as exc:
        raise VocCodingChainError("llm_call", f"Claude call failed: {exc}") from exc


def stream_claude_json_schema(
    *,
    settings: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    temperature: float,
    max_tokens: int,
):
    """Streaming variant of call_claude_json_schema.

    Yields SSE-formatted lines:
      data: {"type":"tokens","output_tokens":<n>}
      data: {"type":"done","output":<parsed_json>,"elapsed_seconds":<f>,"usage":{"input_tokens":<n>,"output_tokens":<n>}}
    """
    import time as _time

    _log = logging.getLogger(__name__)

    api_key = (getattr(settings, "anthropic_api_key", None) or "").strip()
    if not api_key:
        raise VocCodingChainError("config", "ANTHROPIC_API_KEY is required")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key, http_client=httpx.Client(timeout=600.0))

    # Use tool-forcing for streaming (output_config not supported with stream)
    tool_params = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "tools": [
            {
                "name": "emit_json",
                "description": "Return the final JSON output matching the schema.",
                "input_schema": schema,
            }
        ],
        "tool_choice": {"type": "tool", "name": "emit_json"},
        "stream": True,
    }

    _log.info("[stream] Starting stream_claude_json_schema model=%s max_tokens=%d prompt_len=%d",
              model, max_tokens, len(user_prompt))

    start = _time.time()
    output_tokens = 0
    input_tokens = 0
    json_chunks: list[str] = []
    total_chars = 0
    last_reported = 0
    last_heartbeat = _time.time()
    event_count = 0
    bytes_yielded = 0

    try:
        import queue
        import threading

        # Send immediate heartbeat so the proxy sees data before the LLM call
        msg = f": stream-start\n\n"
        bytes_yielded += len(msg)
        _log.info("[stream] Yielding stream-start heartbeat (%d bytes)", len(msg))
        yield msg

        # Run Anthropic stream in a background thread, push events to a queue.
        # This lets us yield heartbeats from the main generator thread while
        # waiting for Anthropic to produce tokens (which can take 60-180s for
        # large prompts with 90k+ input tokens).
        event_queue: queue.Queue = queue.Queue()
        _SENTINEL = object()

        def _anthropic_reader():
            """Read Anthropic stream events and push them to the queue."""
            try:
                raw_params = {k: v for k, v in tool_params.items() if k != "stream"}
                _log.info("[stream-thread] Opening Anthropic stream...")
                with client.messages.stream(**raw_params) as anthropic_stream:
                    _log.info("[stream-thread] Anthropic stream opened, iterating...")
                    for ev in anthropic_stream:
                        event_queue.put(ev)
                    event_queue.put(_SENTINEL)  # signal end
                    _log.info("[stream-thread] Anthropic stream ended normally")
            except Exception as exc:
                _log.error("[stream-thread] Exception: %s", exc, exc_info=True)
                event_queue.put(exc)

        thread = threading.Thread(target=_anthropic_reader, daemon=True)
        thread.start()
        _log.info("[stream] Background thread started, polling queue with heartbeats...")

        # Poll the queue, yielding heartbeats every 10s while waiting
        stream_done = False
        while not stream_done:
            try:
                item = event_queue.get(timeout=10)
            except queue.Empty:
                # No event yet — send heartbeat
                now = _time.time()
                hb = f": heartbeat t={round(now - start, 1)}s events={event_count}\n\n"
                bytes_yielded += len(hb)
                _log.info("[stream] Heartbeat at %.1fs, %d events, %d bytes yielded",
                          now - start, event_count, bytes_yielded)
                yield hb
                continue

            # Check for sentinel (stream complete)
            if item is _SENTINEL:
                _log.info("[stream] Stream complete. %d events, %d json_chunks, %d output_tokens",
                          event_count, len(json_chunks), output_tokens)
                stream_done = True
                break

            # Check for exception from thread
            if isinstance(item, Exception):
                raise item

            # Process the Anthropic event
            event = item
            event_count += 1
            event_type = getattr(event, "type", "")

            if event_type == "message_start":
                usage = getattr(getattr(event, "message", None), "usage", None)
                if usage:
                    input_tokens = getattr(usage, "input_tokens", 0)
                _log.info("[stream] message_start: input_tokens=%d", input_tokens)

            elif event_type == "content_block_delta":
                delta = getattr(event, "delta", None)
                delta_type = getattr(delta, "type", "")
                if delta_type == "input_json_delta":
                    partial = getattr(delta, "partial_json", "")
                    if partial:
                        json_chunks.append(partial)
                        total_chars += len(partial)
                        output_tokens = total_chars // 4
                        if output_tokens - last_reported >= 100:
                            last_reported = output_tokens
                            msg = f"data: {json.dumps({'type': 'tokens', 'output_tokens': output_tokens})}\n\n"
                            bytes_yielded += len(msg)
                            yield msg

            elif event_type == "message_delta":
                usage = getattr(event, "usage", None)
                if usage:
                    output_tokens = getattr(usage, "output_tokens", output_tokens)

        thread.join(timeout=5)

        # Parse the accumulated JSON
        raw_json = "".join(json_chunks)
        _log.info("[stream] Parsing JSON response (%d chars)...", len(raw_json))
        try:
            parsed = json.loads(raw_json)
        except (JSONDecodeError, ValueError):
            _log.warning("[stream] JSON parse failed, attempting repair")
            repaired = repair_json(raw_json)
            parsed = json.loads(repaired) if isinstance(repaired, str) and repaired.strip() else {}

        elapsed = round(_time.time() - start, 2)
        done_msg = f"data: {json.dumps({'type': 'done', 'output': parsed, 'elapsed_seconds': elapsed, 'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens}})}\n\n"
        bytes_yielded += len(done_msg)
        _log.info("[stream] Yielding done event. elapsed=%.2fs input=%d output=%d total_bytes=%d",
                  elapsed, input_tokens, output_tokens, bytes_yielded)
        yield done_msg
        _log.info("[stream] Generator finished successfully")

    except GeneratorExit:
        elapsed = round(_time.time() - start, 2)
        _log.error("[stream] GeneratorExit — client disconnected after %.2fs, %d events, %d bytes yielded",
                   elapsed, event_count, bytes_yielded)

    except Exception as exc:
        elapsed = round(_time.time() - start, 2)
        _log.error("[stream] Exception after %.2fs: %s", elapsed, exc, exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc), 'elapsed_seconds': elapsed})}\n\n"


def call_claude_json_schema_streaming(
    *,
    settings: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    """Call Claude using the streaming path (same as prompt studio) but block until done.

    This reuses stream_claude_json_schema's background-thread + heartbeat approach
    which handles long-running calls reliably. The generator is consumed internally
    and the parsed JSON result is returned.
    """
    _log = logging.getLogger(__name__)
    result = None
    error_msg = None

    for line in stream_claude_json_schema(
        settings=settings, model=model, system_prompt=system_prompt,
        user_prompt=user_prompt, schema=schema, temperature=temperature,
        max_tokens=max_tokens,
    ):
        # Parse SSE data lines
        if not line.startswith("data: "):
            continue
        try:
            evt = json.loads(line[6:])
            if evt.get("type") == "done":
                result = evt.get("output", {})
            elif evt.get("type") == "error":
                error_msg = evt.get("message", "Unknown streaming error")
        except (json.JSONDecodeError, ValueError):
            pass

    if error_msg:
        raise VocCodingChainError("llm_call", error_msg)
    if result is None:
        raise VocCodingChainError("llm_call", "Stream ended without a done event")
    return result


def call_claude_raw_text_streaming(
    *,
    settings: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Call Claude and return raw text output (no JSON schema / tool forcing).

    Uses the same background-thread + heartbeat approach for reliability,
    but streams plain text instead of forcing output through a JSON tool.
    Better for very large outputs (50-70k chars) that don't fit well in JSON string escaping.
    """
    import time as _time
    import queue
    import threading

    _log = logging.getLogger(__name__)

    api_key = (getattr(settings, "anthropic_api_key", None) or "").strip()
    if not api_key:
        raise VocCodingChainError("config", "ANTHROPIC_API_KEY is required")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key, http_client=httpx.Client(timeout=600.0))

    params = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    _log.info("[raw-stream] Starting model=%s max_tokens=%d prompt_len=%d", model, max_tokens, len(user_prompt))

    start = _time.time()
    text_chunks: list = []
    output_tokens = 0
    input_tokens = 0
    event_queue: queue.Queue = queue.Queue()
    _SENTINEL = object()

    def _reader():
        try:
            _log.info("[raw-stream-thread] Opening Anthropic stream...")
            with client.messages.stream(**params) as stream:
                _log.info("[raw-stream-thread] Stream opened")
                for event in stream:
                    event_queue.put(event)
                event_queue.put(_SENTINEL)
                _log.info("[raw-stream-thread] Stream ended normally")
        except Exception as exc:
            _log.error("[raw-stream-thread] Exception: %s", exc)
            event_queue.put(exc)

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()

    done = False
    while not done:
        try:
            item = event_queue.get(timeout=10)
        except queue.Empty:
            continue

        if item is _SENTINEL:
            done = True
            break

        if isinstance(item, Exception):
            raise VocCodingChainError("llm_call", str(item))

        etype = getattr(item, "type", "")
        if etype == "message_start":
            msg = getattr(item, "message", None)
            if msg:
                u = getattr(msg, "usage", None)
                if u:
                    input_tokens = getattr(u, "input_tokens", 0)
                _log.info("[raw-stream] input_tokens=%d", input_tokens)
        elif etype == "content_block_delta":
            delta = getattr(item, "delta", None)
            if delta:
                text = getattr(delta, "text", "")
                if text:
                    text_chunks.append(text)
        elif etype == "message_delta":
            u = getattr(item, "usage", None)
            if u:
                output_tokens = getattr(u, "output_tokens", 0)

    thread.join(timeout=5)

    result = "".join(text_chunks)
    elapsed = round(_time.time() - start, 2)
    _log.info("[raw-stream] Complete. elapsed=%.2fs input=%d output=%d chars=%d",
              elapsed, input_tokens, output_tokens, len(result))
    return result


def _get_live_prompt_by_purpose(db: Session, purpose: str) -> Optional[Prompt]:
    purpose_lower = (purpose or "").strip().lower()
    if not purpose_lower:
        return None
    return (
        db.query(Prompt)
        .filter(func.lower(Prompt.prompt_purpose) == purpose_lower, Prompt.status == "live")
        .order_by(Prompt.version.desc(), Prompt.updated_at.desc(), Prompt.created_at.desc())
        .first()
    )


def _load_voc_prompt_chain_bundle(
    *,
    db: Optional[Session],
    use_prompt_db: bool,
    strict_prompt_db: bool,
) -> Dict[str, str]:
    fallback = {
        "discover_system": DISCOVER_SYSTEM_PROMPT,
        "discover_user": DISCOVER_USER_PROMPT,
        "code_system": CODE_SYSTEM_PROMPT,
        "code_user": CODE_USER_PROMPT,
        "refine_system": REFINE_SYSTEM_PROMPT,
        "refine_user": REFINE_USER_PROMPT,
    }

    if not use_prompt_db:
        return fallback
    if db is None:
        if strict_prompt_db:
            raise VocCodingChainError("config", "Database session is required for prompt DB lookup")
        return fallback

    discover = _get_live_prompt_by_purpose(db, VOC_DISCOVER_PROMPT_PURPOSE)
    code = _get_live_prompt_by_purpose(db, VOC_CODE_PROMPT_PURPOSE)
    refine = _get_live_prompt_by_purpose(db, VOC_REFINE_PROMPT_PURPOSE)

    missing = []
    if not discover:
        missing.append(VOC_DISCOVER_PROMPT_PURPOSE)
    if not code:
        missing.append(VOC_CODE_PROMPT_PURPOSE)
    if not refine:
        missing.append(VOC_REFINE_PROMPT_PURPOSE)
    if missing:
        if strict_prompt_db:
            raise VocCodingChainError("config", f"Missing live DB prompts for purposes: {', '.join(missing)}")
        return fallback

    bundle = {
        "discover_system": (discover.system_message or "").strip(),
        "discover_user": (discover.prompt_message or "").strip(),
        "code_system": (code.system_message or "").strip(),
        "code_user": (code.prompt_message or "").strip(),
        "refine_system": (refine.system_message or "").strip(),
        "refine_user": (refine.prompt_message or "").strip(),
    }

    invalid_fields = [key for key, value in bundle.items() if not value]
    if invalid_fields:
        raise VocCodingChainError("config", f"Prompt DB fields are empty: {', '.join(invalid_fields)}")

    return bundle


def _compute_coding_stats(codebook: Dict[str, Any], coded_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(coded_reviews)
    no_match_count = sum(1 for row in coded_reviews if row.get("status") == "NO_MATCH")
    theme_frequency: Dict[str, int] = {}
    for review in coded_reviews:
        for topic in review.get("topics", []):
            code = topic.get("code")
            if not code:
                continue
            theme_frequency[code] = theme_frequency.get(code, 0) + 1

    lane_coverage: Dict[str, int] = {}
    for category in codebook.get("categories", []):
        for theme in category.get("themes", []):
            lane = theme.get("primary_creative_lane")
            if not lane:
                continue
            lane_coverage[lane] = lane_coverage.get(lane, 0) + 1

    return {
        "total_reviews": total,
        "no_match_count": no_match_count,
        "no_match_rate": round((no_match_count / total), 4) if total else 0.0,
        "theme_frequency": theme_frequency,
        "lane_coverage": lane_coverage,
        "total_themes": sum(len(cat.get("themes", [])) for cat in codebook.get("categories", [])),
    }


def _code_reviews_in_batches(
    *,
    settings: Any,
    reviews: List[Dict[str, Any]],
    codebook: Dict[str, Any],
    state: Dict[str, Any],
    pass_name: str,
    model: str,
    system_prompt: str,
    user_prompt_template: str,
    temperature: float,
    max_tokens: int,
    strict_mode: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    batch_size = state["batch_size"]
    pass_state = state["passes"][pass_name]
    retries = max(getattr(settings, "voc_coding_retry_max_attempts", 3), 1)
    base_delay = max(getattr(settings, "voc_coding_retry_base_delay_seconds", 2), 0)

    for batch_index, start in enumerate(range(0, len(reviews), batch_size)):
        if batch_index in pass_state["completed_batches"]:
            continue

        batch = reviews[start : start + batch_size]
        batch_ids = {row.get("respondent_id") for row in batch if row.get("respondent_id")}
        review_text = _format_reviews_for_coding(batch)
        payload = None
        last_err = None
        for attempt in range(retries):
            try:
                payload = call_claude_json_schema(
                    settings=settings,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt_template.format(
                        codebook=json.dumps(codebook, ensure_ascii=True),
                        reviews=review_text,
                    ),
                    schema=CODE_SCHEMA,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                break
            except Exception as exc:
                last_err = exc
                if attempt + 1 < retries:
                    time.sleep(base_delay * (2**attempt))

        if payload is None:
            pass_state["failed_batches"].append(batch_index)
            state["failed_batches"].append(batch_index)
            state["last_error"] = {
                "step": pass_name,
                "batch_index": batch_index,
                "message": str(last_err) if last_err else "unknown coding error",
            }
            save_checkpoint(settings, state)
            if strict_mode:
                raise VocCodingChainError(pass_name, state["last_error"]["message"])
            continue

        coded_reviews = payload.get("coded_reviews", [])
        matched_reviews = [row for row in coded_reviews if row.get("respondent_id") in batch_ids]

        if len(matched_reviews) == 0 and len(batch) > 1:
            single_results: List[Dict[str, Any]] = []
            for row in batch:
                single_text = _format_reviews_for_coding([row])
                single_payload = None
                single_last_err = None
                for single_attempt in range(retries):
                    try:
                        single_payload = call_claude_json_schema(
                            settings=settings,
                            model=model,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt_template.format(
                                codebook=json.dumps(codebook, ensure_ascii=True),
                                reviews=single_text,
                            ),
                            schema=CODE_SCHEMA,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        break
                    except Exception as exc:
                        single_last_err = exc
                        if single_attempt + 1 < retries:
                            time.sleep(base_delay * (2**single_attempt))
                if single_payload is None:
                    continue
                candidate_rows = single_payload.get("coded_reviews", [])
                for candidate in candidate_rows:
                    if candidate.get("respondent_id") == row.get("respondent_id"):
                        single_results.append(candidate)
            if single_results:
                coded_reviews = single_results
                matched_reviews = single_results

        if len(matched_reviews) == 0:
            pass_state["failed_batches"].append(batch_index)
            state["failed_batches"].append(batch_index)
            state["last_error"] = {
                "step": pass_name,
                "batch_index": batch_index,
                "message": "Coding returned zero matched reviews for batch",
            }
            save_checkpoint(settings, state)
            if strict_mode:
                raise VocCodingChainError(pass_name, state["last_error"]["message"])
            continue

        for coded in coded_reviews:
            rid = coded.get("respondent_id")
            if rid:
                pass_state["coded_reviews_by_id"][rid] = coded

        pass_state["completed_batches"].append(batch_index)
        if batch_index in pass_state["failed_batches"]:
            pass_state["failed_batches"].remove(batch_index)
        save_checkpoint(settings, state)

    all_coded = list(pass_state["coded_reviews_by_id"].values())
    no_matches = [row for row in all_coded if row.get("status") == "NO_MATCH"]
    return all_coded, no_matches


def run_voc_coding_chain(
    *,
    settings: Any,
    reviews: List[Dict[str, Any]],
    product_context: Dict[str, Any],
    resume_run_id: Optional[str] = None,
    run_id_override: Optional[str] = None,
    db: Optional[Session] = None,
    use_prompt_db: bool = False,
    strict_prompt_db: bool = False,
    strict_mode: bool = True,
) -> Dict[str, Any]:
    if not reviews:
        run_id = resume_run_id or uuid.uuid4().hex
        strategy = determine_batch_strategy(total_reviews=0, batch_size=20, discovery_cap=100)
        state = _init_checkpoint_state(run_id, 0, strategy)
        state["status"] = "completed"
        path = finalize_checkpoint(settings, state)
        return {
            "run_id": run_id,
            "checkpoint_path": str(path),
            "codebook_v1": {"categories": []},
            "final_codebook": {"categories": []},
            "coded_reviews": [],
            "no_matches": [],
            "changelog": [],
            "stats": {"v1": {}, "final": {}, "improvement": {}},
        }

    batch_size = getattr(settings, "voc_coding_batch_size", 20)
    discovery_cap = getattr(settings, "voc_coding_discovery_sample_size", 100)
    strategy = determine_batch_strategy(len(reviews), batch_size, discovery_cap)

    run_id = run_id_override or resume_run_id or uuid.uuid4().hex
    prompt_bundle = _load_voc_prompt_chain_bundle(
        db=db,
        use_prompt_db=use_prompt_db,
        strict_prompt_db=strict_prompt_db,
    )
    state = load_checkpoint(settings, run_id) if resume_run_id else None
    if state is None:
        state = _init_checkpoint_state(run_id, len(reviews), strategy)
        save_checkpoint(settings, state)

    context_text = (product_context or {}).get("context_text", "")

    if not state.get("codebook_v1"):
        sample_reviews = reviews[: strategy["discovery_sample_size"]]
        discover = call_claude_json_schema(
            settings=settings,
            model=getattr(settings, "voc_coding_discover_model", "claude-sonnet-4-5-20250929"),
            system_prompt=prompt_bundle["discover_system"],
            user_prompt=prompt_bundle["discover_user"].format(
                product_context=context_text,
                review_count=len(sample_reviews),
                reviews=_format_reviews_for_discovery(sample_reviews),
            ),
            schema=DISCOVER_SCHEMA,
            temperature=float(getattr(settings, "voc_coding_discover_temperature", 0.6)),
            max_tokens=int(getattr(settings, "voc_coding_discover_max_tokens", 8192)),
        )
        state["codebook_v1"] = discover
        save_checkpoint(settings, state)

    coded_v1, no_matches_v1 = _code_reviews_in_batches(
        settings=settings,
        reviews=reviews,
        codebook=state["codebook_v1"],
        state=state,
        pass_name="code_v1",
        model=getattr(settings, "voc_coding_code_model", "claude-haiku-4-5-20251001"),
        system_prompt=prompt_bundle["code_system"],
        user_prompt_template=prompt_bundle["code_user"],
        temperature=float(getattr(settings, "voc_coding_code_temperature", 0.2)),
        max_tokens=int(getattr(settings, "voc_coding_code_max_tokens", 4096)),
        strict_mode=strict_mode,
    )
    stats_v1 = _compute_coding_stats(state["codebook_v1"], coded_v1)

    if not state.get("codebook_v1_1"):
        refined = call_claude_json_schema(
            settings=settings,
            model=getattr(settings, "voc_coding_refine_model", "claude-sonnet-4-5-20250929"),
            system_prompt=prompt_bundle["refine_system"],
            user_prompt=prompt_bundle["refine_user"].format(
                product_context=context_text,
                codebook=json.dumps(state["codebook_v1"], ensure_ascii=True),
                stats=json.dumps(stats_v1, ensure_ascii=True),
                no_matches=json.dumps(no_matches_v1, ensure_ascii=True),
            ),
            schema=REFINE_SCHEMA,
            temperature=float(getattr(settings, "voc_coding_refine_temperature", 0.4)),
            max_tokens=int(getattr(settings, "voc_coding_refine_max_tokens", 8192)),
        )
        state["codebook_v1_1"] = refined
        save_checkpoint(settings, state)

    coded_final, no_matches_final = _code_reviews_in_batches(
        settings=settings,
        reviews=reviews,
        codebook=state["codebook_v1_1"],
        state=state,
        pass_name="recode_final",
        model=getattr(settings, "voc_coding_code_model", "claude-haiku-4-5-20251001"),
        system_prompt=prompt_bundle["code_system"],
        user_prompt_template=prompt_bundle["code_user"],
        temperature=float(getattr(settings, "voc_coding_code_temperature", 0.2)),
        max_tokens=int(getattr(settings, "voc_coding_code_max_tokens", 4096)),
        strict_mode=strict_mode,
    )
    stats_final = _compute_coding_stats(state["codebook_v1_1"], coded_final)
    state["coded_reviews_by_id"] = {
        row.get("respondent_id"): row
        for row in coded_final
        if row.get("respondent_id")
    }
    state["completed_batches"] = sorted(set(state["passes"]["recode_final"]["completed_batches"]))
    state["failed_batches"] = sorted(set(state["passes"]["recode_final"]["failed_batches"]))
    state["stats"] = {
        "v1": stats_v1,
        "final": stats_final,
        "improvement": {
            "no_match_rate_change": stats_v1.get("no_match_rate", 0) - stats_final.get("no_match_rate", 0),
            "theme_count_change": stats_final.get("total_themes", 0) - stats_v1.get("total_themes", 0),
        },
    }
    path = finalize_checkpoint(settings, state)

    return {
        "run_id": run_id,
        "checkpoint_path": str(path),
        "codebook_v1": state["codebook_v1"],
        "final_codebook": state["codebook_v1_1"],
        "coded_reviews": coded_final,
        "no_matches": no_matches_final,
        "changelog": state["codebook_v1_1"].get("changelog", []),
        "stats": state["stats"],
    }


def run_new_voc_pipeline(
    *,
    settings: Any,
    reviews: List[Dict[str, Any]],
    product_context: Dict[str, Any],
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Run the new Extract → Taxonomy → Validate pipeline.

    Uses the same prompts and schemas as the Prompt Studio endpoints.
    Returns a result dict compatible with the old pipeline's shape so
    it can be consumed by merge_coded_reviews_into_rows and the payload
    builder.
    """
    from app.routers.founder_admin.prompt_studio import (
        EXTRACT_SCHEMA,
        EXTRACT_SYSTEM_PROMPT_DEFAULT,
        EXTRACT_USER_PROMPT_DEFAULT,
        TAXONOMY_SCHEMA,
        TAXONOMY_SYSTEM_PROMPT_DEFAULT,
        TAXONOMY_USER_PROMPT_DEFAULT,
        VALIDATE_SCHEMA,
        VALIDATE_SYSTEM_PROMPT_DEFAULT,
        VALIDATE_USER_PROMPT_DEFAULT,
    )

    run_id = uuid.uuid4().hex
    context_text = (product_context or {}).get("context_text", "")
    model = getattr(settings, "voc_coding_discover_model", "claude-sonnet-4-5-20250929")

    if not reviews:
        return {
            "run_id": run_id,
            "pipeline": "extract-taxonomy-validate",
            "extract_output": {"meta": {}, "signals": []},
            "taxonomy_output": {"meta": {}, "categories": []},
            "validate_output": {"meta": {}, "categories": [], "changes_made": [], "strategic_notes": []},
            "coded_reviews": [],
            "no_matches": [],
            "stats": {},
        }

    # ── Step 1: EXTRACT signals ──
    logger.info("[new-pipeline] Step 1/3: Extract signals from %d reviews", len(reviews))
    reviews_text = _format_reviews_for_discovery(reviews)
    extract_user = (EXTRACT_USER_PROMPT_DEFAULT
        .replace("{BUSINESS_CONTEXT}", context_text)
        .replace("{RAW_REVIEWS}", reviews_text)
    )
    extract_output = call_claude_json_schema(
        settings=settings,
        model=model,
        system_prompt=EXTRACT_SYSTEM_PROMPT_DEFAULT,
        user_prompt=extract_user,
        schema=EXTRACT_SCHEMA,
        temperature=0.0,
        max_tokens=64000,
    )
    signals_count = len(extract_output.get("signals", []))
    logger.info("[new-pipeline] Extract complete: %d signals", signals_count)

    # ── Step 2: TAXONOMY construction ──
    logger.info("[new-pipeline] Step 2/3: Build taxonomy from %d signals", signals_count)
    taxonomy_user = (TAXONOMY_USER_PROMPT_DEFAULT
        .replace("{BUSINESS_CONTEXT}", context_text)
        .replace("{JSON_OUTPUT_FROM_PROMPT_1}", json.dumps(extract_output, ensure_ascii=False))
        .replace("{REVIEW_COUNT}", str(signals_count))
    )
    taxonomy_output = call_claude_json_schema(
        settings=settings,
        model=model,
        system_prompt=TAXONOMY_SYSTEM_PROMPT_DEFAULT,
        user_prompt=taxonomy_user,
        schema=TAXONOMY_SCHEMA,
        temperature=0.0,
        max_tokens=64000,
    )
    cat_count = len(taxonomy_output.get("categories", []))
    logger.info("[new-pipeline] Taxonomy complete: %d categories", cat_count)

    # ── Step 3: VALIDATE & refine ──
    logger.info("[new-pipeline] Step 3/3: Validate taxonomy")
    validate_user = (VALIDATE_USER_PROMPT_DEFAULT
        .replace("{BUSINESS_CONTEXT}", context_text)
        .replace("{JSON_OUTPUT_FROM_PROMPT_2}", json.dumps(taxonomy_output, ensure_ascii=False))
        .replace("{JSON_OUTPUT_FROM_PROMPT_1}", json.dumps(extract_output, ensure_ascii=False))
    )
    validate_output = call_claude_json_schema(
        settings=settings,
        model=model,
        system_prompt=VALIDATE_SYSTEM_PROMPT_DEFAULT,
        user_prompt=validate_user,
        schema=VALIDATE_SCHEMA,
        temperature=0.0,
        max_tokens=64000,
    )
    logger.info("[new-pipeline] Validate complete: %d categories",
                len(validate_output.get("categories", [])))

    # ── Convert taxonomy → per-review coded_reviews for downstream compat ──
    coded_reviews = _taxonomy_to_coded_reviews(validate_output, reviews)

    return {
        "run_id": run_id,
        "pipeline": "extract-taxonomy-validate",
        "extract_output": extract_output,
        "taxonomy_output": taxonomy_output,
        "validate_output": validate_output,
        "final_codebook": validate_output,
        "coded_reviews": coded_reviews,
        "no_matches": [r for r in coded_reviews if r.get("status") == "NO_MATCH"],
        "changelog": validate_output.get("changes_made", []),
        "stats": {
            "categories": len(validate_output.get("categories", [])),
            "topics": sum(
                len(c.get("topics", []))
                for c in validate_output.get("categories", [])
            ),
            "signals": len(extract_output.get("signals", [])),
            "coverage_pct": validate_output.get("meta", {}).get("coverage_pct", 0),
        },
    }


def _taxonomy_to_coded_reviews(
    taxonomy: Dict[str, Any],
    reviews: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert a validated taxonomy back into per-review coded rows.

    Each review gets assigned the topics that reference its respondent_id
    in their review_ids arrays. This makes the new pipeline output
    compatible with merge_coded_reviews_into_rows.
    """
    # Build a map: review_id → list of topics
    review_topics: Dict[str, List[Dict[str, Any]]] = {}
    for cat in taxonomy.get("categories", []):
        category_name = cat.get("category", "")
        for topic in cat.get("topics", []):
            for rid in topic.get("review_ids", []):
                if rid not in review_topics:
                    review_topics[rid] = []
                review_topics[rid].append({
                    "category": category_name,
                    "label": topic.get("label", ""),
                    "code": f"{category_name}::{topic.get('label', '')}",
                    "sentiment": "mixed",
                    "headline": topic.get("label", ""),
                    "confidence": 1.0,
                })

    # Map R-001 → actual respondent_id from the reviews list
    rid_map: Dict[str, str] = {}
    for i, review in enumerate(reviews):
        synthetic_id = f"R-{i + 1:03d}"
        actual_id = review.get("respondent_id", synthetic_id)
        rid_map[synthetic_id] = actual_id

    coded: List[Dict[str, Any]] = []
    for review in reviews:
        actual_rid = review.get("respondent_id", "")
        # Find matching topics by either actual or synthetic ID
        topics = review_topics.get(actual_rid, [])
        if not topics:
            # Try synthetic ID
            idx = reviews.index(review)
            synthetic = f"R-{idx + 1:03d}"
            topics = review_topics.get(synthetic, [])

        coded.append({
            "respondent_id": actual_rid,
            "overall_sentiment": "mixed",
            "status": "CODED" if topics else "NO_MATCH",
            "topics": topics,
        })

    return coded


def merge_coded_reviews_into_rows(
    process_voc_rows: List[Dict[str, Any]],
    coded_reviews: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    coded_map = {row.get("respondent_id"): row for row in coded_reviews if row.get("respondent_id")}
    merged_rows: List[Dict[str, Any]] = []

    for row in process_voc_rows:
        merged = dict(row)
        coded = coded_map.get(row.get("respondent_id"))
        if coded:
            merged["topics"] = coded.get("topics", [])
            merged["overall_sentiment"] = coded.get("overall_sentiment")
            merged["processed"] = True
        else:
            merged["topics"] = merged.get("topics") or []
            merged["overall_sentiment"] = merged.get("overall_sentiment")
            merged["processed"] = False
        merged_rows.append(merged)
    return merged_rows


def validate_import_ready_rows(rows: List[Dict[str, Any]]) -> None:
    seen_ids = set()
    allowed_sentiments = {"positive", "negative", "mixed", None}
    for row in rows:
        rid = row.get("respondent_id")
        if not rid:
            raise VocCodingChainError("validate", "Missing respondent_id in output row")
        if rid in seen_ids:
            raise VocCodingChainError("validate", f"Duplicate respondent_id found: {rid}")
        seen_ids.add(rid)

        overall_sentiment = row.get("overall_sentiment")
        if overall_sentiment not in allowed_sentiments:
            raise VocCodingChainError("validate", f"Invalid overall_sentiment for respondent_id={rid}")

        topics = row.get("topics")
        if not isinstance(topics, list):
            raise VocCodingChainError("validate", f"topics must be an array for respondent_id={rid}")

        for topic in topics:
            if not isinstance(topic, dict):
                raise VocCodingChainError("validate", f"topic must be an object for respondent_id={rid}")
            for key in ("category", "label", "code", "sentiment"):
                if key not in topic:
                    raise VocCodingChainError("validate", f"topic missing key '{key}' for respondent_id={rid}")
