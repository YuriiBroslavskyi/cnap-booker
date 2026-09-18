"""
Тонка обгортка над CNAP API: запити на список підрозділів/слотів і бронювання.
"""
import uuid
import logging
from typing import Optional

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from models import Branch, CnapSettings, TimeSlot, ATTRIBUTE_GUIDS

logger = logging.getLogger("cnap.api_client")


class CnapApiError(Exception):
    """Помилка звернення до API ЦНАП."""


def get_branches(job_name: str, job_group_name: str, settings: CnapSettings) -> list[Branch]:
    """
    Повертає список підрозділів з їхніми вільними слотами
    для заданої послуги та групи послуг.
    """
    url = f"{settings.api_url}/prelim/GetBranchesByJobAndGroupName"
    params = {"jobName": job_name, "jobGroupName": job_group_name}

    try:
        resp = requests.get(url, params=params, headers=settings.headers, timeout=settings.request_timeout_seconds, verify=settings.verify_ssl)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise CnapApiError(f"Помилка запиту GetBranchesByJobAndGroupName: {exc}") from exc

    payload = resp.json()
    if not payload.get("isSucceeded", False):
        raise CnapApiError(f"API повернуло помилку: {payload.get('errors')}")

    branches = []
    for item in payload.get("result", []):
        slots = []
        for day_block in item.get("freeSlots", []):

            date_str = day_block["workDaySlot"][:10]
            for time_str in day_block.get("freeTimeSlots", []):
                slots.append(TimeSlot(date=date_str, time=time_str))

        slots.sort(key=lambda s: (s.date, s.time))

        branches.append(Branch(
            guid=item["guid"],
            name=item["name"],
            address=item.get("address", item["name"]),
            job_guid=item["jobGuid"],
            job_name=item["jobName"],
            job_group_guid=item["jobGroupGuid"],
            job_group_name=item["jobGroupName"],
            free_slots=slots,
        ))

    return branches


def save_prelim_order(
    branch: Branch,
    slot: TimeSlot,
    full_name: str,
    phone_with_country_code: str,
    email: str,
    settings: CnapSettings,
    identification_number: str = "",
) -> dict:
    """
    Виконує реальне бронювання (savePrelimOrder).
    УВАГА: цей виклик створює справжній талон. Викликати лише коли
    дійсно потрібно записатись, не для тестів.
    """
    url = f"{settings.api_url}/prelim/savePrelimOrder/"

    order_guid = str(uuid.uuid4()).upper()
    order_job_guid = str(uuid.uuid4()).upper()

    def attr(key: str, value: str) -> dict:
        return {
            "entityGuid": order_guid,
            "attributeGuid": ATTRIBUTE_GUIDS[key],
            "attributeDescription": {
                "full_name": "Person.FullName",
                "identification_number": "Person.IdentificationNumber",
                "phone": "Person.PhoneNumber",
                "email": "Person.Email",
            }[key],
            "value": value,
        }

    body = {
        "guid": order_guid,
        "number": None,
        "orderJobs": [
            {
                "guid": order_job_guid,
                "jobGuid": branch.job_guid,
                "orderGuid": order_guid,
            }
        ],
        "branchGuid": branch.guid,
        "plannedBeginTime": slot.planned_begin_time,
        "entity": {
            "entityAttributes": [
                attr("full_name", full_name),
                attr("identification_number", identification_number),
                attr("phone", phone_with_country_code),
                attr("email", email),
            ]
        },
    }

    logger.info(
        "Надсилаю savePrelimOrder: branch=%s slot=%s",
        branch.name, slot.planned_begin_time,
    )

    try:
        resp = requests.post(url, json=body, headers=settings.headers, timeout=settings.request_timeout_seconds, verify=settings.verify_ssl)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise CnapApiError(f"Помилка запиту savePrelimOrder: {exc}") from exc

    return resp.json()
