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
        rating = row.get("survey_metadata", {}).get("rating")
        text = (row.get("value") or "").strip()
        rid = row.get("respondent_id")
        lines.append(f'ID: {rid}\nRating: {rating}\nReview: "{text}"')
    return "\n\n---\n\n".join(lines)


def _format_reviews_for_coding(reviews: List[Dict[str, Any]]) -> str:
    return _format_reviews_for_discovery(reviews)


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

    client = Anthropic(api_key=api_key, http_client=httpx.Client(timeout=180.0))
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
                    system_prompt=CODE_SYSTEM_PROMPT,
                    user_prompt=CODE_USER_PROMPT.format(
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
                            system_prompt=CODE_SYSTEM_PROMPT,
                            user_prompt=CODE_USER_PROMPT.format(
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

    run_id = resume_run_id or uuid.uuid4().hex
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
            system_prompt=DISCOVER_SYSTEM_PROMPT,
            user_prompt=DISCOVER_USER_PROMPT.format(
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
        temperature=float(getattr(settings, "voc_coding_code_temperature", 0.2)),
        max_tokens=int(getattr(settings, "voc_coding_code_max_tokens", 4096)),
        strict_mode=strict_mode,
    )
    stats_v1 = _compute_coding_stats(state["codebook_v1"], coded_v1)

    if not state.get("codebook_v1_1"):
        refined = call_claude_json_schema(
            settings=settings,
            model=getattr(settings, "voc_coding_refine_model", "claude-sonnet-4-5-20250929"),
            system_prompt=REFINE_SYSTEM_PROMPT,
            user_prompt=REFINE_USER_PROMPT.format(
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
