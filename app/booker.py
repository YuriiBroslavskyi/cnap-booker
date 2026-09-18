"""
Booker: створює реальний попередній запис (талон).
"""
import logging

from models import Branch, CnapSettings, TimeSlot, PersonProfile
from api_client import save_prelim_order, CnapApiError

logger = logging.getLogger("cnap.booker")


def book_slot(profile: PersonProfile, branch: Branch, slot: TimeSlot, settings: CnapSettings) -> bool:
    """
    Виконує бронювання. Повертає True при успіху, False при помилці.
    """
    try:
        result = save_prelim_order(
            branch=branch,
            slot=slot,
            full_name=profile.full_name,
            phone_with_country_code=profile.full_phone,
            email=profile.email,
            settings=settings,
            identification_number="",
        )
    except CnapApiError as exc:
        logger.error("[%s] Не вдалося створити запис: %s", profile.name, exc)
        return False

    if not result.get("isSucceeded", False):
        logger.error("[%s] Сервер відхилив запис: %s", profile.name, result.get("errors"))
        return False

    logger.info(
        "[%s] УСПІШНО ЗАПИСАНО! Підрозділ: %s, час: %s. Відповідь сервера: %s",
        profile.name, branch.name, slot.planned_begin_time, result,
    )
    return True
