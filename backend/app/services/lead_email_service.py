"""
Lead email queue service.

Creates, schedules, sends, and manages the email series
generated from VoC analysis output.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import requests
from sqlalchemy.orm import Session

from app.models.lead_email import LeadEmail

logger = logging.getLogger(__name__)


def create_email_series(
    db: Session,
    *,
    run_id: str,
    client_id: UUID,
    email_address: str,
    voc_analysis: Dict[str, Any],
    magic_link_url: str,
    gamma_deck_url: Optional[str] = None,
) -> List[LeadEmail]:
    """Create LeadEmail records from VoC analysis output.

    D+0 is scheduled for now (sent immediately by the pipeline).
    D+1..N are scheduled one per day for the background sender.
    """
    emails_data = voc_analysis.get("emails", [])
    if not emails_data:
        logger.warning("[email-series] No emails in VoC analysis for run %s", run_id)
        return []

    now = datetime.now(timezone.utc)
    created: List[LeadEmail] = []

    for email in emails_data:
        send_day = email.get("send_day", 0)
        scheduled = now + timedelta(days=send_day)

        # Replace template placeholders in CTA URLs
        cta_url = email.get("cta_url", "")
        cta_url = cta_url.replace("{{MAGIC_LINK_URL}}", magic_link_url)
        if gamma_deck_url:
            cta_url = cta_url.replace("{{GAMMA_DECK_URL}}", gamma_deck_url)
        else:
            cta_url = cta_url.replace("{{GAMMA_DECK_URL}}", magic_link_url)

        # Build template_data from the structured content
        template_data = {
            "headline": email.get("headline", ""),
            "body_sections": email.get("body_sections", []),
            "cta_text": email.get("cta_text", ""),
            "cta_url": cta_url,
            "preview_text": email.get("preview_text", ""),
        }

        record = LeadEmail(
            run_id=run_id,
            client_id=client_id,
            email_address=email_address,
            subject=email.get("subject_line", "Your VoC Analysis"),
            preview_text=email.get("preview_text"),
            template_data=template_data,
            sequence_number=email.get("sequence_number", send_day),
            scheduled_for=scheduled,
            status="queued",
            extra_data={
                "strategic_intent": email.get("strategic_intent", ""),
                "insight_references": email.get("insight_references", []),
            },
        )
        db.add(record)
        created.append(record)

    db.flush()
    logger.info(
        "[email-series] Created %d emails for run %s (D+0 to D+%d)",
        len(created), run_id, max(e.get("send_day", 0) for e in emails_data),
    )
    return created


def send_due_emails(settings: Any, db: Session) -> int:
    """Send all queued emails whose scheduled_for has passed.

    Called by the background sender every 5 minutes.
    Returns count of emails sent.
    """
    from app.utils import build_email_service

    due = (
        db.query(LeadEmail)
        .filter(
            LeadEmail.status == "queued",
            LeadEmail.scheduled_for <= datetime.now(timezone.utc),
        )
        .order_by(LeadEmail.scheduled_for.asc())
        .limit(20)  # batch limit per cycle
        .all()
    )

    if not due:
        return 0

    email_service = build_email_service(settings)
    if not email_service or not email_service.is_configured():
        logger.warning("[email-sender] Email service not configured, skipping %d emails", len(due))
        return 0

    sent_count = 0
    for email in due:
        try:
            resend_id = _send_via_resend(email_service, email)
            email.status = "sent"
            email.sent_at = datetime.now(timezone.utc)
            email.resend_email_id = resend_id
            sent_count += 1
            logger.info("[email-sender] Sent email %s (seq %d) to %s", email.id, email.sequence_number, email.email_address)
        except Exception as e:
            email.status = "failed"
            email.error_message = str(e)[:500]
            logger.error("[email-sender] Failed to send email %s: %s", email.id, e)

    db.commit()
    return sent_count


def _send_via_resend(email_service: Any, email: LeadEmail) -> Optional[str]:
    """Send a single email via Resend API. Returns the Resend email ID."""
    td = email.template_data or {}

    # Build simple HTML from template_data sections
    html_body = _render_html(email.subject, td)
    text_body = _render_text(email.subject, td)

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {email_service.api_key}"},
        json={
            "from": email_service.from_email,
            "to": [email.email_address],
            "subject": email.subject,
            "html": html_body,
            "text": text_body,
            "reply_to": email_service.reply_to_email or email_service.from_email,
            "tags": [
                {"name": "type", "value": "lead_email_series"},
                {"name": "sequence", "value": str(email.sequence_number)},
            ],
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("id")


def _render_html(subject: str, td: Dict[str, Any]) -> str:
    """Render template_data into simple inline-CSS HTML."""
    headline = td.get("headline", subject)
    sections_html = ""
    for section in td.get("body_sections", []):
        stype = section.get("type", "text")
        content = section.get("content", "")
        if stype == "verbatim":
            attr = section.get("attribution", "")
            sections_html += f'<blockquote style="border-left:3px solid #1a73e8;padding:12px 16px;margin:16px 0;color:#555;font-style:italic;">"{content}"<br><span style="font-size:12px;color:#999;">{attr}</span></blockquote>'
        elif stype == "stat":
            sections_html += f'<div style="background:#f0f4ff;border-radius:8px;padding:16px;margin:16px 0;font-size:18px;font-weight:600;color:#1a73e8;text-align:center;">{content}</div>'
        elif stype == "cta":
            cta_url = td.get("cta_url", "#")
            cta_text = td.get("cta_text", content)
            sections_html += f'<div style="text-align:center;margin:24px 0;"><a href="{cta_url}" style="display:inline-block;background:#1a73e8;color:#fff;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:600;font-size:16px;">{cta_text}</a></div>'
        else:
            sections_html += f'<p style="margin:12px 0;line-height:1.6;color:#333;">{content}</p>'

    cta_url = td.get("cta_url", "")
    cta_text = td.get("cta_text", "")
    if cta_text and cta_url:
        sections_html += f'<div style="text-align:center;margin:30px 0;"><a href="{cta_url}" style="display:inline-block;background:#1a73e8;color:#fff;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:600;font-size:16px;">{cta_text}</a></div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.6;color:#333;max-width:600px;margin:0 auto;padding:20px;background:#f5f5f5;">
<div style="background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:30px;box-shadow:0 2px 4px rgba(0,0,0,0.1);">
<h1 style="color:#1a1a1a;font-size:22px;margin-top:0;margin-bottom:20px;">{headline}</h1>
{sections_html}
</div></body></html>"""


def _render_text(subject: str, td: Dict[str, Any]) -> str:
    """Render template_data into plain text."""
    lines = [td.get("headline", subject), ""]
    for section in td.get("body_sections", []):
        stype = section.get("type", "text")
        content = section.get("content", "")
        if stype == "verbatim":
            attr = section.get("attribution", "")
            lines.append(f'"{content}" — {attr}')
        else:
            lines.append(content)
        lines.append("")
    cta_url = td.get("cta_url", "")
    cta_text = td.get("cta_text", "")
    if cta_text and cta_url:
        lines.append(f"{cta_text}: {cta_url}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Series management
# ---------------------------------------------------------------------------

def pause_email_series(db: Session, run_id: str) -> int:
    """Pause all queued emails for a run."""
    count = (
        db.query(LeadEmail)
        .filter(LeadEmail.run_id == run_id, LeadEmail.status == "queued")
        .update({"status": "paused"})
    )
    db.commit()
    logger.info("[email-series] Paused %d emails for run %s", count, run_id)
    return count


def resume_email_series(db: Session, run_id: str) -> int:
    """Resume paused emails, recalculating schedule from today."""
    paused = (
        db.query(LeadEmail)
        .filter(LeadEmail.run_id == run_id, LeadEmail.status == "paused")
        .order_by(LeadEmail.sequence_number.asc())
        .all()
    )
    if not paused:
        return 0

    now = datetime.now(timezone.utc)
    for i, email in enumerate(paused):
        email.status = "queued"
        email.scheduled_for = now + timedelta(days=i)

    db.commit()
    logger.info("[email-series] Resumed %d emails for run %s", len(paused), run_id)
    return len(paused)


def cancel_email(db: Session, email_id: UUID) -> Optional[LeadEmail]:
    """Cancel a single unsent email."""
    email = db.query(LeadEmail).filter(LeadEmail.id == email_id).first()
    if not email:
        return None
    if email.status in ("queued", "paused"):
        email.status = "cancelled"
        db.commit()
        logger.info("[email-series] Cancelled email %s (seq %d)", email.id, email.sequence_number)
    return email


def update_email_content(
    db: Session,
    email_id: UUID,
    *,
    subject: Optional[str] = None,
    template_data: Optional[Dict] = None,
) -> Optional[LeadEmail]:
    """Update content of an unsent email."""
    email = db.query(LeadEmail).filter(LeadEmail.id == email_id).first()
    if not email or email.status not in ("queued", "paused"):
        return None

    if subject is not None:
        email.subject = subject
    if template_data is not None:
        email.template_data = template_data
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(email, "template_data")

    db.commit()
    return email
