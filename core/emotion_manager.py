from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from data.manual_actions import MANUAL_ACTION_SPECS, ManualActionSpec
from data.models import EmotionState, PetVitals
from utils.time_utils import ensure_local, now_local


class EmotionManager:
    BORED_AFTER_MINUTES = 60
    LOW_THRESHOLD = 20
    DRAINED_THRESHOLD = 10

    def __init__(self, vitals: PetVitals) -> None:
        self.vitals = vitals
        self._happiness_value = float(vitals.happiness)
        self._energy_value = float(vitals.energy)

    def bootstrap(self, now: datetime | None = None) -> PetVitals:
        current = ensure_local(now) or now_local()
        if self.vitals.last_updated_at is None:
            self.vitals.last_updated_at = current
            return self.snapshot()
        self._apply_decay_until(current, current)
        return self.snapshot()

    def tick(
        self,
        *,
        now: datetime | None = None,
        last_interaction_time: datetime | None = None,
    ) -> bool:
        current = ensure_local(now) or now_local()
        changed = self._apply_decay_until(current, last_interaction_time)
        return changed

    def current_emotion(self, *, now: datetime | None = None, last_interaction_time: datetime | None = None) -> EmotionState:
        current = ensure_local(now) or now_local()
        inactivity_minutes = self._minutes_since(last_interaction_time, current)

        if self.vitals.happiness <= self.DRAINED_THRESHOLD and self.vitals.energy <= self.DRAINED_THRESHOLD:
            return EmotionState.DRAINED
        if self.vitals.energy < self.LOW_THRESHOLD:
            return EmotionState.LOW_ENERGY
        if self.vitals.happiness < self.LOW_THRESHOLD:
            return EmotionState.LOW_HAPPINESS
        if inactivity_minutes >= self.BORED_AFTER_MINUTES and not self._is_working_time(current):
            return EmotionState.BORED
        if self._is_working_time(current):
            return EmotionState.WORKING
        return EmotionState.NORMAL

    def apply_manual_action(self, action_id: str, *, now: datetime | None = None) -> ManualActionSpec:
        spec = MANUAL_ACTION_SPECS[action_id]
        current = ensure_local(now) or now_local()
        self._happiness_value = self._clamp_value(self._happiness_value + spec.happiness_delta)
        self._energy_value = self._clamp_value(self._energy_value + spec.energy_delta)
        self.vitals.happiness = int(round(self._happiness_value))
        self.vitals.energy = int(round(self._energy_value))
        self.vitals.last_manual_action = action_id
        self.vitals.last_updated_at = current
        return spec

    def set_last_hourly_report_hour(self, hour_key: str | None) -> None:
        self.vitals.last_hourly_report_hour = hour_key

    def snapshot(self) -> PetVitals:
        return replace(self.vitals)

    def _apply_decay_until(
        self,
        current: datetime,
        last_interaction_time: datetime | None,
    ) -> bool:
        last_updated = ensure_local(self.vitals.last_updated_at)
        if last_updated is None or current <= last_updated:
            self.vitals.last_updated_at = current
            return False

        minutes = max(0.0, (current - last_updated).total_seconds() / 60.0)
        if minutes <= 0:
            self.vitals.last_updated_at = current
            return False

        emotion = self.current_emotion(now=current, last_interaction_time=last_interaction_time)
        happiness_rate, energy_rate = self._rates_for_emotion(emotion)
        inactivity_minutes = self._minutes_since(last_interaction_time, current)
        if inactivity_minutes >= self.BORED_AFTER_MINUTES and emotion == EmotionState.NORMAL:
            happiness_rate += 0.12

        new_happiness = self._clamp_value(self._happiness_value - minutes * happiness_rate)
        new_energy = self._clamp_value(self._energy_value - minutes * energy_rate)
        changed = int(round(new_happiness)) != self.vitals.happiness or int(round(new_energy)) != self.vitals.energy

        self._happiness_value = new_happiness
        self._energy_value = new_energy
        self.vitals.happiness = int(round(new_happiness))
        self.vitals.energy = int(round(new_energy))
        self.vitals.last_updated_at = current
        return changed

    def _rates_for_emotion(self, emotion: EmotionState) -> tuple[float, float]:
        rates = {
            EmotionState.NORMAL: (0.08, 0.10),
            EmotionState.WORKING: (0.22, 0.30),
            EmotionState.BORED: (0.14, 0.12),
            EmotionState.LOW_HAPPINESS: (0.10, 0.15),
            EmotionState.LOW_ENERGY: (0.12, 0.22),
            EmotionState.DRAINED: (0.05, 0.08),
        }
        return rates[emotion]

    @staticmethod
    def _clamp_value(value: float) -> float:
        return max(0.0, min(100.0, value))

    @staticmethod
    def _minutes_since(reference: datetime | None, current: datetime) -> float:
        if reference is None:
            return 0.0
        normalized = ensure_local(reference)
        return max(0.0, (current - normalized).total_seconds() / 60.0)

    @staticmethod
    def _is_working_time(current: datetime) -> bool:
        return current.weekday() <= 4 and 10 <= current.hour < 18
