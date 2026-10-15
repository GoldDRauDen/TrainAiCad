"""Run identical synthetic exports/routes against one selected checkout.

Usage: python regression/tools/compare_rule_consolidation.py CHECKOUT OUTPUT_DIR
Run separately for the baseline and candidate, then compare summary.json/routes.json.
OUTPUT_DIR should be a fresh directory outside either checkout. Fixture definitions
come from CHECKOUT/tests; this is maintenance parity evidence, not source PDF QA.
"""
from pathlib import Path
import sys,runpy,json,copy,hashlib
if len(sys.argv) != 3:
    raise SystemExit("usage: compare_rule_consolidation.py CHECKOUT OUTPUT_DIR")
root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
if out.is_relative_to(root):
    raise SystemExit("OUTPUT_DIR must be outside the selected checkout")
if out.exists() and any(out.iterdir()):
    raise SystemExit("OUTPUT_DIR must be fresh/empty to avoid stale DXF comparisons")
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0,str(root/'tools'))
import ezdxf,yaml
from export_dxf import entity_signature,export_job
from resolve_rules import resolve_rules,ResolutionError
from export_canonical_dxf import export_canonical_job
from benchmark_rule_routes import benchmark
from snapshot_manifest import load_manifest,snapshot_text
art=runpy.run_path(str(root/'tests/test_export_artifacts.py'))
v=runpy.run_path(str(root/'tests/test_v434_material_witness_slot_orientation.py'))
dx=runpy.run_path(str(root/'tests/test_dx_inner_face_label.py'))
w=runpy.run_path(str(root/'tests/test_weld_kegaki_guard.py'))
r=runpy.run_path(str(root/'tests/test_export_dxf.py'))
# Reuse identical baseline fixture constructors, not parallel manually redrawn geometry.
cases=[]
cases.append(('v431_flat',art['job']([art['part']('A',bent=False)]),{}))
cases.append(('v431_bend_relief_slot',art['job']([art['part']('A')]),{'individual_dxf':True}))
cases.append(('mixed_review',art['job']([art['part']('A'),art['review_part']('R')]),{'individual_dxf':True}))
cases.append(('v434_flat',v['job'](v['model'](), 'TrainAiCad-CANONICAL-V4.34'),{}))
p=v['model'](material='SUS304 HL',grain={'is_hl':True,'direction_xy':[1,0],'evidence_ref':'PDF:grain-arrow'})
cases.append(('v434_hl_proved',v['job'](p,'TrainAiCad-CANONICAL-V4.34'),{'individual_dxf':True}))
p=copy.deepcopy(p);p['grain'].update(direction_xy=None,evidence_ref=None);p.update(status='REVIEW',review_reason='HL_DIRECTION_UNPROVED',flags=['grain unproved'])
cases.append(('v434_hl_review',v['job'](p,'TrainAiCad-CANONICAL-V4.34'),{}))
p1=dx['part']('26-000001',dx['L_SHAPE']);p1['dx_label']=True
p2=dx['part']('26-000002',dx['MIRROR']);p2['dx_label']=False
cases.append(('dx_mirror',art['job']([p1,p2]),{'individual_dxf':True}))
cases.append(('kh851_marks',w['fixture_job'](),{'individual_dxf':True}))
# Canonical POINT member closure; fine-grained V434 stamp rejection stays in main pytest tests.
p=art['part']('P',bent=False,slot=False,relief=False)
for name,color,role in [('ORDINARY',256,'ordinary_point'),('THROUGH',3,'through_piercing')]:
 eid='E_P_'+name;p['entities'].append({'entity_id':eid,'type':'POINT','role':role,'color':color,'point':[10 if color==3 else 5,12]})
 g,c=art['source_group']('P','PIASU',name,[eid]);p['source_groups'].append(g);p['canonical_members'].append(c)
cases.append(('point_v431',art['job']([p]),{}))
result={}
for name,job,opts in cases:
 target=out/name
 manifest=export_canonical_job(copy.deepcopy(job),target,**opts)
 result[name]={'filename':manifest['filename'],'status':manifest['status']}
# Exercise source-view fallback through the existing compatibility test, with its own assertions.
r['test_one_review_only_with_user_authorized_unknown_diameter_and_source_views'](out/'views_only')
for path in sorted(out.rglob('*.dxf')):
 doc=ezdxf.readfile(path);ents=[]
 for e in doc.modelspace():
  tags=[(t.code,t.value) for t in e.get_xdata('TRAINAICAD')] if e.has_xdata('TRAINAICAD') else []
  ents.append({'physical':entity_signature(e),'xdata':tags})
 result[str(path.relative_to(out))]={'units':doc.header['$INSUNITS'],'entities':ents}
router=yaml.safe_load((root/'skills/lispcad/router/ROUTER.yaml').read_text())
redirect={'references/PDF_DATA_RAW_GEOMETRY_PRESERVATION.md':'references/DATA_RAW_TO_MANUFACTURING_CONTRACT.md','references/DATA_PHYSICAL_CENSUS_AND_BIDIRECTIONAL_QA.md':'references/DATA_RAW_TO_MANUFACTURING_CONTRACT.md','references/ACUTE_BEND_LT85_METHOD.md':'references/ACUTE_BEND_LT85_FROM_SOURCE.md'}
routes={}
for source in router['source_routes']:
 for mode in router['mode_routes']:
  for feature in [None,*router['feature_routes']]:
   for state in (['NO'] if feature is None else ['YES','UNKNOWN']):
    c={'source_mode':source,'part_mode':mode,'reference_present':'NO','multi_code_or_assembly':'NO','features':dict.fromkeys(router['feature_routes'],'NO')}
    if feature:c['features'][feature]=state
    for customer in [None,'433','646']:
     c['customer_code']=customer
     key='|'.join(str(v) for v in (source,mode,feature,state,customer))
     p=resolve_rules(c,root)
     # Old inline relief moved to a routed file at L2, so map that semantic owner.
     stages={}
     for stage,data in p['stage_plans'].items():
      paths={redirect.get(x,x) for x in data['rule_paths']}
      if stage=='L2_GEOMETRY' and 'skills/lispcad/modes/BEND_UNFOLD.md' in paths:paths.add('skills/lispcad/features/SLIT_RELIEF.md')
      stages[stage]=sorted(paths)
     routes[key]={'stage_paths':stages,'checks':p['post_route_checks'],'selected':p['selected_features'],'customer_rules':p['customer_rules']}
# Fail-closed removal of a family cannot silently convert UNKNOWN/missing to NO.
bad=copy.deepcopy(c);bad['features'].pop(next(iter(bad['features'])))
try:resolve_rules(bad,root)
except ResolutionError:result['missing_census']='REJECTED'
else:raise AssertionError('missing census accepted')
snaps=load_manifest(root/"docs/history/SNAPSHOT_MANIFEST.json")
# snapshot_text resolves its own module ROOT; each process imports from the selected worktree.
result['snapshot_hashes']={path:hashlib.sha256(snapshot_text(path,root).encode()).hexdigest() for path in snaps['snapshots']}
(out/'summary.json').write_text(json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2))
(out/'routes.json').write_text(json.dumps(routes,sort_keys=True,ensure_ascii=False))
(out/'benchmark.json').write_text(json.dumps(benchmark(root),indent=2))
print(json.dumps({'exports':len(cases)+1,'dxf_files':len(list(out.rglob('*.dxf'))),'route_cases':len(routes)}))
