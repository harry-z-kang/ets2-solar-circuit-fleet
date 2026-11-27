SOLAR CIRCUIT — GEORGIA TECH SOLAR RACING INSPIRED FLEET
Version 0.5.2 | Personal alumni tribute | 27 November 2026

COACH LOGO ALIGNMENT IN 0.5.2
MAN 13.9 m and Scania 13.7 m logos share a 1.00 m centerline and 0.50 m image height on both sides. Separate UV placements, unchanged logo proportions. Eight Blender views, 381 checks and 18 reopened-scene checks passed. Install coach v0.2.2; truck v0.5.1 and trailer v0.1 are unchanged. Details and previews: docs/COACH-LOGO-ALIGNMENT.md.

NATIVE SCREENSHOT FEEDBACK / BLENDER IN 0.5.1
Raised MAN/Scania bands to the marked panel lines. Removed the Volvo DD logo plaque; the original gold mark sits directly on white. Replaced the sketch with the team's own SR-4 illustration. FH6 Aero XL now reads TK-05 / VAN LEER; lower-front painted accessories are navy and painted upper mirrors white. Details: docs/FEEDBACK-FIX.md.
Local Blender scenes and eight cameras per vehicle: docs/BLENDER-VISUAL-CHECK.md. Actual module DDS textures are checked on private local geometry, with approximate studio materials. Thirty-two views reviewed; the corrected build still needs an ETS2 appearance check.

START HERE
Open FLEET-GUIDE.html for the visual guide, supported vehicles, sources and editing instructions.

QUICK INSTALL
1. Extract this package to a folder of your choice.
2. Copy the desired .scs files from mods/ into your active ETS2 user-data mod folder. The usual Windows location is Documents\Euro Truck Simulator 2\mod. OneDrive redirection or a custom -homedir can change that location. Use the folder that contains your current game.log.txt.
3. In ETS2 Mod Manager, activate the modules you want. The coach module requires SCS Coaches DLC (dlc_bus). All three can be enabled together. If another mod replaces the same paint jobs, put Solar Circuit above it.
4. On the FH6 Aero Globetrotter XL choose "Solar Circuit - Van Leer". Switch it off its retired Heavy selection before upgrading, or select Van Leer afterward. Other vehicles retain their choices: "Solar Circuit - Alumni Support" or, with a supported 8x4 chassis and cabin, "Solar Circuit - Heavy Support 8x4". Each paint job costs EUR 1,000 and unlocks at level 0.
5. Inspect both sides, roof, front, rear and accessories in daylight before buying it for every fleet vehicle. Keep your usual profile backup when testing new mods.

MODULES AND EXACT SCOPE
gtsr-trucks-v0.5.1.scs
  25 SCS truck families, 77 paint-job definitions. All seven Mercedes-Benz and DAF families are covered, with 19 new standard-cab options and four refreshed heavy maps. All previous stock 8x4 coverage remains. Exact cabins and dependencies: docs/MERCEDES-DAF-LIVERIES.md. Heavy coverage: docs/8X4-LIVERIES.md. Earlier trucks: docs/TRUCK-LIVERIES.md.
  Upgrade: deactivate/remove older truck modules and install only truck version 0.5.1 and coach version 0.2.2.

gtsr-trailers-v0.1.scs
  Player-owned SCS Box Trailer: curtainsider and dry-freighter maps, each in Long, Double and B-Double layouts. Insulated, refrigerated, side-door and moving-floor bodies are assigned the matching dry-freighter atlas through accessory definitions. Non-body painted accessories use solid navy. Those related body variants still need an individual visual check.
gtsr-coaches-v0.2.2.scs
  SCS Coaches DLC: MAN Lion's Coach 13.9 m and 12.1 m; Scania Touring HD 13.7 m and 12.9 m; Volvo 9700 DD. Five separate 8192 x 4096 body textures. This does not skin third-party coach mods or DBus World vehicle mods.

WHAT HAS BEEN CHECKED
1595/1595 feedback checks; 1,930 gold-crossing probes; 360/360 rebuild checks; 40 reopened Blender scene checks. All 32 Blender views and 28 native v0.5.0 captures plus two stripe annotations reviewed. See source/feedback-fix-validation.json, source/feedback-fix-rebuild-validation.json and source/blender-workflow-validation.json.
Historical 0.5.0: 1561/1561 refinement checks; 2,490 gold crossing probes including all three painted coach doors; selected SVG editing paths; recipe reproduction; strict archive and unrelated-export preservation. All 37 new captures and one annotated suggestion compared with 25 older captures. Reports: source/panel-refinement-validation.json; source/panel-refinement-rebuild-validation.json; source/panel-calibration.json.
Historical 0.4.1: 1477/1477 focused checks and 1113/1113 workflow checks passed. All 25 new screenshots and five template overlays reviewed. Reports: source/focused-fix-validation.json; source/focused-fix-rebuild-validation.json.
Historical 0.4: 1596/1596 version 0.4 static checks passed; all seven Mercedes/DAF cab inventories and 93 stock/tuning accessory IDs verified. All 30 template overlays reviewed. 756/756 editing/reproduction checks passed. See source/mercedes-daf-validation.json and source/mercedes-daf-rebuild-validation.json.
Historical: 1164/1164 version 0.3 checks passed, including all current stock 8x4 units, mounted textures and previous gameplay-file preservation. All 10 new template overlays reviewed.
Historical version 0.2: 777/777 version 0.2 static checks passed; all 37 new cabin and 19 auxiliary template overlays reviewed. Current cabin IDs were checked against base and truck DLC definitions. One upstream FH6 8x4 identifier was corrected.
Archive integrity; internal texture and material paths; DDS DXT5/BC3 format, full mip chains and power-of-two dimensions; image decode; unique paint-job IDs; manifest dependency; paint-job structure against PJP v2.1.3; texture placement against public wireframe templates. Truck and SCS box accessory names were also checked against locally installed ETS2 1.62.3.3 definitions.

WHAT HAS NOT BEEN CHECKED
The new Mercedes/DAF maps have not been tested in a game session. Your screenshots show earlier modules loading, with mirrored coach text and truck alignment issues. The three photographed coach bodies and selected FH6 Aero XL are refined by 0.5.1; other vehicle maps remain unchanged. No active profile was modified by this build. Complete in-game visual alignment, opposite-side reading direction, body seams, paint gloss, Convoy behaviour and interaction with other vehicle mods remain unverified. This is an installable first build for testing, not a claim of finished in-game validation.

ARTWORK AND EDITING
artwork/: reusable SVG and transparent/opaque PNG decal assets, unchanged source team logo, rear panel, electrical-lead decal, fleet numbers, solar strip and circuit trace.
textures/: mapped vehicle SVG sources, PNG exports, DDS exports and three solid-colour fallback textures. No wireframe lines are baked into game textures.
previews/: flat design board and example texture sheets. These are not in-game screenshots or photorealistic renders.
source/: rebuild utility, texture index and validation report.
credits/: logo provenance, template attribution and MIT notice for adapted PJP code patterns.

Edit an SVG in Inkscape or another SVG editor at its original canvas size. Keep the team logo's proportions and the clear space around it. Arial remains live editable text; the font is not bundled. To change fleet numbers, edit the text on the appropriate vehicle SVG as well as any decal master. Editing a master decal does not automatically alter the mapped vehicle sources.

The package now contains 118 texture sets, including 29 new Mercedes/DAF maps and four refreshed heavy maps. The optional source/rebuild.py utility supports conditional DLC sections and regenerates PNG/DDS files from those SVGs and writes updated .scs modules under rebuilt/mods/. It needs Python, Pillow and PyMuPDF (pip install pillow pymupdf). Run it from any folder:
  python source/rebuild.py
or rebuild selected vehicle textures:
  python source/rebuild.py --texture scania-s-high-roof
Use either original or rebuilt modules in-game, not duplicate copies of both. You can also unpack .scs as ZIP, replace the DDS at the same path and zip the contents again with manifest.sii at archive root.

TO ADAPT ANOTHER VEHICLE
Get the exact model, author, version, cabin/body and UV template. Place the reusable artwork into that template; do not paste an entire mapped truck texture onto another model. Hide template/wireframe layers before export. Preserve correct glass/opacity masks for coach mods that skin windows separately. Generate that model's definitions using Paint Job Packer or the vehicle author's documented method. Use DDS BC3/DXT5 with mipmaps and the required power-of-two dimensions. Verify both sides and every accessory in game. The 8192-wide coach maps are intentionally larger than the truck maps; reducing them trades away detail.

DESIGN
White upper panels, navy lower panels, a gold sweep, solar-cell detailing and a circuit trace. Current Tech Gold #B39051, Tech Navy #051E39 and White #FFFFFF. Large light text sits on navy for contrast. The "Electrical Lead / Alumni Support" decal honours your role; it is supplied separately so you can place it where your preferred cab has a clear panel. Fleet numbers: TK for tractors, TR for trailers and CO for coaches. The fleet design name Solar Circuit is newly coined for this package, not an official team programme.

DISCORD
The supplied invite resolved publicly to ProMods Community. Public invite metadata was accessible; channel discussions were not. No Discord channel content was read and no account joined, messages posted or private channels accessed. Public SCS and author guidance was used instead.

SOURCES
https://gtsolar.org/
https://gtsolar.org/assets/css/custom.css
https://gtsolar.org/assets/images/gtsr-logo.png
https://brand.gatech.edu/our-look/colors
https://github.com/Carsmaniac/paintjob-packer/releases/tag/v2.1.3
https://github.com/Carsmaniac/paintjob-packer/blob/f58bb7d865c3f5af0c6cd8191623b4a17bda0c1e/scripts/ModGeneration.gd
https://truckymods.io/euro-truck-simulator-2/tools/ets2-truck-and-trailer-templates-947834
https://forum.scssoft.com/viewtopic.php?f=33&t=272386
https://modding.scssoft.com/wiki/Documentation/Engine/Units/accessory_paint_job_data
https://modding.scssoft.com/wiki/Documentation/Engine/Mod_manager
https://modding.scssoft.com/wiki/Documentation/Tools/Game_Archive_Extractor
https://discord.gg/HpWvgy5mh

Current 0.4.1 focused details: docs/FOCUSED-FIX.md; source/focused-fix-validation.json.
Historical 0.4 details: docs/MERCEDES-DAF-LIVERIES.md; source/mercedes-daf-support.json; source/mercedes-daf-validation.json.
Screenshot guidance: docs/SCREENSHOT-CHECKLIST.md.
Historical 0.3 heavy support details: docs/8X4-LIVERIES.md; source/8x4-support.json; source/8x4-validation.json.
Historical version 0.2 truck details: docs/TRUCK-LIVERIES.md; source/expanded-truck-support.json; source/expansion-validation.json. The original source/validation.json is the historical version 0.1 report.

Team and Georgia Tech marks remain their owners' property. Personal tribute, no official affiliation claimed. Original templates and game files are not redistributed. No sponsor logos or vehicle models are included.
