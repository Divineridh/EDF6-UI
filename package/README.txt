EDF6 UI Mod  (pre-release)
===========

Two changes to Earth Defense Force 6's interface, independent of each other:
you can install just one if you want.

1) Redesigned equipment screen  (Mods\UI)
   The weapon grid takes the full width at the top, with wide columns so long
   names aren't cut and 14 visible rows. The description goes below, full
   width, and the stats get their own panel on the right, lined up with the
   class box.

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

  - the last stat lines ("Zoom", "Laser Sight", "Homing Capability") overlap
    the class / armor box;
  - on weapons with many stats, the last line gets cut off at the bottom.

The rest works, including every mission-era background.


REQUIREMENT
-----------
EDFModLoader installed, with Redirect=True. If the game folder has no
winmm.dll and no Mods folder, nothing happens.

    https://github.com/BlueAmulet/EDFModLoader


INSTALL
-------
Copy the Mods folder from this package over the game's, the one next to
EDF6.exe. It ends up like this:

    EARTH DEFENSE FORCE 6\Mods\UI\LYT_HUIHQWEAPONSELECT.SGO
    EARTH DEFENSE FORCE 6\Mods\UI\LYT_MAINFRAME.SGO
    EARTH DEFENSE FORCE 6\Mods\UI\LYT_HUIHQCURRENTSTATUS.SGO
    EARTH DEFENSE FORCE 6\Mods\WEAPON\WEAPONTEXT.EN.SGO

To revert, delete those files. Root.cpk is never touched.


THE FRAME IS REMOVED ACROSS THE WHOLE HQ
----------------------------------------
LYT_MAINFRAME.SGO is the decorative frame shared by EVERY HQ screen, not just
the equipment one. Removing it also removes the corner radars in mission
select, options and the rest.

If you'd rather keep it, don't copy that file. The other three work the same,
but the equipment screen was enlarged to use the space it left free, so the
list will sit under the radars.


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
