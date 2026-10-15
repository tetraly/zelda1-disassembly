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
- **Goriyas** still throw boomerangs. Their spin skips the upright frame,
  because that tile is now the boot.

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
| `0x17397` | 5 | Bank 5 `$B387`: `InitLinkSpeed`'s `@SetSpeed` becomes `JMP BootsSpeed` |
| `0x1F4F5` | 8 | Bank 7 `BoomerangFrameCycle`: the Goriya spin never uses frame 0 |
| `0x1F4FE` | 8 | Bank 7 `BoomerangBaseSpriteAttrCycle` |
| `0x083EF` | 32 | Sprite tiles `$36`/`$37` (the boomerang item icon) redrawn as a boot (placeholder art) |
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
- `boot_preview.png`: the placeholder boot tile. The palettes are assumed:
  Link's palette for L1, the blue palette for L2.

## Not yet verified

This was built without a vanilla ROM:
- The disassembly was assembled with zero-filled data files of the correct
  sizes. Code addresses are exact, but nothing has been run in an emulator.
- The art in tile `$36` and its colours haven't been seen in game.
- It hasn't been confirmed that no other sprite uses tile `$36`. An emulator's
  PPU viewer can check this.
