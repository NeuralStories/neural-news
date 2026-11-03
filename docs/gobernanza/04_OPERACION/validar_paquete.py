#!/usr/bin/env python3
"""Validate new plan package: recovered Flow internal hashes, JSON schemas, tasks and uniqueness."""
import csv, json, hashlib, pathlib, collections, sys
BASE=pathlib.Path(__file__).resolve().parents[1]
assert (BASE/'03_EVIDENCIA_FLOW/flow-recovery.rar').is_file()
m=json.loads((BASE/'03_EVIDENCIA_FLOW/reports/manifest.json').read_text(encoding='utf-8'))
assert len(m['files']) == 17, f"Flow has {len(m['files'])} files rather than 17"
for item in m['files']:
    p=BASE/'03_EVIDENCIA_FLOW/source'/item['path']
    assert p.is_file(),f'Missing recovered source: {p}'
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest==item['sha256'],f'Flow SHA mismatch: {p}'
    assert len(p.read_bytes())==item['bytes'],f'Flow size mismatch: {p}'
print('OK: Flow internal SHA256: 17/17 (does not prove Flow remote identity)')
with (BASE/'06_TASKS/BACKLOG.csv').open(encoding='utf-8-sig',newline='') as f: tasks=list(csv.DictReader(f))
ids={x['id'] for x in tasks}; assert len(ids)==len(tasks)
for task in tasks:
    for dep in filter(None,task['dependencies'].split(';')):
        assert dep in ids, f'{task["id"]} missing dep {dep}'
        assert int(dep[3:])<int(task['id'][3:]),f'{task["id"]} forward dep {dep}'
core={x['id'] for x in tasks if x['window_10h']=='CORE'}
for task in tasks:
    if task['window_10h']=='CORE':
        assert all(dep in core for dep in filter(None,task['dependencies'].split(';'))),f'Core dependency is noncore: {task["id"]}'
with (BASE/'06_TASKS/BACKLOG.json').open(encoding='utf-8') as f:obj=json.load(f)
assert len(obj['tasks'])==len(tasks)
print('OK: Tasks',len(tasks),'milestones',dict(collections.Counter(x['milestone'] for x in tasks)),'CORE',len(core),'CORE estimate',sum(int(x['estimate_minutes']) for x in tasks if x['id'] in core),'minutes')
try: import jsonschema
except ImportError:
    print('NOT_RUN: jsonschema missing; run python -m pip install jsonschema to validate contracts')
else:
    for s in sorted((BASE/'02_CONTRATOS').glob('*.schema.json')):
        schema=json.loads(s.read_text(encoding='utf-8'))
        jsonschema.Draft202012Validator.check_schema(schema)
        f=BASE/'05_EJEMPLOS'/s.name.replace('.schema.json','_DEMO.json')
        inst=json.loads(f.read_text(encoding='utf-8'))
        jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(inst)
        print('OK schema + example',s.name)
    graph=json.loads((BASE/'05_EJEMPLOS/graphic_spec_DEMO.json').read_text(encoding='utf-8'))
    assert [d['value'] for d in graph['data']]==[120,80] and graph['is_demo']
    plan=json.loads((BASE/'05_EJEMPLOS/production_plan_DEMO.json').read_text(encoding='utf-8'))
    assert ' '.join(b['text'] for b in plan['beats'])==plan['narration']['text'], 'Narration altered in beats'
    assert plan['identity']['status']=='PENDING' and plan['approval_state']=='BLOCKED'
    flow=json.loads((BASE/'05_EJEMPLOS/flow_manual_package_DEMO.json').read_text(encoding='utf-8'))
    assert flow['generation_result']=='NOT_EXECUTED' and flow['character_name']=='maxDotAi'
    print('OK demo invariants: exact script, no fake presenter, costs/data claims')
print('PACKAGE_VALIDATED')
