"""Draws the radar app icon as PNG with no dependencies:  python tools/make_icons.py"""
import math
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs"


def png(path, size):
    bg = (11, 18, 32)
    teal = (45, 212, 191)
    cx = cy = size / 2
    R = size * 0.40
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            r = math.hypot(dx, dy)
            col = bg
            # sweep wedge (fades from the beam backwards)
            ang = (math.degrees(math.atan2(dy, dx)) + 360) % 360
            beam = 315
            diff = (beam - ang) % 360
            if r < R and diff < 70:
                a = (1 - diff / 70) * 0.55
                col = tuple(int(bg[i] + (teal[i] - bg[i]) * a) for i in range(3))
            # rings
            for k in (0.35, 0.68, 1.0):
                if abs(r - R * k) < size * 0.012:
                    col = tuple(int(c * 0.55 + t * 0.45) for c, t in zip(col, teal))
            # beam line
            if r < R and diff < 2.2:
                col = teal
            # blips
            for bx, by, br in ((0.22, -0.18, 0.045), (-0.16, 0.12, 0.035), (0.05, 0.27, 0.03)):
                if math.hypot(dx - bx * size, dy - by * size) < br * size:
                    col = (250, 250, 250)
            row += bytes(col)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(data)


if __name__ == "__main__":
    png(OUT / "icon-180.png", 180)
    png(OUT / "icon-512.png", 512)
    print("icons written")
