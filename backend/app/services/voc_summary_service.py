"""
Build VOC summary (categories, topics, counts, sample verbatims) for comparison.
Shared by VOC summary endpoint and VOC vs Ads comparison.
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models import ProcessVoc, Client

VOC_SUMMARY_SAMPLE_VERBATIMS = 10


def build_voc_summary_dict(
    db: Session,
    client_uuid: Optional[UUID] = None,
    data_source: Optional[str] = None,
    project_name: Optional[str] = None,
    dimension_ref: Optional[str] = None,
    dimension_refs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build VOC summary as a dict: categories, total_verbatims.
    Same shape as VocSummaryResponse for use by comparison service.
    """
    query = db.query(ProcessVoc).filter(
        ProcessVoc.value.isnot(None),
        ProcessVoc.value != "",
    )
    if client_uuid:
        client = db.query(Client).filter(Client.id == client_uuid).first()
        if client:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    ProcessVoc.client_uuid == client_uuid,
                    ProcessVoc.client_name == client.name,
                )
            )
        else:
            query = query.filter(ProcessVoc.client_uuid == client_uuid)
    if data_source:
        query = query.filter(ProcessVoc.data_source == data_source)
    if project_name:
        query = query.filter(ProcessVoc.project_name == project_name)
    if dimension_refs:
        query = query.filter(ProcessVoc.dimension_ref.in_(dimension_refs))
    elif dimension_ref:
        query = query.filter(ProcessVoc.dimension_ref == dimension_ref)

    rows = query.all()
    category_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    total_verbatims = 0

    for row in rows:
        val = (row.value or "").strip()
        if not val:
            continue
        total_verbatims += 1
        topics = row.topics or []
        for t in topics:
            if not t or not isinstance(t, dict):
                continue
            cat = (t.get("category") or "").strip()
            label = (t.get("label") or "").strip()
            if not cat or not label:
                continue
            code = t.get("code")
            if cat not in category_map:
                category_map[cat] = {}
            if label not in category_map[cat]:
                category_map[cat][label] = {"code": code, "verbatims": []}
            category_map[cat][label]["verbatims"].append(val)

    categories: List[Dict[str, Any]] = []
    for cat_name in sorted(category_map.keys()):
        topics_list: List[Dict[str, Any]] = []
        for topic_label in sorted(category_map[cat_name].keys()):
            data = category_map[cat_name][topic_label]
            verbatims = data["verbatims"]
            sample = verbatims[:VOC_SUMMARY_SAMPLE_VERBATIMS]
            topics_list.append({
                "label": topic_label,
                "code": data.get("code"),
                "verbatim_count": len(verbatims),
                "sample_verbatims": sample,
            })
        categories.append({"name": cat_name, "topics": topics_list})

    return {"categories": categories, "total_verbatims": total_verbatims}
