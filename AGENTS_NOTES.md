<!--
HISTORICAL. Verbatim copy of repo_city's CLAUDE.md as of 2026-07-16, carried over when
the Python package was split out of remsky/repoglyph into this repo. Kept whole and
unedited: it is the only written record of the Python renderer's design rationale.
AGENTS.md is authoritative for how this repo works today; this file is background.

Read it as a snapshot of a LARGER tree than this repo has. It documents the pre-split
monorepo, and this repo has since dropped and renamed parts of it. Verified 2026-07-16:

  Described and still here (rationale applies):
    cli.py, gitsource.py, cache.py, models.py, palette.py, palettes.py, geometry.py,
    hashing.py, render/{compose,styles,districts,svg,typeface,buildings,oblique,
    skyline,highrise,lighting,logo,overlay}.py

  Described but RENAMED here:
    render/voxel.py  ->  render/scene.py
    metrics.py       ->  the metrics/ package (base.py, core.py)

  Described but NOT IN THIS REPO AT ALL (code lives only in git history / the
  2026-07-16 archive zip; this repo is clone/local-path only and has no crowd,
  no timelapse, and no REST source):
    collect.py          the source-picking seam
    github.py           the REST/GitHubClient data source
    render/crowd.py     contributor stick-figures + avatar heads
    animation/          the git-history timelapse (repoglyph-timelapse)

  Here but NOT described (postdates the snapshot):
    okf.py, the metrics/ package

  Sections that describe the OTHER repo (remsky/repoglyph) and never applied here:
    the Worker / web preview / npm package / client-render / deployment material.

  Still load-bearing across both repos: THIS repo owns the parity contract's
  regeneration (tests/test_parity.py, REPOGLYPH_REGEN_GOLDENS=1). remsky/repoglyph
  vendors a copy at worker/test/parity/*.json and nothing detects drift, so
  regenerating expected.json means copying it there too.
-->

# CLAUDE.md

Guidance for working in this repository. 

## What this is

`repoglyph` generates an isometric "city" banner (a single standalone **SVG**)
for any GitHub repository. It encodes three honest signals:

| Layer | What you see | Source |
|-------|--------------|--------|
| **Structure** | skyline — each file is a building; height ≈ file size; color = file type; the whole **directory tree** is a nested treemap (folders = neighbourhoods, subfolders nested inside, depth-scaled streets between them) | the repo file tree |
| **Recent work** | lit windows — buildings glow on files touched by the last *N* commits | recent commit history |
| **The team** | a crowd of stick-figures, each head a real GitHub avatar, busiest committer up front | the contributor list |

Plus a side panel "fingerprint": file/dir/depth counts, the largest district,
and a rough modularity score.

## Commands

Managed with [uv](https://docs.astral.sh/uv/); Python **3.14+**, no runtime deps.

```bash
uv sync                                  # create venv, install package + dev deps
uv run repoglyph owner/repo              # generate owner_repo_oblique.svg
uv run python -m repoglyph owner/repo    # equivalent, no console script
uv run pytest                            # run the test suite
uvx ruff check src tests                 # lint
uvx ruff format src tests                # format
```

By default the SVG is written to `output/<owner>_<repo>/<owner>_<repo>_<style>.svg`
(the directory is created if needed) **and** a sibling `.png` is rasterized
beside it. The PNG step is best-effort: it uses `resvg-py` (a *dev* dependency,
so the runtime stays stdlib-only) and degrades to SVG-only with a logged note if
it isn't installed — `uv sync` installs it. `scripts/svg_to_png.py` is the
standalone batch converter and writes the same sibling `.png`; keep that pairing
when adding outputs.

The output is a **fixed-size banner** by default (1280×480, GitHub-bannerish):
the HUD (title + stats panel top-left, crowd below it, horizontal colour legend
pinned bottom-right) is drawn at locked pixel sizes and the city is scaled to
fit the stage — which now runs the full width to the right edge, with only a
thin bottom strip reserved for the legend. This keeps the text legible and
the rasterized PNG bounded regardless of repo size. `--size WxH` changes the
canvas; `--full` restores the old auto-sized canvas that grows to the unscaled
content (no scaling, can be very large — the HUD stays fixed-size either way).

The `repo` argument is an `owner/repo` slug **or a path to a local git clone**,
which is read in place (no clone, no rate limit); the slug for contributor
faces is derived from its `origin` remote when that points at github.com.

CLI flags: `--commits N` (default 50), `--max-avatars N` (default 60),
`--size WxH` (default 1280x480), `--full` (auto-size to content),
`--out FILE` (override the default path), `--no-png` (skip the PNG),
`--png-scale N` (PNG resolution multiplier, default 2.0),
`--style {towers,skyline,highrise,voxel,oblique}` (default `oblique`; see
**Render styles** below) plus the per-style scalar knobs `--shear N` (oblique
camera tilt, default 0; try 6), `--streets N` (voxel/skyline/highrise lane
width, default 1; 0 = flush), `--depth-cap N` (voxel: collapse dirs past depth
N) and `--detail N` (district label budget, default 14),
`--palette NAME|FILE` (color theme, default `light`; see **Palettes** below),
`--token TOKEN` (or `$GITHUB_TOKEN`),
`--source {auto,clone,api}` (default `auto` — clone, fall back to API; a local
path is always read in place). A token raises the GitHub API limit from 60 to
5000 req/hour and is recommended for repeated runs.

**These product defaults (`light`, shear 0, 50 commits) are shared with the
Worker; the *library* `render()` defaults stay `neon` / shear 2 (the golden
reference look) in both languages.**

Iterating on rendering without re-fetching: a successful run snapshots the
gathered `CityData` to `repo_cache/<owner>_<repo>.json` (disable with
`--no-cache`). Re-render from that snapshot with `--from-cache` — it skips the
network entirely, so you can tweak the render layer against a fixed input.

## Architecture

`src/` layout. Data flows **collect → model → render**. Multiple *data sources*
all produce the same `models.py` dataclasses, and everything downstream
(geometry, metrics, rendering) works only against those models — never raw JSON.
`collect.py` is the seam that picks a source; `render()` neither knows nor cares
which one ran. This is what makes new front-ends (Action, web/Worker) additive
rather than rewrites — see **Data sources & deployment targets** below.

```
src/repoglyph/
  cli.py        argparse + main() -> exit code
  collect.py    collect_city(): pick a data source (auto/clone/api/local path) -> CityData
  github.py     GitHubClient (retry/backoff) + gather_city() — the REST source
  gitsource.py  gather_city_via_clone() (shallow clone) + gather_city_from_path()
                (existing local clone, read in place) — the git sources (no API limit)
  cache.py      save_city()/load_city(): JSON snapshot of CityData at the seam
  models.py     SourceFile / Contributor / CityData dataclasses
  palette.py    file extension -> Category -> (top,left,right) colors (the default look)
  palettes.py   named themes: Palette(colors + Chrome) — neon/light + resolve_palette
  geometry.py   iso projection, nested-treemap packing, Scene (viewport + offsets)
  metrics.py    RepoMetrics fingerprint (counts, modularity)
  hashing.py    stable_unit(): deterministic [0,1) jitter
  render/
    __init__.py thin re-exports only (render, STYLES, StyleSpec, district_set,
                TimelapseContext) — no logic lives here
    compose.py  render(CityData) -> str: fit camera, derive HUD layers, assemble
    styles.py   StyleSpec dataclass + the STYLES registry + district_set
    districts.py the cross-projection district annotation: Projection adapter,
                iso_projection/oblique_projection, DistrictConfig, and the three
                shared drawers (draw_boxes/draw_labels/draw_emphasis)
    svg.py      text() primitive + assemble_document() scaffold
    typeface.py bundled Monaspace Xenon: @font-face CSS (embed) + sfnt paths (resvg)
    fonts/      the Latin-1-subset Xenon faces (woff2 embed + otf for resvg)
    buildings.py  skyline + lit windows (the `towers` style)
    voxel.py      the `voxel` style: dir=tower, file=cube; build_voxel + helpers
    oblique.py    cabinet-oblique style: the same plot packing tuned (loose root files
                  sort last; tight (1,0,0) streets so lone files don't strand),
                  different projection
    crowd.py      contributor stick-figures + avatar heads
    overlay.py    fingerprint panel + color legend
  animation/      history timelapse (the same pipeline, walked over commits)
    history.py  open_history(): clone + reconstruct CityData at each commit
    encode.py   rasterize() frames (resvg) + stitch() to mp4/gif (ffmpeg)
    __init__.py render_timelapse() + main() -> the repoglyph-timelapse command
tests/          unit tests for the pure logic
```

Module dependency direction (no cycles):
`cli → collect, cache, render` · `collect → github, gitsource` ·
`render/* → geometry, metrics, models, palette, hashing` ·
`render: styles, compose → districts → voxel, oblique` (districts is the
annotation leaf; the renderer modules never import it, so there's no cycle) ·
`geometry, metrics → models, palette` ·
`animation/* → gitsource, render, geometry, models`.

### Render styles

There are **five** styles — `towers`, `skyline`, `highrise`, `voxel`, `oblique`
(the JS port ships `oblique`/`skyline`/`highrise`; `towers`/`voxel` are
Python-only). Everything that used to be a separate style (`voxel-tight`,
`voxel-flat`, `oblique-skew`, …) was really a **single scalar on a continuum**, so
it's now a *parameter*, not a registry entry: `StyleParams(shear, streets,
depth_cap)` (`render/styles.py`) carries the knobs the CLI exposes as `--shear` /
`--streets` / `--depth-cap`, each read by the styles that care. This keeps the
menu short and the "play with the styles" surface a small set of base looks with
a couple of sliders each, rather than a flat list where names are secretly the
same look at a different number.

`--style` picks a *city* renderer from the `STYLES` registry in
`render/styles.py`; the HUD (panel, crowd, legend) is identical across all of
them. A style is a `StyleSpec(build, render, projection=None, districts=None)`
(`render/styles.py`): `build` is `(files, params, hints=None) -> scene` (it reads
the knobs it cares about off `StyleParams`), `render` draws it, and the two optional
fields wire the **district annotation** — `projection` is a `scene -> Projection`
adapter (the per-renderer differences: ground projection, footprint corners,
label markup) and `districts` is a `DistrictConfig` (cut method/cap + three
booleans: `boxes`, `labels`, `emphasis`). `compose.render` derives the canvas-
pixel layers from those: `boxes`/`emphasis` → **underlay**, `labels` → overlay,
all drawn by the shared `draw_boxes`/`draw_labels`/`draw_emphasis` in
`render/districts.py` (one implementation each, projection-parameterized — they
replaced the old per-style `voxel_plot_*`/`oblique_*` near-duplicates). The cut
is resolved **once** per render and handed to all three layers, so they always
annotate the same regions. `assemble_document` draws `background → underlay →
city → HUD → overlay`, so the **underlay sits behind the scaled city** (the
towers occlude it) and the **overlay on top** (always legible). Adding a style is
purely additive — one registry entry (and, if it needs a *new* projection, one
`Projection` factory) — and determinism holds for
all of them (brightness/jitter are pure functions of the data).

- **`towers`** — the original: one windowed building per *file* (`buildings.py`).
  Unchanged. No knobs.
- **`skyline`** (`skyline.py`) — the `towers` buildings packed into labelled
  neighbourhood districts (iso projection, balanced cut, centred labels). Reads
  `--streets`.
- **`highrise`** (`highrise.py`) — one tower per neighbourhood, floors are
  immediate sub-dirs, rooms are files; per-floor labels. The building set is a
  `--detail`-budgeted frontier peel (the JS `worker/render/highrise.js` is the
  reference implementation). Reads `--streets` and `--detail`.
- **`voxel`** (`voxel.py`) — one isometric tower per *directory*; each file is a
  stacked cube sized by its bytes, with an inset window lit when the file was
  touched recently. Shares the projection, tree reconstruction, `fit_banner` and
  HUD with `towers`; only the packing and box drawing differ. It *is* the
  **district/plot look** (what used to be `voxel-plot`), built by `build_voxel`
  via a `_PackConfig(streets, max_depth, plot=True)` whose scalars come from
  `StyleParams`. A directory's files spread across a `sqrt(N)` pad so a footprint
  **grows with file count**, turning big repos into broad neighbourhoods instead
  of a sparse forest of 1×1 towers. It layers on three features:
    - **roof-mounted lights** — the lit window moves from the cube's side faces
      onto its roof (read top-down), which suits the flat file-pads
      (`render_voxel_plot` passes `roof_light=True`);
    - **directory labels** (the shared `draw_labels`, the *overlay*) — constant
      pixel size, so they stay legible no matter how far the city is scaled down.
      The district set is the **balanced cut** (`district_cut`, method
      `"balanced"`): a scale-free peel bounded by `_DISTRICT_CAP` (~14), so
      `pandas/` resolves to `core`/`io`/`tests`, a dominant monorepo dir descends
      into its biggest sub-dirs (long tail unlabeled), and small top-level dirs
      stay whole. (The legacy `_DISTRICT_SPLIT` 0.35 `"adaptive"` cut stays
      reachable via `DistrictConfig(cut="adaptive")` for reference.) Each label
      leads from its district's left-edge tower; a greedy collision dodge drops
      any label overlapping one already placed (biggest district wins);
    - **floor outlines** (the shared `draw_boxes`, the *underlay*) — a faint dashed
      parallelogram around each district's ground footprint, drawn behind the
      city so towers occlude it where they stand in front (it reads as an outline
      *on the floor*, hidden naturally, not floating over the skyline). Labels and
      boxes share the once-resolved `district_groups` so both annotate exactly the
      same regions. The `voxel` (iso) and `oblique` styles draw these with the
      *same* `districts.py` drawers, differing only by their `Projection` adapter.
      Streets are `(1, 1, 0)` at the default `--streets 1` — a 1-cell lane between
      top-level dirs *and* between sub-districts (a wider top-level lane compounds
      across many siblings and flings them apart), just enough to separate
      neighbourhoods for their outlines without scattering the city into dark gaps.

  Its two scalar knobs (these *were* separate styles, now just params on
  `voxel`): **`--streets N`** sets the lane width — default `1` is `(1,1,0)`; `0`
  packs flush everywhere (the old `voxel-tight`). **`--depth-cap N`** makes dirs
  past depth N absorb their whole subtree into one cluster, flattening deep thin
  chains (the old `voxel-flat`). `towers` and `voxel` at default params stay
  **byte-identical** to the old `towers` / `voxel-plot`.
- **`oblique`** *(default)* (`oblique.py`) — the same plot packing and district
  boxes/labels as `voxel`, drawn in a **cabinet-oblique** projection instead of
  isometric. The camera is a first-class knob: `ObliqueParams(cell_w, cell_d,
  cell_shear, height_scale)` — a frozen dataclass (the building-angle analogue of
  voxel's `_PackConfig`) that every drawer reads back off `ObliqueScene.params`.
  `build_oblique` sets `cell_shear` from the `--shear` param (the rest fixed
  today); `cell_shear` is the camera tilt and the **only** thing `--shear` moves:
  - the default `--shear 2` (`_FLAT`) tilts almost to top-down, reading like a flat
    relief *map* — districts pack into broad count-sized neighbourhoods and labels
    drop into a clean horizontal lane above each parallelogram;
  - a deeper `--shear 6` fattens the side walls so blocks read as solid 3-D blocks
    (the earlier "citylike" look — what used to be `oblique-skew`). It changes the
    *skew*, **not** the height (`height_scale` is unchanged), and packing is
    camera-independent (grid cells only), so it differs from the default **purely
    in projection** — same buildings, just more dimensional.

  Building-angle (`ObliqueParams`/`--shear`), grouping (`_PackConfig` +
  `--streets`/`--depth-cap` + district cut) and the timelapse are the three
  orthogonal levers; only `cell_shear` is wired to a flag today, but all the
  params are tunable for future styles / a customization front-end.

### Palettes

`--palette` swaps the **whole look**, not just the buildings: a `Palette` carries
both the per-category face triples (`colors`) **and** a `Chrome` block — page
background gradient + glow, panel/legend text inks, the brand accent (subtitle +
logo stroke), the crowd-figure limb stroke and the district floor-outline stroke.
So a palette can flip the banner from dark to a coherent **light mode**, not only
tint the skyline. `palette.py` still owns *categorisation* (extension → `Category`)
and the canonical dark triples; `palettes.py` is the **theme registry** on top of
it. Two built-ins:

- **`neon`** *(default)* — the original dark look. `colors` is literally
  `dict(CATEGORY_COLORS)` and `Chrome()`'s defaults are the exact old hardcoded
  values, so the default render is **byte-identical** to before (goldens unchanged).
- **`light`** — a light-background reskin: soft **pastel** building blocks on a
  gently tinted (not blinding white) blue-grey page gradient, near-black stat text,
  and a deep-teal brand accent. The ink-dark building outlines double as definition
  on the light ground.

What stays **theme-independent on purpose**: building edge strokes + unlit windows
(dark ink reads as line-art on any background), the lit-window/touch glow (always
warm, so "recent work" reads in every theme), the logo's gold centre node, and the
"light = touched" legend swatch. Only the listed `Chrome` tokens move.

`resolve_palette(spec)` is the seam both CLIs call: a built-in name, or a path to a
**palette JSON** —
`{"name", "colors": {"code": ["#top","#left","#right"], …}, "chrome": {"bg": [...], "ink": "#…", …}}`.
Omitted categories keep the default faces and omitted `chrome` keys keep the dark
defaults, so a user can recolour just `code`, or only flip the background. The
resolved `Palette` threads explicitly: `render(..., palette=)` →
`spec.render(..., colors=)` for the faces and `chrome=` into
`assemble_document`/`render_panel`/`render_legend`/`render_crowd`/`draw_boxes`/
`render_logo`. Every chrome-aware function defaults its arg to the dark value
(`Chrome()` / `CATEGORY_COLORS`), so existing callers and goldens stay
byte-identical and determinism holds (colours are a pure function of the palette).
The timelapse takes `--palette` too, forwarded unchanged to every frame.

### History timelapse (`repoglyph-timelapse`)

The `animation/` subpackage renders a repo's **whole git history** as a growing
city — the *same* `collect → model → render` pipeline, just walked over commits.
`open_history` clones the repo (full history, all blobs so sizes exist at every
checkpoint) and reconstructs a `CityData` at each sampled commit straight from
git (reusing `gitsource`'s parsers); each is rendered to a frame and `encode.py`
rasterizes (resvg) + stitches (ffmpeg) to an **mp4** (a gif is opt-in via
`--gif`). It's purely additive — the single-banner path is untouched.

`repoglyph-timelapse owner/repo` (or a path to an existing clone); flags mirror
the banner CLI plus pacing/emphasis knobs: `--step N` (sample every Nth commit),
`--max-frames`, `--commit-secs S` (seconds each commit lingers — the pace),
`--fps` (smooth playback rate), `--no-fade` (hard cuts instead of the default
cross-dissolve), `--hold S` (end hold), `--emphasis-secs S` / `--no-emphasis`
(the new-district pulse), `--no-avatars`. resvg-py is a dev dep; **ffmpeg is an
external binary** — both are looked up lazily so the runtime stays stdlib-only.

Faces come from **one** authoritative HEAD fetch (login → avatar, media-type
already sniffed by `github._image_mime` so it survives the PNG raster), reused
across all frames. The *same* HEAD fetch also builds an **email → login bridge**
(`github.fetch_email_logins`, a bounded scan of recent commits): a per-frame
contributor's git email is resolved to its login via `gitsource.derive_login`
(noreply emails) *or* that bridge (a plain `@gmail.com` address, or one a
contributor changed away from partway through history) — and split identities
that resolve to the same login **merge** into one figure with summed commits, so
e.g. an author who switched signing emails stays a single growing crowd member
instead of vanishing or doubling. An unresolved login stays a plain head. Only an
`owner/repo` slug can be queried — a local clone path stays plain heads. Pacing/
fade live in `encode.stitch`: keyframes are read at a
low `src_fps` (one per commit) and `minterpolate=…:mi_mode=blend` resamples to
`fps`, cross-dissolving consecutive commits.

Three design points make it read as *evolution* rather than chaos:

- **Fixed camera (`render(..., fit_files=HEAD)`).** Normally `fit_banner` re-fits
  the camera to each frame's own bbox — so every frame would zoom to fill the
  canvas and the growth signal vanishes. Passing `fit_files` pins the
  content→canvas `scale`/`translate` **and** the scene's `offset_x/offset_y` to a
  reference tree (HEAD), so a grid cell maps to the same pixel in every frame and
  the city grows *into* a fixed frame. All scene types share those four box slots,
  so it works for every style. `fit_files=None` is byte-identical to before.
  The HEAD box is then **expanded per frame to also bound that frame**
  (`render._fit_camera`): a transient directory (present mid-history, gone by HEAD)
  packs below the HEAD footprint (see next bullet), so a frame can briefly run
  taller than HEAD and the pinned camera alone would clip it. With absolute
  placement below, this is the *only* source of bulge and it's purely vertical
  (width is fully bounded), so the expand fires only on the handful of genuine-
  restructure frames (Kokoro: 4/104). A frame that fits inside HEAD — including HEAD
  itself — leaves the box untouched, so **the final frame matches the static banner
  exactly**; only a bulging frame momentarily zooms out. The expand is a pure
  per-axis union of two boxes — deterministic, and a no-op for the single banner.
- **Absolute placement from HEAD for `oblique`.** `towers`/`voxel` re-pack naively
  each commit (buildings reshuffle as a directory's area rank changes — that *is*
  the "organization changing" signal). `oblique` instead pins every block to a
  **fixed grid position** so anchors never jitter. The HEAD scene is built first
  (the camera reference) and `_pack_node` *records* into `voxel._PackHints`, per
  block, its HEAD **footprint** (`dims`, w×h) and its **absolute top-left** within
  its parent's HEAD arrangement (`offset`). Every frame then drops each block at its
  recorded `offset` verbatim — so a block's position is **independent of its
  siblings' current sizes**, killing the frame-to-frame drift (Kokoro: 4 residual
  drift events, all genuine reorg, down from ~65). `_pad_block` pads a not-yet-grown
  block up to its HEAD `dims` so it fills its final slot and the parent stays
  HEAD-sized even when a child is absent; together with `offset` this bounds a
  HEAD-present frame to HEAD's extent. A block **absent from HEAD** (transient,
  later deleted) has no recorded offset and flows below the HEAD footprint (`area`/
  `width` order it); a block holding *more* cells mid-history than at HEAD overflows
  its slot, so ~handful of genuine-reorg frames hide a few buildings behind their
  neighbours — the honest cost of locking anchors over re-flowing the city. Hints
  are recorded onto `ObliqueScene.pack_hints` and `render` forwards them only when
  `fit_files` is set and the build exposes them — **no-op for the single banner and
  every non-`oblique` style** (byte-identical). Determinism holds: hints are a pure
  function of HEAD.
- **New-district emphasis** (`render(..., emphasis=(districts, intensity))`). Each
  *final* (HEAD) district pulses gold at the frame it **forms and locks in** — the
  start of its unbroken run of presence through HEAD (computed once from the frames'
  district sets in `render_timelapse`). Transient districts (gone by HEAD) never
  pulse, and a district present from frame 0 establishes silently. The timelapse
  pauses on that commit for `--emphasis-secs` and swells the boundary gold (a sin
  0→1→0). It's driven by `DistrictConfig.emphasis` (True only for the `oblique`
  family today): `compose.render` calls the shared `districts.draw_emphasis` when
  the style's config opts in and the timelapse supplies a pulse set, so it's
  additive and a **no-op for styles without a boundary layer** (`voxel` has
  `emphasis=False`; plain styles have no `districts` config at all, so nothing
  ever pulses). The emphasis is a canvas-pixel
  layer drawn into the **underlay** (behind the scaled city), so the pulsing
  boundary obeys sightlines — buildings standing in front of it occlude the
  stretches behind them, and only the near edges + outward glow read over open
  ground, rather than the boundary floating over the skyline.

### Key design points

- **Determinism is a hard requirement.** The same repo at the same commit must
  produce byte-identical SVG. Anywhere the layout wants "randomness" (window
  lighting, crowd jitter), derive it from `hashing.stable_unit(...)` of stable
  inputs — never use `random`.
- **Content vs. canvas are separated.** `Scene` (`geometry.py`) is *content
  only* and *city only*: the placed buildings in their own local coordinate box
  (built from the file list), with no notion of the page.
  `fit_banner(scene, width, height, full)` then computes a `BannerLayout` — the
  fixed canvas size plus the single `translate`/`scale` that fits the city box
  onto the **stage** (the area between the HUD bands), grounded to the stage
  floor so spare room reads as sky overhead. `assemble_document` wraps **only the
  city** in that one transform; the HUD (panel, crowd, legend, divider, plus any
  style underlay/overlay — see **Render styles**) is drawn in **raw canvas
  pixels** so its fonts/faces never scale. This is what makes the banner a fixed
  size with legible text while the city auto-fits.
- **The city is (almost always) height-bound — so vertical room is the only
  lever that makes buildings bigger.** In pure iso the bounding box of *any*
  grid is fixed at the `TILE_W:TILE_H` aspect (≈1.75:1): both screen-width and
  screen-height scale with `(gridW+gridH)`, so re-packing wider/narrower changes
  where buildings sit *inside* the diamond, never the bbox shape. The default
  stage is wider than 1.75:1, so `min(stage_w/content_w, stage_h/content_h)` is
  bound by **height** — the city fills the stage's height and leaves margin on
  the sides. Consequence: *freeing horizontal space (e.g. the legend's old right
  band) does NOT enlarge the city* — it only widens the side margin. To scale a
  big repo up you must add **height** (taller `BANNER_HEIGHT`, or trim top/bottom
  reservations), or flatten `TILE_H` toward top-down so the bbox gets wider than
  the stage (at the cost of building-height drama). The reclaimed right band is
  there to give the taller city room so it isn't width-clipped, not to enlarge it.
- **Layout is a nested treemap of the directory tree** (`pack_districts` ->
  `_build_tree`/`_pack_node`/`_arrange` in `geometry.py`), not a flat top-level
  grouping. Each directory recursively packs its sub-dir blocks plus its own
  file cluster, separated by **depth-scaled streets** (`_STREETS = (1, 0, 0)` —
  a thin lane between top-level dirs, none deeper). Streets are kept tight on
  purpose: wide multi-level lanes scatter the city into isolated buildings with
  dark gaps, whereas tight streets pack the nested districts into solid
  contiguous masses (the dense, gathered look). Everything stays on the
  **integer grid** (one building per cell, streets are empty cells) so
  the box renderer's fixed footprint still lines up; don't switch to float cells
  without revisiting building overlap. Ordering is deterministic: child blocks
  sort largest-area-first with a name tiebreak (the file cluster sorts by area
  with an empty-string name), independent of path insertion order.
- **Projection is 2:1 iso + an optional clockwise screen rotation** (`iso()` in
  `geometry.py`). After the base isometric projection, the whole ground plane can
  be rotated clockwise by `_VIEW_ROT_DEG` to turn the city to a corner-on,
  "looking into the streets" angle rather than a flat head-on lozenge. The
  **default is `_VIEW_ROT_DEG = 0`** — the classic flat isometric view, which
  reads as one tight, gathered, cohesive block (this is the preferred look).
  Crucially **only ground positions rotate** — buildings stay upright iso boxes,
  because the vertical extrusion in `buildings.py` is applied in screen space
  *after* `iso()` and the box-face offsets use raw `TILE_W`/`TILE_H` (so towers
  don't lean as the grid spins beneath them). Two knobs frame the view:
  `_VIEW_ROT_DEG` (turn amount — 0 = flat gathered lozenge (default), ~45° spins
  all the way to axis-aligned columns and tends to collapse into a diagonal
  stripe, so stay well under it; rotating sprawls the city out, which is usually
  *not* wanted) and the `TILE_W:TILE_H` ratio (=28:16, the *elevation*; a larger
  `TILE_H` drops the camera toward street level — taller, more side-on
  buildings). `STAGE_ZOOM` (=1.2) then scales past a perfect fit so the gathered
  city fills the stage. Painter order follows the (rotated) depth: sort by
  `iso()` screen-y then -x.
- **Crowd lives in the panel column, in canvas pixels** (not in the content
  box). `render/crowd.py` tiles the figures in a local box — busiest committer
  front-and-centre, back rows higher/further — and translates/scales that box
  into `BannerLayout.crowd_*` (the region beneath the title + stats text,
  computed in `fit_banner` from `PANEL_STATS_HEIGHT`/`CROWD_PANEL_GAP`),
  bottom-aligned so feet rest near the banner floor. So the crowd is part of the
  **HUD** (fixed-size faces) like the panel and legend, *not* part of the scaled
  city — `assemble_document` draws it outside the content transform. The avatar
  clip-circles are defined in the crowd's *local* coords and the `<image>`s sit
  inside the same scaled `<g>`, so the circular masks still register once the
  group transform applies. Earlier the crowd stood in the content box's
  bottom-left wedge and scaled with the city; it was pulled out so the city can
  fill the whole stage and the faces stay a constant, legible size under the
  stats. Don't reserve crowd room in `Scene` again — that shrinks the city for
  no reason.
- **`render()` math is load-bearing.** The exact coordinate/format expressions
  in `buildings.py`, `crowd.py`, and `overlay.py` determine the visual output.
  If you refactor them, verify the SVG is unchanged on a fixed input (see
  Testing) rather than eyeballing.
- **GitHub errors** raise `GitHubError`; only `cli.main()` turns failures into a
  process exit. Don't call `sys.exit()` from the fetch/render layers.
- **Avatars** are fetched as bytes and inlined as base64 `data:` URIs so the SVG
  is self-contained. The fetch retries transient failures (timeouts, 5xx/429
  from the avatar CDN) — without that, heads drop to plain circles
  *intermittently*; a permanent failure (404) or exhausted retries degrades to a
  plain head and is logged at DEBUG, never aborting a run. (A future web/Worker
  front-end can skip inlining and emit avatar URLs directly — see below.)
  The data URI's media type is **sniffed from the bytes** (`github._image_mime`),
  not assumed: GitHub's `<login>.png` endpoint often returns JPEG/WebP, and
  mislabelling it `image/png` makes browsers sniff-and-render but strict
  renderers (resvg, the PNG export) silently drop it — i.e. faces would show in
  the SVG but be missing from the PNG. Keep the type honest.
- **The typeface is bundled, in two formats, because the two consumers read
  different ones** (`render/typeface.py`). The banner ships **Monaspace Xenon**
  (SIL OFL), subset to Latin-1 (~10 KB/face) so it renders the same everywhere
  rather than borrowing the viewer's monospace. `svg.MONO` leads the font stack
  with `'Monaspace Xenon'` (a system-mono fallback follows). For **browsers / the
  GitHub README**, `font_face_css()` base64-embeds the **woff2** faces in a
  `<defs><style>@font-face</style>` so the SVG is self-contained. But **resvg**
  (the PNG/timelapse rasteriser) *ignores* embedded `@font-face` **and** can't
  decode woff2 — so the PNG would silently fall back to a system font. The fix is
  the same shape as the avatar-MIME one: hand resvg the **otf** faces explicitly
  via `font_files=` (`cli._write_png`, `encode.rasterize`), with `font_family`
  set. So every face exists as both woff2 (embed) and otf (resvg) under `fonts/`;
  keep that pairing. Regular + Bold (the title is weight 700). Determinism holds:
  the base64 is a pure function of fixed bytes (so it sits in every golden — large
  but stable). A web/Worker front-end could drop the embed and reference the font
  by URL instead, mirroring the avatar-URL path.
- **The crowd needs an email→account mapping for faces.** Both sources resolve it
  through `github.fetch_contributors` (`/stats/contributors`), where GitHub has
  already mapped each commit email to an account — so a face resolves for
  *everyone with a GitHub account*, not just those committing with a
  `@users.noreply.github.com` address. The clone source uses this too (one REST
  call) and only falls back to deriving logins locally from noreply commit
  emails (`gitsource.derive_login`) when the API is unavailable (offline, or
  rate-limited without a token) — that fallback finds far fewer faces but keeps
  the run working. So if a crowd comes back mostly blank, check whether the
  fallback path ran. (Stale `repo_cache/*.json` snapshots taken before this
  fix still carry the old blanks — re-collect without `--from-cache`.)

## Conventions

- Type hints + docstrings on public functions. `@dataclass(slots=True)` for data.
- Line length 100; ruff rules `E,F,I,UP,B,SIM` (see `pyproject.toml`). Run
  `uvx ruff check src tests` + `uvx ruff format src tests`. The `worker/` JS port
  is linted/formatted by **Biome** instead (`cd worker && npm run lint` / `format`,
  config in `worker/biome.json`); its dev dependencies are Biome and **esbuild**
  (the latter only bundles the client render lib at build time — the shipped code
  and the Worker runtime stay dependency-free).
- Standard library only at runtime — adding a runtime dependency is a real
  decision; keep `dependencies = []` unless there's a strong reason.
- Logging goes to stderr via the `logging` module; the SVG path summary is the
  only thing printed to stdout.

## Testing

`uv run pytest`. Tests cover the pure logic (`palette`, `geometry`, `metrics`)
and that `render()` returns well-formed, deterministic SVG. Golden snapshots
(`tests/goldens/*.svg`) pin every style byte-for-byte; refresh intentional
visual changes with `REPOGLYPH_REGEN_GOLDENS=1 uv run pytest`.

**Cross-language parity** with the `worker/` JS port is pinned at the *semantic*
layer, not bytes: `tests/test_parity.py` computes categorization, metrics, the
balanced district cut, packing layout and palette values from
`tests/parity/fixture.json` against `tests/parity/expected.json` (regenerated by
the same env var), and `worker/test/parity.test.js` (`cd worker && npm test`,
Node's built-in `node --test` runner — no test framework dependency) checks the
JS port against the **same** expected file. Byte-identical SVG across the two
renderers is explicitly *not* a goal — per-target rendering may differ; the
semantic layer must not. CI (`.github/workflows/ci.yml`) runs ruff + pytest on
Linux **and** Windows (so a platform-dependent divergence against the committed
goldens actually surfaces) plus Biome, the JS tests, and an `npm pack` check.

When changing rendering, the strongest check is **output equivalence**: render a
fixed synthetic `CityData` before and after and diff the strings. They should be
identical unless the change is intentionally visual.

`categorize()` uses `os.path.splitext`, so a bare dotfile like `.env` has *no*
extension and falls through to `"other"` — the `.env` palette entry matches
files like `prod.env`. This is intentional; a test pins it.

## Limitations (by design)

- Shows **organization, not coupling** — a tidy folder tree can still be
  spaghetti. True architecture would need import-graph parsing.
- "Alive" means **recent, not lifetime**: windows are lit from the last *N*
  commits (bounded, tunable cost), not full per-file history.
- Very large repos (>100k tree entries) are **truncated by the GitHub API**; the
  banner then reflects a partial tree (a note is logged).
- File **bytes** is the size proxy, not lines-of-code; tall asset towers are
  height-capped so they don't dominate.
- Both data sources weight the **touch** signal by line churn (additions +
  deletions; see `CityData.touches`), but compute it differently: the clone path
  sums churn per commit (`git log --numstat`), the REST path takes one net
  `base...head` diff (`compare`). Both are normalised in the renderer, so they're
  interchangeable, but exact lit-window intensities differ between sources.

## Data sources & deployment targets

Every front-end is the same pipeline — **a data source → `CityData` → `render()`**
— so the only thing that varies is *how `CityData` is gathered*. Keep new targets
behind that seam; never let a target reach into the render layer.

**The four signals and their cheapest source** (the design tension is that no
single source gives all four cheaply — *file size* always needs blob contents):

| Signal | Cheapest source | Cost |
|--------|-----------------|------|
| Structure (paths/folders) | git trees, or REST `git/trees?recursive=1` | tiny |
| **File size** (heights) | blob contents, **or** REST tree API (sizes precomputed) | blobs are the only heavy bit |
| Touch (lit windows) | `git log --numstat` (clone) or REST `compare/base...head` (1 call) | tiny |
| Contributors (crowd) | `git log` authors, or REST `commits` / `contributors` | tiny |

**Targets:**

1. **Local CLI** *(now)* — `collect.py` picks `clone` (preferred, no rate limit)
   or `api` for a slug, reads a local clone path in place
   (`gather_city_from_path`), and snapshots to `cache.py`. See Commands.
2. **GitHub Action** *(next)* — the install product. Real `git` in CI:
   `git clone --filter=blob:none` (blobless) gives structure + touch
   (`--name-status`, which needs only OIDs) + contributors with no rate limit and
   full history; sizes come from `git ls-tree -l HEAD` (lazily fetches just the
   HEAD revision's blobs) or the REST tree API. Renders a **self-contained**
   SVG (inlined avatars) and commits it back. This is `gitsource.py`'s data via
   CI rather than a local clone — not a rewrite. Note `--numstat` is *not*
   blobless (line counts need blob contents); `--name-status` is.
3. **Web preview / Cloudflare Worker** *(after)* — a star-history-style "try any
   repo" front door. Hard constraint: **a Worker cannot clone in-process** — the
   free tier caps CPU at 10 ms (no pure-JS packfile inflate) and 50 subrequests,
   and isomorphic-git has no partial-clone filter. So the Worker uses the
   **all-REST** assembly (5 cached endpoints): `repos/{r}` (default
   branch) → `git/trees?recursive=1` (structure+size) → paginated `commits`
   (SHAs) → `compare/base...head` (touch; bisects the window to stay under the
   300-file compare cap, so 1–log₂N calls) → `contributors?per_page=1` (a count
   via the `Link` header). For the web target, emit avatar
   **URLs** (`<image href="https://github.com/<login>.png">`) instead of
   base64-inlining, so the browser loads faces — zero Worker subrequests. Cache
   rendered SVGs (KV; the Cache API is a no-op on `*.workers.dev`) and serve
   already-Action-generated SVGs straight from `raw.githubusercontent.com` when
   present. A single service-side token (not per-user) makes the rate limit a
   non-issue behind the cache. (True in-Worker `git` requires the paid Sandbox /
   Containers — an optional later tier, not the free path.)

The web target has landed (`worker/`). **Routes:** `GET /` (landing/viewer SPA),
`GET /:owner/:repo` (viewer page), `GET /:owner/:repo.svg` (rendered banner — the
embed URL), `GET /:owner/:repo/data.json` (cached `CityData` for the client
renderer, behind the same daily-pull breaker as the SVG path),
`GET /:owner/:repo/dirs.json` (autocomplete dir list, cache-read only, no GitHub
call), `POST /feedback` (editor thumbs up/down + optional short note →
Analytics Engine dataset `repoglyph_feedback`, write-only, ~90-day retention;
SQL-API query example in `wrangler.jsonc`); plus
`favicon.ico`/`robots.txt`/`sitemap.xml`.

**Client-render architecture:** the editor's first paint is server-rendered
(edge/KV-warm, fastest first pixel); every subsequent knob change renders in the
browser via the versioned static lib at `public/lib/v<RENDER_VERSION>/client.js`
(built by `cd worker && npm run build` — esbuild bundles + minifies the render
import closure into a single `client.js`, **built at deploy** (the Workers Build
command) and in CI, `.gitignore`d rather than committed, and output-equality-tested
against the source renderer). The build first BFS-asserts the
closure never reaches a server-only module or a non-browser-safe import, so a
broken import fails the build instead of shipping. One request, comments stripped. Only `commits`/`branch` changes refetch `data.json`; every other knob
re-renders locally with zero network calls. The server `.svg` path stays the
fallback (dynamic-import failure, data fetch failure, or a client-render throw)
and remains the embed product. `RENDER_VERSION` (`worker/version.js`) versions
both the SVG cache and the client lib path together — the skew guard, so a
deploy always switches client and server renderers atomically.

### Distribution & auth model (App vs Action vs package)

Three independent delivery vehicles — they compose, and importantly **the early
ones don't need a GitHub App**. Ship Action + packages first; the App is a *later*
auth backbone, not a prerequisite.

- **Packages (PyPI + npm)** — the repo is public, so it's also a dependency you can
  `pip install` / `npx`. The split mirrors the two implementations: the **Python
  pkg (`repoglyph`, PyPI)** is the full-featured local/private path (full styles,
  crowd/avatars, timelapse); the **JS/ESM port (`worker/`, npm)** is the
  zero-dep, native-Node build that also backs the Worker. Run-it-yourself, no
  GitHub identity involved.
- **GitHub Action** *(the install product — needs NO App)* — a workflow drops into
  CI, renders, and commits the SVG back. It authenticates with the **runner's
  auto-provisioned `GITHUB_TOKEN`** (1,000 req/hr/repo, isolated per repo) — so no
  central credential, no shared bucket, no App. The JS port is the lighter Action
  vehicle (runs directly on the runner's Node, no Docker pull); the Python pkg is a
  Docker/composite action if you want the full feature set. This is `gitsource.py`'s
  data via CI, per Target #2 above.
- **GitHub App** *(later — the auth identity, not hosted code)* — a common
  misconception: GitHub does **not** run your code. A GitHub App is a *registration*
  (app ID + private key + least-privilege `contents: read` + optional webhook URL) —
  a first-class actor your **own service (the Worker)** authenticates *as*, instead
  of shipping a personal PAT. It's a **superset of a deprecated OAuth App**: it does
  both **user-to-server** ("Sign in with GitHub" → act on the visitor's own
  rate limit / their private repos — the web-preview login) **and** **server-to-server**
  (installation tokens: scoped to installed repos, 1-hr expiry, *per-installation*
  rate buckets that scale ~5,000→12,500/hr). Build **one** App when you need it; never
  an OAuth App. It does **not** remove the rate limit from *anonymous* preview
  traffic (an installation token can't read repos it isn't installed on) — that path
  stays on the cache-gated service credential; the App is what lets heavy/logged-in
  users bring their own quota and unlock private repos.

### Web-preview anonymous gating (cost axis = cold pulls, not features)

The only thing that costs GitHub quota is a **cache-cold `(repo, branch, commits)`
data pull**. Every render param (palette/shear/detail/weight/prefix/filters) is
render-only — it hits the SVG cache or re-renders from already-pulled data, **zero
GitHub calls**. So gating *features* behind login protects nothing; gate **cold
repo pulls**.

| | Anonymous | Logged in (App user-to-server) |
|---|---|---|
| Cache hits (any cached public repo) | unlimited, free | unlimited, free |
| Cold public-repo pulls | **3 / session**, service credential | unlimited, on **their** 5k/hr |
| Customization (all sliders) | unlimited | unlimited |
| Private repos | ❌ never | ✅ user-scoped key, auth-checked, **never shared-cached, never `<img>`-embeddable** |

Load-bearing rules:
- A **cache hit is free and ungated** — browsing already-rendered popular repos
  costs nothing, so only *cold pulls* count against the 3-repo anon allowance.
- A **public** repo pulled on a *user's* token still populates the **shared global
  cache** — the bytes are public regardless of which token fetched them; the token
  is just the meter for *who may trigger the pull*, not what may be cached.
- A **private** repo must **never** touch the shared cache (leak) and can **never**
  be served via an anonymous `<img>` embed — private support is a logged-in
  "preview/download for yourself" mode, not the public embed product. **The public
  embed product is public-repos-only by design** (a banner in a public README *is*
  public).
- This keeps the cache **public + global + shared** (what makes it scale) and is why
  the prod SVG tier → Cache API / data tier → durable KV-or-R2 split (see the
  Worker header) holds: cold pulls are the scarce thing; everything else is cheap or
  free to regenerate.
