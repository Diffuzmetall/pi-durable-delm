#!/usr/bin/env python3
"""Continue after completed lifecycle assertions and the disclosed shared-RPC field-name probe error."""
import hashlib,importlib.util,json,os,tarfile
from pathlib import Path
E=Path(__file__).resolve().parent;x=json.load(open('/tmp/delm-n14-acceptance-locator.json'));A=Path(x['area']);R=Path(x['root']);project=A/'project';run=A/'run'
assert not R.exists() and not (Path(x['prefix'])/'current').exists() and not (project/'.pi/skills/delm').exists()
m=json.load(open(x['manifest']))
# Retain only the already reviewed PYTHON TEST DRIVER, not Native/SDK/Harness or installed product.
with tarfile.open(x['archive']) as t:data=t.extractfile('package/tests/native14-host.py').read()
assert hashlib.sha256(data).hexdigest()==m['file_hashes']['tests/native14-host.py']
helper=A/'retained-test-fixture.py';helper.write_bytes(data)
spec=importlib.util.spec_from_file_location('exact_archive_test_helper_after_remove',helper);F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
paths=F.installed_paths(Path.home()/'.local/bin/pi-durable');native_before={k:F.digest(p) for k,p in paths.items() if p.is_file()}
protected=[run/'context.sqlite',run/'context-bodies.sqlite',project/'result.txt',project/'AGENTS.md',A/'global.md',A/'approved.txt',run/'launch.json']
oldhome=A/'alice/home'
for actor in ('alice','bob'):
 home=A/actor/'home';protected.extend([home/'.pi/agent/settings.json',home/'.config/pi-durable/extensions/native-defaults.json',home/'.hindsight/coding-agent.json'])
before={str(p):F.digest(p) for p in protected};identity=json.loads((run/'launch.json').read_text())['actors']['alice']['identity']
h=F.Native14Host(paths,A/'after-remove-final',project,session=identity['sessionPath'],routes={'POST_REMOVE_ORIGINAL_NATIVE':[dict(text='ORIGINAL_NATIVE_STILL_WORKS')]},antigravity=Path.home()/'.pi/agent/npm/node_modules/pi-antigravity')
h.env.update(HOME=str(oldhome),PI_CODING_AGENT_DIR=str(oldhome/'.pi/agent'),XDG_CONFIG_HOME=str(oldhome/'.config'),HINDSIGHT_CONFIG=str(oldhome/'.hindsight/coding-agent.json'),PATH=str(A/'bin')+':/usr/bin:/bin',PI_DURABLE_DCG_EXTENSION=str(Path.home()/'.pi/agent/durable-extensions/durable-dcg/index.ts'),DCG_BIN=str(Path.home()/'.local/bin/dcg'))
p=dict(modelPreload=str(E/'model.mjs'),observer=str(E/'observer.mjs'),observations=str(h.area/'actual-prompt.jsonl'),skillLocations=[],expectSkill=False,draft='unused',holdRequestId='unused',admitted=str(h.area/'admitted'),release=str(h.area/'release'))
(h.area/'accept-plan.json').write_text(json.dumps(p));h.env.update(N14_ACCEPT_PLAN=str(h.area/'accept-plan.json'),NODE_OPTIONS='--import='+(E/'preload.mjs').as_uri())
h.command=['strace','-f','-e','trace=connect,execve','-o',str(h.trace),str(paths['launcher']),'--no-mcp','--session',identity['sessionPath'],'--listen',str(h.socket_path)]
try:
 with h:
  response=h.request('attach',cwd=str(project));assert response['success'],response
  view=h.latest_view();assert view['session']['id']==identity['sessionId'] and identity['conversationId']==1
  # Actual shared-server attach explicitly watches ROOT_CONVERSATION_ID (1), not conversation.id.
  assert h.request('get_state',conversationId=1)['success']
  assert 'FINAL_HELD_RETRY_ACK' in json.dumps(view['conversation']) and 'FINAL_PRODUCER_FINISHED' in json.dumps(view['conversation'])
  assert h.request('prompt',message='POST_REMOVE_ORIGINAL_NATIVE')['success'];h.wait_history('ORIGINAL_NATIVE_STILL_WORKS')
 assert h.exit_code==0 and len([v for v in h.model_events() if v['event']=='model_request'])==1
 assert all(F.digest(p)==native_before[k] for k,p in paths.items() if p.is_file())
 assert all(F.digest(p)==before[str(p)] for p in protected)
 result=dict(verdict='PASS',candidateSha256=m['archive_sha256'],installedAfterRemoval=False,sameOriginalNativeSessionConversationAndPriorActualMessages=True,
   actualNativePromptHasNoRemovedSkill=True,originalNativeAndSDKInputsUnchanged=True,externalBoardProjectAndSyntheticSettingsPreserved=True,
   fixtureHelperOnlyRetainedFromExactArchive=True,liveModelCalls=0,additionalFauxModelCalls=1,
   priorLifecycleStage='repeat/update-same37/rollback/uninstall/offline-URL-map/help/protected-file assertions passed BEFORE original probe attach used unsupported workspacePath; corrected continuation uses actual cwd/message ABI, no lifecycle repeat',
   publicGithubFetchOrPublication='NOT_TESTED_NOT_AUTHORIZED')
 (E/'after-remove-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:
 for f in (h.trace,h.model_log,h.area/'actual-prompt.jsonl',h.area/'terminal.bin'):
  if f.exists():(E/('after-remove-final-'+f.name+'.txt')).write_text(f.read_text(errors='replace').replace(str(A),'<FIXTURE>').replace(str(Path.home()),'<OPERATOR_HOME>'))
