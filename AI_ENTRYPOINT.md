# AI ENTRYPOINT — LISPCAD

This is the mandatory starting point for an AI using the modular LISPCAD production skill.

## Load order

1. Read all files in `skills/lispcad/core/`.
2. Inspect the complete drawing before selecting specialized modules.
3. Load the applicable mode:
   - `modes/FLAT_NO_BEND.md`
   - `modes/BEND_UNFOLD.md`
4. Load every applicable topology module. A part may match more than one topology.
5. Load every applicable feature module.
6. Load every applicable shared reference; `references/MATERIAL_RULES.md` is mandatory for any part with holes or uncalled-out eligible laser corners. Load Nobi/Thread Pilot tables when those features occur.
7. Apply validation before emitting production CAD/AutoLISP. A user-requested partial numeric preview is Magenta + FLAG and **not** production PASS; never invent unknown topology or bend sequence.
8. Use `regression/` for all known failure classes; `regression/features/520924-19_APPROVED.md` is the approved new regression suite.

## Selection rule

Do not force a drawing into a single topology category. Modules are composable.

If classification is uncertain, load all plausible modules. If production-safe geometry still cannot be uniquely established, ask the user rather than guessing.

## Migration safety

The historical immutable baseline remains:
`skills/lispcad/versions/V4.3/SKILL_LISPCAD_V4_3_PORTABLE.md`.

**Current approved release V4.5 (520924-19; approved L09–L10):**
- Immutable V4.4 historical snapshot: `skills/lispcad/versions/V4.4/SKILL_LISPCAD_V4_4_PORTABLE.md`.
- Immutable current V4.5 snapshot: `skills/lispcad/versions/V4.5/SKILL_LISPCAD_V4_5_PORTABLE.md`.
- Portable active single-file: `skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md`.
- Modular core/feature/mode files and `references/MATERIAL_RULES.md` must implement the same V4.5 rules. SUS430 uses SS Nobi but SUS/他 Laser R, holes and White Piercing; Cu/Brass t6 uses R0.5 and t>6 no automatic Laser R.
- V4.5 preserves all V4.4 rules and only adds approved L09–L10. V4.4 explicitly supersedes V4.3 blanket DXF-only R0.5 omission, universal hole Ø≥t warning, and green-by-default Piasu POINT. V4.3 remains intact for audit; **do not apply a conflicting historical rule as current**.
- Production updates require direct user approval; unknown J leader / shop relief construction is not production skill knowledge.
