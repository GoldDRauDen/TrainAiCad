# Rule lesson intake (not routed; read before changing any rule)

A new lesson or a corrected rule follows this order. Never append a new "Vx.y supplement" section to a routed file.

1. **FACT -> ROOT_CAUSE -> LESSON** in one short block in `regression/qa/<job>_<topic>_APPROVED.md` (job/code numbers and coordinates live only here).
2. **Edit the one existing rule that owns the topic, in place** (1-3 lines). If the old wording is wrong, replace it; if it is superseded, move the old text to `docs/RULE_HISTORY.md`.
3. **Pick the narrowest home**: only some jobs -> a conditional route in `ROUTER.yaml` (`conditional_default_load` / `mode_routes` / `feature_routes`); every job -> an existing core file. Do not grow `AI_ENTRYPOINT.md`.
4. **Add one executable test** for the behaviour (or a phrase pin in the owning file).
5. **Run** `python -m pytest tests -q`, `python tools/build_gate_index.py`, `python tools/audit_rule_coverage.py`, `python tools/benchmark_rule_routes.py`.
6. `tests/test_rule_load_budget.py` fails when a scenario, a core file or the versioned-heading allowlist grows. Fix by tightening first; raising a budget needs explicit user approval (DUYET).
