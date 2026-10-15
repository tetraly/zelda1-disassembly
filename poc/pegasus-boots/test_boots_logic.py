#!/usr/bin/env python3
"""Runs the patched InitLinkSpeed / BootsSpeed / BootsPressB on a tiny 6502 interpreter.

Usage: python3 test_boots_logic.py PATCHED.nes

Checks the speed the routine leaves in ObjQSpeedFrac for each case, the L1 charge
counter and the charge sound requests. It does not run the game: movement, animation
and collision still need an emulator.
"""
import sys

HEADER = 16
BANK5 = HEADER + 5 * 0x4000

INIT_LINK_SPEED = 0xB366
BOOTS_PRESS_B = 0x8E38
PLAY_EFFECT = 0x6D80          # bank 1 code in save RAM; stubbed here

CUR_LEVEL = 0x10
BUTTONS_DOWN = 0xFA
OBJ_QSPEED = 0x3BC
OBJ_POS_FRAC = 0x3A8
OBJ_COLLIDED_TILE = 0x49E
CHARGE = 0x38F
SELECTED_SLOT = 0x656
INV_BOOMERANG = 0x674
INV_MAGIC_BOOMERANG = 0x675
B = 0x40


class CPU:
    def __init__(self, rom: bytes):
        self.rom = rom
        self.ram = bytearray(0x800)
        self.effects = []

    def rd(self, addr):
        if addr < 0x2000:
            return self.ram[addr & 0x7FF]
        if 0x8000 <= addr < 0xC000:
            return self.rom[BANK5 + addr - 0x8000]
        raise ValueError(f"read {addr:#x}")

    def wr(self, addr, v):
        assert addr < 0x800, f"write {addr:#x}"
        self.ram[addr] = v & 0xFF

    def call(self, pc):
        a = x = y = 0
        n = z = c = v = False
        stack = ["top"]
        for _ in range(1000):
            op = self.rd(pc)
            b1 = self.rd(pc + 1) if pc + 1 < 0xC000 else 0
            w = b1 | self.rd(pc + 2) << 8 if pc + 2 < 0xC000 else 0

            def nz(r):
                nonlocal n, z
                n, z = bool(r & 0x80), r == 0
                return r

            def br(cond):
                return pc + 2 + (b1 - 256 if b1 & 0x80 else b1) if cond else pc + 2

            if op == 0xA9: a = nz(b1); pc += 2
            elif op == 0xA5: a = nz(self.rd(b1)); pc += 2
            elif op == 0xAD: a = nz(self.rd(w)); pc += 3
            elif op == 0xA0: y = nz(b1); pc += 2
            elif op == 0xA4: y = nz(self.rd(b1)); pc += 2
            elif op == 0x85: self.wr(b1, a); pc += 2
            elif op == 0x8D: self.wr(w, a); pc += 3
            elif op == 0x8C: self.wr(w, y); pc += 3
            elif op == 0xEE: self.wr(w, nz((self.rd(w) + 1) & 0xFF)); pc += 3
            elif op == 0x29: a = nz(a & b1); pc += 2
            elif op in (0xC9, 0xC0, 0xCD):
                reg = y if op == 0xC0 else a
                val = self.rd(w) if op == 0xCD else b1
                c = reg >= val; nz((reg - val) & 0xFF); pc += 3 if op == 0xCD else 2
            elif op == 0x24:
                m = self.rd(b1); z = (a & m) == 0; n = bool(m & 0x80); v = bool(m & 0x40); pc += 2
            elif op == 0xD0: pc = br(not z)
            elif op == 0xF0: pc = br(z)
            elif op == 0x50: pc = br(not v)
            elif op == 0xB0: pc = br(c)
            elif op == 0x4C: pc = w
            elif op == 0x20:
                if w == PLAY_EFFECT:
                    self.effects.append(a); y = 3; pc += 3
                else:
                    stack.append(pc + 3); pc = w
            elif op == 0x60:
                ret = stack.pop()
                if ret == "top":
                    return
                pc = ret
            elif op == 0xEA: pc += 1
            else:
                raise ValueError(f"opcode {op:#04x} at {pc:#06x}")
        raise RuntimeError("runaway")


def setup(rom, *, l1=0, l2=0, slot=0, b=False, stairs=False, level=0):
    cpu = CPU(rom)
    cpu.ram[INV_BOOMERANG], cpu.ram[INV_MAGIC_BOOMERANG] = l1, l2
    cpu.ram[SELECTED_SLOT] = slot
    cpu.ram[BUTTONS_DOWN] = B if b else 0
    cpu.ram[OBJ_COLLIDED_TILE] = 0x74 if stairs else 0x00
    cpu.ram[CUR_LEVEL] = level
    return cpu


def speed(cpu):
    cpu.call(INIT_LINK_SPEED)
    return cpu.ram[OBJ_QSPEED]


def main():
    rom = open(sys.argv[1], "rb").read()
    fails = 0

    def check(name, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ("" if ok else f" (want {want!r})"))

    check("no boots, B held", speed(setup(rom, slot=2, b=True)), 0x60)
    check("L2, B held", speed(setup(rom, l1=1, l2=1, b=True)), 0xC0)
    check("L2 only, B held", speed(setup(rom, l2=1, b=True)), 0xC0)
    check("L2, B held, dungeon", speed(setup(rom, l1=1, l2=1, b=True, level=3)), 0xC0)
    check("L2, B not held", speed(setup(rom, l1=1, l2=1)), 0x60)
    check("L2, other item on B", speed(setup(rom, l1=1, l2=1, slot=1, b=True)), 0x60)
    check("L2, B held, stairs", speed(setup(rom, l1=1, l2=1, b=True, stairs=True)), 0x30)

    cpu = setup(rom, l1=1, b=True)
    speeds = [speed(cpu) for _ in range(40)]
    check("L1 charge: speed 0 for 32 frames", speeds[:32], [0] * 32)
    check("L1 charged: speed $80 after", speeds[32:], [0x80] * 8)
    check("L1 charge counter caps at 32", cpu.ram[CHARGE], 0x20)
    check("L1 charge sound: 4 whooshes of effect $02", cpu.effects, [2, 2, 2, 2])
    cpu.ram[BUTTONS_DOWN] = 0
    check("L1 released: vanilla speed", speed(cpu), 0x60)
    check("L1 release alone keeps the charge", cpu.ram[CHARGE], 0x20)
    cpu.call(BOOTS_PRESS_B)
    check("New B press clears the charge", cpu.ram[CHARGE], 0)
    cpu.ram[BUTTONS_DOWN] = B
    check("L1 after re-press: charging again", speed(cpu), 0)

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
