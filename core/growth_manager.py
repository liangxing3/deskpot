from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from data.manual_actions import MANUAL_ACTION_SPECS
from data.models import EmotionState
from data.pet_models import GrowthStage, PetStatus
from utils.time_utils import ensure_local, now_local


@dataclass(slots=True)
class GrowthUpdateResult:
    changed: bool = False
    leveled_up: bool = False
    previous_stage: GrowthStage | None = None
    current_stage: GrowthStage | None = None
    favorability_increased: bool = False


class GrowthManager:
    DECAY_INTERVAL_MINUTES = 15
    LOW_THRESHOLD = 25
    VERY_LOW_THRESHOLD = 12
    BORED_AFTER_MINUTES = 75

    def __init__(self, pet_status: PetStatus) -> None:
        self.pet_status = pet_status

    def bootstrap(self, now: datetime | None = None) -> GrowthUpdateResult:
        current = ensure_local(now) or now_local()
        if self.pet_status.last_growth_check_time is None:
            self.pet_status.last_growth_check_time = current
            self.pet_status.normalize()
            return GrowthUpdateResult(
                changed=True,
                current_stage=self.pet_status.growth_stage,
            )
        return self.tick(now=current)

    def tick(self, *, now: datetime | None = None) -> GrowthUpdateResult:
        current = ensure_local(now) or now_local()
        last_check = ensure_local(self.pet_status.last_growth_check_time)
        if last_check is None:
            self.pet_status.last_growth_check_time = current
            return GrowthUpdateResult(
                changed=True,
                current_stage=self.pet_status.growth_stage,
            )

        if current <= last_check:
            return GrowthUpdateResult(current_stage=self.pet_status.growth_stage)

        elapsed_minutes = (current - last_check).total_seconds() / 60.0
        steps = max(0, int(elapsed_minutes // self.DECAY_INTERVAL_MINUTES))
        if steps <= 0:
            return GrowthUpdateResult(current_stage=self.pet_status.growth_stage)

        result = GrowthUpdateResult(current_stage=self.pet_status.growth_stage)
        for _ in range(steps):
            if self._apply_decay_step(current):
                result.changed = True

        self.pet_status.last_growth_check_time = last_check + timedelta(
            minutes=steps * self.DECAY_INTERVAL_MINUTES
        )
        self.pet_status.normalize()
        result.current_stage = self.pet_status.growth_stage
        return result

    def apply_manual_action(self, action_id: str, *, now: datetime | None = None) -> GrowthUpdateResult:
        current = ensure_local(now) or now_local()
        spec = MANUAL_ACTION_SPECS[action_id]
        previous_stage = self.pet_status.growth_stage
        previous_favorability = self.pet_status.favorability

        self.pet_status.hunger = self._clamp(self.pet_status.hunger + spec.hunger_delta)
        self.pet_status.mood = self._clamp(self.pet_status.mood + spec.mood_delta)
        self.pet_status.energy = self._clamp(self.pet_status.energy + spec.energy_delta)
        self.pet_status.cleanliness = self._clamp(
            self.pet_status.cleanliness + spec.cleanliness_delta
        )
        self.pet_status.favorability = self._clamp(
            self.pet_status.favorability + spec.favorability_delta
        )
        self.pet_status.growth_exp = max(0, self.pet_status.growth_exp + spec.growth_exp_delta)

        if action_id == "feed":
            self.pet_status.last_feed_time = current
        elif action_id in {"play", "exercise", "walkdog", "feather_ball"}:
            self.pet_status.last_play_time = current
        elif action_id == "clean":
            self.pet_status.last_clean_time = current
        elif action_id in {"rest", "charge"}:
            self.pet_status.last_rest_time = current

        self.pet_status.last_growth_check_time = current
        self.pet_status.normalize()
        return GrowthUpdateResult(
            changed=True,
            leveled_up=self.pet_status.growth_stage != previous_stage,
            previous_stage=previous_stage,
            current_stage=self.pet_status.growth_stage,
            favorability_increased=self.pet_status.favorability > previous_favorability,
        )

    def apply_click_interaction(self, *, now: datetime | None = None) -> GrowthUpdateResult:
        current = ensure_local(now) or now_local()
        previous_stage = self.pet_status.growth_stage
        previous_favorability = self.pet_status.favorability
        self.pet_status.mood = self._clamp(self.pet_status.mood + 3)
        self.pet_status.favorability = self._clamp(self.pet_status.favorability + 1)
        self.pet_status.growth_exp = max(0, self.pet_status.growth_exp + 1)
        self.pet_status.last_growth_check_time = current
        self.pet_status.normalize()
        return GrowthUpdateResult(
            changed=True,
            leveled_up=self.pet_status.growth_stage != previous_stage,
            previous_stage=previous_stage,
            current_stage=self.pet_status.growth_stage,
            favorability_increased=self.pet_status.favorability > previous_favorability,
        )

    def current_emotion(
        self,
        *,
        now: datetime | None = None,
        last_interaction_time: datetime | None = None,
    ) -> EmotionState:
        current = ensure_local(now) or now_local()
        self.pet_status.normalize()
        inactivity_minutes = self._minutes_since(last_interaction_time, current)

        if self.pet_status.mood <= self.VERY_LOW_THRESHOLD and self.pet_status.energy <= self.VERY_LOW_THRESHOLD:
            return EmotionState.DRAINED
        if self.pet_status.hunger <= self.LOW_THRESHOLD:
            return EmotionState.HUNGRY
        if self.pet_status.energy <= self.LOW_THRESHOLD:
            return EmotionState.TIRED
        if self.pet_status.cleanliness <= self.LOW_THRESHOLD:
            return EmotionState.DIRTY
        if self.pet_status.mood <= self.LOW_THRESHOLD:
            return EmotionState.LOW_HAPPINESS
        if inactivity_minutes >= self.BORED_AFTER_MINUTES and not self._is_working_time(current):
            return EmotionState.BORED
        if self._is_working_time(current):
            return EmotionState.WORKING
        return EmotionState.NORMAL

    def summary_category(
        self,
        *,
        now: datetime | None = None,
        last_interaction_time: datetime | None = None,
    ) -> str:
        emotion = self.current_emotion(now=now, last_interaction_time=last_interaction_time)
        if emotion == EmotionState.HUNGRY:
            return "pet_hungry"
        if emotion in {EmotionState.TIRED, EmotionState.DRAINED, EmotionState.LOW_ENERGY}:
            return "pet_tired"
        if emotion == EmotionState.DIRTY:
            return "pet_dirty"
        return "pet_status_good"

    def stage_progress(self) -> tuple[int, int]:
        current_exp = self.pet_status.growth_exp
        if current_exp < 100:
            return current_exp, 100
        if current_exp < 300:
            return current_exp - 100, 200
        if current_exp < 600:
            return current_exp - 300, 300
        return 600, 600

    def snapshot(self) -> PetStatus:
        self.pet_status.normalize()
        return replace(self.pet_status)

    def _apply_decay_step(self, current: datetime) -> bool:
        before = (
            self.pet_status.hunger,
            self.pet_status.mood,
            self.pet_status.energy,
            self.pet_status.cleanliness,
        )
        hunger_drop = 4
        energy_drop = 3 if self._is_working_time(current) else 2
        cleanliness_drop = 2
        mood_drop = 0
        low_stats = sum(
            1
            for value in (
                self.pet_status.hunger,
                self.pet_status.energy,
                self.pet_status.cleanliness,
            )
            if value <= 35
        )
        if low_stats >= 2:
            mood_drop = 3
        elif low_stats == 1:
            mood_drop = 1

        self.pet_status.hunger = self._clamp(self.pet_status.hunger - hunger_drop)
        self.pet_status.energy = self._clamp(self.pet_status.energy - energy_drop)
        self.pet_status.cleanliness = self._clamp(self.pet_status.cleanliness - cleanliness_drop)
        if mood_drop:
            self.pet_status.mood = self._clamp(self.pet_status.mood - mood_drop)
        self.pet_status.normalize()
        return before != (
            self.pet_status.hunger,
            self.pet_status.mood,
            self.pet_status.energy,
            self.pet_status.cleanliness,
        )

    @staticmethod
    def _clamp(value: int) -> int:
        return max(0, min(100, int(value)))

    @staticmethod
    def _minutes_since(reference: datetime | None, current: datetime) -> float:
        if reference is None:
            return 0.0
        normalized = ensure_local(reference)
        if normalized is None:
            return 0.0
        return max(0.0, (current - normalized).total_seconds() / 60.0)

    @staticmethod
    def _is_working_time(current: datetime) -> bool:
        return current.weekday() <= 4 and 10 <= current.hour < 18
