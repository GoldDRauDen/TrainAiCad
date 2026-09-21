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
6. Load only the shared reference tables required by the selected modules.
7. Apply validation before emitting production CAD/AutoLISP.
8. Use `regression/` to verify behavior when a case touches a known failure class.

## Selection rule

Do not force a drawing into a single topology category. Modules are composable.

If classification is uncertain, load all plausible modules. If production-safe geometry still cannot be uniquely established, ask the user rather than guessing.

## Migration safety

The immutable baseline is:
`skills/lispcad/versions/V4.3/SKILL_LISPCAD_V4_3_PORTABLE.md`

The portable current copy is:
`skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md`

During this modularization release, if a modular file conflicts semantically with the immutable V4.3 baseline, STOP and report the conflict. Do not silently weaken or reinterpret the approved V4.3 rule.
