"""Owner/stage contracts for the approved consolidation; no source-PDF certification."""
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from resolve_rules import resolve_rules

DATA = 'references/DATA_RAW_TO_MANUFACTURING_CONTRACT.md'
RELIEF = 'skills/lispcad/features/SLIT_RELIEF.md'
ACUTE = 'references/ACUTE_BEND_LT85_FROM_SOURCE.md'


def census(mode='FLAT_NO_BEND', source='PDF_ONLY', **selected):
    router = yaml.safe_load((ROOT / 'skills/lispcad/router/ROUTER.yaml').read_text(encoding="utf-8"))
    return {'source_mode': source, 'part_mode': mode, 'reference_present': 'NO',
            'multi_code_or_assembly': 'NO',
            'features': {name: selected.get(name, 'NO') for name in router['feature_routes']}}


@pytest.mark.parametrize('mode', ['BEND', 'MULTI_FACE', 'UNKNOWN'])
def test_bend_rechecks_relief_before_false_negative_census(mode):
    # Before consolidation this construction was inline in BEND_UNFOLD.
    # Moving it cannot let an early NO silently remove bend-junction inspection.
    plan = resolve_rules(census(mode))
    assert RELIEF in plan['stage_plans']['L2_GEOMETRY']['rule_paths']
    assert 'bend_end_offset_relief_90' in plan['post_route_checks']


def test_flat_does_not_preload_bend_or_data_but_custom_slit_still_routes():
    plan = resolve_rules(census())
    assert RELIEF not in plan['rule_paths'] and DATA not in plan['rule_paths']
    assert RELIEF in resolve_rules(census(SLIT_RELIEF='YES'))['rule_paths']


def test_data_owner_is_scoped_and_all_stages_are_mandatory():
    plan = resolve_rules(census(source='PDF_DATA_RAW'))
    assert DATA in plan['stage_plans']['L1_SOURCE_CENSUS']['rule_paths']
    assert plan['rule_paths'].count(DATA) == 1
    assert list(plan['stage_plans']) == ['L0_BOOTSTRAP', 'L1_SOURCE_CENSUS',
                                        'L2_GEOMETRY', 'L3_VALIDATE_EXPORT_QA']
    assert not any('/history/' in p or p.startswith('regression/') for p in plan['rule_paths'])


@pytest.mark.parametrize('state', ['YES', 'UNKNOWN'])
def test_acute_implementation_owner_keeps_bend_dependencies(state):
    plan = resolve_rules(census(ACUTE_BEND_LT85=state))
    assert ACUTE in plan['rule_paths']
    assert RELIEF in plan['rule_paths']
    assert 'references/FACE_GRAPH_UNFOLD_PROTOCOL.md' in plan['rule_paths']


def test_route_load_lists_have_no_repeated_path():
    r = yaml.safe_load((ROOT / 'skills/lispcad/router/ROUTER.yaml').read_text(encoding="utf-8"))
    for group in ('stage_routes', 'source_routes', 'mode_routes', 'feature_routes', 'customer_routes'):
        for name, route in r[group].items():
            assert len(route['load']) == len(set(route['load'])), (group, name)


def test_template_changes_trigger_both_production_events():
    # YAML 1.1 interprets unquoted 'on' as True.
    wf = yaml.safe_load((ROOT / '.github/workflows/dxf-export-tests.yml').read_text(encoding="utf-8"))
    events = wf.get('on', wf.get(True))
    for event in ('push', 'pull_request'):
        assert 'templates/**' in events[event]['paths']


def test_material_sharp_conflict_and_inner_hole_scope_share_one_decision_table():
    text = (ROOT / 'references/MATERIAL_RULES.md').read_text(encoding="utf-8")
    decision = text.split('## SS t>=19 R3 scope and explicit-corner decisions', 1)[1].split('\n## ', 1)[0]
    assert 'Explicit customer sharp/pin-corner' in decision
    assert 'FLAG and obtain customer confirmation' in decision
    assert 'Inner hole, slot or void contour' in decision
    assert 'No automatic R3' in decision
