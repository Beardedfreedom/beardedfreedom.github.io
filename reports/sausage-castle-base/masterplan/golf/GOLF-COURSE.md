# Gator Greens: an 18-hole course in the land the plan leaves free

Concept grade, on the lidar base (EPSG:2236 ftUS). Made by `scripts/golf_course.py`; plan image
`golf_course_plan.jpg`, CAD `golf_course_EPSG2236_ftUS.dxf`, data `golf_course.json`.

## What fits

| Course type | Typical land | On this estate |
|---|---|---|
| Regulation 18 (par 70 to 72, 6,000+ yd) | 120 to 180 ac | No. The whole estate is about 120 ac and 59 ac of it is free. |
| Executive 18 (par 58 to 62, par 3s and par 4s) | 50 to 80 ac | No. The best search fitted 15 holes with four par 4s. |
| Par-3 18 (par 54) | 25 to 45 ac | **Yes**: 21.5 ac of hole corridors inside the 59 ac that is free. |

## The course

- 18 holes, par 54, 2,860 yd. The front nine is 1,800 yd (nine 200 yd holes in the south-east woods);
  the back nine is 1,060 yd (mostly 100 to 120 yd holes around the house compound, plus one 200 yd hole).
- The Castle is the clubhouse and pro shop. Hole 9 finishes about 740 ft from it and hole 18 about 800 ft.
- Walks between holes total about 4,270 ft; four transfers are longer than 450 ft and need a cart path.
- Two holes play across an existing drive (cart crossings). 221 lidar-measured trees stand inside the
  hole corridors and would have to come out or be worked into the design.
- The ground is gentle: tees sit between 67 and 75 ft NAVD88, and no hole rises or falls more than 8 ft.
- It replaces the 3.3 ac Gator Greens pitch-and-putt in the master plan.

## Hazards and the 3D model

`scripts/golf_3d.py` adds the hazards and grades the course into the 3 ft lidar ground; the result is
`golf_course_3d_EPSG2236_ftUS.dxf`, a 3D CAD model with one mesh per surface per hole on its own layer
(fairway, green, tee, bunker, pond bed, water surface), a flag on every green and 2D outlines at their
elevations. XREF the site base DXF underneath it.

- **Water carries** on holes 1, 3, 6, 13 and 17: a pond across the hole between tee and green, so the
  tee shot must fly the water (carries of 111, 110, 111, 71 and 69 yd). Ponds total 0.94 ac, dug 5 ft
  below a water level 1 ft under the lowest bank, with 4:1 side slopes; they double as stormwater storage.
- **Sand carries** on holes 2, 5, 8, 11 and 15: a cross bunker across the hole (carries of 59 to 115 yd).
- **Greenside bunkers**: 45 in all, two or three per green, dug 2.5 ft.
- **Greens** about 3,200 sq ft, raised 1.5 ft with a 1.5% fall from back to front; **tees** raised 1.5 ft
  and flat. Every hole ties back into the existing ground over its outer 12 ft.
- **Earthwork**: about 9,100 cu yd of cut (ponds and bunkers) against 7,400 cu yd of fill (greens and
  tees), so the course balances on site with about 1,700 cu yd to spare for mounding.
- Hole 9 was dropped as a water hole because its pond would have sat on the drive.

Pictures: `golf_hazards_plan.jpg` (whole course), `golf_yardage_book.jpg` (all 18 holes, tee at the
bottom) and `golf_3d_*.jpg` (Cycles renders of the 3D model made by `scripts/golf_render.py`). The
walkabout game (`game/`) now shows the course too: the ponds are water, the holes are painted on the
ground with their trees cleared, and every tee has a sign and every green a flag.

## Polished for mock-up photos and video

`scripts/golf_polish.py` turns the routing and hazards into a finished-course design and
`scripts/golf_mockup.py` renders it with Cycles.

- **Design**: approach fairways with mown stripes (7.07 ac), maintained rough with an
  irregular tree line (22.09 ac of turf in all), 5 ft collars, cross-hatched greens
  (1.31 ac), a back and a forward tee box on every hole, 4,538 ft of 8 ft cart
  paths (clubhouse to 1, green to next tee with the turn at 9 and 10, 18 home), pond banks with reeds,
  lily pads and cabbage palms. Open ground around the course is painted as Bahia pasture and the woods as
  pine straw under the lidar trees.
- **Grading** on a 2 ft grid: turf smoothed, greens raised and tilted, tee boxes flat, bunkers dug with a
  raised lip, ponds dug with soft banks (about 13,127 cy cut, 10,003 cy fill including the
  turf smoothing).
- **Files**: `golf_course_map.jpg` (the finished course as a 1 ft per pixel map),
  `golf_course_design_EPSG2236_ftUS.dxf` (rough, fairways, collars, greens, tees, bunkers, ponds, cart
  paths and pins, each at its graded elevation), `polish/design.json` (the same as data), `mockup/`
  (renders: an overhead aerial, drone views at midday and golden hour, the hole 13 water carry, the
  view from the 17th tee, a green close-up, the finishing hole toward the Castle, and a 25-second
  drone flyover).
- **Trees** are the lidar trees at their measured positions and heights, drawn as live oaks, slash pines,
  bald cypress near water and cabbage palms; trees inside the turf are cleared.
- These renders are meant as the base for mock-ups: they hold the true layout, so an image or video
  model can restyle them into photographs without moving a hole.

Photoreal test pass (Higgsfield, Nano Banana Pro, image to image at 2752 x 1536, prompted to keep the
exact layout and camera): the results are held in Higgsfield, not in this repo. A check against the
renders found no shift in framing (phase correlation 0 to 1 px at 320 px wide) and edge correlation of
0.37 to 0.52, so the holes stay where the design puts them; the golden-hour shot recolours the turf.

| Render | Photoreal version |
|---|---|
| `golf_mockup_drone_day.jpg` | [drone, midday](https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20261002_015120_4e8c23d6-93b2-4e35-b717-b4f03a7e681c.png) |
| `golf_mockup_hole13.jpg` | [hole 13 water carry](https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20261002_015120_6cafad0b-b9ba-44b2-9305-9e11e92943f5.png) |
| `golf_mockup_tee17.jpg` | [17th tee](https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20261002_015120_4e1c8834-c9a9-4ace-8a0a-e70f8c98ce78.png) |
| `golf_mockup_finish18.jpg` | [18 toward the Castle, golden hour](https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20261002_015120_74121d39-0a4a-4da8-99b1-8ab298f1d033.png) |
| `golf_mockup_aerial.jpg` | [overhead orthophoto](https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20261002_103613_21f18181-d670-4dc8-a58f-e3df0a9bf1fb.png): the west and middle thirds match the plan closely (edge correlation 0.6 to 0.84); the east third, around the house compound, was redrawn (0.2 to 0.4), so use it for mood, not measurement |

Two 10-second photoreal drone clips (Kling 3.0, 1928 x 1076, 24 fps, no cuts) start from those stills:
[glide over the course at midday](https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20261002_103615_1f67d38c-8c94-4da1-bb38-5a9216bb0f9f.mp4)
and [push-in over the hole 13 water carry](https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20261002_103615_48e648e8-b556-4a0b-b463-730ce187f196.mp4).
They are AI motion from a single frame, so treat what comes into view late in each clip as illustrative.

[Photoreal flyover](https://d8j0ntlcm91z4.cloudfront.net/user_2wsk3cZly6RNm78yXXjuBOafIhT/hf_20261002_122338_9387ae28-287f-4972-a9c7-ac93773cac2a.mp4)
(Kling 3.0 Omni Edit, 1920 x 1080, 10 s): seconds 7 to 17 of `golf_flyover.mp4`, the hole 13 water
carry to the 18th, restyled into drone footage with the midday photoreal still as the style reference.
Because it follows the rendered flight, the camera path and the layout come from the design (coarse
layout correlation 0.83 to 0.90 against the render in every second, no cuts); trees, turf and the house
are the model's. The prompt has to ask for the CG trees, grass and house to be replaced: asked only to
"keep everything exactly", the edit came back nearly identical to the render.

Rebuild:

    python3 scripts/golf_polish.py
    python3 scripts/golf_mockup.py --views aerial,drone_day,drone_golden,hole13,tee17,green2,finish18
    python3 scripts/golf_mockup.py --flyover 200 --fps 8 --res 1280x720 --samples 16
    python3 scripts/golf_flyover_video.py       # 200 frames at 8 fps, motion-interpolated to 24 fps

The interpolation leaves faint ghosting on near tree crowns where parallax is strongest. For a clean
master, render every frame (`--flyover 600`, about four hours on 4 CPU cores) and assemble it with
`golf_flyover_video.py --fps-in 24 --fps-out 24`.

## Rules used

Estate edge setback 75 ft; 40 ft from other plan areas; 100 ft from buildings; 30 ft from water.
Par-3 corridors 96 ft wide with a 55 ft green surround, 25 ft between holes. Holes may cross internal
drives. Each tee starts a short walk from the previous green, and a longer cart transfer is allowed only
where nothing nearer fits.

## Assumptions to check

- **Parcel lines.** The estate is assumed to be three 40-acre quarter-quarter sections, south-west,
  north-west and south-east of the survey-grid breaks the lidar shows at E 427,050 and N 1,578,500. The
  north-east quarter is left out because it holds other addresses and a residential street. The master
  plan's RV and tent camp sits in that north-east quarter and needs checking against the real parcels.
- **Water and permits.** Irrigation needs a St. Johns River Water Management District water use permit
  and probably a pond or well; clearing about 20 ac of woods needs a Lake County tree removal review.
- **Design.** This is a fit test, not a golf architect's routing. Hole lengths, angles, green sites,
  bunkers, tee sets and safety netting near the Castle and the drive all need a designer's pass.

Rerun with other assumptions, for example:

    python3 scripts/golf_course.py --parcels SW,NW,NE    # if the north-east quarter turns out to be the estate
    python3 scripts/golf_course.py --max4 2 --time 600   # longer search for a course with two par 4s
