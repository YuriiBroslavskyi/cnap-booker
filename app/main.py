"""
Точка входу воркера. Один контейнер = один профіль (одна людина).

Env-змінні:
  CONFIG_FILE               — шлях до спільного YAML-конфігу (обов'язково)
  PROFILE_NAME              — ключ профілю в YAML-конфігу (обов'язково)
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))

from config_loader import load_profile
from checker import find_best_slot
from booker import book_slot


def setup_logging(profile_name: str) -> logging.Logger:
    os.makedirs("/logs", exist_ok=True)
    log_path = f"/logs/{profile_name}.log"

    logger = logging.getLogger("cnap")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    return logger

def wait_until_start_hour(start_hour: int, timezone: str, logger: logging.Logger) -> None:
    """
    Блокує виконання до найближчого настання заданої години доби.
    Якщо ця година вже минула сьогодні — чекає до завтра.
    Перевіряє кожні 30 секунд, чи не зупинили контейнер (для швидкої реакції
    на Ctrl+C / docker stop), замість одного довгого sleep().
    """
    zone = ZoneInfo(timezone)
    now = datetime.now(zone)
    target = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)

    logger.info(
        "START_HOUR=%d задано. Очікую до %s (зараз %s)...",
        start_hour, target.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%H:%M:%S"),
    )

    while datetime.now(zone) < target:
        time.sleep(min(30, (target - datetime.now(zone)).total_seconds()))

    logger.info("Настав час %02d:00 — починаю перевірку слотів.", start_hour)

def main():
    config_file = os.environ.get("CONFIG_FILE")
    if not config_file:
        print("Помилка: не задано env-змінну CONFIG_FILE", file=sys.stderr)
        sys.exit(1)

    profile_name = os.environ.get("PROFILE_NAME")
    if not profile_name:
        print("Помилка: не задано env-змінну PROFILE_NAME", file=sys.stderr)
        sys.exit(1)
    profile, settings = load_profile(config_file, profile_name)

    logger = setup_logging(profile.name)
    logger.info(
        "Старт воркера для профілю '%s'. Послуга: '%s' / '%s'. Інтервал перевірки: %s сек.",
        profile.name, profile.job_group_name, profile.job_name,
        profile.check_interval_seconds,
    )

    if profile.start_hour is not None:
        wait_until_start_hour(profile.start_hour, profile.timezone, logger)

    while True:
        try:
            result = find_best_slot(profile, settings)
            if result:
                branch, slot = result
                logger.info(
                    "[%s] Знайдено слот — виконую бронювання...", profile.name
                )
                success = book_slot(profile, branch, slot, settings)
                if success:
                    logger.info(
                        "[%s] Задача виконана, воркер завершує роботу.", profile.name
                    )
                    break
            else:
                logger.info("[%s] Слотів поки немає, чекаю...", profile.name)

        except Exception:
            logger.exception("[%s] Неочікувана помилка в циклі перевірки", profile.name)

        time.sleep(profile.check_interval_seconds)


if __name__ == "__main__":
    main()
