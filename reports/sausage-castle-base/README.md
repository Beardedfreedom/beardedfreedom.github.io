# Sausage Castle site base model (existing conditions, concept grade)

**Property:** "The Sausage Castle", 22500 Robbins Road, Astatula, FL 34705 (Lake County). Listing data (Compass / Estately, MLS B4900949) describe a 5 bed / 7 bath, 6,277 sq ft house on 40 acres, parcel 09-21-26-000300004800, with two more parcels (-4600, -4900) for about 120 acres total, zoning A, sold 9/8/2022 for $2.3M. Press coverage describes an 80-acre estate with lakes, campsites, an arena and rides.

**What this folder is:** a legal, public-data replacement for "export the Google Earth 3D model". It was generated entirely from USGS 3DEP lidar (public domain) and Overture Maps vectors (ODbL/CDLA), reprojected into the coordinate system a Florida civil drawing would use. It is not a survey and contains no parcel lines.

## Location check

The address point for 22501 Robbins Rd from Overture (National Address Database lineage) coincides with a 7,423 sq ft footprint at the south end of Robbins Road. Lidar gives that building a 28 ft roof height (two storeys). Southwest of it is a cleared compound with rectangular pads, circular features and a large rectangular enclosure; 1,200 to 1,500 ft north are two lakes with a loop track around the larger one. The lidar hillshade also shows straight land-use breaks on the Public Land Survey grid (a north-south break at about E 427,050 and an east-west break near N 1,578,500), consistent with the 40-acre quarter-quarter parcels named in the listing. Treat the parcel extent as unconfirmed until you pull the polygons from the Lake County Property Appraiser (lakecopropappr.com) or Lake County GIS (gis.lakecountyfl.gov), which this sandbox could not reach.

A search-engine "answer" placed the address at 28.6813, -81.7272. That is 1.7 km west of the real road and was discarded after checking the address points.

## Files

| File | What it is | Open with |
|---|---|---|
| `sausage_castle_base_EPSG2236_ftUS.dxf` | CAD base (2.5 MB). Layers: `C-TOPO-MINR` 1 ft contours, `C-TOPO-MAJR` 5 ft contours (polylines carry their elevation), `A-BLDG-FTPT` 68 footprints at ground elevation, `A-BLDG-3D` extruded MESH solids with lidar-derived heights, `A-BLDG-ANNO` area/height labels, `C-ROAD-CNTR` road centrelines, `C-WATR-BNDY` lake outlines, `G-ANNO-ADDR` address points, `G-ANNO-TRGT` target marker, `G-ANNO-AOI` clip frame, `G-ANNO-NOTE` provenance note | AutoCAD, Civil 3D, BricsCAD, SketchUp, QGIS |
| `sausage_castle_ground_pts_6ft_PNEZD.csv.gz` | 317,224 bare-earth points on a 6 ft grid, only where the lidar had real ground returns (lakes and building interiors excluded). Format PNEZD, comma delimited | Civil 3D: Surfaces > Create Surface > Definition > Point Files, format "PNEZD (comma delimited)" |
| `sausage_castle_dtm_3ft_EPSG2236.asc.gz` | Bare-earth DTM raster, 3 ft cells, ESRI ASCII grid, NAVD88 ft. Lake surfaces filled from the nearest shore | QGIS (then export GeoTIFF for Civil 3D "Add DEM file"), GDAL, Global Mapper |
| `sausage_castle_preview.jpg` | Hillshade from the lidar surface with buildings (red), roads (black), lakes (blue), address numbers (orange), target (magenta) | Any image viewer |
| `sausage_castle_base_metadata.json` | Extents, grid, contour levels, per-building base/height, sources | Text editor |
| `scripts/ept_clip.py` | Clips any USGS 3DEP Entwine dataset to a lon/lat box without PDAL | Python 3.11 + laspy, lazrs, pyproj |
| `scripts/overture_pull.py` | Pulls Overture buildings / roads / water / addresses for a box straight from the public S3 bucket | Python + pyarrow, shapely |
| `scripts/build_base.py` | Turns the clip and vectors into the files above |
| `scripts/build_focus.py` | Builds the two full-resolution focus zones under `focus/` | Python + numpy, scipy, ezdxf, contourpy, matplotlib |

The raw lidar clip (`sausage_site.laz`, 39.5 million points, 211 MB, EPSG:3857, Z in metres) is not in the repo because of its size. Re-create it in about five minutes with:

```
python3 scripts/ept_clip.py https://s3-us-west-2.amazonaws.com/usgs-lidar-public/FL_Peninsular_Lake_2018 -81.7205 28.6700 -81.7095 28.6810 sausage_site.laz
```

## Coordinate system and units

- Horizontal: NAD83 / Florida East (US survey feet), EPSG:2236. Civil 3D code `FL83-EF`. The DXF header sets `$INSUNITS` = 21 (US survey feet).
- Vertical: NAVD88 feet. The USGS point cloud is in metres; multiplied by 3.2808333.
- Datum note: the Entwine copy is in Web Mercator on WGS84 and was reprojected to NAD83 without a datum shift, which is about 1 m horizontally. Fine for concept design; a survey resolves it.
- Extent: E 425,119 to 428,674 ft, N 1,576,976 to 1,581,002 ft (about 3,550 by 4,025 ft, 328 acres). Ground elevations 64 to 91 ft.

## Accuracy

- Lidar: USGS 3DEP quality level 2 or better, nominal 10 cm RMSE vertical, 25 to 35 points per square metre in this clip. 2018 flight, so anything built since is missing.
- Contours: computed from a 3 ft ground grid smoothed with a 1.5-cell Gaussian, then simplified to 0.6 ft. Good for grading concepts, not for permit drawings.
- Building heights: 95th percentile of lidar height above ground inside each Overture footprint. Footprints are machine-derived and can be a few feet off.
- Roads: Overture segment centrelines, not edges of pavement.

## Loading into AutoCAD / Civil 3D

1. Civil 3D: `Toolspace > Settings > Drawing Settings > Units and Zone`, pick "NAD83 Florida State Planes, East Zone, US Foot" (FL83-EF) before inserting anything.
2. `INSERT` or `XREF` the DXF at 0,0, scale 1, no rotation.
3. Build the existing-ground surface either from the PNEZD file (fastest) or from the DXF contours (`Surface > Definition > Contours > Add`, weeding 15 ft / 4 degrees). For the highest fidelity, convert the LAZ to RCP in ReCap and use `Create Surface from Point Cloud` with the ground class.
4. Plain AutoCAD (no Civil 3D): the DXF is still a usable 2D/3D base. `A-BLDG-3D` meshes and contour polylines show in 3D views. Plex-Earth, CAD-Earth or BricsCAD Pro can build a TIN from the ground points if you need one without Civil 3D.
5. Add the parcel polygons from Lake County, then design lots, pads and roads on new layers. Keep the base as an Xref.

## Data sources and licences

- USGS 3DEP lidar, project FL_Peninsular_Lake_2018, via the USGS Entwine Point Tile index on AWS (`s3://usgs-lidar-public`). US Government work, public domain.
- Overture Maps release 2026-09-23.1, themes buildings, transportation, base (water), addresses. Buildings and transportation are ODbL (attribution required: "© OpenStreetMap contributors, Overture Maps Foundation"); addresses are from open government sources.
- No Google data was used. Google's Map Tiles API policy forbids extracting, tracing or deriving 3D objects from Photorealistic 3D Tiles, and the Maps Platform terms forbid building terrain models from Elevation API values. See the research report one folder up.

## Focus zones at full lidar resolution (`focus/`)

Two sub-models were built at the finest resolution the point cloud supports, because the house and the lakes are the parts of the site that will be kept and designed around.

| Zone | Extent (ftUS) | Contents |
|---|---|---|
| `focus/house/` | E 426,050 to 427,050, N 1,577,150 to 1,578,150 (23 acres) | Main house, the tall structure beside it, the 4,479 sq ft outbuilding, the pond, the pads, the ring feature and the big square enclosure southwest of the house |
| `focus/lakes/` | E 425,750 to 427,050, N 1,578,350 to 1,579,550 (36 acres) | Both lakes, the loop track around the round lake, the orchard rows, and the 5,378 sq ft building south of the round lake |

Each zone folder has:

- `sausage_castle_<zone>_focus_EPSG2236_ftUS.dxf` with 0.5 ft (`C-TOPO-HALF`), 1 ft (`C-TOPO-MINR`) and 5 ft (`C-TOPO-MAJR`) contours from a 2 ft ground grid; a 5 ft terrain MESH (`C-TOPO-MESH-3D`) for plain AutoCAD 3D views; every building as a MESH whose roof is the 1 ft lidar surface inside the footprint, so hips, ridges and towers are real (`A-BLDG-ROOF-3D`), with an annotation giving area, approximate finished floor, eave and ridge heights; tree crowns as circles with height labels (`L-PLNT-TREE`, canopy-height local maxima over 12 ft); lake outlines derived from lidar no-return areas as closed polylines at the 2018 water surface elevation (`C-WATR-LIDAR`, usable as Civil 3D breaklines) next to the Overture outline (`C-WATR-OVERTURE`).
- `<zone>_dsm_1ft.asc.gz` (first-return surface at 1 ft: roofs, trees, track), `<zone>_dtm_2ft.asc.gz` (bare earth at 2 ft), both hydro-flattened to the lake levels.
- `<zone>_ground_pts_2ft_PNEZD.csv.gz` for a Civil 3D surface at full density.
- `<zone>_preview.jpg` and `<zone>_metadata.json` (per-building base, eave and ridge, water areas and levels, tree counts).

Measured from the lidar (2018): main house 7,423 sq ft footprint, base about 73.6 ft, eave about 14 ft, ridge about 31 ft above ground; the structure just west of it is 2,198 sq ft with a 43 ft ridge; the pond southwest of the house sits at about 68.8 ft; the elongated lake is about 1.6 acres at about 69.3 ft; the round lake is about 1.1 acres at about 70.0 ft. Ground across both zones runs 68 to 88 ft NAVD88. Contours at 0.5 ft are indicative only, since the lidar's own vertical error is about 0.33 ft.

## 3D renders (`viewer/` and `focus/*/…_render3d.jpg`)

- `viewer/index.html` is a self-contained three.js viewer of the lidar surfaces. It loads the heightmaps and land-cover textures in `viewer/data/` (surface and bare earth for the whole site at 6 ft, the house compound at 1 ft, the lakes at 2 ft), lets you orbit, tilt and zoom, switch between surface and bare earth, set vertical exaggeration and sun angle, toggle a 100 ft grid, click any point to read easting, northing and elevation, take a snapshot, and drape your own aerial image over the zone. It runs from GitHub Pages once this branch is merged (`/reports/sausage-castle-base/viewer/`) and is also published as a Claude artifact.
- Heightmaps are RGB PNGs: elevation in feet = (R × 256 + G) × 0.01 + zmin, with zmin per zone in `viewer/data/meta.json`. Row 0 is north. Textures are synthetic land cover from canopy height (grass, shrub, trees by height), building footprints, road buffers and lidar water, shaded by the surface hillshade. They are not aerial photos; NAIP or a drone orthomosaic cropped to a zone's bounds can be draped instead.
- `focus/house/house_render3d.jpg` and `focus/lakes/lakes_render3d.jpg` are static perspective renders produced by `scripts/render_static.py` from the same data.
- `scripts/export_3d.py` regenerates `viewer/data/` from the lidar clip and the Overture files.

## Lake zones concept (`focus/lakes/LAKE-ZONES-CONCEPT.md`)

First design pass around the round lake: four equal-area zones (2.04 acres each) between a 50 ft no-build water buffer and a limit 250 ft from the water, using the existing 1,640 ft loop track as the lane, with 35 × 50 ft tiny-home pads set 20 ft off the lane and 15 ft apart. Outputs: `lake_zones_concept_EPSG2236_ftUS.dxf`, `lake_zones_plan.jpg`, `lake_zones_concept.json` (rules, metrics, pad corners), and a "Lake zones concept" overlay toggle in the 3D viewer. Regenerate with `scripts/lake_zones.py` (set `ZONE_LIMIT` in the environment to test other ring depths).

## Tiny home concepts (`units/`)

Three themed units designed for the 35 × 50 ft pads, as parametric massing models: the Amanita cottage (mushroom, 412 sq ft), Widow's Peak (haunted house, 564 sq ft) and the Cypress stilt cracker (Florida swamp, 702 sq ft including the screened porch). Each has a sheet with plan, elevations and axon views, a DXF in local feet (3D mesh parts by material layer plus 2D plan layers), and a spec with materials and Florida wind and flood notes. `units/tiny_homes_on_pads_EPSG2236_ftUS.dxf` defines the three as blocks and inserts them on all 22 lake-zone pads (A haunted, B swamp, C mushroom, D mixed), facing the lane at the lidar ground elevation. The 3D viewer's Lakes zone has a "Tiny homes (concept)" toggle showing the same placement. Regenerate with `scripts/tiny_homes.py`. See `units/README.md` for the specs.

## Florida Freedom World (`brand/`, `masterplan/`, `index.html`)

The project owner's poster (`brand/florida-freedom-world-poster.webp`) is the vision: a Florida theme park, festival ground and campground on the estate. `scripts/masterplan.py` maps each element of the poster to a programme area on the lidar base: Gator Gate and midway, the Castle, Freedom Arena, Gator Greens, the lakeside cabins, the Freedom Float lagoon, Butterfly Grove, the Goat Barn farm, Swamp Camp lodge, the RV and tent camp, the Landing Site tower, and the event barns; 12 areas on about 36 acres. Outputs: `masterplan/florida_freedom_world_masterplan.jpg` (plan over the hillshade), `..._EPSG2236_ftUS.dxf` (one layer per programme area plus the trail loop) and `masterplan.json`. `index.html` is the demo page in the poster's voice, also published as a Claude artifact.

## Clearing, grading and the 3D mock-up (`focus/lakes/CLEARING-GRADING.md`, `mockup/`)

`scripts/clear_and_grade.py` grades each of the 22 pads flat at its median existing grade (balanced cut and fill), blends to existing ground over 10 ft, sets an 8 ft clearing limit and lists every 2018 tree that has to come out: 82 trees, 2.24 acres cleared, 155.6 cu yd cut and 135.4 cu yd fill. Outputs: `focus/lakes/clearing_grading_EPSG2236_ftUS.dxf` (pads at finished grade, clearing limits, trees to remove with IDs, graded contours), the plan image, JSON and summary table. It also writes a cleared, graded surface for the 3D viewer ("Cleared and graded" toggle in the Lakes zone, cabins at finished grade) and `mockup/lakes_cleared_3d_mockup_EPSG2236_ftUS.dxf`, a graded terrain mesh with the cabin blocks inserted. `scripts/render_mockup.py` renders the perspective mock-ups in `mockup/`.

## Blender scene (`scripts/blender_build.py`, `mockup/blender/`)

`scripts/blender_build.py` builds the cleared, graded lake zones in Blender from the same data the web viewer uses: the terrain with the land-cover texture, the lakes as water, the kept trees as simple crowns, and all 22 cabins (four lands: haunted A, swamp B, mushroom C, UFO D) placed at finished grade with materials and glowing windows. It saves `mockup/blender/florida_freedom_world_lakes.blend` and `.glb`, sets up five cameras (overall plus one per zone) and renders them with Cycles. Run it inside Blender 3.6 or newer:

```
blender --background --python scripts/blender_build.py -- --base reports/sausage-castle-base --out reports/sausage-castle-base/mockup/blender --renders --samples 64
```

or with the pip `bpy` module on Python 3.11. Options: `--step 2` halves the terrain resolution, `--no-trees` skips the tree instances, `--views overall,C` limits the renders, `--res 1920x1080`.
