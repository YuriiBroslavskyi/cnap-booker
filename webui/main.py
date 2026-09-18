"""
Проста веб-форма для створення YAML-конфігів профілів без ручного редагування файлів.
Підтягує актуальний список підрозділів прямо з CNAP API для випадайки.
"""
import os
import sys
import tempfile
import yaml
import requests
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from config_loader import (  # noqa: E402
    PROFILE_NAME_RE,
    get_cnap_settings,
    load_config,
)

CONFIG_FILE = os.environ.get("CONFIG_FILE", "/config/config.yaml")

app = FastAPI(title="CNAP Booker — конфігурація профілів")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


def fetch_branches(job_name: str, job_group_name: str) -> list[dict]:
    """Отримує актуальний список підрозділів для випадайки на формі."""
    try:
        settings = get_cnap_settings(load_config(CONFIG_FILE))
        resp = requests.get(
            f"{settings.api_url}/prelim/GetBranchesByJobAndGroupName",
            params={"jobName": job_name, "jobGroupName": job_group_name},
            headers=settings.headers,
            timeout=settings.request_timeout_seconds,
            verify=settings.verify_ssl,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {"guid": b["guid"], "name": b["name"]}
            for b in data.get("result", [])
        ]
    except Exception:
        # Якщо API недоступне (напр. під час розробки) — форма все одно відкриється,
        # просто без списку підрозділів.
        return []


def save_config(config: dict) -> None:
    """Atomically replace the shared config, so readers never see partial YAML."""
    directory = os.path.dirname(CONFIG_FILE) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(prefix=".config.", suffix=".yaml", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
        os.replace(temporary_path, CONFIG_FILE)
    except Exception:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise


@app.get("/", response_class=HTMLResponse)
def form_page(request: Request):
    config = load_config(CONFIG_FILE)
    webui = config.get("webui", {})
    default_job_group = webui.get("default_job_group_name", "")
    default_job_name = webui.get("default_job_name", "")
    branches = fetch_branches(default_job_name, default_job_group) if default_job_name and default_job_group else []
    profiles = sorted(p.get("name", "") for p in config["profiles"] if isinstance(p, dict))
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "branches": branches,
            "profiles": profiles,
            "default_job_group": default_job_group,
            "default_job_name": default_job_name,
            "default_interval": config.get("defaults", {}).get("check_interval_seconds", 60),
        },
    )


@app.post("/create")
def create_profile(
    name: str = Form(...),
    full_name: str = Form(...),
    phone_digits: str = Form(...),
    email: str = Form(...),
    job_group_name: str = Form(...),
    job_name: str = Form(...),
    preferred_branch_guid: str = Form(""),
    preferred_branch_name: str = Form(""),
    check_interval_seconds: int = Form(60),
    start_hour: str = Form(""),
):
    name = name.strip()
    if not PROFILE_NAME_RE.fullmatch(name):
        raise ValueError("Ключ профілю: малі латинські літери, цифри, _ та -")
    if check_interval_seconds <= 0:
        raise ValueError("Інтервал перевірки має бути додатнім")
    config_document = load_config(CONFIG_FILE)
    if any(p.get("name") == name for p in config_document["profiles"] if isinstance(p, dict)):
        raise ValueError(f"Профіль '{name}' вже існує")

    config = {
        "name": name,
        "full_name": full_name,
        "phone_digits": phone_digits.strip().lstrip("+").removeprefix("380"),
        "email": email,
        "job_group_name": job_group_name,
        "job_name": job_name,
        "preferred_hours": ["09:00", "12:00"],
        "check_interval_seconds": check_interval_seconds,
    }
    if preferred_branch_guid:
        config["preferred_branch_guid"] = preferred_branch_guid
        config["preferred_branch_name"] = preferred_branch_name
    if start_hour.strip():
        parsed_start_hour = int(start_hour)
        if not 0 <= parsed_start_hour <= 23:
            raise ValueError("Година старту має бути від 0 до 23")
        config["start_hour"] = parsed_start_hour

    config_document["profiles"].append(config)
    save_config(config_document)

    return RedirectResponse(url="/", status_code=303)


@app.get("/health")
def health():
    return {"status": "ok"}
