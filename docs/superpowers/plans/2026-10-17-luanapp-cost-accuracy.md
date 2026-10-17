# LuanAppTools cost/accuracy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native execution, chosen by the user's "duyệt làm đi toàn bộ e2e"). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make a LuanAppTools run on job `520925-07` cheaper, faster and checkable against the reference DXF, without changing production rules.

**Architecture:** App-side changes only: a DXF scorer and metrics tool; a host output contract (schema, exporter-gate advice, VIEWS_ONLY record gate, stalled-validation stop); rules moved into an appended system prompt for cross-session cache sharing; `customer_code` and KH851 weld census passed to the resolver.

**Tech Stack:** Python 3.12, ezdxf 1.4, pytest, FastAPI app already in `LuanAppTools/`, Claude Code CLI 2.1.301.

**Spec:** `docs/superpowers/specs/2026-10-17-luanapp-cost-accuracy-design.md`

## Global Constraints

- Do not edit anything under `skills/`, `references/`, `tools/`, `templates/`, `AI_*.md` (AGENTS.md §5).
- Local branch `codex/luanapp-cost-accuracy-20261017` only; no push, no merge.
- Reference DXF is read only by the scorer; never copied into a job folder or state directory.
- Scorer tolerance default `0.01` mm, strict `<`; cluster gap default `50.0` mm; ordering top to bottom by descending cluster centre Y.
- Failed-validation stop kind is `validation_stalled` (must NOT be in the set that aborts the whole job); stall threshold is the 3rd identical error.
- Test runs: `python -m pytest tests LuanAppTools/tests -q --deselect LuanAppTools/tests/test_runners.py::test_cancel_terminates_provider_process`.

## Review Focus

- A one-code job: scorer pairing, shared context and metrics must not assume two or more codes.
- Result or reference DXF containing POINT, TEXT, LWPOLYLINE or INSERT: ignored/exploded, never crash the scorer.
- An error text no gate matches: `advise` returns `[]` and the original error still reaches the model.
- Resume after the first turn: shared rules are not resent and the session is reused.
- Claude CLI older than 2.1.301: rules fall back into the prompt, run still works.
- Job folder or state path with spaces/non-ASCII: shared-context file is written and passed correctly.

---

### Task 1: DXF scorer

**Files:** Create `LuanAppTools/bench/__init__.py`, `LuanAppTools/bench/score_dxf.py`; Test `LuanAppTools/tests/test_score_dxf.py`.

**Interfaces:**
- Produces: `score(result: Path, reference: Path, *, tol: float = 0.01, gap: float = 50.0) -> dict` with `parts` (list of `{index, status, recall, precision, rotation, translation, max_deviation, circles:{reference,matched}, missing, extra}`), `unmatched_reference`, `unmatched_result`, `summary`. `status` is `MATCH` (recall and precision >= 0.999 and all circles matched), `PARTIAL` (recall >= 0.5), else `DIFF`. CLI: `python -m LuanAppTools.bench.score_dxf RESULT REFERENCE [--tol] [--gap] [--json]`.

- [ ] **Step 1: tests (ezdxf-built fixtures, literal numbers).** `test_identical_translated_rotated_part_is_match` (200x100 rectangle + Ø10 circle at (50,50); result = same rotated 90° and moved +500 in Y; assert one part, `MATCH`, `rotation == 90`); `test_dimension_off_by_point_two_is_not_match` (circle moved 0.2: status != `MATCH`, `levels["0.1"]` recall < `levels["1"]` recall... assert recall at tol 1 is 1.0 and at 0.01 < 1.0); `test_top_to_bottom_pairing_skips_extra_reference_cluster` (reference: A top, small gusset middle, B bottom; result: A, B; assert two parts MATCH and one `unmatched_reference`); `test_text_meta_layer_and_polyline_are_handled` (AI_META TEXT ignored; closed LWPOLYLINE with bulge equals the exploded LINE/ARC reference); `test_single_part_job`; `test_bend_dashed_and_kegaki_red_are_compared_by_category` (same geometry as CUT vs DASHED reports missing+extra).
- [ ] **Step 2: run, expect FAIL (module missing).**
- [ ] **Step 3: implement** per spec §4 WP0: primitives (LINE/ARC/CIRCLE/POINT) with category from linetype/color; cluster LINE/ARC by bbox expanded `gap/2`, circles join the cluster containing their centre; order-preserving alignment (DP) over cluster pairs maximising matched length; per pair try rotations 0/90/180/270 with translation by voting over key points; merge collinear LINEs and same-circle ARCs; length-overlap matching with `tol`.
- [ ] **Step 4: run tests, expect PASS.**
- [ ] **Step 5: commit** `feat(bench): DXF scorer against a reference`.

### Task 2: Run metrics

**Files:** Create `LuanAppTools/bench/run_metrics.py`; Test `LuanAppTools/tests/test_run_metrics.py`.

**Interfaces:**
- Produces: `summarize(db_path: Path, run_id: str | None = None) -> dict` with `wall_seconds`, `calls`, `by_stage_code` (calls, cache_creation, cache_read, output_tokens, prompt_characters, shared_context_characters), `totals`, `repeated_errors`. CLI prints a table.

- [ ] **Step 1: test** using `Store` (`append_event` of `request_prepared`/`usage`/`part_complete`): one-code run asserts per-code call count and token sums; run with no events returns zero totals.
- [ ] **Step 2: run, expect FAIL.** **Step 3: implement** reading the `events` table (kind, payload JSON, created). **Step 4: PASS.** **Step 5: commit** `feat(bench): per-run cost metrics`.

### Task 3: Host output contract

**Files:** Create `LuanAppTools/cad/contract.py`; Modify `LuanAppTools/cad/pipeline.py` (solve schema block ~lines 638-672), `LuanAppTools/cad/repository.py` (add `contract_notes`); Test `LuanAppTools/tests/test_contract.py`.

**Interfaces:**
- Produces: `solve_part_schema(check_names: list[str], code: str) -> dict`; `PinnedRepository.contract_notes() -> str` (the "## Input JSON" section of `tools/DXF_INPUT_SCHEMA.md`, whole file if the heading is missing).

- [ ] **Step 1: tests.** `test_schema_documents_views_only_fields` (properties include `preview_reason`, `unresolved_record`; entity properties include `view_id`, `center`, `radius`, `color`, `linetype`); `test_schema_covers_exporter_keys` (AST-collect string keys of `part.get(...)`/`part[...]` in `tools/export_dxf.py` and `tools/canonical_contract.py` and `ent`/`entity` likewise; each must be in the schema or in `INTERNAL_KEYS`); `test_contract_notes_mention_preview_reason_and_view_id`.
- [ ] **Step 2: run, expect FAIL.** **Step 3: implement** and replace the inline schema with `solve_part_schema`. **Step 4: PASS.** **Step 5: commit** `feat(luanapp): complete host output contract`.

### Task 4: Exporter gate advice

**Files:** Create `LuanAppTools/cad/gates.py`; Modify `LuanAppTools/ai/tools.py` (validate result), `LuanAppTools/cad/pipeline.py` (tool error branch ~line 881 and attempt `issues`); Test `LuanAppTools/tests/test_gates.py`.

**Interfaces:**
- Produces: `GateIndex.from_sources(sources: dict[str, str]) -> GateIndex`; `GateIndex.advise(error: str) -> list[dict]` items `{"gate": "<file>:<line>", "fires_when": "<condition>"}`; `summarize_error(error: str) -> str` (last traceback line).

- [ ] **Step 1: tests.** `test_views_only_error_names_preview_reason` (error `export: 26-056152: VIEWS_ONLY requires independently proved source views, reason and unresolved flags` over the real snapshot sources: `fires_when` contains `preview_reason` and `separate_source_views`); `test_canonical_error_is_indexed`; `test_unknown_error_returns_empty_list`; `test_pipeline_tool_error_carries_gates` (scripted runner sends a bad VIEWS_ONLY part to `validate`; the next prompt's `tool_results` contains `gates`).
- [ ] **Step 2-4: fail, implement (AST over `fail(...)`/`CanonicalContractError(...)` calls, regex from f-string constants, enclosing `ast.If.test` via `ast.unparse`), pass.** **Step 5: commit** `feat(luanapp): tell the model which exporter gate fired`.

### Task 5: Stalled validation stop

**Files:** Modify `LuanAppTools/cad/pipeline.py` (`_interact` tool loop); Test `LuanAppTools/tests/test_single_agent.py`.

**Interfaces:** Consumes Task 4 `summarize_error`. Produces `PipelineError(kind="validation_stalled")`.

- [ ] **Step 1: tests.** `test_third_identical_validation_error_ends_the_attempt_not_the_job` (code A repeats one error; assert attempt consumed, code B still attempted, kind not re-raised); `test_second_identical_error_adds_instruction` (second tool result contains `repeated`).
- [ ] **Step 2-4: fail, implement (count normalized error signatures in `state["interaction"]`), pass.** **Step 5: commit** `feat(luanapp): stop guessing after identical validation errors`.

### Task 6: VIEWS_ONLY record gate

**Files:** Modify `LuanAppTools/cad/contract.py`, `LuanAppTools/ai/tools.py`, `LuanAppTools/cad/pipeline.py`; Test `LuanAppTools/tests/test_views_only_gate.py`.

**Interfaces:**
- Produces: `FLAT_ARITHMETIC` regex, `flat_arithmetic_note_ids(notes: list[dict]) -> list[str]`, `check_views_only_record(part: dict, notes: list[dict]) -> None` raising `ContractError(ValueError)`; `HostTools` gets `notes` (the code's inventory notes).

- [ ] **Step 1: tests.** `test_views_only_without_record_is_rejected`; `test_record_must_cite_flat_arithmetic_note` (note text `Handwritten 80+60-9.78=130.22`, id `n_calc`; record lacking it fails, record with it passes); `test_blocker_class_vocabulary`; `test_non_views_only_part_is_not_checked`.
- [ ] **Step 2-4: fail, implement, pass.** **Step 5: commit** `feat(luanapp): require an unresolved record before VIEWS_ONLY`.

### Task 7: Shared system context

**Files:** Modify `LuanAppTools/ai/protocol.py` (`AIRequest.shared_context`), `LuanAppTools/ai/claude.py` (`argv`, `complete`), `LuanAppTools/cad/pipeline.py` (single_agent prompt build ~lines 679-715); Test `LuanAppTools/tests/test_shared_context.py`, extend `LuanAppTools/tests/test_runners.py`.

**Interfaces:**
- Produces: `AIRequest.shared_context: str = ""`; runner attribute `supports_shared_context: bool`; Claude flag `--append-system-prompt-file <workspace>/prompts/shared-<sha256[:16]>.txt`.

- [ ] **Step 1: tests.** `test_first_turn_rules_go_to_shared_context` (fake runner with `supports_shared_context = True`: request 1 `shared_context` contains `FILE AI_BOOTSTRAP.md`, `prompt` does not); `test_same_route_codes_share_identical_context` (two codes, equal `shared_context`); `test_resume_turn_does_not_resend_rules`; `test_runner_without_support_keeps_inline_rules`; in test_runners: `test_claude_argv_uses_append_system_prompt_file` (path with spaces and non-ASCII), `test_old_cli_falls_back_to_prompt`.
- [ ] **Step 2-4: fail, implement (hash-named UTF-8 file; version >= 2.1.301 else prepend to prompt), pass.** **Step 5: commit** `feat(luanapp): share rules across sessions via appended system prompt`.

### Task 8: customer_code and KH851 census

**Files:** Modify `LuanAppTools/cad/pipeline.py` (intake schema, `normalize_inventory`, `run`, `_job`), `LuanAppTools/cad/repository.py` (intake rules add `references/WELD_SITE_KEGAKI_CLOSURE.md`); Test `LuanAppTools/tests/test_customer_code.py`.

**Interfaces:**
- Produces: intake field `customer_code: str | None` (+ `customer_code_evidence`); census keys `customer_code`, `part_code`, `source_assembly_view_ids`, `source_weld_site_ids`, `weld_site_census` filled by host; job JSON key `customer_code`.

- [ ] **Step 1: tests.** `test_customer_code_reaches_resolver_and_job` (non-851 code `646`: resolver census has it; job JSON has `customer_code == "646"`); `test_non_numeric_customer_code_is_rejected_at_intake`; `test_kh851_requires_weld_census_and_repairs_once` (first intake lacks census → repair turn in the same session; second passes); `test_no_customer_code_keeps_current_behaviour`.
- [ ] **Step 2-4: fail, implement, pass.** **Step 5: commit** `feat(luanapp): carry customer_code and the KH851 weld census`.

### Task 9: Verify and run end to end

**Files:** none new; Create `docs/superpowers/plans/2026-10-17-e2e-report.md` with measured results.

- [ ] **Step 1:** run the full suite (Global Constraints command); expect all pass.
- [ ] **Step 2:** start the backend on a fresh data dir with root `F:\AI\Train_AI_CAD\practice\data-train`, start job `520925-07`, watch with the budget valve (cache read > 1.5M tokens or > 25 min cancels).
- [ ] **Step 3:** `python -m LuanAppTools.bench.score_dxf <job>\520925-07_ALL*.dxf <reference>` and `python -m LuanAppTools.bench.run_metrics <state>\state.sqlite`.
- [ ] **Step 4:** write the report (per-code status, cost, what failed) and commit locally.
