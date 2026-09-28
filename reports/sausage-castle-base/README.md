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
| `scripts/build_base.py` | Turns the clip and vectors into the files above | Python + numpy, scipy, ezdxf, contourpy, matplotlib |

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
