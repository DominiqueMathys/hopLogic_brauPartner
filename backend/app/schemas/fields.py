from datetime import datetime, timezone


def collapse(value: str) -> str:
    return " ".join(value.split())


def optional_text(value: object, label: str, limit: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} ist ungültig.")
    cleaned = collapse(value)
    if not cleaned:
        return None
    if len(cleaned) > limit:
        raise ValueError(f"{label} darf höchstens {limit} Zeichen haben.")
    return cleaned


def required_text(value: object, label: str, limit: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} ist erforderlich.")
    cleaned = collapse(value)
    if not cleaned:
        raise ValueError(f"{label} ist erforderlich.")
    if len(cleaned) > limit:
        raise ValueError(f"{label} darf höchstens {limit} Zeichen haben.")
    return cleaned


def choice(value: object, label: str, allowed: tuple[str, ...], default: str | None = None) -> str:
    if value is None or value == "":
        if default is not None:
            return default
        raise ValueError(f"{label} ist erforderlich.")
    if not isinstance(value, str) or value.strip() not in allowed:
        raise ValueError(f"{label} ist ungültig.")
    return value.strip()


def parse_timestamp(value: object, label: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            raise ValueError(f"{label} ist ungültig.") from None
    else:
        raise ValueError(f"{label} ist erforderlich.")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    if parsed.year < 1900 or parsed.year > 2100:
        raise ValueError(f"{label} ist unplausibel.")
    return parsed
