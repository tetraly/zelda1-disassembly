# Pegasus Boots proof of concept

Replaces the wooden and magical boomerangs with L1 and L2 Pegasus Boots in
*The Legend of Zelda* (USA, PRG0). The patch is space-neutral: all of its
bytes are rewritten in place and none are added.

## Make the test ROM

```
python3 pegasus_boots_poc.py "Legend of Zelda, The (USA).nes" boots_poc.nes
```

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
- **L2:** hold B and a direction. Link runs at once at about 2× walking
  speed (QSpeed `$C0`, 3 frames per 8-pixel tile).
- **L1 (without L2):** hold B and a direction. Link runs in place for 32
  frames, with a whoosh every 8 frames, then runs at 1.5× (QSpeed `$80`,
  4 frames per tile).
- **Releasing B** goes back to walking speed. A new B press clears L1's charge.
- **Stairs** keep the vanilla slow speed.
- **Icon:** the boots have their own icon in the blank sprite tiles `$1C`/`$1D`.
  The boomerang graphics are untouched.
- **Goriyas** throw boomerangs with the full vanilla spin and spark.

**Known quirks (accepted for the POC):**
- The attract-mode item list shows the boots where the boomerangs were.
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
| `0x17397` | 5 | Bank 5 `$B387`: `InitLinkSpeed`'s `@SetSpeed` becomes `JMP BootsSpeed` |
| `0x07154` | 2 | Bank 1 `Anim_ItemFrameOffsets` for item slots `$1D`/`$1E`: `$22` becomes `$25`, the boots icon entry |
| `0x07181` | 1 | Bank 1 `Anim_ItemFrameTiles[$25]`: the boomerang spark's `$3C` becomes the boots tile `$1C` |
| `0x071CE` | 1 | Bank 1 `Anim_WriteSpecificItemSprites`: narrow (half-width) tiles start at `$1C` instead of `$20`. No item drew `$1C`-`$1F` before |
| `0x1F4F5` | 9 | Bank 7 `BoomerangFrameCycle`: the flying boomerang's frames wrap from `$25` back to its vanilla entries `$22`-`$24`, and its spark uses entry 9 (also `$3C`) |
| `0x0824F` | 32 | Sprite tiles `$1C`/`$1D`, blank in PRG0, become the boot (placeholder art). `$1E`/`$1F` after them are the inventory cursor and stay as they are |
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
- `boot_preview.png`: the placeholder boot tile. The palettes are assumed:
  Link's palette for L1, the blue palette for L2.

## Not yet verified

This was built without a vanilla ROM:
- The disassembly was assembled with zero-filled data files of the correct
  sizes, so code addresses are exact.
- The first version (boot drawn over tile `$36`) was play-tested. This
  version, with its own icon, has not been run yet.
- The boot art and its colours haven't been seen in game.
- Tiles `$1C`/`$1D` are blank in PRG0, and no code or table in the disassembly
  draws them. A PPU viewer during play can confirm that nothing else uses them.
