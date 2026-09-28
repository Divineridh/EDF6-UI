# EDF6 UI Mod

Our own tools to read and modify Earth Defense Force 6's UI without depending on third-party
binaries, and a mod built with them: a redesigned equipment screen and weapon notes. The mod is a
pre-release (see the known issues in `package/README.txt`).

Game: `C:\Descargas Pesadas\EARTH DEFENSE FORCE 6\EARTH DEFENSE FORCE 6`
Loader already installed: EDFModLoader v1.0.10 (`winmm.dll`, `Redirect=True`).

## How the UI is put together

`MAINSCRIPT.AS` (AngelScript) drives the screen flow. The `HQMain()` routine loads the base:

```
g_bg.Play("app:/ui/lyt_bg.sgo");
g_main_frame.Play("app:/ui/lyt_MainFrame.sgo");
CreateUiFile("app:/ui/lyt_HUiHQMain.sgo");
```

Each screen is a `.sgo` inside `Root.cpk` (folder `UI/`, 467 layouts). The `.sgo` declares the
screen; the `.rab` files next to it are the art. The layout's last string (`HUiHQWeaponSelect`) is
the name of the C++ class inside `EDF.dll` that gives it behavior.

Equipment screen: `UI/LYT_HUIHQWEAPONSELECT.SGO`.

## SGO format (our own reverse engineering)

0x20-byte header:

| offset | content |
|--------|---------|
| 0x00 | `SGO\0` |
| 0x04 | version (0x102) |
| 0x08 | number of root records |
| 0x0C | offset of the record table |
| 0x10 / 0x14 | count / offset of the name index |
| 0x1C | base of the string table (UTF-16LE, `\0\0`-terminated) |

The whole file is a tree of 12-byte records: `(type u32, count u32, value u32)`.

| type | meaning | value |
|------|---------|-------|
| 0 | array | offset **relative to the record itself**; `count` = children |
| 1 | int | inline |
| 2 | float | inline |
| 3 | string | offset relative to the record, points to UTF-16LE |

A widget is an array shaped like this:

```
[class, skin, pos[x,y,z], area[x,y,w,h], flags[], int, int, props[[key,value],...]]
```

The coordinate space is a fixed 1920x1080. There are only 4 widget classes: `Layout`, `TextField`,
`Button`, `TexButtonTextField`.

Properties the layout accepts (full vocabulary, taken from the 467 files):
`pos`, `area`, `mergin`, `stencil`, `stencil_mergin`, `scroll_bar_info`, `scroll_mergin`,
`font_size`, `font_flag`, `font_border_width`, `font_color`, `font_border_color`, `text`,
`text_dr`, `callback`, `trans_form`, `animation_sec`, `ease_func`, `close_scale`, `hide`,
`transition`, `transition_dir`, `sgo_path`, `init_args`, `hcoord`, `flag_layout`.

There's no property for the number of cells, rows or columns.

## DSGO format (the 64-bit sibling)

The game data (weapon catalog, texts, manual) isn't SGO but **DSGO**. Same tree, but the whole file is
a **flat list of 16-byte records**; nesting is done by index, not by offset.

0x10-byte header:

| offset | content |
|--------|---------|
| 0x00 | `DSGO` |
| 0x04 | 0x10 (record size) |
| 0x08 | number of records |
| 0x0C | offset of the first record (0x10) |

Each record is `(value u64, type u32, 0 u32)`:

| type | meaning | where the data is |
|------|---------|-------------------|
| 0 | **double** | the 8 bytes of `value` are the IEEE754 |
| 1 | **string** | UTF-16LE at `record_offset + value` |
| 2 | int | inline in `value` |
| 3 | **array** | descriptor at `record_offset + value` |

The array descriptor is 16 bytes `(u64 0, u32 0x10, u32 count)` followed by `count` **u32 indices into
the record table**. So the same record can hang from two arrays: the format shares nodes.

⚠️ String and array offsets are **relative to the record that declares them**, same as the 32-bit
SGO. Taking them as absolute parses almost everything fine and returns strings cut in half, which is
the symptom of a wrong base, not of a weird file.

```bash
python tools/dsgo.py <file> json    # full tree
python tools/dsgo.py <file> 1       # just record 1
```

## Weapon catalog

`WEAPON/WEAPONTABLE.SGO` and `WEAPON/WEAPONTEXT.<lang>.SGO` are DSGO and **record 1 of each is the
master list, with 1564 entries in the same order**.

A table entry: `[internal id, sgo path, category, 1.0, level/100, ?, [upgrade caps], 1.0, ?]`. The
category encodes the class in the hundreds (`0xx` Ranger, `1xx` Wing Diver, `2xx` Fencer, `3xx` Air
Raider) and the units are the weapon type within the class. The "Lv" the game shows is
`floor(round(field * 100) / 4)`, checked against 18 weapons on the equipment screen.

A text entry: `[name, description, [stats]]`, and each stat is `[label, template, values...]` where
the template uses `$0`, `$1`… Each value is a group of 7 doubles: base (the value at star 5), stat
type, save byte, max level, two curve coefficients and whether it's fractional. How they combine is
documented in EDF6-Compendium's README.

```bash
python tools/weapons.py                # -> build/catalog.json and build/catalog.csv
```

## Electronic manual

> The compendium was once injected here as an extra chapter (`tools/compendium.py`, deleted in
> Sep-2026). That route was dropped in favor of the plugin overlay in `EDF6-Compendium`: the chapter
> was static, fit a single class per page, overwrote a real manual page, was indexed by name (and
> some weapons share a name) and only opened from the pause menu. It was never installed in the game.
> What follows documents the format, which still holds: the technique of re-pointing strings to the
> end of the file is what `weapon_notes.py` uses.

`ETC/EMANUAL.EN.DSGO` is the manual, and it's a data-driven rich-text document:

- 5 arrays of **67 pages** each (records 1, 986, 1551, 2116 and 2681), which share almost all their
  pages.
- A page is `['', [blocks]]`; a text block is `[0.0, "markup"]` and an image block is
  `[1.0, "file.dds", 1.0]`.
- The markup is real: `<font color=%dq%#c0ffc0%dq%>…</font>`, where `%dq%` escapes the double quote.
  `%LOCALE%` in an image name resolves per language.
- It's read by `EDF.dll`'s `HUiManual` class with the `UI/LYT_MANUAL.SGO` layout.

It's reachable in game: the text table has `OptionPlayer_CallManual` → "Read Instruction Manual" and
"Instruction Manual Available During Gameplay", so it opens from the pause menu.

## Tools

```bash
python tools/cpk.py dirs    "<Root.cpk>"                      # file inventory
python tools/cpk.py list    "<Root.cpk>" ui/                  # list by pattern
python tools/cpk.py extract "<Root.cpk>" "ui/&.sgo" <dest>    # extract (patterns joined with &)
python tools/sgo.py <file.sgo> json                           # full layout as JSON
python tools/patch.py <file.sgo> slots 36.                    # editable slots of a node
python tools/patch.py <source.sgo> set 36.3.3=401 <dest.sgo>
python tools/dsgo.py <file.dsgo> json                         # data (weapons, texts, manual)
python tools/weapons.py                                       # weapon catalog to JSON/CSV
```

`patch.py` rewrites values **in the same place in the binary**: the file keeps the same size and
structure, so nothing has to be reserialized and there's no risk of corrupting offsets.

## Map of LYT_HUIHQWEAPONSELECT.SGO

51 root records. The relevant ones:

| node | what it is | pos | area |
|------|------------|-----|------|
| 40 | WindowUpper: frame of the list | 191, 147 | 1187 x 302 |
| 26 | WeaponIndexArea: category row | 18, 23 | 1162 x 39 |
| 36 | WeaponSelectArea: grid viewport | 18, 67 | 1162 x 201 |
| 34 | weapon cell (template) | — | 355 x 40 |
| 35 | category cell (template) | — | 355 x 39 |
| 39 | WindowLower: description panel | 256, 468 | 1130 x 498 |
| 23 | scrollable description area | 38, 89 | 1050 x 364 |
| 21 | list column with its scrollbar | — | 355 x 201 |

201 / 40 = 5 rows, 1162 / 355 = 3 columns → 15 visible weapons.

Every mission era swaps the screen's background and some skins with it. Node 40 (the list) uses
`Window07_WeaponSel2_skin` explicitly, because the era skin drew an oversized box behind the list on
every background but the blue one.

## Limits

What can be changed per layout: geometry, typography, margins, skins, scroll, animations and texts.

Not in the layout: how many cells get instantiated, the paging and the grid construction. That lives
in `HUiHQWeaponSelect` inside `EDF.dll`. If the row count isn't derived from `area`, growing the grid
takes an AOB patch (`Mods\Patches\*.txt` format) or a C++ plugin with MinHook.

## Rebuilding the mod

```bash
python tools/gen_layout.py    # the three layouts, from extract/UI/
python tools/weapons.py       # weapon catalog
python tools/weapon_notes.py  # notes at the start of the description (--vanilla for a release)
python tools/package.py       # zip in ../builds/
```

`gen_layout.py` has the full list of edited values per node, and reproduces the three files byte by
byte. It's the source of the redesign: `build/` is output and isn't versioned.

## Installing a build

```bash
cp -r "C:/ModsCaseros/EDF6-UI/build/UI" "C:/Descargas Pesadas/EARTH DEFENSE FORCE 6/EARTH DEFENSE FORCE 6/Mods/"
```

To revert, delete the file from `Mods\UI\`. `Root.cpk` is never touched.
