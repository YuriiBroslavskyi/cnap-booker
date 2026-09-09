"""
Checker: знаходить найкращий доступний слот для профілю.
Не виконує жодних побічних дій — лише GET-запити.
"""
import logging
from typing import Optional, Tuple

from models import Branch, TimeSlot, PersonProfile
from api_client import get_branches, CnapApiError

logger = logging.getLogger("cnap.checker")


def find_best_slot(profile: PersonProfile) -> Optional[Tuple[Branch, TimeSlot]]:
    """
    Повертає (branch, slot) для найкращого варіанту, або None якщо ніде немає слотів.

    Пріоритет:
      1. Бажаний підрозділ (якщо задано) — якщо там є слоти, беремо його.
      2. Якщо в бажаному підрозділі немає — перебираємо всі інші підрозділи
         і беремо той, де найраніша дата.
      В обох випадках всередині підрозділу береться найраніший час
      (з пріоритетом на preferred_hours, якщо заданий).
    """
    try:
        branches = get_branches(profile.job_name, profile.job_group_name)
    except CnapApiError as exc:
        logger.error("Помилка отримання списку підрозділів: %s", exc)
        return None

    branches_with_slots = [b for b in branches if b.free_slots]
    if not branches_with_slots:
        logger.info("[%s] Вільних слотів немає в жодному підрозділі", profile.name)
        return None

    # 1. Пріоритетний підрозділ
    if profile.preferred_branch_guid:
        preferred = next(
            (b for b in branches_with_slots if b.guid == profile.preferred_branch_guid),
            None,
        )
        if preferred:
            slot = preferred.earliest_slot(profile.preferred_hours)
            logger.info(
                "[%s] Знайдено слот у бажаному підрозділі '%s': %s",
                profile.name, preferred.name, slot.planned_begin_time,
            )
            return preferred, slot

    candidates = []
    for b in branches_with_slots:
        slot = b.earliest_slot(profile.preferred_hours)
        if slot:
            candidates.append((b, slot))

    if not candidates:
        return None

    candidates.sort(key=lambda pair: (pair[1].date, pair[1].time))
    best_branch, best_slot = candidates[0]

    logger.info(
        "[%s] Найкращий доступний варіант: '%s' о %s",
        profile.name, best_branch.name, best_slot.planned_begin_time,
    )
    return best_branch, best_slot
