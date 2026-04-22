from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from utils.time_utils import parse_datetime, serialize_datetime


def _clamp_stat(value: Any, default: int) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = default
    return max(0, min(100, numeric))


def _clamp_non_negative(value: Any, default: int = 0) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = default
    return max(0, numeric)


class GrowthStage(str, Enum):
    BABY = "BABY"
    CHILD = "CHILD"
    TEEN = "TEEN"
    ADULT = "ADULT"

    @classmethod
    def from_exp(cls, growth_exp: int) -> "GrowthStage":
        if growth_exp >= 600:
            return cls.ADULT
        if growth_exp >= 300:
            return cls.TEEN
        if growth_exp >= 100:
            return cls.CHILD
        return cls.BABY

    @property
    def label(self) -> str:
        labels = {
            GrowthStage.BABY: "幼年期",
            GrowthStage.CHILD: "成长期",
            GrowthStage.TEEN: "青春期",
            GrowthStage.ADULT: "成熟期",
        }
        return labels[self]


@dataclass(slots=True)
class PetStatus:
    pet_name: str = "Momo"
    species: str = "default"
    growth_stage: GrowthStage = GrowthStage.BABY
    growth_exp: int = 0
    is_resting: bool = False
    hunger: int = 85
    mood: int = 80
    energy: int = 78
    cleanliness: int = 90
    favorability: int = 20
    last_feed_time: object | None = None
    last_play_time: object | None = None
    last_clean_time: object | None = None
    last_rest_time: object | None = None
    last_growth_check_time: object | None = None

    @classmethod
    def default(cls) -> "PetStatus":
        return cls()

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "PetStatus":
        payload = payload or {}
        growth_exp = _clamp_non_negative(payload.get("growth_exp"), 0)
        raw_stage = str(payload.get("growth_stage") or "").upper()
        try:
            growth_stage = GrowthStage(raw_stage) if raw_stage else GrowthStage.from_exp(growth_exp)
        except ValueError:
            growth_stage = GrowthStage.from_exp(growth_exp)
        normalized_stage = GrowthStage.from_exp(growth_exp)
        if normalized_stage.value != growth_stage.value:
            growth_stage = normalized_stage

        return cls(
            pet_name=str(payload.get("pet_name") or "Momo"),
            species=str(payload.get("species") or "default"),
            growth_stage=growth_stage,
            growth_exp=growth_exp,
            is_resting=bool(payload.get("is_resting", False)),
            hunger=_clamp_stat(payload.get("hunger"), 85),
            mood=_clamp_stat(payload.get("mood"), 80),
            energy=_clamp_stat(payload.get("energy"), 78),
            cleanliness=_clamp_stat(payload.get("cleanliness"), 90),
            favorability=_clamp_stat(payload.get("favorability"), 20),
            last_feed_time=parse_datetime(payload.get("last_feed_time")),
            last_play_time=parse_datetime(payload.get("last_play_time")),
            last_clean_time=parse_datetime(payload.get("last_clean_time")),
            last_rest_time=parse_datetime(payload.get("last_rest_time")),
            last_growth_check_time=parse_datetime(payload.get("last_growth_check_time")),
        )

    def normalize(self) -> None:
        self.growth_exp = _clamp_non_negative(self.growth_exp, 0)
        self.hunger = _clamp_stat(self.hunger, 85)
        self.mood = _clamp_stat(self.mood, 80)
        self.energy = _clamp_stat(self.energy, 78)
        self.cleanliness = _clamp_stat(self.cleanliness, 90)
        self.favorability = _clamp_stat(self.favorability, 20)
        self.growth_stage = GrowthStage.from_exp(self.growth_exp)

    def to_dict(self) -> dict[str, Any]:
        self.normalize()
        return {
            "pet_name": self.pet_name,
            "species": self.species,
            "growth_stage": self.growth_stage.value,
            "growth_exp": self.growth_exp,
            "is_resting": self.is_resting,
            "hunger": self.hunger,
            "mood": self.mood,
            "energy": self.energy,
            "cleanliness": self.cleanliness,
            "favorability": self.favorability,
            "last_feed_time": serialize_datetime(self.last_feed_time),
            "last_play_time": serialize_datetime(self.last_play_time),
            "last_clean_time": serialize_datetime(self.last_clean_time),
            "last_rest_time": serialize_datetime(self.last_rest_time),
            "last_growth_check_time": serialize_datetime(self.last_growth_check_time),
        }
