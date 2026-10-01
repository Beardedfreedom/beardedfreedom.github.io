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
