# 05 — SLIT / RELIEF | Production rules V4.34

> Separate evidence-scoped custom source slits, bend-end relief and BOXMET; do not combine formulas across scope.

<!-- BEGIN MODULE: skills/lispcad/features/SLIT_RELIEF.md -->
# LISPCAD Feature — SLIT / bend relief routing

**V4.29 custom source-slit gate; V4.20 base formulas retained.**

## V4.29 — custom source-instructed slit

A printed/handwritten `スリット`, `SLIT`, or equivalent explicit slit instruction may define a **custom source-instructed slit**.

- This custom branch is instruction-driven. Do **not** add it merely because a bend exists, because a slit would be mechanically useful, or because a reference/sample contains one.
- The source value is drawing-specific. For example, `スリット 8` means the controlling explicit slit value for that scoped feature is 8 in that drawing. It does not establish a universal 8 mm rule.
- Read quantity, host edge/face, position, direction, and relation to BEND from the actual instruction, witnesses, leaders, and geometry. Such slits are often used around bend regions to reduce deformation, but that purpose does not prove that the slit lies at the bend center.
- Never hardcode a centerline or copy a reference-DXF coordinate into a new drawing.
- When the custom slit has an explicit controlling dimension, preserve it. Do not replace it with the generic `D90=t+0.2` or `D=t*sin(theta)` formulas below.
- If slit identity/scope is proved but a required numeric/position field remains unresolved, retain the feature and FLAG the unresolved field; do not silently drop `SLIT_RELIEF`.
- Load/close `references/SOURCE_MANUFACTURING_NOTE_CENSUS.md` for source-note provenance.

Existing crossing-bend, opposite-fold `R=t`, `055958`, BOXMET and other separately-triggered relief mechanisms remain independent. This section does not require an explicit `スリット` note for those already-approved mechanisms and does not change their trigger/orientation rules.

## Base classification

First classify whether a source feature is ordinary CUT slot/notch, custom source slit, bend relief slit, BOXMET slit, lance, KEGAKI or another process. Similar appearance or Green color does not prove process identity.

## 90-degree bend slit

For the approved generic 90° bend-relief family, and only when that mechanism is actually the routed controlling mechanism rather than an explicit custom slit dimension, retain:

`D90 = t + 0.2 mm`.

## Bend angle greater than 90 degrees

For the approved >90° bend-relief family, with included physical bend angle `theta` satisfying `90° < theta < 180°`:

`D = t * sin(theta)`.

Equivalent reflex form: `D = t * abs(sin(phi))` when `phi = 360°-theta`.

Approved t=3.2 examples:
- 150° -> 1.600000 mm
- 130° -> 2.45134221798 mm
- 110° -> 3.00701638651 mm

The 150° value equals t/2 only because sin(150°)=0.5; do NOT generalize t/2. Exactly 90° uses the separate `t+0.2` rule when the generic 90° relief mechanism applies. Slit depth is not Nobi.

Preserve source-proved slit direction/connectivity and applicable local fillet/tangent construction. Do not universalize a local R0.5 unless the source/existing mechanism proves it. Green LINE/ARC geometry may be slit/relief; Green is supporting evidence only. A Green POINT with proved PIASU semantics is a different family.

QA: close source-note provenance when applicable, correct quantity/value/position/direction, correct mechanism/connectivity, no duplicate/coincident paths, no helper geometry in manufacturing CUT, correct BEND interaction, and saved-DXF physical read-back.
<!-- END MODULE: skills/lispcad/features/SLIT_RELIEF.md -->

---

<!-- BEGIN MODULE: references/BEND_EDGE_RELIEF_90.md -->
# BEND_EDGE_RELIEF_90 — bend-edge length + bend-end offset relief gate

**Status:** USER APPROVED 2026-10-05 from calibration job `521005-05` and the supplied three-example bend-relief DXF.

## Scope

This reference applies only to a **90-degree bend-end junction** where the need for a bend-relief slit is controlled by the signed edge offset at the end of a proved bend edge.

It does **not** replace or redefine:
- an explicit source-instructed custom `スリット` / `SLIT` value;
- BOXMET corner slit/relief;
- opposite-fold fixed-outside `R=t` relief;
- approved relief rules for bend angles other than 90 degrees;
- unrelated CUT notch/slot/lance/KEGAKI geometry.

If another more specific routed mechanism controls the same junction, apply that mechanism and do not double-create relief geometry.

## 1. Terminology

Use the following terms consistently:

- **cạnh uốn** = **bend edge / shared bend edge**;
- **chiều dài cạnh uốn** = **bend-edge length**;
- **độ bậc tại đầu cạnh uốn** = **bend-end offset**;
- **rạch thoát uốn** = **bend-relief slit**.

Do not call the bend-end offset `bend setback`; bend setback is a different sheet-metal term.

## 2. BEND_EDGE_LENGTH_LOCK

For every proved bend, lock the actual material shared edge before unfold/output:

`bend_id | face_A | face_B | shared-edge endpoints | bend-edge length | source witnesses | material domain`.

The **bend-edge length** is the physical length of the shared edge over which material actually bends. It is not the face bbox, not the total flat width/height, and not a convenient extension through neighboring material.

A bend pair must be clipped to this real material domain and to any real void/relief intersections.

### 057873 regression intent

For calibration code `057873`, the source proves a `248` bend-edge length for the long bend and `50` bend-edge lengths for the two end bends. These numbers are job-specific regression evidence only. They must never become generic coordinates or default bend lengths.

## 3. Signed bend-end offset S

At each relevant bend end, establish a local frame from source-proved physical edges. Define `S` as the signed **bend-end offset** between the actual material edge and the zero-offset/flush reference for that junction:

- `S > 0`: the retained material/bend-end region **protrudes** beyond the flush reference;
- `S = 0`: the two controlling edges are **flush**;
- `S < 0`: the actual material edge is **recessed** from the flush reference.

The sign and magnitude must come from actual source geometry/witnesses. Do not infer `S` from visual similarity, sample coordinates, symmetry, bbox, or Nobi arithmetic.

`S` is a local edge/topology parameter. It is not Nobi and it is not a bend allowance.

## 4. BEND_END_OFFSET_90 relief decision

Let `T` be sheet thickness. For this 90-degree mechanism:

### Case A — `S > 0`

**NO bend-relief slit is required by this mechanism.**

There is no active `T/2` threshold or intermediate FLAG branch. Any positive proved bend-end offset uses this NO-SLIT branch unless another separately routed mechanism or explicit source instruction requires relief.

### Case B — `S = 0`

Create the bend-relief slit from the **actual edge** inward by:

`D_actual = T + 0.2 mm`.

### Case C — `S < 0`

The edge is recessed. From the **actual recessed edge**, slit inward by exactly:

`D_actual = T + 0.2 mm`.

If the same endpoint is reported from the original zero-offset/outside reference, the total distance is:

`D_reference = |S| + T + 0.2 mm`.

The `|S|` term is the already-recessed edge distance; it is not an additional slit beyond the actual edge.

### Unresolved S

If the relevant 90-degree junction is proved but `S` cannot be closed after source exhaustion, retain `SLIT_RELIEF = UNKNOWN` and FLAG only that local relief decision. Do not guess NO-SLIT or insert `T+0.2` by habit.

## 5. Direction and connectivity

The formulas above determine required depth only after the local junction and relief direction are proved. Preserve source topology for:
- which edge receives the slit;
- inward direction;
- endpoint/connectivity;
- interaction with the bend-line material domain.

Do not assume a global X/Y direction, centerline location, mirror, or diagonal lead from these formulas alone.

When a physical slit intersects a BEND segment, apply the existing real-geometry intersection/clipping rules; do not leave dashed BEND geometry running through an actual CUT slit.

## 6. Approved t=2 decision matrix

For `T = 2 mm`:

- `S = -2` -> slit `2.2` from the actual recessed edge; endpoint is `4.2` from the zero/outside reference;
- `S = 0` -> slit `2.2` from the actual edge;
- `S = +1` -> NO SLIT;
- `S = +1.5` -> NO SLIT;
- `S = +2` -> NO SLIT.

This matrix supersedes the earlier provisional idea that `0 < S <= T/2` should be FLAGGED. That branch is **not active**.

For `057873`, `T=2` and the proved relevant bend-end step is `S=+2`, therefore this mechanism requires **NO SLIT**.

## 7. Mechanism precedence

For one physical junction, apply the first controlling mechanism whose scope is actually proved:

1. explicit revision/cancellation and explicit source-instructed custom slit semantics;
2. topology-specific approved mechanism such as BOXMET or opposite-fold `R=t` where its trigger is proved;
3. this `BEND_END_OFFSET_90` gate for the scoped 90-degree bend-end junction;
4. generic crossing-bend relief only when its own crossing-bend trigger remains physically true after bend-domain and material-edge closure.

Never generate duplicate reliefs from multiple mechanisms at the same junction.

## 8. QA

Before production PASS for an affected junction, verify:

- bend-edge length and endpoints are source-locked;
- bend line exists only on the true material domain;
- `T` and signed `S` are proved;
- 90-degree scope is proved;
- the controlling relief mechanism is identified and not duplicated;
- for `S=0`, slit depth is `T+0.2` from the actual edge;
- for `S<0`, slit depth is `T+0.2` from the actual recessed edge and any reference-distance report equals `|S|+T+0.2`;
- for `S>0`, no slit is added by this mechanism;
- saved DXF read-back preserves the final physical CUT/BEND interaction.
<!-- END MODULE: references/BEND_EDGE_RELIEF_90.md -->

---

<!-- BEGIN MODULE: references/BOXMET_SLIT_RELIEF.md -->
# BOXMET_SLIT_RELIEF — V4.16 construction + V4.18 signed-orientation hardening

**Status:** USER APPROVED 2026-09-28.  
**V4.18 hardening:** USER APPROVED / PUSH 2026-09-29 from 520929-18 direct audit. The V4.16 topology/parameters are unchanged; V4.18 makes the four local slit direction signs executable and makes BEND trimming depend on actual geometric intersection rather than corner proximity.

**Scope:** Only source-proved BOXMET-style sheet-metal boxes with a central/base rectangle and four adjacent bent flanges.

## 1. Trigger / no-trigger gate

Apply this reference when the source topology proves all of:
- one central/base rectangle `L × W`;
- four adjacent bent flanges;
- adjacent flange bend directions meet at the box corners;
- a BOXMET corner slit is required to prevent corner bend interference/deformation.

In this topology, do **not** omit a required slit merely because the outer CUT contour already closes.

Do **not** auto-apply this reference to:
- ordinary L/U/Z profiles;
- a single flange or free edge;
- a non-crossing bend;
- an unrelated slit/relief/seam topology;
- a drawing-specific alternate or explicitly cancelled relief.

For these cases, “no BOXMET trigger” means the BOXMET slit is not added; evaluate any other explicit/approved relief rule independently.

## 2. Orientation: which flaps retreat by t

Let `L` and `W` be the proved base-rectangle dimensions.

### Case A — L >= W
Bottom and Top flaps retreat by `t`; Right and Left flaps remain full. Slit base points in a local base frame:
`(t,0)`, `(L-t,0)`, `(L-t,W)`, `(t,W)`.

### Case B — W > L
Right and Left flaps retreat by `t`; Bottom and Top remain full. Slit base points:
`(L,t)`, `(L,W-t)`, `(0,W-t)`, `(0,t)`.

The signs/orientations of the slit and lead rays follow the corresponding physical corner.

### V4.18 BOXMET_SIGNED_ORIENTATION — executable local directions

Use a local base frame with `+X` right and `+Y` up. Let `S` be the short slit-ray direction of length `SlitLen`; let `D` be the lead endpoint delta using `LeadVal` on each signed axis. Construct the local slit with these signs before any proved whole-part rotation/reflection.

For **Case A — L >= W**:
- bottom-left `B=(t,0)`: `S=(0,+1)`, `D=(-LeadVal,-LeadVal)`
- bottom-right `B=(L-t,0)`: `S=(0,+1)`, `D=(+LeadVal,-LeadVal)`
- top-right `B=(L-t,W)`: `S=(0,-1)`, `D=(+LeadVal,+LeadVal)`
- top-left `B=(t,W)`: `S=(0,-1)`, `D=(-LeadVal,+LeadVal)`

For **Case B — W > L**:
- bottom-right `B=(L,t)`: `S=(-1,0)`, `D=(+LeadVal,-LeadVal)`
- top-right `B=(L,W-t)`: `S=(-1,0)`, `D=(+LeadVal,+LeadVal)`
- top-left `B=(0,W-t)`: `S=(+1,0)`, `D=(-LeadVal,+LeadVal)`
- bottom-left `B=(0,t)`: `S=(+1,0)`, `D=(-LeadVal,-LeadVal)`

These signs are part of the BOXMET construction, not an optional visual mirror. A different final orientation is allowed only through an independently proved part/view transform; do not flip a single slit across a bend line because the result “looks symmetric.”


## 3. Parameters from approved BOXMET tool

- `SlitLen = t + 0.2`
- `LeadVal = 3.0` only when the BOXMET tool material value is exactly `SS` and `t < 6.0`
- otherwise `LeadVal = 6.0`
- local fillet radius `R = 0.5`
- Layer `0`
- slit color ACI `3` Green

Do not silently remap a different material string into the tool's exact `SS` branch. TrainAiCad material-family rules remain separate unless an approved conversion explicitly controls this tool input.

## 4. One slit = one connected three-primitive feature

Each BOXMET slit is ONE manufacturing feature: `LINE + ARC R0.5 + LINE`.

Let `B` be the theoretical corner/base point, `E1` the slit end with `|B→E1|=SlitLen`, `E2` the lead end, `θ` the included ray angle, `R=0.5`.
- `tangentDist = R / tan(θ/2)`
- `centerDist = R / sin(θ/2)`
- tangent point 1 = `B + unit(B→E1) × tangentDist`
- tangent point 2 = `B + unit(B→E2) × tangentDist`
- arc center = `B + unit-bisector × centerDist`

Output the trimmed LINE, tangent ARC R0.5, trimmed LINE. The arc is not a separate relief and not automatic Laser R.

## 5. CUT/BEND interaction

Construct the solid BOXMET slit/CUT first, then intersect its actual LINE+ARC+LINE geometry with each dashed BEND/reference segment. Interrupt/split BEND only where the slit truly crosses or overlaps the INTERIOR of that BEND segment. Empty intersection keeps the BEND continuous; endpoint-only contact terminates at the common endpoint and MUST NOT create an artificial gap. Do not trim by corner proximity, retreat-point proximity, or assumed symmetry. Do not overlay BEND/reference through an actual slit CUT.

## 6. 520801-04 / 044858-044859 approved regression

Source recognition: box-corner bend transition around `285 | 43`; purpose: prevent bend deformation/interference.

For `t=1.5`:
- `SlitLen=1.7`
- `LeadVal=6`
- `θ=135°`
- `R=0.5`
- tangentDist `0.207106781186...`
- short straight `1.492893218813...`
- diagonal straight `8.278174593052...`

Both `044858` and `044859` require the corresponding mirrored slit.

## 7. Deduplication with 055958

Older `055958` already proves one relief may be connected `LINE + ARC R0.5 + LINE`. V4.16 adds only BOXMET trigger/omission, L/W retreat selection, exact parameters, analytic construction, four-corner placement, bend interruption and 044858/044859 regression.
<!-- END MODULE: references/BOXMET_SLIT_RELIEF.md -->
