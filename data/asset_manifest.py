from __future__ import annotations

import json
from pathlib import Path

from data.models import AnimationManifestEntry, EmotionState, PetState
from utils.paths import manifest_path, resource_path


class AssetManifest:
    def __init__(self, manifest_file: Path | None = None) -> None:
        self.manifest_file = manifest_file or manifest_path()
        self._entries = self._load_entries()

    def _load_entries(self) -> list[AnimationManifestEntry]:
        if not self.manifest_file.exists():
            return []
        payload = json.loads(self.manifest_file.read_text(encoding="utf-8-sig"))
        return [AnimationManifestEntry.from_dict(item) for item in payload.get("animations", [])]

    @property
    def entries(self) -> list[AnimationManifestEntry]:
        return list(self._entries)

    def entries_for_state(
        self,
        state: PetState,
        *,
        variant: str | None = None,
    ) -> list[AnimationManifestEntry]:
        entries = [entry for entry in self._entries if entry.state == state]
        if variant:
            variant_matches = [entry for entry in entries if entry.variant == variant]
            if variant_matches:
                return variant_matches
        return [entry for entry in entries if entry.variant is None] or entries

    def entries_for_emotion(self, emotion_state: EmotionState) -> list[AnimationManifestEntry]:
        return [entry for entry in self._entries if entry.emotion_state == emotion_state]

    def resolve(self, entry: AnimationManifestEntry) -> Path:
        return resource_path(entry.path)
