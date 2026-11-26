"""Заглушки медиа для seed без внешних зависимостей: PNG (zlib) и WAV (wave).

Настоящие файлы можно положить в backend/seed/assets/<ключ>.<png|jpg|wav|mp3|ogg> —
seed возьмёт их вместо сгенерированных.
"""
import io
import math
import random
import struct
import wave
import zlib


def make_png(width: int, height: int, top: tuple, bottom: tuple, circle: tuple) -> bytes:
    """Вертикальный градиент и круг по центру."""
    cx, cy, r = width // 2, height // 2, height // 4
    raw = bytearray()
    for y in range(height):
        k = y / (height - 1)
        base = [round(top[i] + (bottom[i] - top[i]) * k) for i in range(3)]
        raw.append(0)  # фильтр строки: None
        for x in range(width):
            inside = (x - cx) ** 2 + (y - cy) ** 2 <= r * r
            raw.extend(circle if inside else base)

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8 бит, RGB
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def _wav(samples: list[float], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in samples))
    return buf.getvalue()


def make_bell(seconds: float = 3.0, rate: int = 22050) -> bytes:
    """Колокольный удар: несколько негармонических обертонов с затуханием."""
    partials = [(220, 1.0, 1.2), (440, 0.6, 1.6), (594, 0.5, 2.0), (880, 0.3, 2.8)]
    out = []
    for i in range(int(seconds * rate)):
        t = i / rate
        out.append(sum(a * math.exp(-t * d) * math.sin(2 * math.pi * f * t) for f, a, d in partials) * 0.35)
    return _wav(out, rate)


def make_salvo(rate: int = 22050) -> bytes:
    """Три «залпа»: затухающий шум с низкочастотным гулом."""
    rng = random.Random(1812)
    out = []
    for burst in range(3):
        for i in range(int(0.9 * rate)):
            t = i / rate
            noise = rng.uniform(-1, 1) * math.exp(-t * 7)
            boom = math.sin(2 * math.pi * 55 * t) * math.exp(-t * 4)
            out.append((noise * 0.5 + boom * 0.6) * 0.8)
    return _wav(out, rate)
