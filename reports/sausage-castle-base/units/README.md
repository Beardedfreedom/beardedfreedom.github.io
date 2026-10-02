# Tiny home concepts for the lake zones

Generated 2026-09-29. Concept massing models, not construction drawings. Each unit is designed to sit on a 35 x 50 ft pad with its front toward the loop lane.

## Amanita cottage (mushroom)

A single tall-stemmed amanita with the sleeping loft inside the cap, a round skylight at the crown, and a baby mushroom as the bathroom pod. The cap overhangs 6 ft all round so the stem stays in shade.

| Item | Value |
|---|---|
| Footprint | 18 ft diameter stem, 30 ft diameter cap, plus a 7 ft bath pod growing off the back |
| Gross area | 412 sq ft |
| Height | 24 ft |
| Pad fit | fits 35 x 50 pad with 2.5 ft to spare each side |
| Materials | Stem: shotcrete or SIP panels with lime plaster; cap: sprayed foam roof over steel ribs, elastomeric coating in red with cream spots; gill soffit: tongue-and-groove cypress; porthole windows 3 ft round; oak plank deck |
| Florida notes | Round shell sheds hurricane wind well; foam roof needs Miami-Dade rated coating; raise finished floor 18 in on a slab plinth; mechanical closet under the stair. |

Files: `mushroom_sheet.png` (plan, elevations, axon), `mushroom_unit_local_ft.dxf` (3D mesh parts by material layer plus 2D plan layers, local feet).

## Widow's Peak (haunted house)

A narrow Gothic cottage with a steep gable, a corner turret with a reading nook, a hooded front porch on a raised lattice base, and a sleeping loft tucked under the roof with a round attic window over the door.

| Item | Value |
|---|---|
| Footprint | 14 x 24 ft main body, 9 ft octagonal turret, 6 ft deep front porch |
| Gross area | 564 sq ft |
| Height | 34 ft |
| Pad fit | fits 35 x 50 pad; total length with porch and steps 36 ft |
| Materials | Board-and-batten in charcoal slate with black-plum trim; steep 24:12 standing-seam roof in matte black; turret with fish-scale shingles and a witch-hat spire; turned porch posts; tall 2 x 6 ft lancet windows with amber glass; wrought-iron weathervane; brick chimney |
| Florida notes | Steep roof and turret need engineered wind bracing (Zone 2, 140 mph); raised floor gives flood clearance and crawl-space ventilation; amber glazing must be impact rated; shutters double as storm protection. |

Files: `haunted_sheet.png` (plan, elevations, axon), `haunted_unit_local_ft.dxf` (3D mesh parts by material layer plus 2D plan layers, local feet).

## Cypress stilt cracker (Florida swamp)

A Florida cracker house lifted clear of the wet ground on piers, wrapped in a deep screened porch for bugs and afternoon rain, with a cupola pulling hot air out through the roof and shutters that close for storms.

| Item | Value |
|---|---|
| Footprint | 12 x 26 ft core on 7 ft stilts, 6 ft screened porch wrapping the front and both sides (24 x 32 ft overall), 11-tread front stair |
| Gross area | 702 sq ft |
| Height | 28 ft |
| Pad fit | fits 35 x 50 pad; overall length with stair 43 ft |
| Materials | Pressure-treated pier grid with cross bracing; cypress board-and-batten walls; 5V-crimp galvanized tin hip roof with 2.5 ft overhangs and a vented cupola; fibreglass screen panels between 6 x 6 posts; louvered shutters in bottle green; rain barrel; oak porch floor |
| Florida notes | Stilts put the floor above the flood elevation and let storm surge or lake rise pass under; hip roof and short overhangs perform best in hurricanes; screens and cross-ventilation reduce cooling load; cupola needs a storm closure. |

Files: `swamp_sheet.png` (plan, elevations, axon), `swamp_unit_local_ft.dxf` (3D mesh parts by material layer plus 2D plan layers, local feet).

## Saucer pod (UFO)

A classic saucer hovering 6 ft off the ground on three legs. The bridge sits under the dome at the centre where the ceiling is 9 ft; the ceiling falls to 4.5 ft at the rim, so the outer ring holds bunks, seating and storage. A ramp drops from a hatch at the front.

| Item | Value |
|---|---|
| Footprint | 24 ft diameter saucer on three legs, 6 ft ground clearance, 14 ft boarding ramp at the front |
| Gross area | 403 sq ft |
| Height | 19 ft |
| Pad fit | fits 35 x 50 pad; saucer plus legs 26 ft wide, with ramp 34 ft long |
| Materials | Steel ring frame with SIP wedge panels; aluminium composite skin in brushed silver; dark rim band with eight 2 ft acrylic portholes; 8 ft acrylic dome skylight over the bridge; three welded steel legs on 2.6 ft foot pads with tie-downs; aluminium boarding ramp; LED ring under the hull |
| Florida notes | Round aero shape sheds hurricane wind; 6 ft clearance beats flood elevation; legs need engineered footings and tie-downs; dome needs a storm cover; skin colour keeps it cool. |

Files: `ufo_sheet.png` (plan, elevations, axon), `ufo_unit_local_ft.dxf` (3D mesh parts by material layer plus 2D plan layers, local feet).

## Placement

`tiny_homes_on_pads_EPSG2236_ftUS.dxf` defines the three units as blocks and inserts them on all 22 pads of the lake zones concept (zone A haunted, B swamp, C mushroom, D UFO), rotated to face the lane and set at the lidar ground elevation. The 3D viewer's Lakes zone has a "Tiny homes" toggle that shows the same placement in 3D.

| Unit | Count |
|---|---|
| mushroom | 8 |
| haunted | 4 |
| swamp | 5 |
| ufo | 5 |

## CAD drawing sets (`cad/`)

One dimensioned sheet per house, drawn in decimal feet: floor plan with wall thickness, door swings, window openings and furniture; front and side elevations with level markers; a section; notes and a title block. `<unit>_cad_set.dxf` (layers A-WALL, A-DOOR, A-GLAZ, A-ROOF, A-ANNO-DIMS and so on) and `<unit>_cad_set.png` rendered from the DXF. Generated by `scripts/house_cad.py`. Concept design, not for construction: no framing, no code checks, no engineer's stamp.

## Concept art (AI, generated from the design specs)

Three images were generated on the owner's Higgsfield account (GPT Image 2.5, 16:9) from prompts written to match the massing models; the sandbox could not download them, so they are linked here. The UFO pod has no concept image yet.

- Mushroom: https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20260928_225118_0054bdb1-84f7-4862-af92-53fb41ba444f.png
- Haunted house: https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20260928_225118_bfef9a54-d725-46a6-bee7-179994f6d0a2.png
- Florida swamp: https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20260928_225118_0b090e9c-ffe5-45cf-9882-f79dad4bc3b1.png
