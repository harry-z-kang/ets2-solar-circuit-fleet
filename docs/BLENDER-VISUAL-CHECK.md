# Local Blender visual checks

Blender **5.3.0** was found on this machine through the Scoop `blender` command. The workflow uses Blender's Python API and CPU Cycles rendering. It does not require installing an SCS addon, changing Blender preferences on disk, or opening ETS2.

The importer reads privately converted PIM/PIT files, selects visible parts from the named variant, assigns the actual packaged DDS paint through the correct UV aliases, and assembles doors, end panels and the configured accessories. SCS triangle winding is reversed for Blender, custom normals are rotated, and SCS shadow-only meshes are omitted. An explicit backface shader prevents reversed cab artwork appearing through gaps where the interior is omitted in Cycles. Accessory attachment transforms are included. Standard reference tires/rims are assembled from the exported wheel locators.

## Run a check

From this project folder in PowerShell:

```powershell
.venv/Scripts/python.exe source/blender_qa.py --all
```

This saves four local `.blend` files and eight views per vehicle under `work/blender-qa/<vehicle>/studio/`: left, right, front, rear, front-left, front-right, rear-right and roof. Each `inspection.json` records the Blender version, imported parts, paint-file SHA-256 hashes, warnings and render paths. Open the `.blend` file to orbit, zoom and select individual panel meshes.

For one vehicle or faster iteration:

```powershell
.venv/Scripts/python.exe source/blender_qa.py --vehicle volvo-9700-dd --views left,right,front-right --width 1120 --samples 8
.venv/Scripts/python.exe source/blender_report.py --output work/blender-qa
```

The second command writes a local HTML gallery and contact sheets. Other vehicle keys are `man-lions-coach-139`, `scania-touring-137` and `fh6-van-leer`.

`--flat` uses unlit paint colors for checking the artwork without highlights. `--scene-only` builds the scene without rendering. `--blender` selects another executable. All output must remain under this project's ignored `work/` folder.

## Edit, rebuild, inspect

```powershell
.venv/Scripts/python.exe source/rebuild.py --texture volvo-9700-dd
.venv/Scripts/python.exe source/blender_qa.py --vehicle volvo-9700-dd --texture-dir rebuilt/textures
```

The override folder supplies edited DDS files, or PNG files if a DDS is absent. Unchanged maps fall back to the current module. Rebuild before inspecting an SVG change; an existing DDS takes priority over a PNG. Existing open Blender scenes can reload external images, but rerunning the command is the reproducible route and records fresh texture hashes.

By default the current module names come from `fh6-logo-layout.json` (falling back to the earlier accessory/logo/feedback/refinement layouts if absent). To compare a different build, pass `--truck-module` and `--coach-module`. The extracted paint DDS cache is local; Blender never edits the installed mods or an active game profile.

## Recreate private model inputs

This machine already has the converter and private exports. After a game update, run:

```powershell
.venv/Scripts/python.exe source/prepare_blender_models.py
```

Use `--game-dir` for another ETS2 installation and `--converter` for another local ConverterPIX executable. The converter used here is [mwl4/ConverterPIX](https://github.com/mwl4/ConverterPIX), pinned previously to commit `3cd4e73a86d0c6bd28e117664c50a36cabeccf38`. Models are read from the installed base/truck/coach archives and exported only under `work/`. No downloads, addon installation or game-file changes are performed by these scripts.

The selected parts are in `source/blender-vehicles.json`. The FH6 scene represents the stock 8×4 Aero XL with painted cab fenders, Exclusive Aero headlights, Quatro painted sunshade and digital painted mirrors. The sunshade inspection configuration requires the Volvo tuning pack. The Scania scene includes the Standard Painted front intake. It is an inspection configuration, not a reconstruction of the user's saved accessory inventory.

## Review checklist and limits

- Compare both sides for reading direction and clipped marks.
- Inspect door and luggage-panel seams, front/rear corners and deflector joins.
- Check the front accessories and painted mirrors separately from the main cab map.
- Inspect the 9700's logo band, rear vents, car illustration and road placement at full resolution.
- Compare Blender views against the supplied ETS2 captures before accepting a visual change.

Blender's materials approximate SCS shaders. Glazing is deliberately opaque, interiors are omitted, and unconfigured trim/accessories may be absent. Rims and tires are reference choices. Studio lighting changes apparent color and gloss; use the flat pass for paint-color inspection. These renders verify geometry/texture placement, not exact ETS2 reflections, material behavior or compatibility with every tuning combination.

All model exports, extracted game textures, `.blend` scenes and build logs stay private in ignored `work/`. Only the workflow code, authored liveries and selected rendered previews belong in a public package.

Blender documents [background command-line rendering](https://docs.blender.org/manual/en/latest/advanced/command_line/render.html). SCS also provides its separate [official Blender Tools addon](https://github.com/SCSSoftware/BlenderTools); this workflow uses a small read-only importer to avoid making addon compatibility a prerequisite for the installed Blender version.
