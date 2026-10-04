"""Rebuilds the modified layouts from the game's own, plus the EDF.dll patch.

The edits are in place: patch.py rewrites floats and re-points strings to the
table the file already has, so the size doesn't change and no offset moves.
Reserializing a whole SGO/DSGO crashes the game.

Each entry is (node path, value). A value starting with "@" is a string that
gets re-pointed to an existing entry of the table.

docs/equipment-screen.md explains the nodes, the skins and the limits behind
these numbers.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from patch import load

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = os.path.join(RAIZ, "extract", "UI")
SALIDA = os.path.join(RAIZ, "build", "UI")
PATCHES = os.path.join(RAIZ, "build", "Patches")
PATCH_FILE = "EDF6UI_EquipmentScreen.txt"

PANEL = "@app:/UI/Window_Test01_skin.sgo"
PANEL_MARGIN = 24
NONE = "@app:/UI/Transparent_skin.sgo"
OFFSCREEN = -600

CONTENT_TOP = 110
CONTENT_BOTTOM = 958

LIST_X = 40
LIST_W = 1260
LIST_PAD = 20
GRID_W = LIST_W - 2 * LIST_PAD
COLUMNS = 2
COLUMN_W = GRID_W // COLUMNS
ROW_H = 40
ROWS = 13
GRID_H = ROWS * ROW_H
HEADER_Y = 14
HEADER_H = 39
GRID_Y = HEADER_Y + HEADER_H + 5
BAR_THICKNESS = 10
BAR_CLEARANCE = 14
UNDER_BAR_Y = GRID_Y + GRID_H + BAR_CLEARANCE + BAR_THICKNESS
LIST_H = UNDER_BAR_Y + 12

NAME_X = 16
LEVEL_X = COLUMN_W - 105
QUALITY_X = COLUMN_W - 50
BADGE_W = 45
BADGE_H = 15
NAME_W = LEVEL_X - NAME_X - BADGE_W - 24
BADGE_X = NAME_X + NAME_W + 5
BADGE_Y = (ROW_H - BADGE_H) // 2

DESC_PANEL_Y = CONTENT_TOP + LIST_H + 16
DESC_PANEL_H = CONTENT_BOTTOM - DESC_PANEL_Y
DESC_PAD = 16
TITLE_Y = DESC_PANEL_Y + 14
TITLE_H = 34
DESC_LINE_H = 25
DESC_Y = TITLE_Y + TITLE_H + 4
DESC_H = (CONTENT_BOTTOM - 12 - DESC_Y) // DESC_LINE_H * DESC_LINE_H

PANEL_X = LIST_X + LIST_W + 20
PANEL_W = 560
CLASS_H = 289
CLASS_Y = CONTENT_BOTTOM - CLASS_H
CLASS_FRAME_OVERHANG = 26
STATS_H = CLASS_Y - CLASS_FRAME_OVERHANG - 8 - CONTENT_TOP
STATS_PAD_TOP = 12
STAT_LINES = 13
STAT_PITCH = (STATS_H - 2 * STATS_PAD_TOP) // STAT_LINES
STAT_PAD = 16


def n(value):
    return str(value)


CAMBIOS = {
# equipment screen
"LYT_HUIHQWEAPONSELECT.SGO": [
    ("2.2.0", n(OFFSCREEN)),
    ("10.1", PANEL),
    ("10.2.0", n(LIST_X)),
    ("10.2.1", n(DESC_PANEL_Y)),
    ("10.3.2", n(LIST_W)),
    ("10.3.3", n(DESC_PANEL_H)),
    ("10.5", "0"),
    ("10.6", "0"),
    ("40.1", PANEL),
    ("40.2.0", n(LIST_X)),
    ("40.2.1", n(CONTENT_TOP)),
    ("40.3.2", n(LIST_W)),
    ("40.3.3", n(LIST_H)),
    ("26.2.0", n(LIST_PAD - PANEL_MARGIN)),
    ("26.2.1", n(HEADER_Y - PANEL_MARGIN)),
    ("26.3.2", n(GRID_W)),
    ("26.3.3", n(HEADER_H)),
    ("36.2.0", n(LIST_PAD - PANEL_MARGIN)),
    ("36.2.1", n(GRID_Y - PANEL_MARGIN)),
    ("36.3.2", n(GRID_W)),
    ("36.3.3", n(GRID_H)),
    ("36.7.0.1.0", "0"),
    ("36.7.0.1.2", "0"),
    ("6.1.0.1.0", n(LIST_PAD + GRID_W + 3 - PANEL_MARGIN)),
    ("6.1.0.1.1", n(GRID_Y - PANEL_MARGIN)),
    ("6.1.1.1.3", n(GRID_H)),
    ("19.1.0.1.0", n(LIST_PAD - PANEL_MARGIN)),
    ("19.1.0.1.1", n(UNDER_BAR_Y - PANEL_MARGIN)),
    ("19.1.1.1.2", n(BAR_THICKNESS)),
    ("19.1.1.1.3", n(GRID_W)),
    ("20.1.1.1.2", n(BAR_THICKNESS)),
    ("21.3.2", n(COLUMN_W)),
    ("21.3.3", n(GRID_H)),
    ("21.7.1.1.1", n(ROW_H)),
    ("21.7.1.1.3", n(ROW_H)),
    ("34.3.2", n(COLUMN_W)),
    ("34.3.3", n(ROW_H)),
    ("35.3.2", n(COLUMN_W)),
    ("28.2.0", n(LEVEL_X)),
    ("29.2.0", n(LEVEL_X)),
    ("32.2.0", n(QUALITY_X)),
    ("33.2.0", n(QUALITY_X)),
    ("31.2.0", n(BADGE_X)),
    ("31.2.1", n(BADGE_Y)),
    ("37.2.0", n(BADGE_X)),
    ("37.2.1", n(BADGE_Y)),
    ("39.1", NONE),
    ("39.2.0", "0"),
    ("39.2.1", "0"),
    ("39.3.2", "1920"),
    ("39.3.3", "1080"),
    ("30.2.0", n(LIST_X + DESC_PAD)),
    ("30.2.1", n(TITLE_Y)),
    ("30.3.2", n(LIST_W - 2 * DESC_PAD)),
    ("30.3.3", n(TITLE_H)),
    ("30.7.1.1.0", "28"),
    ("30.7.1.1.1", "28"),
    ("27.1", PANEL),
    ("27.2.0", n(PANEL_X)),
    ("27.2.1", n(CONTENT_TOP)),
    ("27.3.2", n(PANEL_W)),
    ("27.3.3", n(STATS_H)),
    ("27.7.1.1.0", "0"),
    ("27.7.1.1.1", "0"),
    ("23.2.0", n(LIST_X)),
    ("23.2.1", n(DESC_Y)),
    ("23.3.2", n(LIST_W)),
    ("23.3.3", n(DESC_H)),
    ("22.2.0", n(DESC_PAD)),
    ("22.2.1", "0"),
    ("22.3.2", n(LIST_W - 2 * DESC_PAD - 14)),
    ("22.3.3", n(DESC_H)),
    ("11.1.0.1.0", n(LIST_X + LIST_W - 18)),
    ("11.1.0.1.1", n(DESC_Y)),
    ("11.1.1.1.3", n(DESC_H)),
    ("17.2.0", n(OFFSCREEN)),
    ("18.2.0", n(OFFSCREEN)),
    ("24.2.0", n(PANEL_X)),
    ("24.2.1", n(CONTENT_TOP + STATS_PAD_TOP)),
    ("24.3.2", n(PANEL_W)),
    ("24.3.3", n(STATS_H - 2 * STATS_PAD_TOP)),
    ("25.2.0", n(STAT_PAD)),
    ("25.3.2", n(PANEL_W - 2 * STAT_PAD)),
    ("25.3.3", n(STAT_PITCH)),
],
# the HQ's decorative frame
"LYT_MAINFRAME.SGO": [
    ("10.1", NONE),
],
# class and equipment box
"LYT_HUIHQCURRENTSTATUS.SGO": [
    ("19.2.0", n(PANEL_X)),
    ("19.2.1", n(CLASS_Y)),
    ("19.3.2", n(PANEL_W)),
    ("9.2.0", n(PANEL_X + 270)),
    ("9.2.1", n(CLASS_Y - 40)),
    ("11.3.2", n(PANEL_W - 32)),
    ("12.3.2", n(PANEL_W - 32)),
    ("13.3.2", n(PANEL_W - 32)),
    ("14.3.2", n(PANEL_W - 32)),
    ("10.3.2", "400"),
    ("1.3.2", "400"),
    ("17.3.2", n(PANEL_W - 32 - 8 - 84 - 8)),
],
}

PATCH = """; EDF6 UI Mod: sizes that EDF.dll hard-codes in the equipment screen.
; HUiHQWeaponSelect writes the selection cursor size on every move (355 x 40)
; and the width of every item and category name (250, longer names get
; squeezed). The mod's columns are {column} wide, so both follow them here.
aob EquipCursorWidth C780B80100000080B143488B442430C780BC01000000002042
aob EquipItemNameWidth C786B801000000007A434885DB74
aob EquipHeaderNameWidth C787B801000000007A434885DB74
EquipCursorWidth+6: f32! {column}.0 ; vanilla 355
EquipItemNameWidth+6: f32! {name}.0 ; vanilla 250
EquipHeaderNameWidth+6: f32! {name}.0 ; vanilla 250
"""


def main():
    os.makedirs(SALIDA, exist_ok=True)
    for nombre, pares in CAMBIOS.items():
        e = load(os.path.join(ORIGEN, nombre))
        for ruta, valor in pares:
            if valor.startswith("@"):
                e.repoint(ruta, valor[1:])
            else:
                e.set(ruta, valor)
        destino = os.path.join(SALIDA, nombre)
        open(destino, "wb").write(bytes(e.buf))
        print("%s: %d values, %d bytes" % (nombre, len(pares), len(e.buf)))
    os.makedirs(PATCHES, exist_ok=True)
    with open(os.path.join(PATCHES, PATCH_FILE), "w", newline="\r\n") as f:
        f.write(PATCH.format(column=COLUMN_W, name=NAME_W))
    print("%s: cursor %d, names %d" % (PATCH_FILE, COLUMN_W, NAME_W))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
