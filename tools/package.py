"""Builds ../builds/EDF6UIMod.zip from the rebuilt layouts, WEAPONTEXT, the tabs plugin and package/."""

import glob
import os
import shutil
import sys
import zipfile

import panelskin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
SOURCE = os.path.join(ROOT, "package")
STAGING = os.path.join(BUILD, "package")
OUTPUT = os.path.join(os.path.dirname(ROOT), "builds")
ZIP = os.path.join(OUTPUT, "EDF6UIMod.zip")
PLUGIN_SOURCES = os.path.join(ROOT, "plugin", "src", "*")
PLUGIN = os.path.join(ROOT, "plugin", "build", "EDF6UITabs.dll")

CONTENTS = [
    (os.path.join(BUILD, "UI", "LYT_HUIHQWEAPONSELECT.SGO"),
     "Mods/UI/LYT_HUIHQWEAPONSELECT.SGO"),
    (os.path.join(BUILD, "UI", "LYT_MAINFRAME.SGO"),
     "Mods/UI/LYT_MAINFRAME.SGO"),
    (os.path.join(BUILD, "UI", "LYT_HUIHQCURRENTSTATUS.SGO"),
     "Mods/UI/LYT_HUIHQCURRENTSTATUS.SGO"),
    (os.path.join(BUILD, "Patches", "EDF6UI_EquipmentScreen.txt"),
     "Mods/Patches/EDF6UI_EquipmentScreen.txt"),
    (os.path.join(BUILD, "WEAPON", "WEAPONTEXT.EN.SGO"),
     "Mods/WEAPON/WEAPONTEXT.EN.SGO"),
    (PLUGIN, "Mods/Plugins/EDF6UITabs.dll"),
    (os.path.join(SOURCE, "README.txt"), "README.txt"),
]
CONTENTS += [(os.path.join(BUILD, "UI", f), "Mods/UI/" + f) for f in panelskin.output_names()]


def main():
    missing = [src for src, _ in CONTENTS if not os.path.exists(src)]
    if missing:
        raise SystemExit("missing files for the package:\n  " + "\n  ".join(missing))
    stale = [src for src in glob.glob(PLUGIN_SOURCES) if os.path.getmtime(src) > os.path.getmtime(PLUGIN)]
    if stale:
        raise SystemExit("the plugin is older than its sources, run plugin/build.bat:\n  " + "\n  ".join(stale))

    if os.path.exists(STAGING):
        shutil.rmtree(STAGING)
    for src, dest in CONTENTS:
        target = os.path.join(STAGING, dest.replace("/", os.sep))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(src, target)

    os.makedirs(OUTPUT, exist_ok=True)
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for _, dest in CONTENTS:
            z.write(os.path.join(STAGING, dest.replace("/", os.sep)), dest)

    print(ZIP)
    for _, dest in CONTENTS:
        path = os.path.join(STAGING, dest.replace("/", os.sep))
        print("  %-44s %8d bytes" % (dest, os.path.getsize(path)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
