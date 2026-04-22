from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from utils.paths import default_gif_path, resource_path
from utils.time_utils import now_local


class PetAnimationKey(str, Enum):
    APPEAR = "APPEAR"
    DRAG = "DRAG"
    HEART = "HEART"
    CLICK_CONFUSED = "CLICK_CONFUSED"
    WORK = "WORK"
    HAPPY = "HAPPY"
    CLEAN = "CLEAN"
    IDLE = "IDLE"
    SAD = "SAD"
    SLEEP = "SLEEP"
    FEED = "FEED"
    EXERCISE = "EXERCISE"


class AnimationKind(str, Enum):
    BASE = "BASE"
    EVENT = "EVENT"
    OVERLAY = "OVERLAY"


@dataclass(frozen=True, slots=True)
class AnimationClip:
    key: PetAnimationKey
    relative_dir: str
    kind: AnimationKind
    priority: int
    duration_ms: int | None = None
    fallback: PetAnimationKey | None = None


@dataclass(slots=True)
class AnimationTransition:
    key: PetAnimationKey
    path: Path | None
    duration_ms: int | None
    is_event: bool
    is_overlay: bool


ANIMATION_REGISTRY: dict[PetAnimationKey, AnimationClip] = {
    PetAnimationKey.APPEAR: AnimationClip(
        key=PetAnimationKey.APPEAR,
        relative_dir="assets/GIF/pet/appear",
        kind=AnimationKind.EVENT,
        priority=50,
        duration_ms=2600,
        fallback=PetAnimationKey.IDLE,
    ),
    PetAnimationKey.DRAG: AnimationClip(
        key=PetAnimationKey.DRAG,
        relative_dir="assets/GIF/pet/drag",
        kind=AnimationKind.OVERLAY,
        priority=60,
    ),
    PetAnimationKey.FEED: AnimationClip(
        key=PetAnimationKey.FEED,
        relative_dir="assets/GIF/pet/feed",
        kind=AnimationKind.EVENT,
        priority=40,
        duration_ms=3200,
        fallback=PetAnimationKey.IDLE,
    ),
    PetAnimationKey.CLEAN: AnimationClip(
        key=PetAnimationKey.CLEAN,
        relative_dir="assets/GIF/pet/clean",
        kind=AnimationKind.EVENT,
        priority=40,
        duration_ms=3400,
        fallback=PetAnimationKey.IDLE,
    ),
    PetAnimationKey.EXERCISE: AnimationClip(
        key=PetAnimationKey.EXERCISE,
        relative_dir="assets/GIF/pet/exercise",
        kind=AnimationKind.EVENT,
        priority=40,
        duration_ms=3600,
        fallback=PetAnimationKey.IDLE,
    ),
    PetAnimationKey.HEART: AnimationClip(
        key=PetAnimationKey.HEART,
        relative_dir="assets/GIF/pet/heart",
        kind=AnimationKind.EVENT,
        priority=30,
        duration_ms=2400,
        fallback=PetAnimationKey.IDLE,
    ),
    PetAnimationKey.CLICK_CONFUSED: AnimationClip(
        key=PetAnimationKey.CLICK_CONFUSED,
        relative_dir="assets/GIF/pet/click_confused",
        kind=AnimationKind.EVENT,
        priority=20,
        duration_ms=2000,
        fallback=PetAnimationKey.IDLE,
    ),
    PetAnimationKey.IDLE: AnimationClip(
        key=PetAnimationKey.IDLE,
        relative_dir="assets/GIF/pet/idle",
        kind=AnimationKind.BASE,
        priority=0,
    ),
    PetAnimationKey.HAPPY: AnimationClip(
        key=PetAnimationKey.HAPPY,
        relative_dir="assets/GIF/pet/happy",
        kind=AnimationKind.BASE,
        priority=0,
        fallback=PetAnimationKey.IDLE,
    ),
    PetAnimationKey.SAD: AnimationClip(
        key=PetAnimationKey.SAD,
        relative_dir="assets/GIF/pet/sad",
        kind=AnimationKind.BASE,
        priority=0,
        fallback=PetAnimationKey.IDLE,
    ),
    PetAnimationKey.SLEEP: AnimationClip(
        key=PetAnimationKey.SLEEP,
        relative_dir="assets/GIF/pet/sleep",
        kind=AnimationKind.BASE,
        priority=0,
        fallback=PetAnimationKey.IDLE,
    ),
    PetAnimationKey.WORK: AnimationClip(
        key=PetAnimationKey.WORK,
        relative_dir="assets/GIF/pet/work",
        kind=AnimationKind.BASE,
        priority=0,
        fallback=PetAnimationKey.IDLE,
    ),
}


class AnimationSelector:
    def __init__(self, _manifest=None) -> None:
        self.registry = ANIMATION_REGISTRY
        self._last_choice: dict[PetAnimationKey, Path] = {}

    def resolve_animation_path(self, key: PetAnimationKey, *, fallback_key: PetAnimationKey | None = None) -> Path | None:
        checked: list[PetAnimationKey] = []
        current: PetAnimationKey | None = key
        while current is not None and current not in checked:
            checked.append(current)
            candidates = self.category_paths(current)
            if candidates:
                chosen = self._pick(current, candidates)
                self._last_choice[current] = chosen
                return chosen
            if current == key and fallback_key is not None and fallback_key not in checked:
                current = fallback_key
                continue
            current = self.registry[current].fallback
        return default_gif_path()

    def category_paths(self, key: PetAnimationKey) -> list[Path]:
        directory = resource_path(self.registry[key].relative_dir)
        if not directory.exists():
            return []
        return sorted(path for path in directory.glob("*.gif") if path.is_file())

    def duration_for(self, key: PetAnimationKey) -> int | None:
        return self.registry[key].duration_ms

    def priority_for(self, key: PetAnimationKey) -> int:
        return int(self.registry[key].priority)

    def is_event(self, key: PetAnimationKey) -> bool:
        return self.registry[key].kind == AnimationKind.EVENT

    def is_overlay(self, key: PetAnimationKey) -> bool:
        return self.registry[key].kind == AnimationKind.OVERLAY

    def select_base_animation(self, status, *, current_time=None) -> PetAnimationKey:
        current = current_time or now_local()
        if bool(getattr(status, "is_resting", False)):
            return PetAnimationKey.SLEEP
        if _is_working_time(current) and int(getattr(status, "energy", 0)) >= 25:
            return PetAnimationKey.WORK
        if (
            int(getattr(status, "mood", 0)) <= 30
            or int(getattr(status, "energy", 0)) <= 25
            or int(getattr(status, "cleanliness", 0)) <= 25
            or int(getattr(status, "hunger", 0)) <= 25
        ):
            return PetAnimationKey.SAD
        if (
            int(getattr(status, "mood", 0)) >= 75
            and int(getattr(status, "energy", 0)) >= 50
            and int(getattr(status, "cleanliness", 0)) >= 45
            and int(getattr(status, "hunger", 0)) >= 35
        ):
            return PetAnimationKey.HAPPY
        return PetAnimationKey.IDLE

    def select_click_animation(self, status) -> PetAnimationKey:
        favorability = int(getattr(status, "favorability", 0))
        if favorability >= 60:
            chance = min(0.75, 0.25 + (favorability - 60) * 0.015)
            if random.random() < chance:
                return PetAnimationKey.HEART
        return PetAnimationKey.CLICK_CONFUSED

    def _pick(self, key: PetAnimationKey, candidates: list[Path]) -> Path:
        if len(candidates) <= 1:
            return candidates[0]
        previous = self._last_choice.get(key)
        pool = [candidate for candidate in candidates if candidate != previous] or candidates
        return random.choice(pool)


class AnimationManager:
    def __init__(self, selector: AnimationSelector) -> None:
        self.selector = selector
        self.current_animation = PetAnimationKey.IDLE
        self.base_animation = PetAnimationKey.IDLE
        self._active_event: PetAnimationKey | None = None
        self._active_overlay: PetAnimationKey | None = None

    def bootstrap(self, status, *, current_time=None) -> AnimationTransition:
        self.refresh_base_animation(status, current_time=current_time)
        transition = self.play_event_animation(PetAnimationKey.APPEAR, force=True)
        return transition or self._build_transition(self.base_animation)

    def play_base_animation(self, key: PetAnimationKey) -> AnimationTransition | None:
        self.base_animation = key
        if self._active_event is not None or self._active_overlay is not None:
            return None
        self.current_animation = key
        return self._build_transition(key)

    def refresh_base_animation(self, status, *, current_time=None) -> AnimationTransition | None:
        key = self.selector.select_base_animation(status, current_time=current_time)
        return self.play_base_animation(key)

    def play_event_animation(self, key: PetAnimationKey, *, force: bool = False) -> AnimationTransition | None:
        if not self.selector.is_event(key):
            return self.play_base_animation(key)
        if self._active_overlay is not None:
            return None
        if self._active_event is not None and not force:
            if self.selector.priority_for(key) < self.selector.priority_for(self._active_event):
                return None
        self._active_event = key
        self.current_animation = key
        return self._build_transition(key)

    def start_overlay_animation(self, key: PetAnimationKey) -> AnimationTransition | None:
        if not self.selector.is_overlay(key):
            return self.play_base_animation(key)
        self._active_event = None
        self._active_overlay = key
        self.current_animation = key
        return self._build_transition(key, fallback_key=self.base_animation)

    def stop_overlay_animation(self) -> AnimationTransition | None:
        if self._active_overlay is None:
            return None
        self._active_overlay = None
        self.current_animation = self.base_animation
        return self._build_transition(self.base_animation)

    def on_animation_finished(self) -> AnimationTransition | None:
        if self._active_overlay is not None or self._active_event is None:
            return None
        self._active_event = None
        self.current_animation = self.base_animation
        return self._build_transition(self.base_animation)

    def is_event_active(self) -> bool:
        return self._active_event is not None

    def is_overlay_active(self) -> bool:
        return self._active_overlay is not None

    def _build_transition(
        self,
        key: PetAnimationKey,
        *,
        fallback_key: PetAnimationKey | None = None,
    ) -> AnimationTransition:
        return AnimationTransition(
            key=key,
            path=self.selector.resolve_animation_path(key, fallback_key=fallback_key),
            duration_ms=self.selector.duration_for(key) if self.selector.is_event(key) else None,
            is_event=self.selector.is_event(key),
            is_overlay=self.selector.is_overlay(key),
        )


def _is_working_time(current_time) -> bool:
    return current_time.weekday() <= 4 and 10 <= current_time.hour < 18
