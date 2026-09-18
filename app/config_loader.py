"""
Завантаження профілю людини з YAML-файлу.
"""
import re
from zoneinfo import ZoneInfo
import yaml

from models import CnapSettings, DEFAULT_USER_AGENT, PersonProfile


REQUIRED_FIELDS = ["full_name", "phone_digits", "email", "job_group_name", "job_name"]
PROFILE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Конфіг {path} має бути YAML-об'єктом")
    if not isinstance(raw.get("profiles"), list):
        raise ValueError(f"У конфігу {path} має бути список profiles")
    return raw


def get_cnap_settings(raw: dict) -> CnapSettings:
    cnap = raw.get("cnap", {})
    if not isinstance(cnap, dict):
        raise ValueError("cnap має бути YAML-об'єктом")
    required = ["api_url", "frontend_origin"]
    missing = [field for field in required if not cnap.get(field)]
    if missing:
        raise ValueError(f"У секції cnap відсутні обов'язкові поля: {missing}")
    return CnapSettings(
        api_url=cnap["api_url"].rstrip("/"),
        frontend_origin=cnap["frontend_origin"].rstrip("/"),
        verify_ssl=bool(cnap.get("verify_ssl", False)),
        request_timeout_seconds=float(cnap.get("request_timeout_seconds", 15)),
        accept_language=cnap.get("accept_language", "en-US,en;q=0.9"),
        user_agent=cnap.get("user_agent") or DEFAULT_USER_AGENT,
    )


def load_profile(path: str, profile_name: str) -> tuple[PersonProfile, CnapSettings]:
    raw = load_config(path)
    settings = get_cnap_settings(raw)
    defaults = raw.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError("defaults має бути YAML-об'єктом")
    profile_raw = next((p for p in raw["profiles"] if isinstance(p, dict) and p.get("name") == profile_name), None)
    if profile_raw is None:
        raise ValueError(f"Профіль '{profile_name}' не знайдено у конфігу {path}")
    if not PROFILE_NAME_RE.fullmatch(profile_name):
        raise ValueError("Ключ профілю може містити лише малі латинські літери, цифри, _ та -")

    merged = {**defaults, **profile_raw}

    missing = [f for f in REQUIRED_FIELDS if not merged.get(f)]
    if missing:
        raise ValueError(f"У профілі '{profile_name}' відсутні обов'язкові поля: {missing}")

    preferred_hours = merged.get("preferred_hours")
    if preferred_hours and len(preferred_hours) == 2:
        preferred_hours = tuple(preferred_hours)
    else:
        preferred_hours = None

    start_hour = merged.get("start_hour")
    if start_hour is not None and not 0 <= int(start_hour) <= 23:
        raise ValueError("start_hour має бути числом від 0 до 23")
    timezone = merged.get("timezone", "Europe/Kyiv")
    try:
        ZoneInfo(timezone)
    except Exception as exc:
        raise ValueError(f"Невідома timezone: {timezone}") from exc

    interval = int(merged.get("check_interval_seconds", 60))
    if interval <= 0:
        raise ValueError("check_interval_seconds має бути додатнім")

    return PersonProfile(
        name=profile_name,
        full_name=merged["full_name"],
        phone_digits=str(merged["phone_digits"]),
        email=merged["email"],
        job_group_name=merged["job_group_name"],
        job_name=merged["job_name"],
        preferred_branch_guid=merged.get("preferred_branch_guid"),
        preferred_branch_name=merged.get("preferred_branch_name"),
        preferred_hours=preferred_hours,
        check_interval_seconds=interval,
        start_hour=int(start_hour) if start_hour is not None else None,
        timezone=timezone,
    ), settings
