# Nebuchadnezzar Approval, Prestige and Objectives (v1.0)

## Approval Rating

Approval is shown in the status bar as a percentage with a delta value,
e.g. "22%(-540)". The percentage is the current rating; the delta shows
the trend over the last period.

Approval above 0% is required to avoid mission failure. A strongly
negative delta (worse than -200) is an urgent crisis requiring immediate
action.

Approval is reduced by:
- Food shortage: any house not receiving its required food types
- Goods shortage: any house not receiving required pottery, linen, etc.
- No entertainment: houses needing entertainment (tier 4+) not covered
- No religion: noble estates not receiving priest walker coverage
- High unemployment: excess workers with no jobs lowers morale
- Housing devolution: houses dropping tiers causes approval loss

Approval is increased by:
- Consistent food supply across all housing
- Entertainment building walker coverage (jugglers, musicians)
- Religion coverage (temples with priest walkers)
- Meeting objective milestones

Quick approval fix when delta is strongly negative:
1. Check food supply — most common cause
2. Check bazaar stock and walker coverage
3. Add entertainment building if tier 4+ housing has no coverage
4. Check for recently devolving housing blocks

## Prestige

Prestige is a score earned from monuments, large temples, noble estates,
and certain decorative buildings. Required by later missions as an
explicit objective.

Prestige sources (approximate values):
- Small shrine: 1-2 prestige
- Standard temple: 5-10 prestige
- Large temple: 15-25 prestige
- Noble estate (per tile): 1-2 prestige
- Monuments (ziggurat, etc.): 50-200 prestige depending on size

To increase prestige: build larger temples, evolve housing to noble estates,
and construct monuments. Monuments require significant brick and material
stockpiles — plan material production well in advance.

## Mission Objectives

Objectives are shown in the top-right panel. Typical objectives include:

Population goal: reach a target population. Population grows by adding
housing tiles and evolving existing houses.

Money goal: accumulate a treasury target. Money comes from trade and
tax revenue. Trade requires a trade post and surplus goods above city needs.

Prestige goal: reach a prestige score threshold. See prestige section above.

House level goal: evolve a number of houses to a specific tier. This forces
housing evolution — ensure all evolution requirements are met for the target tier.

## Tracking Objectives

Check the objectives panel every few minutes. Identify which objective is
furthest from completion and prioritise accordingly.

If population is the bottleneck: add more housing tiles and ensure all
evolution requirements are met.

If money is the bottleneck: establish trade routes with surplus goods.
Pottery, linen, and oil are commonly tradeable. Ensure a trade post exists
and goods are reaching it.

If prestige is the bottleneck: build one large temple rather than multiple
small shrines — large temples give significantly more prestige per build cost.
