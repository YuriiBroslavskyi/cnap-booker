"""
Моделі даних та константи для роботи з CNAP API.
"""
from dataclasses import dataclass, field
from typing import Optional

VERIFY_SSL = False

ATTRIBUTE_GUIDS = {
    "full_name": "cf63e2de-f3cc-4e51-adbe-30919bbfb5e1",       # Person.FullName
    "identification_number": "dc56c43c-9ba0-4a47-a304-921e512350f2",  # Person.IdentificationNumber
    "phone": "7aee0bf8-e31b-43a9-af89-064ba7c2f5be",            # Person.PhoneNumber
    "email": "ca781cb6-9a95-44fc-ab91-0ccf68eeee08",            # Person.Email
}

BASE_API_URL = "https://cnap_lviv.qsolutions.com.ua:2651"
FRONTEND_ORIGIN = "https://cnap-lviv.qsolutions.com.ua:2657"

DEFAULT_HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "origin": FRONTEND_ORIGIN,
    "referer": f"{FRONTEND_ORIGIN}/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}


@dataclass
class TimeSlot:
    """Один конкретний вільний час у конкретний день."""
    date: str
    time: str

    @property
    def planned_begin_time(self) -> str:
        """Формат, який очікує сервер у savePrelimOrder: без таймзони."""
        return f"{self.date}T{self.time}"


@dataclass
class Branch:
    """Підрозділ ЦНАП з даними про послугу та вільні слоти."""
    guid: str
    name: str
    address: str
    job_guid: str
    job_name: str
    job_group_guid: str
    job_group_name: str
    free_slots: list = field(default_factory=list) 

    def earliest_slot(self, preferred_hours: Optional[tuple] = None) -> Optional[TimeSlot]:
        """
        Повертає найраніший доступний слот.
        Якщо задано preferred_hours (напр. ("09:00", "12:00")) — спершу шукає в цьому діапазоні,
        якщо там нічого немає — бере найраніший будь-який.
        """
        if not self.free_slots:
            return None

        if preferred_hours:
            start, end = preferred_hours
            in_range = [s for s in self.free_slots if start <= s.time <= end]
            if in_range:
                return in_range[0]

        return self.free_slots[0]


@dataclass
class PersonProfile:
    """Профіль людини, для якої виконується пошук і бронювання."""
    name: str
    full_name: str
    phone_digits: str
    email: str
    job_group_name: str
    job_name: str
    preferred_branch_guid: Optional[str] = None
    preferred_branch_name: Optional[str] = None
    preferred_hours: Optional[tuple] = ("09:00", "12:00")
    check_interval_seconds: int = 60

    @property
    def full_phone(self) -> str:
        return f"380{self.phone_digits}"
