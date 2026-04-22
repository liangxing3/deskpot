from __future__ import annotations

from dataclasses import dataclass

from data.manual_actions import MANUAL_ACTION_SPECS, ManualActionSpec
from data.models import EmotionState
from data.pet_models import PetStatus
from utils.time_utils import minutes_since, now_local


@dataclass(slots=True)
class ActionFeedback:
    action_id: str
    label: str
    bubble_text: str
    variant: str
    duration_ms: int
    emotion: EmotionState


def clone_status(status: PetStatus) -> PetStatus:
    return PetStatus.from_dict(status.to_dict())


def update_pet_name(status: PetStatus, pet_name: str) -> PetStatus:
    updated = clone_status(status)
    updated.pet_name = pet_name.strip() or status.pet_name
    return updated


def apply_manual_action(
    status: PetStatus,
    action_id: str,
    *,
    current_time=None,
) -> tuple[PetStatus, ActionFeedback]:
    spec = MANUAL_ACTION_SPECS.get(action_id)
    if spec is None:
        raise KeyError(f"Unknown manual action: {action_id}")

    now = current_time or now_local()
    updated = clone_status(status)
    updated.hunger = _clamp(updated.hunger + spec.hunger_delta)
    updated.mood = _clamp(updated.mood + spec.mood_delta)
    updated.energy = _clamp(updated.energy + spec.energy_delta)
    updated.cleanliness = _clamp(updated.cleanliness + spec.cleanliness_delta)
    updated.favorability = _clamp(updated.favorability + spec.favorability_delta)
    updated.growth_exp = max(0, int(updated.growth_exp) + int(spec.growth_exp_delta))
    updated.is_resting = spec.action_id == "rest"
    _stamp_action_time(updated, spec, now)
    updated.last_growth_check_time = now
    updated.normalize()

    return updated, ActionFeedback(
        action_id=spec.action_id,
        label=spec.label,
        bubble_text=spec.bubble_text,
        variant=spec.variant,
        duration_ms=spec.duration_ms,
        emotion=derive_emotion(updated, now=now),
    )


def derive_emotion(status: PetStatus, *, now=None) -> EmotionState:
    current = now or now_local()
    if status.mood <= 12 and status.energy <= 12:
        return EmotionState.DRAINED
    if status.hunger <= 25:
        return EmotionState.HUNGRY
    if status.energy <= 25:
        return EmotionState.TIRED
    if status.cleanliness <= 25:
        return EmotionState.DIRTY
    if status.mood <= 25:
        return EmotionState.LOW_HAPPINESS
    if _minutes_since_last_interaction(status, current) >= 75 and not _is_working_time(current):
        return EmotionState.BORED
    if _is_working_time(current):
        return EmotionState.WORKING
    return EmotionState.NORMAL


def _stamp_action_time(status: PetStatus, spec: ManualActionSpec, current_time) -> None:
    mapping = {
        "feed": "last_feed_time",
        "play": "last_play_time",
        "clean": "last_clean_time",
        "rest": "last_rest_time",
    }
    target = mapping.get(spec.action_id)
    if target:
        setattr(status, target, current_time)


def _minutes_since_last_interaction(status: PetStatus, current_time) -> float:
    timestamps = (
        status.last_feed_time,
        status.last_play_time,
        status.last_clean_time,
        status.last_rest_time,
    )
    available = [item for item in timestamps if item is not None]
    if not available:
        return 0.0
    return minutes_since(max(available), current_time)


def _is_working_time(current_time) -> bool:
    return current_time.weekday() <= 4 and 10 <= current_time.hour < 18


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))
