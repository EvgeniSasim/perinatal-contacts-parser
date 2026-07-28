from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import MailCampaign
from app.services.query import query_institutions


def run_mailing(db: Session, campaign: MailCampaign) -> MailCampaign:
    campaign.status = "running"
    db.commit()
    payload = campaign.filter_json or {}
    rows, _ = query_institutions(
        db,
        q=payload.get("q"),
        type=payload.get("type"),
        region=payload.get("region"),
        city=payload.get("city"),
        has_email=True,
        has_phone=payload.get("has_phone"),
        nmic_ref=payload.get("nmic_ref"),
        page=1,
        page_size=100000,
    )
    recipients: list[str] = []
    for row in rows:
        recipients.extend(row.emails_json or [])
    recipients = list(dict.fromkeys(recipients))

    if campaign.dry_run or not get_settings().allow_live_mail:
        campaign.sent_count = 0
        campaign.skipped_count = len(recipients)
        campaign.status = "done"
        db.commit()
        return campaign

    # Live sending intentionally not implemented in MVP without provider creds.
    campaign.sent_count = 0
    campaign.skipped_count = len(recipients)
    campaign.status = "failed"
    db.commit()
    return campaign
