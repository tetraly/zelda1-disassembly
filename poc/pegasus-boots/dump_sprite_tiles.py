#!/usr/bin/env python3
"""Lists and draws the always-loaded sprite tiles ($00-$6F) of a Zelda 1 PRG0 ROM.

Usage: python3 dump_sprite_tiles.py "Legend of Zelda, The (USA).nes" [tiles.png]

Prints the blank (all-zero) tiles and writes a PNG of the 112 tiles, 16 per row, each
labelled by position: row = high digit, column = low digit. A free 8x16 slot for a boots
icon needs an even tile N and N+1 that are both unused; for the narrow item drawing
N must be in $20-$61.
"""
import struct
import sys
import zlib

HEADER = 16
COMMON_SPRITES = HEADER + 32895      # bins.xml CommonSpritePatterns, loaded at PPU $0000
TILES = 0x70
GREYS = (0, 0x55, 0xAA, 0xFF)


def tile_pixels(data: bytes, n: int) -> list[list[int]]:
    t = data[COMMON_SPRITES + 16 * n:COMMON_SPRITES + 16 * n + 16]
    return [[(t[y] >> (7 - x) & 1) | (t[y + 8] >> (7 - x) & 1) << 1 for x in range(8)] for y in range(8)]


def write_png(path: str, rows: list[bytes], width: int) -> None:
    raw = b"".join(b"\0" + r for r in rows)
    chunk = lambda kind, body: struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, len(rows), 8, 0, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def main() -> None:
    data = open(sys.argv[1], "rb").read()
    out = sys.argv[2] if len(sys.argv) > 2 else "sprite_tiles.png"
    blank = [n for n in range(TILES) if not any(data[COMMON_SPRITES + 16 * n:COMMON_SPRITES + 16 * n + 16])]
    print("Blank tiles:", " ".join(f"${n:02X}" for n in blank) or "none")
    pairs = [n for n in blank if n % 2 == 0 and n + 1 in blank]
    print("Blank even/odd pairs (8x16 slots):", " ".join(f"${n:02X}" for n in pairs) or "none")

    scale, gap = 4, 2
    cell = 8 * scale + gap
    width = 16 * cell
    rows = []
    for ty in range(TILES // 16):
        tiles = [tile_pixels(data, ty * 16 + tx) for tx in range(16)]
        for y in range(8):
            line = bytearray()
            for tx in range(16):
                for x in range(8):
                    line += bytes([GREYS[tiles[tx][y][x]] if tiles[tx][y][x] else 0x30]) * scale
                line += bytes([0x80]) * gap
            rows += [bytes(line)] * scale
        rows += [bytes([0x80]) * width] * gap
    write_png(out, rows, width)
    print(f"Wrote {out} (rows $0x-$6x top to bottom, columns x0-xF; blank pixels dark grey)")


if __name__ == "__main__":
    main()
