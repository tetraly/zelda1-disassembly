#!/usr/bin/env python3
"""Pegasus Boots proof of concept for The Legend of Zelda (USA, PRG0).

Replaces the wooden and magical boomerangs with L1 and L2 Pegasus Boots:
  - Boots act only while selected on B and B is held, with a direction pressed.
  - L1 (old wooden boomerang): runs in place for 32 frames, whooshing every 8,
    then runs at QSpeed $80 (2.0 px/frame, 1.5x vanilla).
  - L2 (old magical boomerang): runs at once at QSpeed $C0 (2.67 px/frame, 2x).
  - Releasing B returns to vanilla speed. Stairs keep their vanilla slow speed.
  - The boots get their own icon in the blank sprite tiles $1C/$1D. Goriyas
    keep the full vanilla boomerang spin and spark.
  - Test shop: the overworld shop that sells the blue candle also sells L1 and
    L2 boots for 1 rupee each.

Every code byte below comes from assembling the patched disassembly (see
README.md); the patch is space-neutral (bytes rewritten in place, none added).

Usage:
    python3 pegasus_boots_poc.py "Legend of Zelda, The (USA).nes" boots_poc.nes

Writes the patched ROM and an IPS patch beside it (boots_poc.ips).
"""
import argparse
import hashlib
import sys
from pathlib import Path

HEADER_SIZE = 16
ROM_SIZE = HEADER_SIZE + 0x20000
# No-Intro "Legend of Zelda, The (USA)" (PRG0), the 128 KiB after the iNES header.
PRG0_DATA_SHA1 = "a12d74c73a0481599a5d832361d168f4737bbcf6"

# (headered file offset, vanilla bytes, patched bytes, what)
CODE_SITES = (
    (0x14E48,
     "ad74060d7506f031a20fb5acf0030a9028a91095acac7506b91a8e9d8003201b71a9c09dbc03a9039dd003a9018dd003adf803d002a5989598",
     "a9008d8f0360a060ad5606d02824fa5024ad7506d01dad7406f01aa080ad8f03c920b011ee8f032907d005a90220806da0002ca0c0840060ea",
     "WieldBoomerang body -> BootsPressB + BootsSpeed (bank 5 $8E38-$8E70)"),
    (0x17376, "a9608500", "203e8eea",
     "InitLinkSpeed: LDA #$60 / STA $00 -> JSR BootsSpeed / NOP (bank 5 $B366-$B369)"),
    (0x07154, "2222", "2525",
     "Anim_ItemFrameOffsets[$1D/$1E]: boots icon at Anim_ItemFrameTiles[$25] (bank 1)"),
    (0x07181, "3c", "1c",
     "Anim_ItemFrameTiles[$25]: the boomerang's spark tile $3C -> boots tile $1C (bank 1)"),
    (0x071CE, "20", "1c",
     "Anim_WriteSpecificItemSprites: narrow tiles start at $1C instead of $20 (bank 1)"),
    (0x1F4F5, "000102010001020103", "fdfefffefdfefffee4",
     "BoomerangFrameCycle: Goriya frames wrap back to the vanilla tiles; spark uses entry 9 ($3C) (bank 7 $F4E5)"),
)

# Sprite tiles $1C (top) and $1D (bottom) of CommonSpritePatterns (bank 2 $807F + $1C0):
# blank and unused in PRG0 ($1E/$1F after them are the inventory cursor).
# 0 = transparent, 2/3 = sprite colors 2/3: outline 3, fill 2 (design A). L1 is drawn in
# Link's palette (brown outline, tan fill), L2 in the blue palette (white outline, light blue).
BOOT_TILE_OFFSET = HEADER_SIZE + 32895 + 0x1C * 16
BOOT_ART = """
........
.33333..
.32223..
.33333..
.32223..
.32223..
.32223..
.32223..
.32223..
.322233.
.3222233
.3222223
.3333333
........
........
........
""".split()

# Overworld cave wares and prices (zora/rom/layout.py): 20 caves x 3 wares.
CAVE_WARES_OFFSET = HEADER_SIZE + 0x18600      # LevelBlockOW ($18400 in bins.xml) + $200
CAVE_PRICES_OFFSET = CAVE_WARES_OFFSET + 60
CAVE_COUNT = 20
ITEM_MASK = 0x3F
BLUE_CANDLE = 0x06
L1_BOOTS = 0x1D        # wooden boomerang's item id
L2_BOOTS = 0x1E        # magical boomerang's item id
TEST_PRICE = 1

# BootsSpeed's two LDY # operands (bank 5 $8E54 and $8E6C), QSpeed per frame / 4.
L1_SPEED_OFFSET = 0x14E64
L2_SPEED_OFFSET = 0x14E7C
# Effective speed is quantized by Link's 8-pixel movement grid (vanilla $60 = 1.33 px/frame).
SPEED_NOTES = {0x79: "1.78 px/frame, ~1.34x, nearly smooth (1-2 px steps)",
               0xA5: "2.31 px/frame, ~1.73x, nearly smooth (1-3 px steps)",
               0x80: "2.0 px/frame, 1.5x, smooth", 0xC0: "2.67 px/frame, 2x, smooth",
               0xF4: "3.25 px/frame, ~2.44x, uneven (1-4 px steps)",
               0xF8: "3.5 px/frame, ~2.63x, uneven (1-4 px steps)"}

# The attract mode's item list (bins.xml DemoTextFields): fields of an offset byte, tiles, $FF.
DEMO_TEXT_OFFSET = HEADER_SIZE + 37530
DEMO_TEXT_SIZE = 531
RENAMES = (("MAGICAL BOOMERANG", "MAGICAL BOOTS"), ("BOOMERANG", "BOOTS"))


def tile_bytes(art: list[str]) -> bytes:
    assert len(art) == 16 and all(len(row) == 8 for row in art)
    out = bytearray()
    for half in (art[:8], art[8:]):
        values = [[0 if c == "." else int(c) for c in row] for row in half]
        out += bytes(sum((v[i] & 1) << (7 - i) for i in range(8)) for v in values)
        out += bytes(sum((v[i] >> 1 & 1) << (7 - i) for i in range(8)) for v in values)
    return bytes(out)


def encode(text: str) -> bytes:
    """Zelda 1 tile codes: 0-9 = $00-$09, A-Z = $0A-$23, space = $24."""
    return bytes(ord(c) - 48 if c.isdigit() else 0x24 if c == " " else ord(c) - 55 for c in text)


def rename_demo_text(rom: bytearray) -> list[str]:
    """Same-length, centered replacements in the attract mode's item list."""
    log = []
    block = slice(DEMO_TEXT_OFFSET, DEMO_TEXT_OFFSET + DEMO_TEXT_SIZE)
    for old, new in RENAMES:
        pad = len(old) - len(new)
        old_b, new_b = encode(old), encode(" " * (pad // 2) + new + " " * (pad - pad // 2))
        text = bytearray(rom[block])
        at = text.find(old_b)
        while at >= 0:
            rom[DEMO_TEXT_OFFSET + at:DEMO_TEXT_OFFSET + at + len(new_b)] = new_b
            log.append(f"{DEMO_TEXT_OFFSET + at:#07x} {len(new_b):2} bytes  attract-mode text {old!r} -> {new!r}")
            text[at:at + len(new_b)] = new_b
            at = text.find(old_b)
    if not log:
        log.append("warning: no BOOMERANG text found in the attract mode's item list")
    return log


def patch(rom: bytearray, l1_speed: int = 0x80, l2_speed: int = 0xC0) -> list[str]:
    log = []
    for offset, old, new, what in CODE_SITES:
        old, new = bytes.fromhex(old), bytes.fromhex(new)
        if rom[offset:offset + len(old)] != old:
            raise SystemExit(f"Unexpected bytes at {offset:#x} ({what}); is this an unmodified PRG0 ROM?")
        rom[offset:offset + len(new)] = new
        log.append(f"{offset:#07x} {len(new):2} bytes  {what}")

    for offset, speed, name in ((L1_SPEED_OFFSET, l1_speed, "L1"), (L2_SPEED_OFFSET, l2_speed, "L2")):
        rom[offset] = speed
        log.append(f"{offset:#07x}  1 byte   {name} boots speed ${speed:02X} ({SPEED_NOTES.get(speed, 'see README')})")

    log += rename_demo_text(rom)

    tile = tile_bytes(BOOT_ART)
    if any(rom[BOOT_TILE_OFFSET:BOOT_TILE_OFFSET + len(tile)]):
        raise SystemExit("Sprite tiles $1C/$1D are not blank in this ROM; the boots icon needs them.")
    rom[BOOT_TILE_OFFSET:BOOT_TILE_OFFSET + len(tile)] = tile
    log.append(f"{BOOT_TILE_OFFSET:#07x} {len(tile):2} bytes  sprite tiles $1C/$1D (blank) -> boot icon")

    shops = [i for i in range(CAVE_COUNT)
             if any(rom[CAVE_WARES_OFFSET + 3 * i + j] & ITEM_MASK == BLUE_CANDLE for j in range(3))]
    if not shops:
        raise SystemExit("No overworld shop sells the blue candle in this ROM.")
    cave = shops[0]
    boots = iter((L1_BOOTS, L2_BOOTS))
    for j in range(3):
        at = CAVE_WARES_OFFSET + 3 * cave + j
        if rom[at] & ITEM_MASK == BLUE_CANDLE:
            continue
        item = next(boots, None)
        if item is None:
            break
        rom[at] = rom[at] & ~ITEM_MASK & 0xFF | item       # keep the cave-flag bits 6-7
        rom[CAVE_PRICES_OFFSET + 3 * cave + j] = TEST_PRICE
        log.append(f"{at:#07x}  1 byte   cave {cave} ware {j} -> item {item:#04x} for {TEST_PRICE} rupee")
    return log


def ips(before: bytes, after: bytes) -> bytes:
    out = bytearray(b"PATCH")
    i = 0
    while i < len(after):
        if before[i] == after[i]:
            i += 1
            continue
        start = i
        while i < len(after) and before[i] != after[i] and i - start < 0xFFFF:
            i += 1
        out += start.to_bytes(3, "big") + (i - start).to_bytes(2, "big") + after[start:i]
    return bytes(out + b"EOF")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("rom", type=Path, help="Legend of Zelda, The (USA).nes (PRG0)")
    parser.add_argument("out", type=Path, help="patched ROM to write")
    parser.add_argument("--force", action="store_true", help="skip the PRG0 hash check")
    speed = lambda text: int(text, 16)
    parser.add_argument("--l1-speed", type=speed, default=0x80, metavar="HEX",
                        help="L1 QSpeed, $60-$FF (default 80 = 1.5x; C0 = 2x)")
    parser.add_argument("--l2-speed", type=speed, default=0xC0, metavar="HEX",
                        help="L2 QSpeed, $60-$FF (default C0 = 2x; F4 = ~2.44x, uneven)")
    args = parser.parse_args()
    for value in (args.l1_speed, args.l2_speed):
        if not 0x60 <= value <= 0xFF:
            sys.exit("Speeds must be between 60 (vanilla) and FF.")

    data = args.rom.read_bytes()
    if len(data) != ROM_SIZE or data[:4] != b"NES\x1a":
        sys.exit(f"Expected a headered 128 KiB NES ROM ({ROM_SIZE} bytes), got {len(data)}.")
    digest = hashlib.sha1(data[HEADER_SIZE:]).hexdigest()
    if digest != PRG0_DATA_SHA1 and not args.force:
        sys.exit(f"Not the PRG0 ROM (SHA-1 {digest}). PRG1 is not supported by this POC.")

    rom = bytearray(data)
    for line in patch(rom, args.l1_speed, args.l2_speed):
        print(line)
    args.out.write_bytes(rom)
    ips_path = args.out.with_suffix(".ips")
    ips_path.write_bytes(ips(data, rom))
    print(f"Wrote {args.out} and {ips_path}")


if __name__ == "__main__":
    main()
