# Nebuchadnezzar Bazaar, Distribution and Walker System (v1.0)

## How the Bazaar Works

The bazaar is the central distribution hub of every city. Bazaar workers
(walkers) collect goods from storehouses and granaries, then walk fixed
routes delivering goods to houses along the road network.

A house receives food and goods only when a bazaar walker passes in front
of it. If no walker route covers a housing tile, that house receives
nothing regardless of how many goods are in the city's storehouses.

## Walker Route Mechanics

Walkers leave from the bazaar's door and walk along roads. They follow
the road network and turn at intersections. They do not cross open terrain.

Walker range: approximately 60-80 road tiles from the bazaar. Houses
beyond this range receive no service from that bazaar.

The direction a walker travels is influenced by the road layout. Dead-end
roads cause walkers to turn back. Loop roads allow walkers to cover more
ground in one pass.

Design implication: road layout is the most important factor in bazaar
coverage. A grid of connected loops gives better coverage than many
dead-end spurs.

## Bazaar Placement Rules

Place the first bazaar as centrally as possible relative to the housing
district. A central position minimises the maximum distance to any house.

One bazaar typically serves 20-40 houses depending on road layout and
housing density. When coverage gaps appear, add a second bazaar rather
than trying to extend the existing one beyond its walker range.

Bazaars must be stocked. Check the bazaar panel to confirm it holds the
food and goods types your housing evolution requires. If a bazaar is
empty of a required item, trace back to the storehouse or granary.

## Storehouses and Granaries

Granaries store food (grain, dates, fish, meat, bread). Storehouses
store goods and materials (pottery, linen, tools, bricks, etc.).

Bazaar walkers collect from the nearest accessible storage building.
Place storage buildings on the same road network as the bazaar — walkers
cannot collect across open terrain.

Storehouse placement rule: place storehouses between production buildings
and bazaars. This minimises the walk distance for both supply walkers
(from production to storage) and bazaar workers (from storage to bazaar).

Multiple storehouses can specialise: one for food goods (bread, beer),
one for luxury goods (linen, pottery, jewellery). This reduces congestion
at a single storehouse.

## Signs of Distribution Failure

- Housing stuck at a tier despite food and goods being in storage:
  bazaar walker is not reaching that housing block. Check road connectivity.

- Bazaar showing empty goods panel despite production running:
  storehouse is full or not connected to the bazaar road network.
  Check that production → storehouse → bazaar road path exists.

- Approval rating dropping despite food production running:
  specific housing blocks may not be receiving food. Use the overlay
  to check individual house access to food types.
