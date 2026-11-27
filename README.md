# Solar Circuit — ETS2 Fleet Theme

A Georgia Tech Solar Racing inspired personal alumni fleet theme for Euro Truck Simulator 2: white upper panels, navy lower panels, gold detailing, solar-cell geometry and a circuit trace. Includes an optional **Electrical Lead / Alumni Support** decal.

![Solar Circuit fleet design preview](previews/fleet-preview.png)

**Version 0.1 is an installable first build for testing.** Static checks passed, but the paint jobs have not been tested in an ETS2 game session. Preview drawings are flat design elevations, not game screenshots.

## Included paint-job modules

| Module | Vehicles and layouts | Limits |
| --- | --- | --- |
| [Scania S trucks](mods/gtsr-trucks-v0.1.scs) | SCS Scania S 2016 High Roof and Normal Roof; painted 4x2 and 6x short/long skirts | Excludes 8x4 and third-party Scania variants |
| [SCS box trailers](mods/gtsr-trailers-v0.1.scs) | Owned curtainsider and dry-freighter maps in Long, Double and B-Double layouts; related bodies assigned the matching dry atlas | Related insulated, refrigerated, side-door and moving-floor variants need individual visual checks |
| [SCS coaches](mods/gtsr-coaches-v0.1.scs) | MAN Lion's Coach 13.9 m / 12.1 m; Scania Touring HD 13.7 m / 12.9 m; Volvo 9700 DD | Requires SCS Coaches DLC; third-party coaches are not mapped |

## Install

1. Download or clone this repository. For an individual module on GitHub, open its file and use **Download raw file**.
2. Copy the desired `.scs` files from `mods/` into your active ETS2 user-data `mod` folder. On Windows this is usually `Documents\Euro Truck Simulator 2\mod`; OneDrive redirection or a custom `-homedir` can change the location.
3. Activate the modules in ETS2 Mod Manager. All three can be enabled together.
4. At the matching vehicle's paint shop, choose **Solar Circuit - Alumni Support**. Price: EUR 1,000; unlock level: 0.
5. Check both sides, front, rear, roof, seams and painted accessories before applying across your fleet. Use your usual profile backup when testing mods.

See [README.txt](README.txt) for complete instructions. Open [FLEET-GUIDE.html](FLEET-GUIDE.html) locally in a browser after downloading the repository for the visual guide. GitHub displays the HTML source rather than rendering that document.

## Package contents

- `artwork/` — editable SVG and PNG decal masters, fleet numbers, rear panel, solar strip, circuit trace and unchanged source team logo.
- `textures/` — 19 SVG, PNG and DDS textures: 16 mapped cab/body/skirt maps and three solid fallback colors.
- `mods/` — three installable `.scs` archives, compressed as standard ZIP files with their original contents preserved.
- `previews/` — fleet design board and example texture sheets.
- `source/` — optional rebuilding utility, dependency list, texture index and validation reports.
- `credits/` — logo provenance, template attribution and the MIT notice for adapted Paint Job Packer code patterns.

## Edit and rebuild

Edit a vehicle SVG in `textures/` at its original canvas size. Keep the team logo proportional. Text uses Arial or a compatible system font; no font files are bundled. Editing a reusable decal master does not automatically change the mapped vehicle SVGs.

With Python installed:

```sh
python -m pip install -r source/requirements.txt
python source/rebuild.py
```

Or rebuild one texture:

```sh
python source/rebuild.py --texture scania-s-high-roof
```

The utility writes updated PNG/DDS files and modules under `rebuilt/`, which Git ignores. Install either the original modules or the rebuilt modules, not duplicate copies of both. A separate vehicle model requires its own exact UV template and definitions; these maps are not universal skins.

## Validation status

The [original validation report](source/validation.json) records **258/258 static checks passed**: archive integrity, texture paths, image decoding, DDS DXT5/BC3 format and mip chains, dimensions, unit identifiers, UI images and coach dependency. Truck and SCS box assignments were compared with available local ETS2 **1.62.3.3** definitions. Some tuning-DLC assignments and coach definitions follow Paint Job Packer metadata and were not independently verified against extracted DLC files.

[Repository preparation checks](source/repository-validation.json) verify that compressing the `.scs` archives preserved every member's size and CRC. Runtime loading, side reading direction, gloss, seams, model variants, multiplayer and compatibility with other vehicle mods remain unverified.

## Identity and sources

- [Georgia Tech Solar Racing](https://gtsolar.org/): team logo, palette and “Design. Build. Race.” wording.
- [Georgia Tech color guide](https://brand.gatech.edu/our-look/colors): Gold `#B39051`, Navy `#051E39`, White `#FFFFFF`.
- [Paint Job Packer v2.1.3](https://github.com/Carsmaniac/paintjob-packer/releases/tag/v2.1.3): vehicle templates and definition patterns.
- [Template author's public guidance](https://forum.scssoft.com/viewtopic.php?f=33&t=272386).
- [SCS paint-job documentation](https://modding.scssoft.com/wiki/Documentation/Engine/Units/accessory_paint_job_data) and [mod packaging documentation](https://modding.scssoft.com/wiki/Documentation/Engine/Mod_manager).

The supplied Discord invite resolved to ProMods Community. Public invite metadata was available, but channel discussions were not read.

## Credits and rights

This is a **personal alumni tribute**, not an official Georgia Tech or Georgia Tech Solar Racing release. The fleet design name “Solar Circuit” was created for this package. Team and Georgia Tech marks remain their respective owners' property. No sponsor logos, original wireframe templates, vehicle models or game files are included.

See [full attribution](credits/ATTRIBUTION.txt) and the [Paint Job Packer MIT notice](credits/Paint-Job-Packer-MIT.txt). That MIT notice applies to the adapted code patterns identified in the attribution; it does not grant rights to team marks or license the entire artwork package.
