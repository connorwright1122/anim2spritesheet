# Model2Pixel product context

## Confirmed direction

- Platform: a native Blender add-on, implemented in Python with `bpy`.
- Purpose: turn animated 3D assets into pixel-art sprite sheets for game development.
- Audience: developers and artists using Blender to produce sprites for games.
- Product goal: a polished add-on other developers can use, rather than a workflow limited to one personal project.
- Engine strategy: engine-neutral. These last two choices were confirmed by the user on November 3, 2026.

## Existing implementation

- The repository contains the single-file add-on `anim2spritesheet.py`, a README, and focused foundation tests.
- It renders a manually configured camera over one scene frame range, with selectable base, normal, and emission outputs, then packs PNG sheets.
- It includes a manually refreshed still preview in the Blender sidebar.
- The repository directory uses `model2pixel`; the displayed add-on name is `anim2spritesheet`. A final product name has not been selected.
- The repository currently has an MIT license.

## Boundaries and open decisions

- The current request is assessment, competitor research, and overhaul recommendations. Implementation has not been requested.
- Pricing, distribution channels, final Blender compatibility range, branding, and first optional engine adapter remain undecided.
- Proposed features and release gates live in `OVERHAUL.md`; they are recommendations, not claims about existing functionality or confirmed commitments.
- There are no committed demo scenes or rendered sprite examples in this checkout. Foundation tests now cover pure PNG/export logic and state guards; Blender render fixtures remain outstanding.

## Evidence

The source and README were inspected directly. Competitor and Blender documentation links, research limitations, and technical findings are recorded in `OVERHAUL.md`.
