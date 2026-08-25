# Timberborn v0.6 Changes and Meta-Strategy

## Key v0.6 Changes

Version 0.6 (Update 6) introduced significant changes to water mechanics,
terrain, and progression. Key changes relevant to strategy:

Drought escalation curve is steeper than previous versions. Droughts lengthen
faster — colonies that coasted on a small dam setup in v0.5 will run dry
earlier in v0.6. Build water infrastructure one full cycle ahead of need.

Floodgate controls were improved — the height slider is more precise. Use
floodgates everywhere instead of plain dams.

Badwater season mechanics were refined. Badwater now flows more predictably
along terrain contours. Isolating badwater upstream with a dedicated floodgate
system is more reliable than in previous versions.

The District Crossing cost was adjusted upward — plan second district timing
carefully around this expense.

Mechanical Batteries received a capacity buff — each battery stores more
power than in v0.5. Fewer batteries are needed for the same buffer, but
wind-only power still requires 2–3 batteries minimum for overnight coverage.

## Terrain and Map Meta

High ground is always valuable — windmill placement, flood protection,
battery co-location. Claim high-ground tiles early even before you need them.

River bends create natural dam sites — the narrower the river crossing,
the fewer dam/floodgate tiles needed. Prioritise narrow crossing points
for your first dam.

Trees grow faster on fertile tiles. Fertility overlay (press F by default
or access from the map overlay menu) shows which tiles have highest
tree regrowth speed — place Forester zones on high-fertility tiles.

## Common Failure Modes

Plank starvation: colony expands construction faster than sawmill output.
Fix: pause all non-critical construction, add a second sawmill if labour
allows, prioritise lumberyard restocking.

Drought death spiral: water reserve runs out mid-drought, beavers dehydrate
and die, production collapses. Fix: never let water reserve drop below
20% of tank capacity before drought ends. If it does, throttle all
water-consuming production (farms, irrigation) immediately.

Forest depletion: all trees cut with no forester replanting. Fix: pause
all lumberjack flags until forester zone has significant young trees.
It takes 4–6 days for birch to mature — survive on current log stock.

Power blackout: unexpected surge in demand overwhelms generation. Fix:
build 1–2 batteries as a buffer. Batteries alone cannot solve a sustained
shortage — add another windmill on high terrain.

Population overshoot: too many beavers, not enough food. Fix: disable
Breeding Pods immediately, expand farmland, add food storage.

## Useful Ratios (v0.6 baseline)

- Beavers per Lumberjack Flag: 2–3
- Forester zones per 2 Lumberjack Flags: 1
- Water Tanks per 10 beavers: 1–1.5 (more in late cycles)
- Windmills per Water Wheel: 2:1 for drought resilience
- Batteries per 3 Windmills: 1–2
- Builders as % of population: 20–25% during expansion, 10% steady state
- Farmhouse acres per 10 beavers: 1 farmhouse with 6–8 crop tiles
