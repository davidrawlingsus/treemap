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
    screenshot_url: Optional[str] = None,
) -> List[LeadEmail]:
    """Create LeadEmail records from VoC analysis output.

    D+0 is scheduled for now (sent immediately by the pipeline).
    D+1..N are scheduled one per day for the background sender.
    """
    emails_data = voc_analysis.get("emails", [])
    if not emails_data:
        logger.warning("[email-series] No emails in VoC analysis for run %s", run_id)
        return []

    # Skip if emails already exist for this run (prevent duplicates on re-trigger)
    existing = db.query(LeadEmail).filter(LeadEmail.run_id == run_id).count()
    if existing:
        logger.info("[email-series] %d emails already exist for run %s, skipping creation", existing, run_id)
        return []

    now = datetime.now(timezone.utc)
    created: List[LeadEmail] = []

    for email in emails_data:
        send_day = email.get("send_day", 0)
        # Email 1 always sends immediately regardless of send_day
        if email.get("sequence_number", 0) == 1:
            send_day = 0
        scheduled = now + timedelta(days=send_day)

        # Replace template placeholders throughout
        def _replace_placeholders(text: str) -> str:
            if not text:
                return text
            text = text.replace("{{MAGIC_LINK_URL}}", magic_link_url)
            text = text.replace("{{visualisation_url}}", magic_link_url)
            if screenshot_url:
                text = text.replace("{{screenshot_url}}", screenshot_url)
            text = text.replace("{{deck_url}}", gamma_deck_url or magic_link_url)
            if gamma_deck_url:
                text = text.replace("{{GAMMA_DECK_URL}}", gamma_deck_url)
            else:
                text = text.replace("{{GAMMA_DECK_URL}}", magic_link_url)
            return text

        cta_url = _replace_placeholders(email.get("cta_url") or "")

        # Replace placeholders in body section content
        body_sections = []
        for sec in email.get("body_sections", []):
            body_sections.append({
                **sec,
                "content": _replace_placeholders(sec.get("content", "")),
            })

        # Build template_data from the structured content
        template_data = {
            "headline": _replace_placeholders(email.get("headline", "")),
            "body_sections": body_sections,
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


def test_send_all(settings: Any, db: Session, run_id: str, test_email: str) -> int:
    """Send all emails in a series to a test address immediately (does not change status)."""
    from app.utils import build_email_service

    emails = (
        db.query(LeadEmail)
        .filter(LeadEmail.run_id == run_id)
        .order_by(LeadEmail.sequence_number.asc())
        .all()
    )
    if not emails:
        return 0

    email_service = build_email_service(settings)
    if not email_service or not email_service.is_configured():
        raise ValueError("Email service not configured")

    sent = 0
    for email in emails:
        td = email.template_data or {}
        html_body = _render_html(email.subject, td)
        text_body = _render_text(email.subject, td)

        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {email_service.api_key}"},
            json={
                "from": "David Rawlings <david@mapthegap.ai>",
                "to": [test_email],
                "subject": f"[TEST {email.sequence_number}] {email.subject}",
                "html": html_body,
                "text": text_body,
                "reply_to": "david@mapthegap.ai",
                "tags": [
                    {"name": "type", "value": "lead_email_test"},
                    {"name": "sequence", "value": str(email.sequence_number)},
                ],
            },
            timeout=15,
        )
        resp.raise_for_status()
        sent += 1
        logger.info("[test-send] Sent test email %d/%d to %s", sent, len(emails), test_email)

    return sent


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
            "from": "David Rawlings <david@mapthegap.ai>",
            "to": [email.email_address],
            "subject": email.subject,
            "html": html_body,
            "text": text_body,
            "reply_to": "david@mapthegap.ai",
            "headers": {
                "List-Unsubscribe": "<mailto:david@mapthegap.ai?subject=unsubscribe>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
            "tags": [
                {"name": "type", "value": "lead_email_series"},
                {"name": "sequence", "value": str(email.sequence_number)},
            ],
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("id")


def _md_to_html(text: str) -> str:
    """Convert markdown italics (_text_) to HTML <em> tags, and auto-link bare URLs."""
    import re
    # Italics
    text = re.sub(r'(?<!\w)_([^_]+?)_(?!\w)', r'<em>\1</em>', text)
    # Auto-link bare URLs (not already inside an href)
    text = re.sub(
        r'(?<!href=")(https?://[^\s<>"]+)',
        r'<a href="\1" style="color:#1a73e8;">\1</a>',
        text,
    )
    return text


def _strip_md(text: str) -> str:
    """Strip markdown italics for plain text output."""
    import re
    return re.sub(r'(?<!\w)_([^_]+?)_(?!\w)', r'\1', text)


def _render_html(subject: str, td: Dict[str, Any]) -> str:
    """Render template_data into plain-text-style HTML (no fancy formatting)."""
    sections_html = ""
    pdf_url = td.get("cta_url", "")
    for section in td.get("body_sections", []):
        stype = section.get("type", "text")
        content = _md_to_html(section.get("content", ""))
        # Verbatim sections: wrap in italics with quotes
        if stype == "verbatim":
            # Strip any existing quotes to avoid doubling
            clean = content.strip().strip('"').strip('\u201c').strip('\u201d').strip()
            sections_html += f'<p style="margin:12px 0;line-height:1.6;color:#333;"><em>"{clean}"</em></p>'
            continue
        # Insert PDF link on the specific anchor phrase
        if pdf_url and "this is what it looks like when someone organises it" in content.lower():
            import re
            content = re.sub(
                r"(?i)(this is what it looks like when someone organises it)",
                f'<a href="{pdf_url}" style="color:#1a73e8;">\\1</a>',
                content,
            )
        sections_html += f'<p style="margin:12px 0;line-height:1.6;color:#333;">{content}</p>'

    unsub = '<p style="margin:40px 0 0;font-size:11px;color:#a0aec0;">Not useful? <a href="mailto:david@mapthegap.ai?subject=unsubscribe" style="color:#a0aec0;">Unsubscribe</a></p>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.6;color:#333;max-width:600px;margin:0 auto;padding:20px;">
{sections_html}
{unsub}
</body></html>"""


def _render_text(subject: str, td: Dict[str, Any]) -> str:
    """Render template_data into plain text."""
    lines = []
    pdf_url = td.get("cta_url", "")
    for section in td.get("body_sections", []):
        stype = section.get("type", "text")
        content = _strip_md(section.get("content", ""))
        if stype == "verbatim":
            clean = content.strip().strip('"').strip('\u201c').strip('\u201d').strip()
            lines.append(f'"{clean}"')
        else:
            lines.append(content)
        # Add PDF link after the anchor phrase
        if pdf_url and "this is what it looks like when someone organises it" in content.lower():
            lines.append(pdf_url)
        lines.append("")
    lines.append("")
    lines.append("Not useful? Reply 'unsubscribe' to stop these emails.")
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


def reassign_email_series(
    db: Session,
    run_id: str,
    email_addresses: List[str],
) -> int:
    """Re-assign a series to new recipient(s) and restart the schedule.

    Cancels all existing queued/paused emails, then creates fresh copies
    of them for each email address with a new D+0, D+1, D+2... schedule.
    """
    import copy as _copy

    # Grab unsent emails as templates before cancelling
    unsent = (
        db.query(LeadEmail)
        .filter(
            LeadEmail.run_id == run_id,
            LeadEmail.status.in_(["queued", "paused"]),
        )
        .order_by(LeadEmail.sequence_number.asc())
        .all()
    )
    if not unsent:
        logger.warning("[email-series] No unsent emails to reassign for run %s", run_id)
        return 0

    # Snapshot the data we need before cancelling
    templates = []
    for em in unsent:
        templates.append({
            "client_id": em.client_id,
            "subject": em.subject,
            "preview_text": em.preview_text,
            "template_data": _copy.deepcopy(em.template_data) if em.template_data else None,
            "sequence_number": em.sequence_number,
            "extra_data": _copy.deepcopy(em.extra_data) if em.extra_data else None,
        })

    # Cancel existing unsent emails
    for em in unsent:
        em.status = "cancelled"
    db.flush()

    now = datetime.now(timezone.utc)
    created = 0

    for addr in email_addresses:
        addr = addr.strip()
        if not addr:
            continue
        for i, tpl in enumerate(templates):
            record = LeadEmail(
                run_id=run_id,
                client_id=tpl["client_id"],
                email_address=addr,
                subject=tpl["subject"],
                preview_text=tpl["preview_text"],
                template_data=tpl["template_data"],
                sequence_number=tpl["sequence_number"],
                scheduled_for=now + timedelta(days=i),
                status="queued",
                extra_data=tpl["extra_data"],
            )
            db.add(record)
            created += 1

    db.commit()
    logger.info(
        "[email-series] Reassigned run %s to %d recipient(s), created %d emails",
        run_id, len(email_addresses), created,
    )
    return created
