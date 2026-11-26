"""Валидация медиафайлов по сигнатуре (magic bytes) и лимитам размера."""
from dataclasses import dataclass

IMAGE_MAX_BYTES = 5 * 1024 * 1024   # 5 МБ
AUDIO_MAX_BYTES = 10 * 1024 * 1024  # 10 МБ


@dataclass(frozen=True)
class MediaSpec:
    kind: str          # "image" | "audio"
    content_type: str
    extension: str
    max_bytes: int


def detect_media_spec(header: bytes) -> MediaSpec | None:
    """Определяет тип файла по его первым байтам (magic bytes)."""
    if not header:
        return None

    # JPEG: FF D8 FF
    if header.startswith(b"\xff\xd8\xff"):
        return MediaSpec("image", "image/jpeg", ".jpg", IMAGE_MAX_BYTES)

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return MediaSpec("image", "image/png", ".png", IMAGE_MAX_BYTES)

    # WebP: RIFF....WEBP
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return MediaSpec("image", "image/webp", ".webp", IMAGE_MAX_BYTES)

    # OGG: OggS
    if header.startswith(b"OggS"):
        return MediaSpec("audio", "audio/ogg", ".ogg", AUDIO_MAX_BYTES)

    # WAV: RIFF....WAVE
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        return MediaSpec("audio", "audio/wav", ".wav", AUDIO_MAX_BYTES)

    # MP3: тег ID3v2 или синхрослово MPEG-фрейма (11 единичных бит + валидные version/layer)
    if header.startswith(b"ID3") or (
        len(header) >= 2
        and header[0] == 0xFF
        and (header[1] & 0xE0) == 0xE0
        and (header[1] & 0x18) != 0x08
        and (header[1] & 0x06) != 0x00
    ):
        return MediaSpec("audio", "audio/mpeg", ".mp3", AUDIO_MAX_BYTES)

    return None