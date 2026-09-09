"""
Завантаження профілю людини з YAML-файлу.
"""
import os
import yaml

from models import PersonProfile


REQUIRED_FIELDS = ["full_name", "phone_digits", "email", "job_group_name", "job_name"]


def load_profile(path: str) -> PersonProfile:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    missing = [f for f in REQUIRED_FIELDS if not raw.get(f)]
    if missing:
        raise ValueError(f"У конфігу {path} відсутні обов'язкові поля: {missing}")

    preferred_hours = raw.get("preferred_hours")
    if preferred_hours and len(preferred_hours) == 2:
        preferred_hours = tuple(preferred_hours)
    else:
        preferred_hours = None

    return PersonProfile(
        name=raw.get("name", os.path.splitext(os.path.basename(path))[0]),
        full_name=raw["full_name"],
        phone_digits=str(raw["phone_digits"]),
        email=raw["email"],
        job_group_name=raw["job_group_name"],
        job_name=raw["job_name"],
        preferred_branch_guid=raw.get("preferred_branch_guid"),
        preferred_branch_name=raw.get("preferred_branch_name"),
        preferred_hours=preferred_hours,
        check_interval_seconds=int(raw.get("check_interval_seconds", 60)),
    )
