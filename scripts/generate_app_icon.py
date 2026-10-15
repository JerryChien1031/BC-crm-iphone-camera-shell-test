"""Generate the shell's opaque camera icon with Python's standard library only.

Geometry follows the existing website icon. Does not import or write website files.
"""
from pathlib import Path
import struct
import zlib


def rounded(x, y, left, top, right, bottom, radius):
    nx = max(left + radius, min(x, right - radius))
    ny = max(top + radius, min(y, bottom - radius))
    return (x - nx) ** 2 + (y - ny) ** 2 <= radius ** 2


def white(x, y):
    if not (rounded(x, y, .18, .34, .82, .73, .055)
            or rounded(x, y, .35, .25, .65, .415, .035)):
        return False
    distance = (x - .5) ** 2 + (y - .535) ** 2
    if distance <= .128 ** 2:
        return distance <= .077 ** 2
    return (x - .735) ** 2 + (y - .415) ** 2 > .022 ** 2


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


def main():
    size = 1024
    pixels = bytearray()
    for row in range(size):
        pixels.append(0)
        for col in range(size):
            samples = sum(white((col + sx) / size, (row + sy) / size)
                          for sx in (.25, .75) for sy in (.25, .75))
            pixels.extend((base * (4 - samples) + 255 * samples + 2) // 4 for base in (36, 91, 232))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(pixels, 9)) + chunk(b"IEND", b""))
    target = Path(__file__).resolve().parents[1] / "CameraShell/Assets.xcassets/AppIcon.appiconset/AppIcon.png"
    target.write_bytes(png)
    print(f"Generated {target.name}: 1024 x 1024 RGB")


if __name__ == "__main__":
    main()
