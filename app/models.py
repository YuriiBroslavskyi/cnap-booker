"""
Моделі даних та константи для роботи з CNAP API.
"""
from dataclasses import dataclass, field
from typing import Optional

ATTRIBUTE_GUIDS = {
    "full_name": "cf63e2de-f3cc-4e51-adbe-30919bbfb5e1",       # Person.FullName
    "identification_number": "dc56c43c-9ba0-4a47-a304-921e512350f2",  # Person.IdentificationNumber
    "phone": "7aee0bf8-e31b-43a9-af89-064ba7c2f5be",            # Person.PhoneNumber
    "email": "ca781cb6-9a95-44fc-ab91-0ccf68eeee08",            # Person.Email
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


@dataclass
class CnapSettings:
    api_url: str
    frontend_origin: str
    verify_ssl: bool = False
    request_timeout_seconds: float = 15.0
    accept_language: str = "en-US,en;q=0.9"
    user_agent: str = DEFAULT_USER_AGENT

    @property
    def headers(self) -> dict:
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "accept-language": self.accept_language,
            "origin": self.frontend_origin,
            "referer": f"{self.frontend_origin}/",
            "user-agent": self.user_agent,
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
    start_hour: Optional[int] = None
    timezone: str = "Europe/Kyiv"

    @property
    def full_phone(self) -> str:
        return f"380{self.phone_digits}"
