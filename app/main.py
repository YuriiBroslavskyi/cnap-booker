"""
Точка входу воркера. Один контейнер = один профіль (одна людина).

Env-змінні:
  CONFIG_FILE               — шлях до YAML-конфігу профілю (обов'язково)
  CHECK_INTERVAL_SECONDS    — інтервал перевірки в секундах (опційно,
                               якщо не задано — береться зі значення в самому
                               конфізі, або 60 секунд за замовчуванням)
"""
import os
import sys
import time
import logging

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


def main():
    config_file = os.environ.get("CONFIG_FILE")
    if not config_file:
        print("Помилка: не задано env-змінну CONFIG_FILE", file=sys.stderr)
        sys.exit(1)

    profile = load_profile(config_file)


    env_interval = os.environ.get("CHECK_INTERVAL_SECONDS")
    if env_interval:
        profile.check_interval_seconds = int(env_interval)

    logger = setup_logging(profile.name)
    logger.info(
        "Старт воркера для профілю '%s'. Послуга: '%s' / '%s'. Інтервал перевірки: %s сек.",
        profile.name, profile.job_group_name, profile.job_name,
        profile.check_interval_seconds,
    )

    while True:
        try:
            result = find_best_slot(profile)
            if result:
                branch, slot = result
                logger.info(
                    "[%s] Знайдено слот — виконую бронювання...", profile.name
                )
                success = book_slot(profile, branch, slot)
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
