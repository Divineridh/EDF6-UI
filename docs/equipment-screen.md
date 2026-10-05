# Equipment screen internals

Everything below was read from the game files and from `EDF.dll`, then checked against three in-game
screenshots (old layout in the green era, the same new layout in the green and blue eras). Values marked
**inferred** fit the evidence but haven't been isolated by a test yet.

## What's on screen

Four independent layers, each from its own file:

| layer | file | class | what it draws |
|-------|------|-------|---------------|
| era background | `LYT_BG.SGO` | `HUiBG` | one of `BG_BASE` (blue), `BG_BASE_B`, `BG_BASE_C`, `BG_BASE_D` |
| main frame | `LYT_MAINFRAME.SGO` | main frame | title ("Class / Equipment") and the help line |
| equipment | `LYT_HUIHQWEAPONSELECT.SGO` | `HUiHQWeaponSelect` | item list, description, stats |
| status | `LYT_HUIHQCURRENTSTATUS.SGO` | `HUiHQCurrentStatus` | class, armor and equipped items box |

The main frame moves its texts per era, and our layouts must leave those zones free (1920x1080 units,
measured from screenshots):

| era | title | help line |
|-----|-------|-----------|
| blue | x 221-710, y 67-106 | x 1243-1738, y 970-998 |
| the other three | x 806-1296, y 58-91 (centered) | x 749-1243, y 994-1022 (centered) |

## Node names and the layout tree

The SGO header has a name index at 0x10/0x14 that the first tools never read: every root record has a
name. Record 45, `layout_tree`, is the hierarchy. **Only the nodes in the tree are drawn**; every other
record is a template that the C++ instantiates (cells, columns, stat lines, the cursor).

```
BaseFrame
    Panel7_WeaponSelect_skin
    WindowUpper
        LeftScrollBarBase
            LeftScrollBarKnob
        UnderScrollBarBase
            UnderScrollBarKnob
        WeaponIndexArea          <- runtime: WeaponSel_IndexBase per category
        WeaponSelectArea         <- runtime: SelectCursor + WeaponColumns per category,
                                    each with WeaponSel_CellBase per item
    WindowLower
        ScrollBarBase
            ScrollBarKnob
        WeaponName
        WeaponLevel
        WeaponDescArea
            WeaponDesc
        WeaponDescParam
            WeaponDescParamLine  <- plus 12 runtime copies: 13 stat lines
        TextUpButton
        TextDownButton
    DescSeparatorLine
```

| node | name | role in the vanilla screen |
|------|------|----------------------------|
| 10 | Panel7_WeaponSelect_skin | full-screen decoration |
| 40 | WindowUpper | frame of the item list |
| 26 | WeaponIndexArea | row of category headers |
| 36 | WeaponSelectArea | viewport of the item grid |
| 21 | WeaponColumns | one column per category (template) |
| 34 | WeaponSel_CellBase | one item (template) |
| 35 | WeaponSel_IndexBase | one category header (template) |
| 28 / 32 | WeaponLevelCell / WeaponQualityCell | Lv and star of an item |
| 29 / 33 | WeaponLevelIndex / WeaponQualityIndex | "Lv" and "☆" of a header |
| 31 / 37 | WeaponNew / WeaponUp | NEW and UP badges |
| 16 | SelectCursor | highlight of the selected item |
| 39 | WindowLower | one window holding description and stats side by side |
| 30 | WeaponName | name of the selected item (top-left of WindowLower) |
| 27 | WeaponLevel | level of the selected item (top-right of WindowLower) |
| 23 / 22 | WeaponDescArea / WeaponDesc | scrolling description and its text |
| 24 / 25 | WeaponDescParam / WeaponDescParamLine | stats box and one stat line |
| 18 / 17 | TextUpButton / TextDownButton | PgUp / PgDn labels |
| 2 | DescSeparatorLine | divider between description and stats |

`python tools/lyt.py <file.sgo>` prints every node with its name, flags and coordinates, then the tree.

## Node record

`[class, skin, pos[x,y,z], area[x,y,w,h], flags[], hcoord, vcoord, props[]]`

- `pos` is relative to the parent's origin.
- `area` w/h is the size. The x/y pair takes part in stacking (below); leave it at 0.
- `flags` is OR'ed into a bitmask. Observed: 4 = child of a horizontal stack (headers, columns),
  8 = child of a vertical stack (items, stat lines), 2048 = clip the children, 128 / 256 = horizontal /
  vertical scroll.
- `hcoord` / `vcoord` (fields 5 and 6, also accepted as properties): 0 measures from the left/top,
  1 centers (`BaseFrame`, `Panel7_WeaponSelect_skin`), 2 measures from the right/bottom (other screens
  use `hcoord 2` on their scroll bars). **Inferred.** `vcoord` isn't used by any vanilla layout.
- Stacked children advance by **`pos.y - area.y + area.h`**: items measured 0 - 0 + 44 = 44, stat lines
  80 - 40 + 28 = 68 and 80 - 22 + 28 = 86, and vanilla 0 - 0 + 28 = 28 fits its 364 px box exactly. With
  `pos.y != 0` the first stat line also moves in a way not yet explained, so keep `pos.y = area.y = 0`
  and set the pitch with `area.h`. Verified in game with `pos.y = area.y = 0`: the stack starts at the
  parent's top and the stat text sits at the top of each slot.
- Siblings are drawn in `layout_tree` order, earlier ones below. Under WindowLower that's ScrollBarBase,
  WeaponName, WeaponLevel, WeaponDescArea, WeaponDescParam, TextUp, TextDown: a panel skin on
  WeaponDescArea covers WeaponName if they overlap, and WeaponLevel can be a background for the stats.
- `scroll_mergin` on WeaponColumns is the margin kept around the selection when the column scrolls to
  it: vanilla 22 leaves half rows at the edges of the list, and one row (40) keeps whole rows when
  moving with the keyboard (checked in game).
- The mouse wheel scrolls freely: `+8B9380` adds `delta * 1000 / content height` to a 0-1 scroll
  ratio, so wheel scrolling stops between rows no matter what the layout says. All columns share the
  same vertical scroll, sized from the longest column.
- The horizontal scroll bar (UnderScrollBarBase) is the vertical template rotated -90 degrees around
  its `pos`, so it occupies `[pos.y - thickness, pos.y]` (area w is the thickness, area h the length).
  Clicks are tested against that whole area (`+969060` uses the node's matrix and area), which is
  thicker than the line the skin draws. Pressing inside it grabs the bar, so the area needs clearance
  from the last row: with no gap, clicking the last item scrolled the columns.
- Panel7_WeaponSelect_skin is the first child of BaseFrame, so it's drawn below everything. With
  `hcoord = vcoord = 0` it's positioned by its top-left corner like the rest, which makes it the
  background of the description: the weapon name and a padded, clipped text area both sit on top.

## Skins

A skin SGO is `[base sgo, states..., class]`. The class decides how it fills the node's area:

| class | what it is | sizes | eras |
|-------|------------|-------|------|
| `Solid` | flat RGBA rectangle | any | identical |
| `Window` | textured mesh with four corner bones | minimum size per skin | geometry may change |
| `Button` | textured mesh with `left`/`right` bones | minimum width, fixed height | geometry may change |
| `Model` / `Texture` | not stretched | fixed | |

A skin can also declare content margins `[left, top, right, bottom]` (Window_Test01 has 24 on every
side, Window09_Common 8/17/12/0, the Window06/07 skins none). The node's children are positioned
from that inner box, so switching to a skin with margins moves everything inside the node: seen in
game when the item list took Window_Test01 and its header, grid and scroll bars shifted 24 px.

A `Window` skin is a 3D model (`MDB0`) plus DDS textures inside `<NAME>_MERGE.rab` (an SSA archive whose
entries are CMPL-compressed). Every vertex is bound to one of the bones `LT`, `LB`, `RT`, `RB`, and the
engine moves those bones to the corners of the node's area. A piece bound to one corner keeps its size
and travels with that corner, so:

- each skin has a **minimum size**, the sum of the fixed pieces. Below it, pieces overlap and draw
  outside the area;
- some pieces sit **outside the frame on purpose** (decorative lines).

The merge model holds one object per era: `X_mesh` (base), `X_mesh.B` and `X_mesh.c`. B and C always
share the geometry and only swap the texture, so there are **two geometry families**: base (the blue
era) and B/C (the green, beige and violet eras). That's why a layout tuned in one family breaks in the
other.

`python tools/skins.py [filter...]` prints, per skin and family, the minimum size, how far it reaches
outside its area, and whether it's loaded in the HQ:

| skin | family | min w | min h | outside frame (l t r b) |
|------|--------|-------|-------|--------------------------|
| WINDOW07_WEAPONSEL2 | base | 1030 | 315 | 2 2 2 3 |
| WINDOW07_WEAPONSEL2 | B/C | 929 | 387 | 9 10 **534** 9 |
| WINDOW06_WEAPONSEL1 | base | 789 | 200 | 2 2 2 1 |
| WINDOW06_WEAPONSEL1 | B/C | **1133** | 167 | 0 33 **542** 9 |
| WINDOW05_SOLDIERINFO (frame) | all | 11 | 330 | 0 26 29 0 |
| WINDOW05_SOLDIERINFO (fill) | all | 286 | 185 | 9 8 2 3 |
| WINDOW04_SOLDIERSEL | all | 278 | 266 | 2 2 2 2 |
| WINDOW10_NOFRAME | all | 200 | 30 | 0 0 0 0 |
| WINDOW_TEST01 | base / B/C | 317 / 126 | 62 / 96 | 0 |
| SOLDIERINFO_DATA (class box rows) | base / B/C | 225 / 165 | - | 2 / **176** right |
| SCROLLBAR_GUIDE (Solid 50,100,120,130) | all | 0 | 0 | - |

Loaded in the HQ (`UIRESOURCEGROUP_HQ` / `_GLOBAL`): Window02, 04, 05, 06, 07, 08, 10_NoFrame, _Test01,
ScrollBar_guide and Transparent. `Test_Solid`, `SeparateLine`, `VerticalLine` and `LoadingTipsWindow`
belong to other groups; using them here is untested.

### Why Window07 only worked in the blue era

In the B/C mesh the left piece is 201 px wide and the right piece is **738 px wide, anchored to the right
edge**, followed by a 534 px line that leaves the frame at the bottom right. That right piece carries the
vanilla description/stats divider (at right - 508) and the arrow tab (at right - 552). Top and bottom
pieces are 218 and 190 px.

- Stats box with Window07, right edge at 1905 / 1880: the right piece starts at 1167 / 1142, which is
  exactly where the dark block over the item list started in both green screenshots.
- Description box with Window07, 225 px tall: below the 387 minimum, so top and bottom pieces overlap,
  and the divider and the arrow tab land in the middle of the box.
- Base mesh: the left pieces are 702 px wide, so narrow boxes spill past their *right* edge instead.
  The fill is uniform there, which is why the blue era looked right.

## The mod's own skins

Two things that hadn't been tried before work in game:

- **New strings in a layout.** The string table sits at the end of the file and records point to it
  with relative offsets, so `patch.py` can append a path and re-point a record to it (`@+` in
  `gen_layout.py`) without moving anything else.
- **New files.** EDFModLoader serves files from `Mods\` that don't exist in `Root.cpk`, and skins
  outside the HQ resource group load when a node uses them.

`tools/panelskin.py` clones a game skin under a new name (skin SGO, base SGO and `_MERGE.rab`) and
repaints its textures; the mesh, margins and per-era geometry stay the game's. The panels clone
Window_Test01 and the class box clones Window05_SoldierInfo, SoldierInfo_Name and SoldierInfo_Data,
all in the handoff's palette. `rab.py` writes the repainted textures as literal-only CMPL, which any
LZSS decoder reads, about 12% bigger than raw.

The HQ keeps its layouts in memory: reopening the equipment screen re-reads skins but not layouts,
so a layout change needs a game restart (or leaving the HQ) to show.

## Hard-coded in EDF.dll (HUiHQWeaponSelect)

| what | where | effect |
|------|-------|--------|
| 12 stat lines created | `+8B54AF` (`mov r8d, 0xC`), loop at `+8B64C1` | with the line that's already in `layout_tree`, a weapon shows at most 13 stats (seen in game) |
| cursor 355 x 40 | `+8BB68A`, `+8BB699`, on every selection move | the highlight ignores the cell size |
| name width 250 | `+8B59B9` (headers), `+8B5B81` (items) | longer names are squeezed, whatever the cell width |
| `this+0xE4F0 >= 6`, `this+0xE5D8 = count * 40` | `+8B6532`, `+8B654C` | E4F0 is the item count of the longest column: 6 or more turns vertical scrolling on, and its height is taken as 40 px per item. With 40 px rows the longest column reaches its last item (checked in game) |

The cursor and the two name widths can be changed with the `Mods\Patches` format. These patterns are
unique in the current `EDF.dll`, and `gen_layout.py` writes them into
`build/Patches/EDF6UI_EquipmentScreen.txt` (applied in game on 2026-10-04 at `+8BB690`, `+8B5B87` and
`+8B59BF`):

```
aob CursorSize C780B80100000080B143488B442430C780BC01000000002042
CursorSize+6: <float32 width>    ; vanilla 355.0 = 00 80 B1 43
CursorSize+21: <float32 height>  ; vanilla 40.0  = 00 00 20 42
aob HeaderNameWidth C787B801000000007A434885DB74
HeaderNameWidth+6: <float32>     ; vanilla 250.0 = 00 00 7A 43
aob ItemNameWidth C786B801000000007A434885DB74
ItemNameWidth+6: <float32>
```

## Category tabs (the EDF6UITabs plugin)

A layout can't add input handling or new nodes, so the tabs are a C++ plugin for EDFModLoader
(`plugin/`, MinHook, no overlay). It builds the tabs out of the screen's own templates, so they use
the game's font, skins and fades. Everything below is from `EDF.dll` and checked in game unless it
says otherwise.

### HUiHQWeaponSelect

| address | what it is |
|---------|------------|
| `+8B4280` | constructor (`this`, 0xE640 bytes, created every time the screen opens): instantiates the headers, columns and cells. The plugin hooks it and adds its nodes afterwards |
| `+8BAB90` | per-frame update (vtable). Reads the menu actions of the player's input record (`ctx+8`, byte at `+0xDC0 + 0xDD0*i` or `+0x4528`): bit 1 up, 2 down, 4 left, 8 right |
| `+8BA240` | move column (`this`, 0 = left, 1 = right). Clamps to the ends, **skips empty columns**, clamps the row to the new column, plays the cursor sound. Its only caller is the update |
| `+8B9380` | mouse-wheel scroll, called by the update only after its "screen accepts input" checks. The plugin hooks it as its per-frame input point |
| `+8BB4B0` | select a weapon by id (finds column and row) |

| field | content |
|-------|---------|
| `+0x7D8` | `std::wstring[]` category names (begin, end at `+0x7E0`) |
| `+0xE4E8` | category count |
| `+0xE500` / `+0xE510` | column array (0x20 bytes each: items at `+8`, item count at `+0x18`; items are 0x90 bytes, weapon id first) and column count |
| `+0xE548` / `+0xE54C` | current column / selected row |
| `+0xE550` | `vector<int>` node ids of the columns |

### UI framework helpers

| address | signature |
|---------|-----------|
| `+8454B0` | `instantiate(screen, shared_ptr* out, parent name, template name)`: creates a template as a child of a named node |
| `+839FD0` | `find(screen, shared_ptr* out, const wstring& name)`: first node with that name |
| `+839560` | node by id (the ids `+839830` returns for a name) |
| `+83B880` | set the text of a `HUiButton` (`const wstring*`) |
| `+7F8BB0` | set the text of a `TextField` (`const wchar_t*`, 0) |
| `+12DA7AA` | `__RTDynamicCast`; type descriptors `Component` `+2062F00`, `TextField` `+2062F28`, `HUiButton` `+2062F50` |

All of them return strong `shared_ptr`s (MSVC layout; release with the control block's vtable 0 and
1, as the game's inlined code does). Instantiated nodes are owned by their parent, so releasing the
returned reference right away is safe; the tree frees them when the screen closes.

Node fields: `+0x1A0` position (x, y, z, 1), `+0x1B0` area (x, y, w, h), `+0x1F0` / `+0x1F4` hcoord /
vcoord. The game writes position and size at runtime (the selection cursor, the name width), and so
can a plugin. A button's text is a `TextField` held by a weak pointer at `+0x220`; its `+0x1B8` is the
width the text is squeezed into. `WeaponSelectArea+0x210` is the horizontal scroll (negative, animated);
column `i` sits at `i * column width` inside it.

**Don't write the font parameters.** The property parser (`+84D5F0`) stores `font_size` at `+0x10C` and
`font_color` at `+0x130` of a temporary parameter block, not of the node. In the node those offsets
are pointers: writing a color there crashed the game when the screen closed (`+7E9026`, inside a node
destructor). The real font scale ends up at `+0x278` of the text field; the color wasn't found.

### What the plugin builds

Created under `BaseFrame` after the constructor, in this order (later ones draw on top):

1. one `WeaponSel_IndexBase` per category, with name and item count, in two rows from the left edge
   of the list to the right edge of the stats panel. Widths follow the text (about 0.53 x the font
   size per character for this font) and each row is stretched to full width;
2. the same template once more for the `← 2 / 11 →` indicator, at the end of the second row;
3. one `SelectCursor` per category: a 3 px bar under the tabs whose column is on screen;
4. one more `SelectCursor` over the active tab, and a `WeaponLevelIndex` text field on top of it with
   the active tab's name (the tab's own text is emptied while active so it doesn't show through).

The row positions come from `WindowUpper` and `WeaponLevel`, so the layout stays the only source of
geometry. Q / E call the move-column function; a click on a tab calls it until the column matches
(clicking an empty category does nothing, since the game never leaves one active).

Two skins make the templates work as tabs: `EDF6UI_Tab` (a clone of WeaponSel_IndexBase whose
textures are regenerated as one bordered box, without the Lv / ☆ cells; the column headers share it)
and `EDF6UI_Accent`, a `Solid` skin (`[Color [r, g, b, a], mergin, object_class]`, copied from
ScrollBar_guide) that `SelectCursor` uses, so the list's selected row is the handoff's flat orange.

## How the earlier iterations failed

- `0aae41b` turned `WeaponLevel` (27), a text field, into the stats background with Window07: the 738 px
  right piece produced the dark block in the B/C eras. The description used Window07 at 205 px, under
  the 387 minimum. Its commit message also misnamed nodes (17 is TextDownButton, not the description).
- The 2026-10-03 attempt kept the same skins with smaller boxes (worse), widened the cells to 610 px
  (the names stayed at 250 and the cursor at 355) and read `area.y` of the stat line as a gap, which it
  isn't.

## Rules for an era-proof layout

1. Every box is at least its skin's minimum size **in both families**, and its overflow lands somewhere
   harmless. Otherwise use a skin with the same geometry in every era: `Solid`, Window10_NoFrame,
   Window04, Window05.
   The panels use Window_Test01: a dark fill with a thin border, minimum 317 x 62 (base) and
   126 x 96 (B/C), only 4 px of overflow, loaded in the HQ, and already in the layout's string table.
2. Know what a node is before reusing it (`tools/lyt.py`), and mind the draw order. A hidden text field
   with a `Solid` skin is a plain rectangle, which is how WeaponLevel became the stats background;
   the same field with a `Window` skin was the dark block. WindowLower stays a transparent container.
3. Stat lines: `pos.y = area.y = 0`, pitch = `area.h`, 13 lines at most. Item rows stay at 40 px,
   the height EDF.dll uses to size the vertical scroll.
4. A column width other than 355 needs the EDF.dll patch (cursor and name width).
5. Keep the main frame's title and help line zones free in both families.
6. Check sizes with `tools/skins.py` before touching the game; use the game only to confirm.

## Tools

```bash
python tools/lyt.py <file.sgo>              # nodes with names, flags, hcoord/vcoord, then the tree
python tools/rab.py <file.rab> [dest]       # list or extract an SSA archive (CMPL)
python tools/mdb.py <file.mdb>              # bones, textures and skinned vertices of a model
python tools/skins.py [filter...]           # minimum size and overflow per skin and era family
python tools/skinview.py <SKIN> <w> <h> <dest>  # render a skin at a given size for base, B and C
python tools/panelskin.py [dest]               # build the mod's recolored skins
plugin/build.bat                                # build the category tabs plugin (EDF6UITabs.dll)
```

CMPL is LZSS with a 4096-byte window starting at 0xFEE, LSB-first flag bits, and a 12-bit offset made of
the first byte plus the high nibble of the second (`(b1 << 4) | (b2 >> 4)`); the low nibble + 3 is the
length.
