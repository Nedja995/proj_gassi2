# Nebuchadnezzar Housing Evolution Chain (v1.0)

## Housing Tiers

Housing evolves upward when all requirements for the next tier are met.
If any single requirement is missing, evolution is blocked entirely for
that housing block — the house stays at its current tier.

Tier 1 — Shack: starting housing. Requires only road access.

Tier 2 — Standard House: requires road access + 1 food type (grain or dates)
+ bazaar walker access.

Tier 3 — Standard Villa: requires road + 2 food types + bazaar access
+ water-bearer access (from a well within range) + 1 goods type (pottery).

Tier 4 — Large Villa: requires road + 3 food types + bazaar + water +
2 goods types + entertainment access (juggler or musician walker range).

Tier 5 — Noble Estate: requires road + 4 food types (including bread) +
bazaar + water + 3 goods types (including linen or oil) + entertainment +
religion access (priest walker from a temple within range) + prestige
neighbourhood (adjacent monuments or large temples count).

## Evolution Checklist — Diagnosing Blocked Housing

If housing is not evolving check these in order:

1. Road access: is every house tile connected to a road that leads to
   a bazaar? Gaps in road network completely cut off walker service.

2. Bazaar walker coverage: does the bazaar's walker route pass through
   the housing block? Walkers travel fixed distances — a bazaar too far
   away will not reach distant housing.

3. Food variety: open a housing tile and check which food types it is
   receiving. Missing food = blocked evolution.

4. Water: is there a well within coverage radius of the housing block?
   Wells cover approximately 5x5 tiles. Place wells centrally within
   dense housing grids.

5. Goods at the bazaar: check the bazaar's stock. If it has no pottery,
   linen, or oil, the relevant production building is not supplying
   the bazaar. Trace the supply chain from production to storehouse
   to bazaar.

6. Entertainment: are juggler or musician walker routes reaching the block?
   Entertainment buildings send walkers that wander from the building's
   door — road layout determines where they go.

7. Religion: is a temple within range and staffed? Priest walkers from
   temples provide religion coverage. Required for tier 5 only.

## Key Numbers

- Standard House to Standard Villa: needs a Well within ~5 tiles
- Well coverage radius: approximately 5x5 tiles (25 tiles total)
- Bazaar walker range: approximately 60-80 road tiles from the bazaar
- Entertainment walker range: approximately 40-60 road tiles
- Priest walker range: approximately 50-70 road tiles

## Devolution Warning

If a requirement is removed (bazaar destroyed, well runs dry, food supply
drops), housing will devolve back down one or more tiers. This reduces
workers per tile and can cascade into a labour shortage.

Always maintain supply continuity. When replacing or relocating service
buildings, build the new one before demolishing the old one.
