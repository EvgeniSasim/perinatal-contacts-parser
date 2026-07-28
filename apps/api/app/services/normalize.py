import re


_PREFIX_RE = re.compile(
    r"^(гбуз|гауз|фгбу|фгбоу|ооо|ао|пао|мку|гку)\s+",
    re.IGNORECASE,
)


def normalize_name(name: str) -> str:
    value = name.strip().lower().replace("ё", "е")
    value = _PREFIX_RE.sub("", value)
    value = re.sub(r"[«»\"'()]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_phone(phone: str) -> str | None:
    digits = re.sub(r"\D+", "", phone or "")
    if not digits:
        return None
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 10:
        digits = "7" + digits
    if len(digits) < 11:
        return None
    return digits


def normalize_email(email: str) -> str | None:
    value = (email or "").strip().lower()
    if not value or "@" not in value:
        return None
    return value


def split_multi(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[;,|/]", value)
    return [p.strip() for p in parts if p.strip()]
