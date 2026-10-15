# Pegasus Boots proof of concept

Replaces the wooden and magical boomerangs with L1 and L2 Pegasus Boots in
*The Legend of Zelda* (USA, PRG0). The patch is space-neutral: all of its
bytes are rewritten in place and none are added.

## Make the test ROM

```
python3 pegasus_boots_poc.py "Legend of Zelda, The (USA).nes" boots_poc.nes
```

Options: `--l1-speed HEX` and `--l2-speed HEX` set the boots' QSpeed (defaults
`79` and `A5`, the beta tester's pick). For example, `--l1-speed C0 --l2-speed F4` gives L1 2× and L2 about
2.44×.

| QSpeed | Effective speed | vs vanilla | Motion |
| --- | --- | --- | --- |
| `60` (vanilla) | 1.33 px/frame | 1× | |
| `79` | 1.78 px/frame | ~1.34× | nearly smooth (1–2 px steps) |
| `80` | 2.0 px/frame | 1.5× | smooth (2 px every frame) |
| `A5` | 2.31 px/frame | ~1.73× | nearly smooth (1–3 px steps) |
| `C0` | 2.67 px/frame | 2× | smooth (3, 3, 2 px) |
| `F4` | 3.25 px/frame | ~2.44× | uneven: steps of 1 to 4 px per frame |
| `F8` | 3.5 px/frame | ~2.63× | uneven |

Link moves on an 8-pixel grid and stops at each grid point, so speeds above 2×
mix 4-pixel and 1-pixel frames. A smooth 2.5× or 3× would need changes to the
shared movement routine in the full fixed bank.

The script checks that the input is the PRG0 ROM (No-Intro SHA-1
`a12d74c7…` of the data after the header) and that every code site still has
its vanilla bytes. It writes `boots_poc.nes` and `boots_poc.ips`. The IPS
patch is made from your ROM and works with any IPS patcher. PRG1 is not
supported.

## What to test

- **Shop:** the overworld shop that sells the blue candle now also sells L1
  and L2 boots for 1 rupee each. The candle stays. A new game starts with 0
  rupees, so pick one up first.
- **Selecting the boots:** open the menu with Start and put the boots on B.
  They show where the boomerang used to be.
- **L2:** hold B and a direction. Link runs at once at about 1.73× walking
  speed (QSpeed `$A5` by default).
- **L1 (without L2):** hold B and a direction. Link runs in place for 32
  frames, with a whoosh every 8 frames, then runs at about 1.34× (QSpeed
  `$79` by default).
- **Releasing B** goes back to walking speed. A new B press clears L1's charge.
- **Stairs** keep the vanilla slow speed.
- **No boots, no effect:** with no B items at all the game leaves the B
  selection on the boots slot; the boots check ownership, so Link walks
  normally then.
- **Icon:** the boots have their own icon in the blank sprite tiles `$1C`/`$1D`.
  The boomerang graphics are untouched.
- **Goriyas** throw boomerangs with the full vanilla spin and spark.
- **Attract mode:** the title screen's item list says BOOTS and MAGICAL BOOTS
  where it said BOOMERANG and MAGICAL BOOMERANG.

**Known quirks (accepted for the POC):**
- L1 keeps its charge while B stays held, even through a sword swing or a
  screen scroll.
- Re-pressing B during a sword swing doesn't clear the charge.
- Getting hit doesn't cancel the charge.
- Goriya boomerangs turn blue once you own L2 boots (vanilla behaviour of
  the magical boomerang).

## Bytes changed

| File offset | Bytes | What |
| --- | --- | --- |
| `0x14E48` | 57 | Bank 5 `$8E38`: `WieldBoomerang`'s body becomes `BootsPressB` and `BootsSpeed` |
| `0x17376` | 4 | Bank 5 `$B366`: `InitLinkSpeed`'s `LDA #$60 / STA $00` becomes `JSR BootsSpeed / NOP` (the bytes ZORA reserves for co-op) |
| `0x07154` | 2 | Bank 1 `Anim_ItemFrameOffsets` for item slots `$1D`/`$1E`: `$22` becomes `$25`, the boots icon entry |
| `0x07181` | 1 | Bank 1 `Anim_ItemFrameTiles[$25]`: the boomerang spark's `$3C` becomes the boots tile `$1C` |
| `0x071CE` | 1 | Bank 1 `Anim_WriteSpecificItemSprites`: narrow (half-width) tiles start at `$1C` instead of `$20`. No item drew `$1C`-`$1F` before |
| `0x1F4F5` | 9 | Bank 7 `BoomerangFrameCycle`: the flying boomerang's frames wrap from `$25` back to its vanilla entries `$22`-`$24`, and its spark uses entry 9 (also `$3C`) |
| `0x0824F` | 32 | Sprite tiles `$1C`/`$1D`, blank in PRG0, become the boot (design A: outline color 3, fill color 2). `$1E`/`$1F` after them are the inventory cursor and stay as they are |
| `0x14E64`, `0x14E7C` | 1 each | L1 and L2 speed operands inside `BootsSpeed` (`--l1-speed`, `--l2-speed`) |
| attract text | 26 | `MAGICAL BOOMERANG` and `BOOMERANG` become `MAGICAL BOOTS` and `BOOTS`, centered in the same length (found in DemoTextFields at patch time) |
| shop | 4 | Two wares and two prices of the blue candle shop (found at patch time) |

RAM: the L1 charge counter is `$038F` (`ObjMovingLimit+15`, which only the
player's boomerang used).

## Files

- `pegasus_boots_poc.py`: the patcher.
- `boots-source.diff`: the code change as a diff against `src/`. The code
  bytes in the patcher come from assembling the disassembly with this diff
  applied.
- `test_boots_logic.py`: runs the patched `InitLinkSpeed`, `BootsSpeed` and
  `BootsPressB` on a minimal 6502 interpreter and checks speeds, the
  32-frame charge, the charge sound and the charge reset:
  `python3 test_boots_logic.py boots_poc.nes`.
- `dump_sprite_tiles.py`: lists the blank tiles among the always-loaded
  sprites and draws all of them to a PNG.
- `boot_preview.png`: the boot icon. Left: L1 in Link's palette (brown outline,
  tan fill). Right: L2 in the blue palette (white outline, light-blue fill). The
  palette colors are assumed, not read from the ROM.

## Not yet verified

This was built without a vanilla ROM:
- The disassembly was assembled with zero-filled data files of the correct
  sizes, so code addresses are exact.
- The first version (boot drawn over tile `$36`) was play-tested. This
  version, with its own icon, has not been run yet.
- The boot art and its colours haven't been seen in game.
- Tiles `$1C`/`$1D` are blank in PRG0, and no code or table in the disassembly
  draws them. A PPU viewer during play can confirm that nothing else uses them.
