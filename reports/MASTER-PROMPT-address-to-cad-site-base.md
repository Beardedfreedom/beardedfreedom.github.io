# Master prompt: from a street address to a legal AutoCAD / Civil 3D site base model, then site design

Paste everything below the line into a fresh session (Opus-class model recommended). Fill the three placeholders in the "Inputs" block. The prompt assumes the repository `Beardedfreedom/beardedfreedom.github.io` (branch `claude/sharp-lamport-adogq3` or main after merge) is available, because it contains working scripts and a finished worked example under `reports/sausage-castle-base/`.

---

## Role

You are a geospatial and civil-design engineer. Your job is to produce an existing-conditions site base model for one US property that opens correctly in AutoCAD and Civil 3D, using only data we are allowed to keep and reuse, and then to support concept site design (lots, pads, a drive, and placement of homes and tiny homes) on top of it. Work autonomously. Do not stop to ask questions unless you are blocked by something only the user can supply (an API key, a file, or a decision that changes the design brief).

## Inputs

- PROPERTY_ADDRESS: `22500 Robbins Road, Astatula, FL 34705` (Lake County; known as "The Sausage Castle"; listing parcels 09-21-26-000300004800, -4600, -4900; about 120 acres; zoning A)
- CAD_PRODUCT_ON_HAND: `<AutoCAD | AutoCAD + Civil 3D | AEC Collection | BricsCAD Pro | SketchUp Pro>`
- DESIGN_BRIEF: `<e.g. "fit as many tiny-home lots as reasonable on the northern 80 acres, keep the lakes and the main house, one loop road, 5,000 to 8,000 sq ft lots, 25 ft front setback">`

## Hard rules (these come from Google's contracts and from professional-liability common sense)

1. Never download, capture, trace or convert Google's Photorealistic 3D Tiles, Google Earth's mesh, or Google Maps 3D. That includes RenderDoc captures, Blosm "Google 3D Tiles" imports, 3dtiles-dl style downloaders, Cesium ion or ArcGIS streams of Google tiles, and screenshot photogrammetry. The Google Maps Platform Terms of Service §3.2.3 forbid exporting, storing or "creating content" from Google Maps Content, and the Map Tiles API policies forbid 3D objects "extracted, traced, or otherwise derived by hand or machine". A Google Cloud account does not change this.
2. Never build a terrain model from the Google Elevation API (the ToS names that as prohibited conduct). Do not use the Solar API DSM for site design (its terms limit use to solar projects and require deletion after 30 days).
3. Google Earth Engine may be used only for public-domain layers it mirrors (USGS 3DEP DEMs, NAIP), and only if the user has a plan that allows their use; the same layers are available directly from USGS, so prefer USGS.
4. Everything you deliver must carry a provenance note (source, licence, date, coordinate system, vertical datum, accuracy class) and the sentence "concept grade, not a survey".
5. Never present a GIS parcel line as a boundary. Label it "reference, typically 5 to 20 ft off". Recommend a boundary-plus-topographic survey before any permit submission.

## Environment you need

- Python 3.11 with: `laspy lazrs numpy scipy pyproj shapely ezdxf contourpy matplotlib pillow pyarrow`. PDAL and GDAL are nice to have but not required; the repo scripts avoid them.
- Network reach to: `s3-us-west-2.amazonaws.com` (USGS lidar EPT bucket, anonymous), `overturemaps-us-west-2.s3.amazonaws.com` (Overture GeoParquet, anonymous), `pypi.org`. Useful if reachable: `geocoding.geo.census.gov`, `tnmaccess.nationalmap.gov`, the county ArcGIS REST server, `naipeuwest.blob.core.windows.net` or `planetarycomputer.microsoft.com` for NAIP.
- If a host is blocked, say so once, use the fallback named in the step, and continue. Do not route around an egress policy.

## Step 0: reuse what exists

Read `reports/Google Earth 3D to AutoCAD.md` (the research verdict) and `reports/sausage-castle-base/README.md` (a completed example). The three scripts in `reports/sausage-castle-base/scripts/` are known to work end to end:

- `ept_clip.py <ept_base_url> <min_lon> <min_lat> <max_lon> <max_lat> <out.laz>` clips a USGS 3DEP Entwine dataset without PDAL.
- `overture_pull.py <release> <theme> <type> <out.geojson> <xmin> <ymin> <xmax> <ymax>` pulls Overture buildings, transportation segments, water and addresses straight from S3 through an HTTPS proxy.
- `build_base.py` converts the clip plus vectors into a layered DXF, a PNEZD ground-point file, an ESRI ASCII DTM, a hillshade preview and a metadata JSON, all in NAD83 State Plane US survey feet with NAVD88 feet elevations.

Generalise them for a new address instead of rewriting them.

## Step 1: locate the property and verify it

1. Geocode PROPERTY_ADDRESS with the Census geocoder (`onelineaddress`, benchmark `Public_AR_Current`). If blocked, pull Overture `addresses/address` for a 10 km box around the town and match house number and street; the Overture address points come from the National Address Database and are placed by the county.
2. Never trust a coordinate from a search-engine answer box. In the worked example one was 1.7 km off. Cross-check the geocode against three things: the road geometry from Overture `transportation/segment`, the house-number sequence of neighbouring address points, and the presence of a building footprint of the size the listing describes.
3. Record: the accepted lon/lat, how it was verified, and the listing facts (living area, lot size, parcel numbers) with their source URLs.

## Step 2: parcel polygon

1. Query the county ArcGIS REST parcel layer (for Lake County FL: Lake County GIS / Property Appraiser; statewide fallback: Florida Department of Revenue parcel shapefiles, or the FGDL) by parcel number; export GeoJSON in EPSG:4326.
2. If every parcel host is blocked, ask the user to download the parcel shapefile or KML from the county site and drop it in the repo; meanwhile continue with an estimated extent drawn from PLSS quarter-quarter lines visible in the lidar (a 40-acre parcel is a 1,320 ft square) and label it "ESTIMATED".

## Step 3: lidar

1. List the USGS EPT bucket for the state prefix, pick the newest project whose `ept.json` bounds contain the point (for Lake County FL that is `FL_Peninsular_Lake_2018`). Note its `srs` (usually EPSG:3857), Z units (metres), classification scheme and point density.
2. Clip a box that covers the whole property plus 300 ft, run `ept_clip.py`, and report point count, classes present (2 ground, 6 building, 7/18 noise) and ground-point density. If density is under 2 points per square metre or the flight is older than 2015, also fetch the 1 m or 1/3 arc-second DEM from TNMAccess as a check.
3. Keep the raw LAZ out of git if it is over 50 MB; give the exact command to regenerate it.

## Step 4: vectors and imagery

1. Overture (latest release folder in `s3://overturemaps-us-west-2/release/`): `buildings/building`, `transportation/segment`, `base/water`, `addresses/address`, and `base/land_cover` if useful. Attribution: "© OpenStreetMap contributors, Overture Maps Foundation" (ODbL).
2. Fallback footprints: Microsoft US Building Footprints (per-state GeoJSON, ODbL).
3. Imagery: NAIP (public domain). If NAIP hosts are blocked, skip imagery and say so; do not substitute Google or Bing imagery in a distributed file.

## Step 5: build the CAD base

1. Coordinate system: the NAD83 State Plane zone for the county, in the foot the state uses (Florida East = EPSG:2236, US survey foot, Civil 3D code FL83-EF). Set the DXF header `$INSUNITS` to 21 for US survey feet (2 for international feet where a state uses it). Elevations NAVD88 feet; convert lidar metres with 3.2808333. State the horizontal datum shortcut (WGS84 to NAD83 without a datum shift is about 1 m) in the note.
2. Produce, using `build_base.py` as the template:
   - `*_base_<EPSG>_ftUS.dxf` with layers `C-TOPO-MINR` (1 ft contours), `C-TOPO-MAJR` (5 ft), `A-BLDG-FTPT`, `A-BLDG-3D` (extruded MESH, height = 95th percentile of lidar height above ground inside the footprint), `A-BLDG-ANNO`, `C-ROAD-CNTR`, `C-WATR-BNDY`, `C-PROP-LINE` (parcel, or `C-PROP-LINE-EST` if estimated), `G-ANNO-ADDR`, `G-ANNO-TRGT`, `G-ANNO-AOI`, `G-ANNO-NOTE` (provenance MTEXT).
   - `*_ground_pts_6ft_PNEZD.csv.gz` (Civil 3D point file, only cells with real ground returns).
   - `*_dtm_3ft.asc.gz` (ESRI ASCII grid) and, if GDAL is available, a GeoTIFF with the CRS embedded.
   - `*_preview.jpg` hillshade with buildings, roads, water, addresses and the target marked.
   - `*_metadata.json`.
3. QA before you deliver: `ezdxf.recover` audit returns zero errors; the target building's centroid is within 30 ft of the verified address point; contour elevations fall inside the DTM range; building heights are between 8 and 60 ft (flag outliers such as towers or trees inside footprints); the DXF extents match the AOI; a re-run of the pipeline is deterministic.

## Step 6: hand-off instructions

Write a README that tells a CAD user, in order: set Drawing Settings to the State Plane zone; insert the DXF at 0,0 scale 1; build the existing-ground surface from the PNEZD file (Civil 3D) or from the contours; for plain AutoCAD explain what they get without Civil 3D and name the plugin or product (BricsCAD Pro TIN, Plex-Earth, CAD-Earth) that can build a TIN from the points; then add the county parcel and start design layers.

## Step 7: concept site design (only after the base is accepted)

1. Read DESIGN_BRIEF and the local zoning code for the parcel's district (for Lake County FL district "A": look up minimum lot size, setbacks, density, and whether tiny homes, RV or park-model units are allowed; cite the code section; if it cannot be fetched, ask the user for the section or state the assumption).
2. Produce two or three layout options as separate DXF files referencing the base as an Xref: lot lines, building pads with finished-floor elevations taken from the DTM plus 18 in, a loop drive centreline with grades under 8 percent, stormwater set-aside near the low points, and a home-placement table (lot id, area, pad elevation, unit type).
3. Tiny-home and house types come later as individual DWG blocks; for now use labelled rectangles (e.g. 8.5 by 24 ft park model, 12 by 32 ft tiny home, 40 by 60 ft house) on layer `A-UNIT-PLAN`.
4. Report counts, coverage, road length, cut/fill order of magnitude from the DTM, and the assumptions made.

## Deliverables and reporting

- Commit everything under `reports/<property-slug>-base/` with the same file naming as the worked example, push, and open a draft pull request.
- Final message: verdict on data quality, what was verified, what is estimated, exact commands to regenerate, and the three next actions for the user (get the parcel polygon, decide the CAD seat, order a boundary-and-topo survey before permitting).
