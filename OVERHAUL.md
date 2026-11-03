# Model2Pixel overhaul assessment

Research date: November 3, 2026. Direction confirmed by the user: a polished Blender add-on for other developers, with an engine-neutral core.

## Recommendation

Build a dependable sprite production pipeline with strong pixel-art controls and safe revision workflows. The product promise should be: **model and animate in Blender; publish consistent sprites; revise without rebuilding the game integration.**

Multi-direction rendering, palettes, normals, and JSON export are necessary, but competitors already offer them. The opportunity is to make the whole workflow easier to trust: inspect actual output before rendering a batch, keep exported identities stable, explain what changed, and preserve an artist's approved work.

This is a proposed strategy. Market demand and willingness to pay still need validation with working developers.

## What the current code actually does

The existing add-on is a useful workflow prototype: select a resolution and scene frame range, toggle three outputs, render, and pack images. The normal/emission intent and short path to a result are worth preserving.

It currently automates low-resolution rendering and packing. It does not yet provide palette control, outlines, temporal pixel-art processing, animation clip management, camera setup, direction batches, or game metadata.

### Foundation issues to fix before adding breadth

| Finding | Source evidence | Consequence and required change |
| --- | --- | --- |
| Enabling the add-on installs and upgrades packages | `anim2spritesheet.py:51–68` runs ensurepip, upgrades pip, and installs Pillow into Blender's Python environment at module import | Install must work offline and without modifying Blender's environment. Bundle compatible dependency wheels or remove the dependency. Blender's extension guidelines explicitly disallow add-ons installing packages themselves. |
| Compatibility is implicit | Lines 144, 176, and 340 hardcode `BLENDER_EEVEE`; no extension manifest exists | Add a tested compatibility layer and declare a support matrix. The identifier became `BLENDER_EEVEE_NEXT` in 4.2 and returned to `BLENDER_EEVEE` in 5.0; blindly replacing the string would introduce another break. |
| Export changes the working scene | Lines 143–189 replace engine, frame range, output dimensions, transparency, and display settings; line 283 applies base settings again | Success does not restore the original scene. There are no `try/finally` blocks; errors also bypass restoration. Use a controlled staging scene and guaranteed cleanup for all source state touched. |
| Old frames can enter a new sheet | Lines 191–247 reuse directories and enumerate their existing files without a run manifest | Render 100 frames, then 20 into the same folder, and the remaining old frames are eligible for packing. Pack only explicitly generated frame paths in a fresh staging directory; publish only a completed export. |
| Packing counts unrelated files | Lines 201–240 count all files, special-case only an initial `.DS_Store`, then paste PNGs only | Non-PNG files can change layout or fail first-image loading. Validate image types and sizes and use numeric frame identities rather than directory ordering. |
| Output configuration leaks in from the scene | Render setup does not explicitly establish PNG, RGBA, 100% output scale, or a complete color/alpha policy | Requested sprite size and transparency are not guaranteed. Define the complete export configuration separately from the user's render settings. |
| “Base/albedo” is ambiguous | Lines 143–157 select the combined render rather than extracting unlit albedo | Offer explicit Beauty and Unlit Albedo choices. Dynamic lighting needs a deliberate unlit workflow to avoid unintentionally lighting baked shading again. |
| Normals use a display shortcut | Lines 160–173 render a Workbench normal matcap | The code does not define the normal-space, channel, or color-management contract. Replace or validate this against known geometry and reference shaders before claiming engine-ready normals. |
| Emission depends on a viewport | Lines 175–189 and 279 access region/space state and call `render.opengl` | Output depends on UI context and is unsuitable as a general headless export path. Produce emission through a defined render pass or material override. |
| Preview differs from export | Lines 334–359 render using current scene dimensions, resize afterward, and stretch the result to 256×256 | Non-square sprites are distorted; the preview does not use the complete export pipeline. Use the same processing configuration for preview and final output, preserve aspect ratio, and display at integer zoom. |

These are source findings, not a successful Blender render test. Python syntax parsing passed. Local background launches of Blender 4.0.2 and 5.2.3 both exited with code 139 before the audit expression ran, so visual quality, timing, and runtime compatibility were not verified. The add-on itself was not imported, avoiding its package-install side effects.

Technical references: [Blender extension add-on guidelines](https://developer.blender.org/docs/handbook/extensions/addon_guidelines/), [4.2 API changes](https://developer.blender.org/docs/release_notes/4.2/python_api/), [5.0 API changes](https://developer.blender.org/docs/release_notes/5.0/python_api/).

## Competitor landscape

The following compares published capabilities, not hands-on quality. An undocumented capability is unknown, not proven absent. Prices are snapshots and should not determine our pricing.

| Product | Published strengths | Implication for Model2Pixel |
| --- | --- | --- |
| [Spriteturn](https://kedrem.itch.io/spriteturn) | Multiple camera presets, up to 32 directions, framing across animations/directions, action batches, palettes, dithering, outlines, PNG/JSON/Godot export, cancellation and state restoration. Listed standard price $9.99. | A close baseline competitor. Direction counts and style presets alone are weak differentiation. |
| [Sprite Forge](https://thatindiesphinx.itch.io/sprite-forge) | Locked scale and feet pivot across frames/directions; world- or camera-locked lighting; direction preview; batch animations and engine exports in Pro. Pro listed at $4 minimum. | Stable framing, clear direction names, and a quick contact sheet should be standard. Its page explicitly lists automatic outlines as a limitation. |
| [Sprite Sheet Maker](https://github.com/ManasMakde/SpriteSheetMaker/) | Configurable rows, automatic camera, dimension consistency, strips/sheets/images, settings import/export, and continuation after failure. | Match flexible job configuration and recovery; do not describe resume support as a new invention. |
| [PixelatorPlus](https://github.com/CloudyTabzy/PixelatorPlus) | Extensive palette/dither processing, selective outlines, material/object part lines, shared animation palettes, live preview, and sprite sheet JSON. | Pixel-art processing is a substantial product in its own right. Match a focused subset exceptionally well. Shared palettes and scene-aware interior lines already exist. |
| [PixelOver](https://docs.pixelover.io/manual/introduction/) | Standalone real-time effects, palette workflows, 2D/3D animation, rigging, drawing, particles, and rotation-based sprite export. | Compete on staying inside Blender and preserving complex Blender scenes, rather than rebuilding a full animation editor. |
| [2DFactory](https://tamara-rifqi.itch.io/2dfactory) | Multi-direction action queues, pivots, cropping, normals/AO/roughness/emission/diffuse, modular equipment sheets, sockets, and Godot/Unity/Unreal integrations. Listed at $10. Its page lists exported-animation preview as future work. | The closest competitor for the broader production pipeline. Modular equipment, sockets, and multiple maps are already established features. Integrated playback could improve this workflow, but is not a market-wide first. |
| [Playable Workshop Tools](https://blender.playableworkshop.com/docs/setup) | Animation events, viewport hitboxes/spawn points, sprite sheets, and Aseprite-compatible/Godot output alongside broader game export tools. | Hitboxes and event export are useful, but not novel. |
| [SpriteKiln](https://pypi.org/project/spritekiln/) | Procedural 3D sprite generation with timing, events, sockets, normal/emission maps, QA reports, style controls, and caching. Its listing classifies it as alpha. | Even QA and metadata are not unique in isolation. Our advantage would be bringing revision safety and art-direction tools to existing Blender assets. |
| [SpriteIlluminator](https://www.codeandweb.com/spriteilluminator/documentation/export) | Dedicated normal-map workflow with explicit axis inversion and encoding choices. | Normal export needs a documented contract and a convincing moving-light preview, not just an RGB-looking output. |

### Features to match

1. One-click orthographic rig; side, top-down, true-isometric, and 2:1 pixel-isometric presets with clearly named angles.
2. Collection/rig targeting and named clips from scene ranges, Actions with correct slot bindings, and explicit NLA ranges.
3. 1/4/8/16 directions with customizable starting angle, labels, and order; add arbitrary counts later if requested.
4. Fixed pixels-per-world-unit and a locked pixel pivot. Automatic fit scans all included frames/directions once, then locks; users can retain that lock when adding content.
5. Native-size PNG/RGBA output, transparent checkerboard playback, contact sheets, integer zoom, frame stepping, and an atlas view.
6. Imported palettes, shared palette across clips, material ramps, limited tone bands, ordered dithering, and controllable outlines.
7. Aligned Beauty/Albedo, Normal, and Emission sheets; optional AO, depth, and ID masks later. Define each map's meaning.
8. Grid/strip output, configurable columns/padding/extrusion, common crop rules, maximum atlas size, multi-page output, and JSON metadata.
9. Saved export profiles, batch queue, progress, cancellation, recovery, and a useful first-run demo scene.

## Where we can go further

These are differentiation hypotheses based on the reviewed documentation. They should be prototyped and compared with actual competitor output before claiming exclusivity.

### 1. Safe re-rendering and review — first differentiator to ship

Give each asset, clip, view, and source sample a persistent identity independent of atlas location. Preserve IDs through renames. Store the export recipe, tool/Blender version, map conventions, and source dependencies with each build.

On the next render, show old/new playback, a pixel difference overlay, and a readable change list: changed silhouettes, frame timing, pivot, canvas, map conventions, and atlas layout. Compare corresponding frames before packing so a layout change does not look like an artwork change.

Provide three deliberate operations: rebuild changed clips, restyle cached frames, and repack existing frames. Start with conservative clip-level invalidation and a force-full-rebuild option; shaders, drivers, simulations, and external textures make fine-grained invalidation difficult. A cache must prefer unnecessary rendering over stale output.

Offer stable-layout packing with reserved cells and explicit overflow. Atlas coordinates cannot remain unchanged forever when assets grow; require a visible layout migration rather than silently moving everything.

**Proof:** changing a palette reuses eligible render data; shortening a clip removes obsolete published frames; changing one action does not recreate unrelated engine assets; cancellation retains the last completed export.

### 2. Pixel-motion diagnostics and controls — second differentiator

Locked framing and a shared palette solve only part of consistency. Fine features, shading bands, and dithering can still crawl during motion.

Add a playback inspector for isolated-pixel changes, disappearing thin features, boundary clipping, palette use, pivot motion, and loop seams. Use scene IDs/depth or motion information where practical to distinguish real motion from unstable processing. A simple frame difference is not a reliable shimmer detector.

Start with deterministic sampling, stable palette ramps, explicit pixel-grid phase, outline budgets, and selectable screen-space versus surface-attached dithering. Offer reduced-dither previews at target size. Later prototype motion-aware quantization and artist-pinned feature masks.

Do not promise that a camera setting eliminates all shimmer, or smooth the animation with frame blending. Any temporal method must handle disocclusion and retain crisp pixels.

**Proof:** compare a thin sword, facial features, cloth, and a slow turn at 32/64/128 pixels against a fixed-framing/shared-palette baseline. Review loops at actual display size; never accept a better score that visibly damages motion.

### 3. Preserve paintovers through revisions — high-value experiment

Export a working package for an existing pixel editor. Keep generated pixels, artist corrections, masks, and frame identities separate. For the first version, corrections remain valid only when sample identity, canvas, pivot, palette interpretation, and relevant source pixels are compatible.

Re-rendering should perform a three-way comparison: prior generated frame, edited frame, and new generated frame. Unchanged source regions can retain corrections; overlapping changes become reviewable conflicts. Never silently paint old pixels over a new pose.

Later explore object/material/UV-aware correspondence for better reuse. That is research work, especially around silhouettes, occlusion, and topology changes—not a first-release guarantee.

**Proof:** a background or unrelated material change retains compatible corrections; a changed sword silhouette flags the affected corrections; deleting a frame never applies its edits to another frame accidentally.

### 4. Art-direction overrides that remain editable

Provide per-clip/per-direction overrides for pose offsets, visibility, outline settings, and held frames, stored in the export profile rather than destructively editing source animation. An attack may need a stronger side-view silhouette, a longer anticipation hold, or a deliberately exaggerated weapon.

Events belong to time/source samples rather than atlas cells. Resampling must explicitly preserve or flag event timing. Root motion can remain baked into pixels or be removed and exported as metadata.

Some reviewed tools already advertise per-direction cheats and timing controls. The hypothesis is a particularly usable Blender-native workflow with preview and validation, not a unique underlying idea.

### 5. Modular characters with verified compositing

Match equipment layers and sockets, then make correctness visible. A sword can pass in front of and behind a body in one cycle, so a single global draw order is insufficient. Offer a documented combination of split layers, per-frame order, or depth masks, with limitations stated for the chosen method.

Preview different equipment combinations with the actual export transforms and flag mismatched canvas, timing, pivot, palette, and occlusion contracts. First constrain support to opaque/cutout components; transparent materials and interactions between independently lit layers need separate handling.

**Proof:** a weapon crossing the torso, a cape behind the body, a shield rotating across views, and normal/emission maps all composite correctly in two independent reference consumers. This extends a category already represented by 2DFactory.

## Proposed Blender workflow

Keep the interface native to Blender. Retain a short sidebar path for simple jobs and offer an optional workspace layout using existing Blender editors for longer sessions. No visual redesign is finalized by this report.

1. **Asset:** choose a collection/rig and a reusable export profile. Set the camera preset, desired pixel size, world scale, and anchor.
2. **Clips & Views:** list actions/ranges, fps or held-frame timing, loop behavior, directions, and optional variants. Show a contact sheet before batch rendering.
3. **Pixel Style:** show the actual animation at integer zoom. Palette, shading, outlines, and dithering use the same processor as export.
4. **Maps & Metadata:** choose Beauty or Albedo, optional maps, pivots, and later sockets/events. A draggable preview light makes normal orientation errors visible.
5. **Publish:** choose destination and packing profile, inspect expected files and collisions, then render. Progress reports the current asset/clip/view/sample; success opens the output and a playback report.

Use quick defaults and fold advanced options. Keep export destination independent of `scene.render.filepath`. Before running, report missing cameras, unresolved slots, empty clips, invalid paths, clipping bounds, incompatible map options, and output size limits with fixes near the relevant setting.

Show job size before committing: 12 clips × 8 views × 16 samples = 1,536 frame/view samples. Three separately rendered maps could raise that to 4,608 renders; capture multiple passes together where supported. Estimate time only after measuring a representative sample.

## Engineering shape

Replace the single file incrementally with a small extension package:

```text
model2pixel/
  blender_manifest.toml
  __init__.py
  properties.py          # namespaced scene/profile data and migration
  ui/                    # panels, lists, previews, validation feedback
  pipeline/              # recipes, jobs, identities, cache, publishing
  blender/               # evaluated assets, camera rig, actions, passes
  pixel/                 # palette, ramps, outlines, dithering, diagnostics
  export/                # packing, PNGs, canonical metadata, adapters
  tests/                 # pure processing checks + Blender fixtures
```

Use a single job model for preview, interactive export, and headless export. Blender operations stay on supported Blender execution paths; use a modal/event-driven queue for UI responsiveness and a background worker process for longer jobs if needed. Avoid Python threads manipulating `bpy`.

Temporary scenes/materials must not mutate shared source datablocks. Restore source state on success, failure, and cancellation. Publish a complete staged build and manifest; retain the previous successful build until replacement succeeds. Recovery reads validated job records, not whatever files happen to exist in a directory.

Version support should be explicit and modest: propose Blender 4.5 LTS and 5.2 LTS first, contingent on testing. Action handling must account for slots introduced in 4.4. See [Blender's action-slot migration guidance](https://developer.blender.org/docs/release_notes/4.4/upgrading/slotted_actions/).

### Engine-neutral export contract

Publish PNGs plus a documented, versioned JSON schema with stable IDs, frame rectangles, original size, trim offsets, pivot, direction angle/order, duration, clip loop mode, map filenames, color/alpha conventions, and optional root motion, sockets, and events.

Specify coordinate origin, axis directions, units, angle conventions, and how trimming affects every coordinate. Publish a tiny reference reader and real sample exports. Keep custom data namespaced; do not imply arbitrary custom JSON is automatically compatible with every engine.

Offer a separate Aseprite-style compatibility exporter using supported frame/tag fields; custom metadata remains in the canonical file. [Aseprite's CLI documentation](https://www.aseprite.org/docs/cli/) defines JSON export modes and frame-tag options. Engine adapters consume the canonical format, so no engine controls the render pipeline.

All maps share the same packing rectangles and crop transforms. Start without rotated atlas cells. Normals use an explicit camera/sprite-space basis, documented RGB encoding and optional Y inversion; they bypass artistic color transforms. Normal filtering must renormalize vectors. ID masks must preserve discrete IDs. Outline pixels need an explicit lighting policy. These contracts require reference-shader tests, not visual inspection of the map alone.

## Delivery order and release gates

| Stage | Deliverable | Gate before advancing |
| --- | --- | --- |
| 1 — reliable core | Extension packaging, bundled dependencies, state isolation, explicit PNG settings, staging/manifest packing, useful validation | Offline install; source scene restored after success/error/cancel; shorter rerenders contain no stale frames; non-square preview matches exported dimensions. |
| 2 — competitive baseline | Asset targeting, camera presets, locked framing/world scale, named clips, direction batches, common pixel controls, playback, aligned maps, PNG + canonical JSON | A small rigged character exports idle/walk/attack in eight directions with consistent anchors and correct timing; the same files load in two reference consumers. |
| 3 — first differentiator | Stable identities, conservative clip cache, cached restyling/repacking, before/after review, layout migration feedback | Changes invalidate the right outputs; unsafe reuse falls back to rendering; revisions preserve consumer references; canceled export never replaces a good build. |
| 4 — advanced production | Socket/event/root-motion tools, verified modular layers, animation diagnostics and controlled temporal experiments | Weapon-crossing, clip-retiming, thin-feature, loop-seam, and equipment-combination fixtures pass with human review. |
| 5 — paintover research | Separate artist corrections and three-way revision review | Corrections survive supported edits; incompatible changes are flagged rather than silently merged. Only then consider broader correspondence. |

Do not assign calendar estimates before measuring render/pass costs and prototyping the compatibility and preview paths. Stages 4 and 5 contain meaningful research uncertainty.

## Validation and product decisions

Build a small fixture library: a non-square prop; a rigged character with idle/walk/attack; a long weapon reaching outside the original bounds; multiple armatures; NLA and slotted-action examples; thin hair/cloth; emissive parts; and a modular body/weapon/cape. Record integer-scale previews and reference images alongside metadata expectations.

Test Windows, macOS, and Linux on each supported Blender line. Measure first-use success, setup time, renders avoided, frame alignment, and failures recovered. Treat clipping and palette constraints as hard checks where valid; treat shimmer and aesthetic quality as artist-reviewed diagnostics.

Ask a small group of developers to export a real asset, change its animation/material/equipment, and export again. Observe where they repair things manually. The strongest validation for this strategy is that the second export saves substantial work, not merely that the first sheet looks appealing.

Preserve a complete basic workflow if a paid edition is later chosen. Pricing and licensing changes remain open decisions; the reviewed low-cost and free alternatives make a generic renderer difficult to position on features alone. Demo assets, predictable installation, documentation, and support will matter alongside code.

Defer a standalone pixel editor, generative image features, dozens of engine adapters, and every possible render pass. **The first build should deliver stages 1 and 2 with stable identities designed in; stage 3 should provide the first distinctive release story.**
