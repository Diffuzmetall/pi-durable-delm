#!/usr/bin/env python3
"""Complement Bob's owner/input self-check: actual Native1.4 + board + native Bash/wait/reopen/readACK."""
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import signal
import shlex
import subprocess
import tempfile
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
# Reuse the owner/input peer's existing client and the independently accepted frozen actual-main fixture.
spec=importlib.util.spec_from_file_location('native14_existing_owner_test',ROOT/'tests/native14-adapter-host.py')
peer=importlib.util.module_from_spec(spec);spec.loader.exec_module(peer)
fixture=peer.fixture


def main():
    paths=fixture.installed_paths(Path.home()/'.local/bin/pi-durable')
    area=Path(tempfile.mkdtemp(prefix='n14-board-'));workspace=area/'work';workspace.mkdir(mode=0o700)
    run=area/'run';boot=area/'boot';boot.mkdir(mode=0o700)
    evidence=ROOT/'docs/evidence/native14/fixture-integration';evidence.mkdir(parents=True,exist_ok=True)
    product=['extensions/delm/native14.js','extensions/delm/native14-owner.js','extensions/delm/index.js',
        'extensions/delm/protocol.js','skills/delm/Tools/NativeInput.mjs','scripts/delm_local.py',
        'scripts/delm_domain.py','scripts/delm_delivery.py']
    before={name:fixture.digest(ROOT/name) for name in product}
    subprocess.run(['python3','-B',str(ROOT/'scripts/delm_local.py'),'init',str(run),'--shared-workspace',str(workspace),
        '--n','2','--task','Actual current Native14 board/wake/readACK fixture'],check=True,capture_output=True)
    base_env={k:os.environ[k] for k in ('PATH','LANG') if k in os.environ}|{'PYTHONDONTWRITEBYTECODE':'1'}
    board=subprocess.Popen(['python3','-B',str(ROOT/'scripts/delm_local.py'),'serve',str(run)],env=base_env,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    selector=selectors.DefaultSelector();selector.register(board.stdout,selectors.EVENT_READ)
    hosts=[];control_pool=ThreadPoolExecutor(max_workers=1)
    def rpc(path,method,**fields):
        # Keep actual owner PTYs/observation streams drained while awaiting a separate control reply.
        future=control_pool.submit(peer.rpc,path,method,**fields)
        while not future.done():
            for h in hosts:
                if h.process and h.process.poll() is None and not hasattr(h,'exit_code'):h.pump(.01)
        return future.result()
    def close_once(h):
        if not hasattr(h,'exit_code'):h.close()
    def domain(actor,payload):
        r=subprocess.run([str(run/actor/'bin/context'),'domain',json.dumps(payload)],capture_output=True,text=True,env=base_env)
        assert r.returncode==0,r.stdout+r.stderr
        return json.loads(r.stdout)
    def command(actor,body):
        code="import json,subprocess\nfrom pathlib import Path\ncli="+repr(str(run/actor/'bin/context'))+"\ndef d(p):return json.loads(subprocess.check_output([cli,'domain',json.dumps(p)],text=True))\n"+body
        return 'python3 -B -c '+shlex.quote(code)
    def host(actor,phase,routes,original=None,previous=None):
        own=area/(actor+'-'+phase);control=own/'delm.sock';adapter=boot/(actor+'-'+phase+'.mjs')
        adapter.write_text('import install from '+json.dumps((ROOT/'extensions/delm/native14.js').as_uri())+';\n'+
            'export default base=>install(base,'+json.dumps(dict(run=str(run),actor=actor,controlSocket=str(control)))+');\n')
        h=fixture.Native14Host(paths,own,workspace,session=original['sessionPath'] if original else None,
            extensions=[adapter],routes=routes,antigravity=Path.home()/'.pi/agent/npm/node_modules/pi-antigravity')
        # Select the SAME installed trusted DCG addon/binary; do not disable the native execution boundary.
        h.env['PI_DURABLE_DCG_EXTENSION']=str(Path.home()/'.pi/agent/durable-extensions/durable-dcg/index.ts')
        h.env['DCG_BIN']=str(Path.home()/'.local/bin/dcg')
        assert Path(h.env['PI_DURABLE_DCG_EXTENSION']).is_file() and Path(h.env['DCG_BIN']).is_file()
        if previous:
            for key in ('HOME','PI_CODING_AGENT_DIR','XDG_CONFIG_HOME','HINDSIGHT_CONFIG','HINDSIGHT_DISABLED'):h.env[key]=previous.env[key]
        hosts.append(h);return h,control
    def input(control,identity,key,text):
        r=rpc(control,'input',identity=identity,type='input',requestId=key,text=text,expectedSha256=hashlib.sha256(text.encode()).hexdigest())
        assert r['ok'],r
        return r['result']
    try:
        assert selector.select(15),'Board did not start';board.stdout.readline()
        task=domain('alice',dict(op='create',request_id='n14-create-output',subject='actual Native early output',detail='Native Bash owns and completes this result'))['task']
        claimfile=workspace/'claim.json';resultfile=workspace/'result.txt'
        claim=command('alice',f"r=d(dict(op='claim',request_id='n14-native-claim',item={task['id']!r},expected_revision={task['revision']}))['task']\nPath({str(claimfile)!r}).write_text(json.dumps(r))\nprint('N14_ACTUAL_CLAIM')\n")
        complete=command('alice',f"t=json.loads(Path({str(claimfile)!r}).read_text())\nPath({str(resultfile)!r}).write_text('N14 actual Native shared result\\n')\nd(dict(op='complete',request_id='n14-native-complete',item=t['id'],expected_revision=t['revision'],generation=t['generation'],summary='Actual Native Bash result'))\nprint('N14_ACTUAL_DONE')\n")
        ack=command('bob',f"p=d(dict(op='pending',request_id='n14-wake-pending'))['receipts']\nassert len(p)==1,p\nr=p[0]\ns=d(dict(op='snapshot',request_id=r['request_id']))\nassert s['receipt_id']==r['receipt_id']\nassert next(t for t in s['view']['queue'] if t['id']=={task['id']!r})['state']=='done'\na=d(dict(op='ack',request_id=r['request_id']+':ack',receipt_id=r['receipt_id']))\nassert a['acked_sequence']==s['to_sequence']\nassert not d(dict(op='pending',request_id='n14-wake-after-ack'))['receipts']\nprint('N14_ACTUAL_SNAPSHOT_READ_ACK')\n")
        alice_routes={'N14_CLAIM':[dict(tool='bash',arguments=dict(command=claim)),dict(text='N14_CLAIMED',expectToolText='N14_ACTUAL_CLAIM')],
            'N14_COMPLETE':[dict(tool='bash',arguments=dict(command=complete)),dict(text='N14_PRODUCER_DONE',expectToolText='N14_ACTUAL_DONE')]}
        bob_wait={'N14_WAIT':[dict(tool='delm_wait',arguments=dict(action='wait',items=[task['id']],reason='current Native board output')),
            dict(text='N14_WAIT_ARMED')]}
        bob_wake={'[delm]':[dict(tool='bash',arguments=dict(command=ack)),dict(tool='delm_wait',arguments=dict(action='status'),expectToolText='N14_ACTUAL_SNAPSHOT_READ_ACK'),dict(text='N14_WAKE_ACKED')]}
        with ExitStack() as stack:
            alice,ac=host('alice','initial',alice_routes);alice.__enter__();stack.callback(close_once,alice)
            assert alice.request('attach',cwd=str(workspace))['success']
            ai=rpc(ac,'identity')['result']['identity'];input(ac,ai,'n14-initial-claim','N14_CLAIM');alice.wait_history('N14_CLAIMED')
            bob,bc=host('bob','initial',bob_wait);bob.__enter__();stack.callback(close_once,bob)
            assert bob.request('attach',cwd=str(workspace))['success']
            bi=rpc(bc,'identity')['result']['identity'];input(bc,bi,'n14-initial-wait','N14_WAIT');bob.wait_history('N14_WAIT_ARMED')
            waiting=rpc(bc,'status',identity=bi);assert waiting['ok'],waiting
            waits=waiting['result']['waits'];assert len(waits)==1 and waits[0]['state']=='waiting',waits
            wait_id=waits[0]['id'];bob.close();assert bob.exit_code==0
            with ExitStack() as reopened_scope:
                bob2,bc2=host('bob','reopen',bob_wake,bi,bob);reopened_scope.enter_context(bob2)
                assert bob2.request('attach',cwd=str(workspace))['success']
                bi2=rpc(bc2,'identity')['result']['identity'];assert bi2==bi
                status=rpc(bc2,'status',identity=bi2);assert status['ok'];assert status['result']['waits'][0]['id']==wait_id
                assert not [e for e in bob2.model_events() if e['event']=='model_request']
                assert input(bc2,bi2,'n14-initial-wait','N14_WAIT')['replay'] is True
                input(ac,ai,'n14-produce-early-output','N14_COMPLETE');alice.wait_history('N14_PRODUCER_DONE');bob2.wait_history('N14_WAKE_ACKED')
                status=rpc(bc2,'status',identity=bi2);assert status['ok'],status
                delivered=status['result']['waits'][0];assert delivered['state']=='sent' and delivered['acked'],delivered
                assert resultfile.read_text()=='N14 actual Native shared result\n'
                assert not domain('bob',dict(op='pending',request_id='n14-final-pending'))['receipts']
                for control,identity in ((ac,ai),(bc2,bi2)):
                    assert rpc(control,'stop',identity=identity)['result']['stopped']
                    assert rpc(control,'resume',identity=identity)['result']['resumed']
                assert len([e for e in alice.model_events() if e['event']=='model_request'])==4
                assert len([e for e in bob.model_events() if e['event']=='model_request'])==2
                assert len([e for e in bob2.model_events() if e['event']=='model_request'])==3
        assert all(h.exit_code==0 for h in hosts)
        url=urlsplit(json.loads((run/'endpoint.json').read_text())['url']);assert url.hostname=='127.0.0.1' and url.port
        expected=f'sa_family=AF_INET, sin_port=htons({url.port}), sin_addr=inet_addr("127.0.0.1")'
        inet=[line for h in hosts for line in h.trace.read_text().splitlines() if re.search(r'connect\(.*AF_INET6?[, ]',line)]
        assert all(expected in line for line in inet),'INET connect outside the owned loopback board'
        assert all(fixture.digest(ROOT/name)==value for name,value in before.items()),'Product changed during run'
        result=dict(schema=1,verdict='ACTUAL_NATIVE14_BOARD_REOPEN_WAKE_READACK_PASS',actualMain=True,modelSubstitutionOnly=True,
            modelCalls=9,liveModelCalls=0,inetConnects=len(inet),externalInetConnects=0,onlyOwnedLoopbackBoardConnections=True,
            actualNativeBashClaimAndResult=True,existingTrustedDCGBoundarySelected=True,
            pendingWaitSurvivesExactReopen=True,sameWaitAndNativeInstance=True,sameApprovedInputReplayedWithoutModel=True,
            actualBoardEventWake=True,actualSnapshotReadAndExplicitACK=True,statusSentAcked=True,sharedResult=True,
            stopResumeWithoutExtraInput=True,productHashes=before,currentLiveBuild='NOT_TESTED',finalInstalledPackage='NOT_TESTED')
        def clean(text):
            return text.replace(str(area),'<FIXTURE>').replace(str(paths['lane']),'<INSTALLED_HOST_LANE>').replace(str(paths['extensions']),'<INSTALLED_EXTENSIONS>').replace(str(ROOT),'<PACKAGE>').replace(str(Path.home()),'<OPERATOR_HOME>')
        (evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        for h in hosts:
            for file in (h.model_log,h.observer_log,h.trace):
                if file.exists():(evidence/(h.area.name+'-'+file.name)).write_text(clean(file.read_text()))
        (area/'private-locator.json').write_text(json.dumps(dict(area=str(area),workspace=str(workspace),run=str(run))))
        print(json.dumps(dict(verdict=result['verdict'],modelCalls=9,liveModelCalls=0,privateLocator=str(area/'private-locator.json'))))
    finally:
        selector.close();control_pool.shutdown(wait=True)
        if board.poll() is None:board.send_signal(signal.SIGTERM)
        out,err=board.communicate(timeout=10)
        (evidence/'board.log').write_text((out+err).decode(errors='replace').replace(str(area),'<FIXTURE>'))


if __name__=='__main__':main()
