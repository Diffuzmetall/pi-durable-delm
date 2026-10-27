#!/usr/bin/env python3
"""Managed install/update/rollback/remove and actual existing Native reopening after removal. Corrected cwd/message/root-view ABI, tested in the disclosed first-attempt continuation."""
import hashlib,importlib.util,json,os,re,subprocess,sys,tarfile
from io import BytesIO
from pathlib import Path
E=Path(__file__).resolve().parent
x=json.load(open('/tmp/delm-n14-acceptance-locator.json'));A=Path(x['area']);R=Path(x['root']);run=A/'run';project=A/'project';archive=Path(x['archive']);prefix=Path(x['prefix'])
assert (A/'flow-result.json').exists()
spec=importlib.util.spec_from_file_location('installed_fixture_lifecycle',R/'tests/native14-host.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
paths=F.installed_paths(Path.home()/'.local/bin/pi-durable');original_inputs={k:F.digest(p) for k,p in paths.items() if p.is_file()}
m=json.load(open(x['manifest']));assert all(F.digest(R/n)==v for n,v in m['file_hashes'].items())
protected=[run/'context.sqlite',run/'context-bodies.sqlite',project/'result.txt',project/'AGENTS.md',A/'global.md',A/'approved.txt',run/'launch.json']
for actor in ('alice','bob'):
 h=A/actor/'home';protected.extend([h/'.pi/agent/settings.json',h/'.config/pi-durable/extensions/native-defaults.json',h/'.hindsight/coding-agent.json'])
before={str(p):F.digest(p) for p in protected}
ops=[]
def manager(action,*extra):
 r=subprocess.run([sys.executable,'-B',x['bootstrap'],action,*map(str,extra),'--prefix',str(prefix)],capture_output=True,text=True,check=True)
 v=json.loads(r.stdout);ops.append(dict(action=action,status=v['status']));return v
manager('install',archive);assert (prefix/'current').resolve()==R
# Derive an ordinary metadata-only successor from the EXACT accepted archive, never from the working tree.
update=A/'metadata-successor.tgz'
with tarfile.open(archive) as old,tarfile.open(update,'w:gz') as new:
 for info in old:
  data=old.extractfile(info).read() if info.isfile() else None
  if info.name=='package/README.md':data+=b'\nSynthetic metadata-only update for offline installer acceptance.\n';info.size=len(data)
  new.addfile(info,BytesIO(data) if data is not None else None)
manager('install',update);successor=(prefix/'current').resolve();assert successor!=R and (prefix/'previous').resolve()==R
assert all(F.digest(successor/n)==v for n,v in m['runtime_hashes'].items())
manager('rollback');assert (prefix/'current').resolve()==R and (prefix/'previous').resolve()==successor
# The one-URL entry point is an offline deterministic reading-map check, not a public-network/model claim.
assert 'https://github.com/Diffuzmetall/pi-durable-delm' in (R/'prompts/setup-delm.md').read_text()
for name in ('prompts/setup-delm.md','docs/agent-setup.md'):
 assert name in (R/'README.md').read_text()
for name in ('docs/native14-contract.md','docs/native14-operations.md','skills/delm/SKILL.md','skills/delm/Tools/Run.help.md'):
 assert name in (R/'prompts/setup-delm.md').read_text() and (R/name).is_file()
for args in (['--help'],['open','--help'],['prepare','--help']):
 r=subprocess.run([sys.executable,'-B',str(R/'skills/delm/Tools/Run.py'),*args],capture_output=True,text=True,check=True);assert r.stdout
# Only the synthetic project skill link is disabled. No installed personal skill/global registration was touched.
skill=project/'.pi/skills/delm';assert skill.is_symlink() and skill.resolve()==R/'skills/delm';skill.unlink()
removed=manager('uninstall');assert not (prefix/'current').exists() and not R.exists()
assert all(F.digest(p)==before[str(p)] for p in protected),'Installer changed external run/workspace/synthetic settings'
record=json.loads((run/'launch.json').read_text())['actors']['alice'];identity=record['identity']
h=F.Native14Host(paths,A/'after-remove',project,session=identity['sessionPath'],routes={'POST_REMOVE_ORIGINAL_NATIVE':[dict(text='ORIGINAL_NATIVE_STILL_WORKS')]},antigravity=Path.home()/'.pi/agent/npm/node_modules/pi-antigravity')
oldhome=A/'alice/home';h.env.update(HOME=str(oldhome),PI_CODING_AGENT_DIR=str(oldhome/'.pi/agent'),XDG_CONFIG_HOME=str(oldhome/'.config'),HINDSIGHT_CONFIG=str(oldhome/'.hindsight/coding-agent.json'),PATH=str(A/'bin')+':/usr/bin:/bin')
h.env.update(PI_DURABLE_DCG_EXTENSION=str(Path.home()/'.pi/agent/durable-extensions/durable-dcg/index.ts'),DCG_BIN=str(Path.home()/'.local/bin/dcg'))
plan=dict(modelPreload=str(E/'model.mjs'),observer=str(E/'observer.mjs'),observations=str(h.area/'actual-prompt.jsonl'),skillLocations=[],expectSkill=False,draft='unused',holdRequestId='unused',admitted=str(h.area/'admitted'),release=str(h.area/'release'))
(h.area/'accept-plan.json').write_text(json.dumps(plan));h.env.update(N14_ACCEPT_PLAN=str(h.area/'accept-plan.json'),NODE_OPTIONS='--import='+(E/'preload.mjs').as_uri())
h.command=['strace','-f','-e','trace=connect,execve','-o',str(h.trace),str(paths['launcher']),'--no-mcp','--session',identity['sessionPath'],'--listen',str(h.socket_path)]
try:
 with h:
  assert h.request('attach',cwd=str(project))['success']
  view=h.latest_view();assert view['session']['id']==identity['sessionId']
  assert identity['conversationId']==1 and h.request('get_state',conversationId=1)['success']
  assert 'FINAL_HELD_RETRY_ACK' in json.dumps(view['conversation']) and 'FINAL_PRODUCER_FINISHED' in json.dumps(view['conversation'])
  assert h.request('prompt',message='POST_REMOVE_ORIGINAL_NATIVE')['success'];h.wait_history('ORIGINAL_NATIVE_STILL_WORKS')
 assert h.exit_code==0
 assert all(F.digest(p)==v for k,p in paths.items() if p.is_file() for v in [original_inputs[k]])
 assert all(F.digest(p)==before[str(p)] for p in protected),'Plain Native altered protected board/settings/project files'
 result=dict(verdict='PASS',candidateSha256=m['archive_sha256'],installRepeat=True,metadataOnlyUpdateSame37Runtime=True,rollbackExactCandidate=True,
  uninstallManagedVersionsOnly=True,externalBoardWorkspaceAndSyntheticSettingsPreserved=True,noPersonalSkillOrGlobalRegistration=True,
  originalCurrentNativeAfterRemovalSameSessionConversation=True,priorActualMessagesAndToolResultsPreserved=True,removedSkillAbsentActualNativePrompt=True,
  originalNativeAndSDKInputsUnchanged=True,oneAdditionalFauxModelCall=True,liveModelCalls=0,
  oneGithubURLReadingMap='PASS_OFFLINE_PACKAGED_MAP_AND_REAL_CLI_HELP',publicGithubFetchOrPublication='NOT_TESTED_NOT_AUTHORIZED',operations=ops)
 (E/'lifecycle-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:
 for f in (h.trace,h.model_log,h.area/'actual-prompt.jsonl',h.area/'terminal.bin'):
  if f.exists():(E/('after-remove-'+f.name+'.txt')).write_text(f.read_text(errors='replace').replace(str(A),'<FIXTURE>').replace(str(Path.home()),'<OPERATOR_HOME>'))
