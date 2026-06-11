from __future__ import annotations

from pathlib import Path

try:
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover
    WhisperModel = None


class VoiceTranscriber:
    def __init__(self, model_size: str = "tiny") -> None:
        self._model_size = model_size
        self._model = None

    def _ensure_model(self) -> WhisperModel:
        if WhisperModel is None:
            raise RuntimeError("faster-whisper is not installed")
        if self._model is None:
            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio_path: str | Path) -> str:
        model = self._ensure_model()
        segments, _info = model.transcribe(str(audio_path))
        parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        return " ".join(parts).strip()
