# VIEWS_ONLY Admission Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A part may leave the solve stage as VIEWS_ONLY only after the model has tried a real flat and that attempt failed a named repository gate, whenever the code's printed flat arithmetic closes against its own views.

**Architecture:** A pure module `cad/closure.py` decides whether printed arithmetic (`161+41-9.78=192.22`) closes against the dimensions the intake recorded per view, and whether the conversation contains a qualifying failed flat attempt. It is called from the `validate` host tool (feedback inside the same conversation) and once more on the final answer (so skipping `validate` does not bypass it). Intake gains a per-view `dimensions` list and an owner rule for arithmetic notes; the model may also record a structured `blocker`.

**Tech Stack:** Python 3.11+, pytest, pinned TrainAiCad repo (read only), existing `ScriptedRunner`/`SingleRunner` fakes.

**Spec:** `docs/superpowers/specs/2026-10-18-luanapp-views-only-admission-design.md`

## Global Constraints

- Only `LuanAppTools/` changes. Never edit `tools/`, rules or any pinned repository file. Do not push; commits stay on local branch `codex/luanapp-cost-accuracy-20261017` until the user says `PUSH`/`DUYỆT`.
- The gate may only reject VIEWS_ONLY. It never creates, upgrades or relaxes a PASS/PREVIEW; every repository gate still runs afterwards.
- Printed arithmetic and dimension matching tolerance: `0.005`. Attempt outer-extent tolerance: `0.011` (the repository's own bend-closure tolerance in `tools/holistic_engineering_guard.py`).
- Dimensions are optional in the intake schema (existing fixtures and fakes keep working); they are required by `validate_inventory` only when a flat-arithmetic note exists (single-agent intake only).
- Test fixtures derived from run `48cf0b85` keep only arithmetic strings, dimension numbers, view ids and the candidate structure. No customer name, no barcode.
- Never run a real job or call the AI in any step of this plan. Real runs need the user's explicit permission.
- Spec deviation: the spec's page-based fallback for note ownership is dropped. Task 3 makes an owning code mandatory, so `closed_equations` only sees notes the code owns.
- Commands run from `C:\Users\Administrator\TrainAiCad`; use `LuanAppTools/.venv/Scripts/python.exe -m pytest ...`.

## Review Focus

- Unicode minus (`−`) and en dash (`–`) in printed arithmetic must parse like `-` (covered in Task 1).
- The model's part has no or non-numeric `thickness_mm`: no crash, `±t` matching is skipped (Task 1).
- The attempt has no outer polyline, or its vertices carry bulges: extents are `None` or taken from vertices only, never a crash (Task 1).
- After a crash/resume the conversation history comes back from JSON: `attempt_log` must give the same answer on a JSON round-trip (Task 1).
- Another code in the same job has no closed arithmetic: its VIEWS_ONLY is untouched (Task 2).

## File Structure

- Create `LuanAppTools/cad/closure.py`: pure functions and `ClosureContext` (Task 1).
- Create `LuanAppTools/tests/test_closure.py`, `test_views_only_admission.py`, `test_inventory_owner.py`, `test_blocker.py`, `test_weld_pair_replay.py` and `tests/fixtures/weld_pair.json`.
- Modify `LuanAppTools/ai/tools.py` (`HostTools`), `LuanAppTools/cad/pipeline.py` (`_interact`, `run`, `interaction_schema`, `validate_inventory`), `LuanAppTools/cad/contract.py` (`BLOCKER_CLASSES`, `PART_PROPERTIES`, `split_blocker`, `HOST_BLOCKER_NOTE`), `LuanAppTools/tests/test_views_only_gate.py` (its `NotedRunner`).

---

### Task 1: Closure and admission logic (pure)

**Files:**
- Create: `LuanAppTools/cad/closure.py`
- Test: `LuanAppTools/tests/test_closure.py`

**Interfaces:**
- Produces (all in `LuanAppTools/cad/closure.py`):
  - `TOLERANCE = 0.005`, `EXTENT_TOLERANCE = 0.011`
  - `@dataclass(frozen=True) Equation(note_id: str, text: str, positive: tuple[float, ...], negative: tuple[float, ...], result: float)`
  - `@dataclass(frozen=True) ClosedEquation(equation: Equation, matches: tuple[str, ...])`
  - `@dataclass(frozen=True) Attempt(failed: bool, gate: str | None, extents: tuple[float, float] | None)`
  - `class ViewsOnlyRejected(ValueError)`
  - `parse_equations(note_id: str, text: str) -> list[Equation]` (only equations whose arithmetic holds within `TOLERANCE`)
  - `match_terms(positive: Sequence[float], dimensions: Sequence[float], thickness: float | None) -> tuple[str, ...] | None` (`None` when any term fails)
  - `closed_equations(notes: Sequence[dict], views: Sequence[dict], thickness: float | None) -> list[ClosedEquation]` (notes carry `id`, `text`; views carry optional `dimensions`; dimensions of all given views are pooled)
  - `attempt_log(history: Sequence[dict]) -> list[Attempt]` (history entries are `{"request": {"name", "arguments"}, "result": {...}}`; one `Attempt` per `validate` call whose part status is not `VIEWS_ONLY`)
  - `admit_views_only(part: dict, closed: Sequence[ClosedEquation], attempts: Sequence[Attempt]) -> None` (raises `ViewsOnlyRejected`)
  - `@dataclass(frozen=True) ClosureContext(notes: tuple[dict, ...], views: tuple[dict, ...])` with `admit(self, part: dict, history: Sequence[dict]) -> None`

- [ ] **Step 1: Write the failing tests** in `LuanAppTools/tests/test_closure.py`:

```python
DIMS_056152 = [155, 50, 6, 22, 70, 3, 38, 25, 30, 10, 15, 65, 88, 33]
NOTE = {"id": "N7", "text": "Handwritten '161+41\u22129.78=192.22' and '73+71-9.78=134.22'"}

def test_parse_two_equations_unicode_minus():
    eqs = parse_equations("N7", NOTE["text"])
    assert [(e.positive, e.negative, e.result) for e in eqs] == [
        ((161.0, 41.0), (9.78,), 192.22), ((73.0, 71.0), (9.78,), 134.22)]

def test_wrong_arithmetic_is_dropped():
    assert parse_equations("n", "161+41-9.78=192.23") == []

def test_terms_close_by_pair_sum_and_thickness():
    assert match_terms([161, 41, 73, 71], DIMS_056152, 6) == ("161=155+6", "41=38+3", "73=70+3", "71=65+6")
    assert match_terms([161, 999], DIMS_056152, 6) is None
    assert match_terms([161], [155], 6) == ("161=155+t",)
    assert match_terms([161], [155], None) is None          # no thickness: no +-t matching

def test_closed_equations_need_every_term():
    two = closed_equations([NOTE], [{"dimensions": DIMS_056152}], 6)
    assert [c.equation.result for c in two] == [192.22, 134.22]
    assert two[0].matches == ("161=155+6", "41=38+3")
    assert closed_equations([NOTE], [{"dimensions": [155, 6]}], 6) == []
    assert closed_equations([NOTE], [{"id": "v"}], 6) == []          # view without "dimensions"

def outer(width, height, bulge=0):
    return {"entity_id": "E", "type": "LWPOLYLINE", "role": "outer", "closed": True,
            "vertices": [[0, 0, 0], [width, 0, bulge], [width, height, 0], [0, height, 0]]}

def validate_entry(status, entities, result):
    return {"request": {"name": "validate", "arguments": {"part": {"status": status, "entities": entities}}},
            "result": result}

def test_attempt_log_names_the_gate_and_extents():
    history = [
        validate_entry("PASS", [outer(192.22, 134.22)], {"error": "x", "gates": [{"gate": "tools/canonical_contract.py:331"}]}),
        validate_entry("PASS", [outer(1, 2)], {"error": "canonical: WITNESS_REQUIRED_FEATURE_MISSING:['M']"}),
        validate_entry("PASS", [outer(1, 2)], {"error": "oops"}),
        validate_entry("PASS", [outer(3, 4)], {"parts": []}),
        validate_entry("VIEWS_ONLY", [outer(5, 6)], {"error": "A_B_C"}),
        validate_entry("PASS", [{"type": "CIRCLE", "role": "hole"}], {"error": "A_B_C"}),
        validate_entry("PASS", [outer(7, 8, bulge=0.4)], {"error": "A_B_C"}),
        {"request": {"name": "crop", "arguments": {}}, "result": {}},
    ]
    assert attempt_log(history) == [
        Attempt(True, "tools/canonical_contract.py:331", (192.22, 134.22)),
        Attempt(True, "WITNESS_REQUIRED_FEATURE_MISSING", (1.0, 2.0)),
        Attempt(True, None, (1.0, 2.0)),                       # unnamed failure does not unlock
        Attempt(False, None, (3.0, 4.0)),                      # validate passed
        Attempt(True, "A_B_C", None),                          # no outer polyline
        Attempt(True, "A_B_C", (7.0, 8.0)),                    # extents from vertices only
    ]                                                          # VIEWS_ONLY validate and non-validate calls are skipped
    assert attempt_log(json.loads(json.dumps(history))) == attempt_log(history)

def test_admit_views_only():
    closed = closed_equations([NOTE], [{"dimensions": DIMS_056152}], 6)
    views_only = {"status": "VIEWS_ONLY", "thickness_mm": 6}
    with pytest.raises(ViewsOnlyRejected, match=r"VIEWS_ONLY_ADMISSION.*161=155\+6.*192\.22.*HOLISTIC_ENGINEERING_CHALLENGE"):
        admit_views_only(views_only, closed, [])
    admit_views_only(views_only, closed, [Attempt(True, "WITNESS_REQUIRED_FEATURE_MISSING", (192.22, 134.22))])   # qualifies
    for attempt in (Attempt(True, "G", (100.0, 40.0)),          # extent does not reproduce a result
                    Attempt(True, None, (192.22, 134.22)),      # unnamed failure
                    Attempt(False, None, (192.22, 134.22))):    # passed validate: model should have answered PASS/PREVIEW
        with pytest.raises(ViewsOnlyRejected):
            admit_views_only(views_only, closed, [attempt])
    admit_views_only({"status": "PASS"}, closed, [])             # only VIEWS_ONLY is gated
    admit_views_only(views_only, [], [])                         # nothing closed: accepted as before
```

  Write the `...` bodies out as concrete assertions per the comments; the first two `test_` names above are complete as shown.

- [ ] **Step 2: Run to verify failure:** `LuanAppTools/.venv/Scripts/python.exe -m pytest LuanAppTools/tests/test_closure.py -q` → FAIL (`ModuleNotFoundError: LuanAppTools.cad.closure`).

- [ ] **Step 3: Implement `LuanAppTools/cad/closure.py`.** Reuse `FLAT_ARITHMETIC` from `cad/contract.py` to find each equation in a note's text, then split terms with a sign-aware regex that treats `+`, `-`, `\u2212`, `\u2013` the same. `match_terms` tries, in order per term: direct dimension equal; pair sum of two different dimension entries (`"161=155+6"`); one dimension plus thickness (`"161=155+t"`, skipped when `thickness` is not a positive number). Message strings use `format(x, "g")`. A named gate is the first `gates[i]["gate"]` of the result, else the first token matching `[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){2,}` in `result["error"]`. Extents come from the first entity with `role == "outer"` and `type == "LWPOLYLINE"`, from vertex x/y only. `ViewsOnlyRejected` message must contain `VIEWS_ONLY_ADMISSION`, each closed equation with its matches, `HOLISTIC_ENGINEERING_CHALLENGE §3` and `§7`, and the instruction to validate a flat (PASS, or PREVIEW with a FLAG for what is unproved) before submitting VIEWS_ONLY, or to submit that flat when one already passed validate.

- [ ] **Step 4: Run to verify pass:** same command → all PASS.

- [ ] **Step 5: Commit**

```bash
git add LuanAppTools/cad/closure.py LuanAppTools/tests/test_closure.py
git commit -m "feat(luanapp): closure check and VIEWS_ONLY admission logic"
```

---

### Task 2: Wire the admission gate into the solve stage

**Files:**
- Modify: `LuanAppTools/ai/tools.py` (`HostTools.__init__`, `HostTools.execute`)
- Modify: `LuanAppTools/cad/pipeline.py` (`CadPipeline._interact` tool-call line; `CadPipeline.run` solve branch)
- Test: `LuanAppTools/tests/test_views_only_admission.py`

**Interfaces:**
- Consumes: `ClosureContext`, `ViewsOnlyRejected` from Task 1.
- Produces: `HostTools(..., closure: ClosureContext | None = None)`; `HostTools.execute(call, *, timeout=1200, history=())`. New `PipelineError` kind `"views_only_unproved"`.

- [ ] **Step 0 (preflight):** `git status --short`. If `LuanAppTools/cad/pipeline.py`, `cad/contract.py`, `core/settings.py`, `service/*` or `tests/test_one_conversation.py` show uncommitted changes from the separate one-conversation feature, stop and ask the user whether to commit them first. Do not mix them into this plan's commits.

- [ ] **Step 1: Write the failing tests** in `test_views_only_admission.py`. Helpers: `NOTE = {"id": "n_calc", "page_id": "source.pdf:p1", "text": "Handwritten 80+60-9.78=130.22", "codes": ["26-000001"]}`; a runner `TurnRunner(SingleRunner)` whose intake adds `NOTE` and sets `dimensions = [80, 60, 6]` on view `v1`, and whose solve calls first return the scripted `tool_requests` turns in order, then the final `{"part": ..., "evidence_refs": [...]}` (use the pattern of `RepeatingRunner` in `test_validation_stall.py`; vary each turn's `flags` so the identical-request guard does not fire). `views_only_part(record=True, cite=("v1","n_calc"))` comes from `test_views_only_gate.py`; `flat_attempt(width)` is `synthetic_part(hole=True)` with the outer polyline widened to `width` (fails `WITNESS_REQUIRED_FEATURE_MISSING`).
  - `test_views_only_is_rejected_until_a_flat_was_attempted`: turns = `[validate(views_only), validate(flat_attempt(130.22)), validate(views_only)]`, final answer `views_only`. Assert the tool result after turn 1 has `"VIEWS_ONLY_ADMISSION"` in its `error`; the result after turn 3 has no `error` mentioning it; `result.parts[0].status == "VIEWS_ONLY"`.
  - `test_attempt_that_does_not_reproduce_the_result_does_not_unlock`: turns use `flat_attempt(100.0)`; the second `validate(views_only)` result still contains `VIEWS_ONLY_ADMISSION`.
  - `test_skipping_validate_is_caught_on_the_final_answer`: no tool turns, final answer `views_only`; `pytest.raises(PipelineError, match="Some codes have no")`; every issue in the checkpoint contains `VIEWS_ONLY_ADMISSION`; two attempts were consumed (`control.store.attempts(...) == 2`).
  - `test_unclosed_arithmetic_keeps_todays_behaviour`: same runner with `dimensions = []`, final answer `views_only_part(record=True, cite=("v1","n_calc"))` → accepted as VIEWS_ONLY.
  - `test_other_code_is_untouched` (Review Focus): two codes, `NOTE` owned only by `26-000001`; `26-000002` returns a VIEWS_ONLY part with the full record → accepted.
  - `test_non_single_agent_mode_is_untouched`: wrap `HostTools.__init__` (monkeypatch) to record the `closure` keyword of every instance; run `CadPipeline(repo, ScriptedRunner({"26-000001": synthetic_part()}))` (no `single_agent`); assert every recorded `closure` is `None`.

- [ ] **Step 2: Run to verify failure:** `... -m pytest LuanAppTools/tests/test_views_only_admission.py -q` → FAIL.

- [ ] **Step 3: Implement.**
  - `HostTools.__init__` gains `closure=None`; `execute` gains `history=()` and forwards it to the validate branch; the validate branch calls `self.closure.admit(args["part"], history)` when `closure` is set, right after the existing check that `args["part"]` is a dict and before `prepare_part`.
  - `_interact`: change the call to `tools.execute(call, timeout=remaining, history=history)`. The existing `except (ValueError, ...)` branch already turns `ViewsOnlyRejected` into a `validate` error with the stall counter.
  - `run()` solve branch: when `self.single_agent`, build `closure = ClosureContext(notes=tuple(code_notes), views=tuple(v for v in inventory["views"] if v["id"] in code["view_ids"]))`, pass it to the solve-stage `HostTools`, and right after `answer = await self._interact("solve", ...)` call `closure.admit(answer["part"], state.get("interaction", {}).get("history", []))`, converting `ViewsOnlyRejected` to `PipelineError("views_only_unproved", str(exc))`.

- [ ] **Step 4: Run to verify pass:** the new file, then `... -m pytest LuanAppTools/tests -q --deselect LuanAppTools/tests/test_runners.py::test_cancel_terminates_provider_process` → all PASS (fix any fake that rejects the new `history` kwarg by accepting `**kwargs`).

- [ ] **Step 5: Commit**

```bash
git add LuanAppTools/ai/tools.py LuanAppTools/cad/pipeline.py LuanAppTools/tests/test_views_only_admission.py
git commit -m "feat(luanapp): refuse VIEWS_ONLY until a flat was attempted and failed a named gate"
```

---

### Task 3: Intake dimensions and arithmetic-note owners

**Files:**
- Modify: `LuanAppTools/cad/pipeline.py` (`interaction_schema` single-agent `views` shape; intake `full_task` text; `validate_inventory`)
- Modify: `LuanAppTools/tests/test_views_only_gate.py` (`NotedRunner`)
- Test: `LuanAppTools/tests/test_inventory_owner.py`

**Interfaces:**
- Consumes: `FLAT_ARITHMETIC` from `cad/contract.py`.
- Produces: single-agent intake views accept `dimensions: list[number]`; `validate_inventory(..., require_difficulty=False)` rejects (as `PipelineError("inventory_invalid", ...)`) a flat-arithmetic note with empty `codes` ("needs an owning code") and, when such a note exists, any view with `codes` lacking the `dimensions` key ("printed dimensions").

- [ ] **Step 1: Write the failing tests** in `test_inventory_owner.py` (build `evidence` with `types.SimpleNamespace(pages=[{"id": "p1"}], dxf=[])` and a minimal valid inventory for one code `26-000001`):
  - `test_flat_arithmetic_note_without_owner_is_rejected`: note `"80+60-9.78=130.22"`, `codes: []`, with a `disposition` → `pytest.raises(PipelineError, match="owning code")`.
  - `test_views_need_dimensions_when_arithmetic_exists`: owned note, view without `dimensions` → `match="printed dimensions"`; same view with `dimensions: []` → returns the inventory.
  - `test_plain_unscoped_note_is_still_allowed`: note `"2-M8"`, `codes: []`, `disposition` set, no arithmetic → accepted (today's behaviour).
  - `test_multi_agent_intake_is_unaffected`: `require_difficulty=True` ignores both new rules.
  - `test_intake_schema_documents_dimensions`: `interaction_schema("intake", single_agent=True)["properties"]["views"]["items"]["properties"]["dimensions"]` is an array of numbers and `"dimensions"` is not in that item's `required`.
  - `test_ownerless_note_is_repaired_in_the_same_conversation`: pipeline-level, modelled on `test_invalid_inventory_shape_is_corrected_in_same_conversation` in `test_single_agent.py`; first intake answer has the ownerless note, the repair turn fixes it; the run proceeds.

- [ ] **Step 2: Run to verify failure:** `... -m pytest LuanAppTools/tests/test_inventory_owner.py -q` → FAIL.

- [ ] **Step 3: Implement** the schema property, one sentence in the intake task text ("For every view also return `dimensions`: the numeric dimension values printed on that view, empty when it has none"), and the two checks inside `validate_inventory`'s `try` block, applied only when `require_difficulty` is false. Update `NotedRunner` in `test_views_only_gate.py` so its intake sets `dimensions = []` on every view and keeps `NOTE`'s `codes`.

- [ ] **Step 4: Run to verify pass:** the new file, then `... -m pytest LuanAppTools/tests -q --deselect LuanAppTools/tests/test_runners.py::test_cancel_terminates_provider_process` → all PASS. Note in the commit message that `INTAKE_CACHE_VERSION` changes, so stored inventories are not reused.

- [ ] **Step 5: Commit**

```bash
git add LuanAppTools/cad/pipeline.py LuanAppTools/tests/test_inventory_owner.py LuanAppTools/tests/test_views_only_gate.py
git commit -m "feat(luanapp): record printed dimensions per view and require an owner for flat arithmetic notes"
```

---

### Task 4: Structured blocker record

**Files:**
- Modify: `LuanAppTools/cad/contract.py`, `LuanAppTools/cad/pipeline.py` (`run`), `LuanAppTools/ai/tools.py` (validate branch)
- Test: `LuanAppTools/tests/test_blocker.py`

**Interfaces:**
- Produces in `cad/contract.py`: `BLOCKER_CLASSES: list[str]` = `TRUE_SOURCE_AMBIGUITY, AI_INTERPRETATION_GAP, SOURCE_MEMBER_CENSUS_GAP, PART_IDENTITY_GAP, GEOMETRY_DECODE_GAP, ROUTING_COVERAGE_GAP, CUSTOMER_CONFIRMATION_PENDING` (the seven classes of `HOLISTIC_ENGINEERING_CHALLENGE` §5); `PART_PROPERTIES["blocker"]` (object with `class` enum, `rule` string, optional `evidence` string; `class` and `rule` required); `split_blocker(part: dict) -> tuple[dict, dict | None]` (copy without `blocker`, and the blocker); `HOST_BLOCKER_NOTE: str`. `HOST_VIEWS_ONLY_NOTE` must not change (its test checks that every key it names exists in the repository guard).
- Event: `{"kind": "blocker_recorded", "code": <code>, "blocker": {...}}`; checkpoint `parts[code]["blocker"]`. The dashboard timeline (`frontend/src/App.tsx`) already prints every event kind with its payload, so no frontend change is needed.

- [ ] **Step 1: Write the failing tests** in `test_blocker.py`:
  - `test_split_blocker_removes_the_host_key_and_keeps_the_rest`.
  - `test_schema_offers_the_blocker_classes`: `solve_part_schema(...)["properties"]["blocker"]["properties"]["class"]["enum"] == BLOCKER_CLASSES`; `tests/test_contract.py` stays green (extra schema keys are allowed).
  - `test_pipeline_records_blocker_and_keeps_it_out_of_the_export`: a scripted part with `blocker = {"class": "PART_IDENTITY_GAP", "rule": "references/PART_IDENTITY_GRAPH.md", "evidence": "N6"}` completes; the events contain one `blocker_recorded` for the code with that payload; `parts[code]["blocker"]` is stored; the `canonical.json` written under `control.workspace / "aggregate"` has no `blocker` key.
  - `test_solve_prompt_asks_for_a_blocker_when_the_part_is_not_pass`: `"blocker"` and `"HOLISTIC"` appear in the solve request prompt.

- [ ] **Step 2: Run to verify failure.**

- [ ] **Step 3: Implement.** Append `HOST_BLOCKER_NOTE` to the solve `full_task` next to `HOST_VIEWS_ONLY_NOTE`. In `run()`, call `split_blocker` on `answer["part"]` before `prepare_part`; store and emit the blocker when present; the validate branch of `HostTools` also strips it before `prepare_part`.

- [ ] **Step 4: Run to verify pass:** new file, `LuanAppTools/tests/test_contract.py`, then the full `LuanAppTools/tests` command from Task 2 → all PASS.

- [ ] **Step 5: Commit**

```bash
git add LuanAppTools/cad/contract.py LuanAppTools/cad/pipeline.py LuanAppTools/ai/tools.py LuanAppTools/tests/test_blocker.py
git commit -m "feat(luanapp): structured blocker record for unresolved parts"
```

---

### Task 5: Replay of the recorded weld-pair run and full verification

**Files:**
- Create: `LuanAppTools/tests/fixtures/weld_pair.json`, `LuanAppTools/tests/test_weld_pair_replay.py`

**Interfaces:**
- Consumes: `ClosureContext`, `ViewsOnlyRejected` (Task 1).

- [ ] **Step 1: Write the fixture and failing test.** `weld_pair.json` holds, from run `48cf0b85`: the note text `161+41-9.78=192.22 ; 73+71-9.78=134.22` with `codes: ["26-056152"]`; the 056152 views `V2_TL` `[38,3,25,25,30,10,15,65,6]`, `V2_TR` `[155,50,6,22,70,3,6]`, `V2_BL` `[88,33,30,25,38]`; `thickness_mm: 6`; the recorded candidate skeleton (`status: VIEWS_ONLY`, `preview_reason`, `source_exhausted`, `holistic_challenge_run`, `flat_attempted` true, three `face_graph_candidates` whose `constraint_result` starts `UNPROVED`/`FAIL`) with flags reduced to neutral text; and the 056159 control note `80+60-9.78=130.22` with view `V3_SIDE` `[80,60,6]`. Tests: `test_recorded_056152_candidate_is_rejected` (`ClosureContext.admit(candidate, [])` raises with `192.22` and `134.22` in the message); `test_056159_control_closes_but_is_not_gated_when_not_views_only`; `test_recorded_candidate_passes_after_a_matching_failed_attempt` (history with a failed named validate whose outer extent is `192.22 × 134.22`).

- [ ] **Step 2: Run:** `... -m pytest LuanAppTools/tests/test_weld_pair_replay.py -q`. The tests should pass immediately because the code exists; if the first one fails, the gate does not reproduce the recorded decision and Tasks 1–2 need fixing before anything else.

- [ ] **Step 3: Full verification.** Run `... -m pytest tests LuanAppTools/tests -q --deselect LuanAppTools/tests/test_runners.py::test_cancel_terminates_provider_process`. Expected: all PASS (the deselected test fails on `main` as well). `git status --short` must list nothing under `tools/`, `skills/` or `references/`.

- [ ] **Step 4: Commit**

```bash
git add LuanAppTools/tests/fixtures/weld_pair.json LuanAppTools/tests/test_weld_pair_replay.py
git commit -m "test(luanapp): replay the recorded weld-pair VIEWS_ONLY decision through the admission gate"
```

- [ ] **Step 5: Report to the user** the test counts and that no real run was made. Ask for permission before any real run of `520925-07`; if given, the acceptance check is spec §2 item 3 (056152 ends with a flat and a local FLAG; score with `bench/score_dxf.py`; compare cost with run `48cf0b85`: 14.7 minutes, about 57k output tokens).
