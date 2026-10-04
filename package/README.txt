EDF6 UI Mod  (pre-release)
===========

Two changes to Earth Defense Force 6's interface, independent of each other:
you can install just one if you want.

1) Redesigned equipment screen  (Mods\UI and Mods\Patches)
   The item list sits on the left: two categories side by side in wide
   columns, 13 visible rows, full names and a highlight that covers the whole
   row. The weapon's name and description go below it, and the stats get their
   own panel on the right, above the class box, so nothing overlaps. The panels
   are flat, so the screen looks the same on every mission-era background.

   A small patch, Mods\Patches\EDF6UI_EquipmentScreen.txt, changes two sizes
   the game hard-codes: the selection highlight (355 px) and the room for item
   names (250 px, the reason long names come out squeezed). Without it the
   screen still works, with squeezed names and a shorter highlight.

   It also removes the HQ's decorative frame (the corner radars and the veil
   over the 3D scene), which took up useful space without adding anything.

2) Notes at the start of the description  (Mods\WEAPON)
   Two things the game buries at the end of the text, moved to the first line
   so you see them without scrolling:

     - Fencer boost type: whether the weapon wants Side Thruster (dash) or
       Jump Booster (jump).
     - Single magazine: weapons that never reload, so the shots in the
       magazine are all you get for the mission.


KNOWN ISSUES
------------
This is a pre-release. On the equipment screen:

  - scrolling the item list with the mouse wheel can stop between rows,
    because the game scrolls freely with the wheel. The keyboard keeps whole
    rows;
  - the longest names are slightly squeezed to fit their column.


REQUIREMENT
-----------
EDFModLoader installed, with Redirect=True. If the game folder has no
winmm.dll and no Mods folder, nothing happens.

    https://github.com/BlueAmulet/EDFModLoader

The patch also needs EDFModLoader's Patcher plugin (Mods\Plugins\Patcher.dll),
which applies the files in Mods\Patches when the game starts.


INSTALL
-------
Copy the Mods folder from this package over the game's, the one next to
EDF6.exe. It ends up like this:

    EARTH DEFENSE FORCE 6\Mods\UI\LYT_HUIHQWEAPONSELECT.SGO
    EARTH DEFENSE FORCE 6\Mods\UI\LYT_MAINFRAME.SGO
    EARTH DEFENSE FORCE 6\Mods\UI\LYT_HUIHQCURRENTSTATUS.SGO
    EARTH DEFENSE FORCE 6\Mods\Patches\EDF6UI_EquipmentScreen.txt
    EARTH DEFENSE FORCE 6\Mods\WEAPON\WEAPONTEXT.EN.SGO

To revert, delete those files. Root.cpk is never touched.


THE FRAME IS REMOVED ACROSS THE WHOLE HQ
----------------------------------------
LYT_MAINFRAME.SGO is the decorative frame shared by EVERY HQ screen, not just
the equipment one. Removing it also removes the corner radars in mission
select, options and the rest.

If you'd rather keep it, don't copy that file. The rest work the same, but the
equipment screen uses the space it left free, so the panels will sit under the
radars.


CAREFUL WITH WEAPONTEXT
-----------------------
WEAPONTEXT.EN.SGO holds the text of EVERY weapon in the game. If you already
have another mod that replaces it, installing this one overwrites it and you
lose the other mod's changes. In that case, rebuild it from the one you have
installed with tools/weapon_notes.py (see the repository).


ENGLISH ONLY
------------
The Fencer patch looks for the texts "Side Thruster" and "Jump Booster", so it
only works with the game in English. In another language the file installs
but changes nothing.
