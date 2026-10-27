#!/usr/bin/env python3
"""Bounded measurement of the SAME post-removal conversation; no product/Native changes."""
import hashlib,importlib.util,json,tarfile
from pathlib import Path
from postremove_witness import validate
E=Path(__file__).resolve().parent;x=json.load(open('/tmp/delm-n14-acceptance-locator.json'));A=Path(x['area']);project=A/'project';run=A/'run'
assert not Path(x['root']).exists() and not (project/'.pi/skills/delm').exists()
m=json.load(open(x['manifest']))
with tarfile.open(x['archive']) as t:data=t.extractfile('package/tests/native14-host.py').read()
assert hashlib.sha256(data).hexdigest()==m['file_hashes']['tests/native14-host.py']
f=A/'repair-test-helper.py';f.write_bytes(data);s=importlib.util.spec_from_file_location('postremove_measure_test_helper',f);F=importlib.util.module_from_spec(s);s.loader.exec_module(F)
paths=F.installed_paths(Path.home()/'.local/bin/pi-durable');identity=json.loads((run/'launch.json').read_text())['actors']['alice']['identity']
h=F.Native14Host(paths,A/'postremove-measure-final',project,session=identity['sessionPath'],routes={'POSTREMOVE_MEASURE':[dict(text='POSTREMOVE_MEASUREMENT_COMPLETE')]},antigravity=Path.home()/'.pi/agent/npm/node_modules/pi-antigravity')
home=A/'alice/home';h.env.update(HOME=str(home),PI_CODING_AGENT_DIR=str(home/'.pi/agent'),XDG_CONFIG_HOME=str(home/'.config'),HINDSIGHT_CONFIG=str(home/'.hindsight/coding-agent.json'),PATH=str(A/'bin')+':/usr/bin:/bin',PI_DURABLE_DCG_EXTENSION=str(Path.home()/'.pi/agent/durable-extensions/durable-dcg/index.ts'),DCG_BIN=str(Path.home()/'.local/bin/dcg'))
p=dict(modelPreload=str(E/'model.mjs'),observer=str(E/'postremove-measure-observer.mjs'),observations=str(h.area/'measurement.jsonl'),privateSystem=str(h.area/'private-system.json'))
(h.area/'accept-plan.json').write_text(json.dumps(p));h.env.update(N14_ACCEPT_PLAN=str(h.area/'accept-plan.json'),NODE_OPTIONS='--import='+(E/'preload.mjs').as_uri())
h.command=['strace','-f','-e','trace=connect,execve','-o',str(h.trace),str(paths['launcher']),'--no-mcp','--session',identity['sessionPath'],'--listen',str(h.socket_path)]
try:
 with h:
  assert h.request('attach',cwd=str(project))['success'];assert h.latest_view()['session']['id']==identity['sessionId']
  assert h.request('prompt',message='POSTREMOVE_MEASURE')['success'];h.wait_history('POSTREMOVE_MEASUREMENT_COMPLETE')
 assert h.exit_code==0
 witness=h.area/'measurement.jsonl';assert witness.exists(),'Measurement missing; no negative claim permitted'
 rows=[json.loads(v) for v in witness.read_text().splitlines()];calls=sum(v['event']=='model_request' for v in h.model_events());assert len(rows)==calls==1
 (E/'postremove-measurement.json').write_text(witness.read_text().replace(str(A),'<FIXTURE>').replace(str(Path.home()),'<OPERATOR_HOME>'))
 result=validate(rows,calls)
 (E/'postremove-current-prompt-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:
 for f in (h.trace,h.model_log,h.area/'terminal.bin'):
  if f.exists():(E/('postremove-measure-final-'+f.name+'.txt')).write_text(f.read_text(errors='replace').replace(str(A),'<FIXTURE>').replace(str(Path.home()),'<OPERATOR_HOME>'))
