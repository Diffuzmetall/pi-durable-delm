#!/usr/bin/env python3
"""Self-verification through the SAME installed Native1.4 entrypoint. Only MODEL replies are faux."""
import atexit
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import uuid

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('frozen_native14_fixture',ROOT/'tests/native14-host.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


def rpc(path,method,**fields):
    request=dict(id=str(uuid.uuid4()),method=method,**fields)
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(20);client.connect(str(path));client.sendall((json.dumps(request)+'\n').encode())
        data=b''
        while b'\n' not in data:
            part=client.recv(65536)
            if not part:raise RuntimeError('Native adapter closed before response')
            data+=part
        result=json.loads(data.split(b'\n',1)[0]);assert result['id']==request['id']
        return result


def main():
    paths=fixture.installed_paths(Path.home()/'.local/bin/pi-durable')
    installed_before={key:fixture.digest(p) for key,p in paths.items() if p.is_file()}
    area=Path(tempfile.mkdtemp(prefix='n14-adapter-'));workspace=area/'work';workspace.mkdir(mode=0o700)
    run=area/'run';boot=area/'boot';boot.mkdir(mode=0o700)
    subprocess.run(['python3','-B',str(ROOT/'scripts/delm_local.py'),'init',str(run),
        '--shared-workspace',str(workspace),'--n','2','--task','Actual current Native adapter self-check'],check=True,capture_output=True)
    board=subprocess.Popen(['python3','-B',str(ROOT/'scripts/delm_local.py'),'serve',str(run)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def close_board():
        if board.poll() is None:board.terminate()
        board.communicate(timeout=10)
    atexit.register(close_board)
    readiness=board.stdout.readline().decode();assert readiness, 'Fixture board did not start'
    board_port=int(re.search(r'127\.0\.0\.1:(\d+)',readiness).group(1))
    def expected_board_connect(line):
        return 'sa_family=AF_INET,' in line and f'sin_port=htons({board_port})' in line and 'sin_addr=inet_addr("127.0.0.1")' in line
    assert expected_board_connect(f'connect(3, {{sa_family=AF_INET, sin_port=htons({board_port}), sin_addr=inet_addr("127.0.0.1")}}, 16)')
    assert not expected_board_connect(f'connect(3, {{sa_family=AF_INET, sin_port=htons({board_port}), sin_addr=inet_addr("203.0.113.2")}}, 16)')
    assert not expected_board_connect('connect(3, {sa_family=AF_INET, sin_port=htons(1), sin_addr=inet_addr("127.0.0.1")}, 16)')
    sequence=0
    def domain(actor,payload):
        nonlocal sequence
        sequence+=1
        return json.loads(subprocess.check_output([str(run/actor/'bin/context'),'domain',json.dumps({'request_id':f'n14-self-{sequence}',**payload})],text=True))
    task=domain('alice',dict(op='create',subject='actual early output',detail='Native14 restart dependency'))['task']
    claim=domain('alice',dict(op='claim',item=task['id'],expected_revision=task['revision']))['task']
    sessions=[];reports=[];model_calls=0;persisted_wait=None;board_connects=0
    for actor in ('alice','bob'):
        original=None
        for generation in (1,2):
            process_area=area/(actor+str(generation));control=process_area/'delm.sock'
            bootstrap=boot/(actor+str(generation)+'.mjs')
            bootstrap.write_text('import install from '+json.dumps((ROOT/'extensions/delm/native14.js').as_uri())+';\n'+
                'export default base => install(base,'+json.dumps(dict(run=str(run),actor=actor,controlSocket=str(control)))+');\n')
            marker='N14_ADAPTER_APPROVED_'+actor.upper();answer='N14_ADAPTER_ACK_'+actor.upper()
            routes={marker:[dict(text=answer)]} if generation==1 else {}
            if actor=='bob':
                routes=({marker:[dict(tool='delm_wait',arguments=dict(action='wait',items=[task['id']],reason='actual Native14 persisted dependency')),dict(text=answer)]}
                    if generation==1 else {'[delm] READY:':[dict(text='N14_ADAPTER_ACTUAL_WAKE_BOB')]})
            host=fixture.Native14Host(paths,process_area,workspace,
                session=Path(original['sessionPath']) if original else None,extensions=[bootstrap],
                routes=routes,
                antigravity=Path.home()/'.pi/agent/npm/node_modules/pi-antigravity')
            if original:
                for key in ('HOME','PI_CODING_AGENT_DIR','XDG_CONFIG_HOME','HINDSIGHT_CONFIG','HINDSIGHT_DISABLED'):
                    host.env[key]=previous.env[key]
            with host:
                attached=host.request('attach',cwd=str(workspace));assert attached['success']
                assert control.is_socket(),'DeLM plugin endpoint missing after real Native startup'
                assert control.stat().st_mode&0o777==0o600
                metadata=rpc(control,'identity');assert metadata['ok'],metadata
                identity=metadata['result']['identity']
                assert identity['protocol']=='delm.native14.control.v1' and identity['sdkVersion']=='1.4.0'
                assert identity['actor']==actor and identity['workspace']==str(workspace)
                assert identity['sessionId']==attached['data']['session']['id']
                assert identity['sessionPath']==str(Path(attached['data']['session']['directory'])/'session.sqlite')
                assert identity['conversationId']==1
                if original:assert identity==original
                else:original=identity
                payload=dict(identity=identity,type='input',requestId='approved-'+actor,text=marker,
                    expectedSha256=hashlib.sha256(marker.encode()).hexdigest())
                accepted=rpc(control,'input',**payload);assert accepted['ok'],accepted
                assert accepted['result']['replay']==(generation==2)
                assert rpc(control,'input',**payload)['result']['replay'] is True
                changed=marker+' CHANGED'
                rejected=rpc(control,'input',**(payload|dict(text=changed,expectedSha256=hashlib.sha256(changed.encode()).hexdigest())))
                assert not rejected['ok']
                assert not rpc(control,'input',**(payload|dict(type='write')))['ok']
                assert not rpc(control,'status',identity=identity|dict(instanceId=str(uuid.uuid4())))['ok']
                host.wait_history(answer)
                events=host.model_events();calls=len([e for e in events if e['event']=='model_request'])
                assert calls==((2 if actor=='bob' else 1) if generation==1 else 0),calls
                if actor=='bob':
                    status=rpc(control,'status',identity=identity)['result']['waits']
                    assert len(status)==1 and status[0]['state']=='waiting',status
                    if generation==1:persisted_wait=status[0]['id']
                    else:
                        assert status[0]['id']==persisted_wait
                        domain('alice',dict(op='complete',item=claim['id'],expected_revision=claim['revision'],generation=claim['generation'],summary='actual early output after Native14 reopen'))
                        host.wait_history('N14_ADAPTER_ACTUAL_WAKE_BOB')
                        calls=len([e for e in host.model_events() if e['event']=='model_request']);assert calls==1
                        receipts=domain('bob',dict(op='pending'))['receipts'];assert len(receipts)==1
                        receipt=receipts[0]
                        snapshot=domain('bob',dict(op='snapshot',request_id=receipt['request_id']))
                        assert snapshot['receipt_id']==receipt['receipt_id']
                        assert next(t for t in snapshot['view']['queue'] if t['id']==task['id'])['state']=='done'
                        domain('bob',dict(op='ack',receipt_id=receipt['receipt_id']))
                        assert not domain('bob',dict(op='pending'))['receipts']
                        status=rpc(control,'status',identity=identity)['result']['waits']
                        assert status[0]['state']=='sent' and status[0]['acked'] is True,status
                model_calls+=calls
                if generation==1:
                    observations=[json.loads(line) for line in host.observer_log.read_text().splitlines()]
                    assert any('approved-'+actor in e.get('admittedRequests',[]) for e in observations),'Stable ID missing from real Hindsight admission'
                if not (actor=='bob' and generation==1):
                    assert rpc(control,'stop',identity=identity)['result']['stopped'] is True
                    assert not rpc(control,'input',**(payload|dict(requestId='must-not-run-'+actor)))['ok']
                    assert rpc(control,'resume',identity=identity)['result']['resumed'] is True
                    assert rpc(control,'status',identity=identity)['result']['stopped'] is False
                assert len([e for e in host.model_events() if e['event']=='model_request'])==calls,'resume generated input'
            assert host.exit_code==0
            connections=[line for line in host.trace.read_text().splitlines() if re.search(r'connect\(.*AF_INET6?[, ]',line)]
            assert all(expected_board_connect(line) for line in connections),'Unexpected external or non-board INET connect'
            board_connects+=len(connections)
            previous=host
        sessions.append(original)
        reports.append(dict(actor=actor,exactNativeSessionAndInstance=True,realTrustedStableAdmission=True,
            replayWithoutExtraModel=True,changedPayloadTypeAndIdentityRejected=True,stopResumeNoInput=True,
            pendingWaitReopenAndActualWake=actor=='bob',twoCleanQuits=True))
    close_board();atexit.unregister(close_board)
    assert sessions[0]['sessionId']!=sessions[1]['sessionId']
    assert all(fixture.digest(paths[key])==value for key,value in installed_before.items())
    evidence=ROOT/'evidence/native14/adapter';evidence.mkdir(parents=True,exist_ok=True)
    def clean(text):
        return text.replace(str(area),'<FIXTURE>').replace(str(paths['lane']),'<INSTALLED_HOST_LANE>').replace(str(paths['extensions']),'<INSTALLED_EXTENSIONS>').replace(str(Path.home()),'<OPERATOR_HOME>').replace(str(ROOT),'<PACKAGE>')
    result=dict(verdict='ACTUAL_CURRENT_NATIVE14_ADAPTER_SELF_CHECK_PASS',actualInstalledEntrypoint=True,
        actualTrustedOwnerAdmission=True,privateEndpointInsideExistingOwner=True,hostModified=False,
        fixtureConstructedHarness=False,modelSubstitutionOnly=True,modelCalls=model_calls,liveModelCalls=0,
        externalInetConnects=0,boardLoopbackConnects=board_connects,sessions=sessions,checks=reports,installedHashesUnchanged=installed_before,
        actualNativeWaitTool=True,pendingWaitSameIdentityAcrossReopen=True,actualNativeWakeAfterBoardDone=True,
        actorCLIReadAckByFixture=True,statusReconciledActualBoardAck=True,
        currentLiveBuild='NOT_RELOADED_NOT_TESTED',finalPackageAndLauncher='SEPARATE_N14_ACCEPT',
        productHashes={name:fixture.digest(ROOT/name) for name in ('extensions/delm/native14.js',
            'extensions/delm/native14-owner.js','extensions/delm/index.js','skills/delm/Tools/NativeInput.mjs')})
    (evidence/'actual-host-result.json').write_text(clean(json.dumps(result,ensure_ascii=False,indent=2))+'\n')
    for path in area.rglob('*'):
        if path.is_file() and path.name in ('model-events.jsonl','registry-events.jsonl','connect.trace'):
            out=evidence/'actual-host'/path.relative_to(area);out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(clean(path.read_text()))
    (area/'private-locator.json').write_text(json.dumps(dict(area=str(area),sessions=sessions)))
    print(json.dumps(dict(verdict=result['verdict'],modelCalls=model_calls,liveModelCalls=0,privateLocator=str(area/'private-locator.json'))))


if __name__=='__main__':main()
