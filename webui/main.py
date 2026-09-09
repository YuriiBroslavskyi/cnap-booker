"""
Проста веб-форма для створення YAML-конфігів профілів без ручного редагування файлів.
Підтягує актуальний список підрозділів прямо з CNAP API для випадайки.
"""
import os
import sys
import yaml
import requests
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from models import BASE_API_URL, DEFAULT_HEADERS, VERIFY_SSL  # noqa: E402

CONFIGS_DIR = os.environ.get("CONFIGS_DIR", "/configs")

JOB_GROUP_NAME = "Паспортні послуги"
JOB_NAME = "Паспорт громадянина України (ID-картка) / для виїзду за кордон"

app = FastAPI(title="CNAP Booker — конфігурація профілів")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


def fetch_branches() -> list[dict]:
    """Отримує актуальний список підрозділів для випадайки на формі."""
    try:
        resp = requests.get(
            f"{BASE_API_URL}/prelim/GetBranchesByJobAndGroupName",
            params={"jobName": JOB_NAME, "jobGroupName": JOB_GROUP_NAME},
            headers=DEFAULT_HEADERS,
            timeout=10,
            verify=VERIFY_SSL
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


def list_profiles() -> list[str]:
    if not os.path.isdir(CONFIGS_DIR):
        return []
    return sorted(
        f[:-5] for f in os.listdir(CONFIGS_DIR)
        if f.endswith(".yaml") and not f.endswith(".example.yaml")
    )


@app.get("/", response_class=HTMLResponse)
def form_page(request: Request):
    branches = fetch_branches()
    profiles = list_profiles()
    return templates.TemplateResponse(
        "form.html",
        {"request": request, "branches": branches, "profiles": profiles},
    )


@app.post("/create")
def create_profile(
    name: str = Form(...),
    full_name: str = Form(...),
    phone_digits: str = Form(...),
    email: str = Form(...),
    preferred_branch_guid: str = Form(""),
    preferred_branch_name: str = Form(""),
    check_interval_seconds: int = Form(60),
):
    os.makedirs(CONFIGS_DIR, exist_ok=True)

    config = {
        "name": name,
        "full_name": full_name,
        "phone_digits": phone_digits.strip().lstrip("+").removeprefix("380"),
        "email": email,
        "job_group_name": JOB_GROUP_NAME,
        "job_name": JOB_NAME,
        "preferred_hours": ["09:00", "12:00"],
        "check_interval_seconds": check_interval_seconds,
    }
    if preferred_branch_guid:
        config["preferred_branch_guid"] = preferred_branch_guid
        config["preferred_branch_name"] = preferred_branch_name

    path = os.path.join(CONFIGS_DIR, f"{name}.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    return RedirectResponse(url="/", status_code=303)


@app.get("/health")
def health():
    return {"status": "ok"}
