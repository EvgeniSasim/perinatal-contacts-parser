from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Institution, MailCampaign
from app.services.query import query_institutions

PLACEHOLDER = re.compile(r"\{\{\s*(name|city|region|chief|address)\s*\}\}")


def render_template(text: str, inst: Institution) -> str:
    """Подставить данные учреждения в шаблон.

    Обращение по ФИО главврача — основной смысл обогащения v0.2: письмо «Уважаемый
    Иван Иванович» вместо безличного. Если ФИО нет, обращение деградирует корректно.
    """
    values = {
        "name": inst.name,
        "city": inst.city,
        "region": inst.region,
        # единственное число, чтобы «Уважаемый(ая) {{chief}}» осталось согласованным
        "chief": inst.chief_physician or "коллега",
        "address": inst.address,
    }
    return PLACEHOLDER.sub(lambda m: values.get(m.group(1), ""), text)


def build_recipients(db: Session, filter_json: dict) -> list[dict]:
    payload = filter_json or {}
    rows, _ = query_institutions(
        db,
        q=payload.get("q"),
        type=payload.get("type"),
        region=payload.get("region"),
        city=payload.get("city"),
        has_email=True,
        has_phone=payload.get("has_phone"),
        has_chief=payload.get("has_chief"),
        nmic_ref=payload.get("nmic_ref"),
        page=1,
        page_size=100000,
    )
    recipients: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        for email in row.emails_json or []:
            if email in seen:
                continue
            seen.add(email)
            recipients.append(
                {
                    "email": email,
                    "institution_id": row.id,
                    "institution_name": row.name,
                    "chief": row.chief_physician,
                }
            )
    return recipients


def run_mailing(db: Session, campaign: MailCampaign) -> MailCampaign:
    campaign.status = "running"
    db.commit()

    recipients = build_recipients(db, campaign.filter_json or {})

    if campaign.dry_run or not get_settings().allow_live_mail:
        campaign.sent_count = 0
        campaign.skipped_count = len(recipients)
        campaign.status = "done"
        db.commit()
        return campaign

    # Живая отправка требует SMTP-провайдера — сознательно не реализована,
    # чтобы нельзя было случайно отправить письма реальным учреждениям.
    campaign.sent_count = 0
    campaign.skipped_count = len(recipients)
    campaign.status = "failed"
    db.commit()
    return campaign


def preview_mailing(db: Session, subject: str, body_html: str, filter_json: dict, limit: int = 5) -> dict:
    recipients = build_recipients(db, filter_json)
    samples = []
    for item in recipients[:limit]:
        inst = db.get(Institution, item["institution_id"])
        if not inst:
            continue
        samples.append(
            {
                "email": item["email"],
                "subject": render_template(subject, inst),
                "body_html": render_template(body_html, inst),
                "personalized": bool(inst.chief_physician),
            }
        )
    return {
        "total_recipients": len(recipients),
        "personalized_count": sum(1 for r in recipients if r["chief"]),
        "samples": samples,
    }
