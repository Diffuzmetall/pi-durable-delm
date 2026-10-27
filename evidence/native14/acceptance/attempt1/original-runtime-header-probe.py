#!/usr/bin/env python3
"""Final exact-archive acceptance through installed product CLI and installed CURRENT Native1.4."""
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import re
import select
import selectors
import shlex
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tarfile
import termios
import time
from types import SimpleNamespace
from urllib.parse import urlsplit

EVIDENCE=Path(__file__).resolve().parent


def main():
    locator=json.loads(Path('/tmp/delm-n14-acceptance-locator.json').read_text())
    area=Path(locator['area']);root=Path(locator['root']);tool=root/'skills/delm/Tools/Run.py'
    meta=json.loads(Path(locator['manifest']).read_text());assert hashlib.sha256(Path(locator['archive']).read_bytes()).hexdigest()==meta['archive_sha256']
    load=lambda name,p:importlib.util.spec_from_file_location(name,p)
    spec=load('installed_n14_peer',root/'tests/native14-adapter-host.py');peer=importlib.util.module_from_spec(spec);spec.loader.exec_module(peer);fixture=peer.fixture
    paths=fixture.installed_paths(Path.home()/'.local/bin/pi-durable');installed_hashes={k:fixture.digest(p) for k,p in paths.items() if p.is_file()}
    project=area/'project';project.mkdir();(project/'AGENTS.md').write_text('Synthetic final acceptance. Only this workspace; no external services.\n')
    (area/'global.md').write_text('Synthetic supplied global rules; no paid models or extra agents.\n')
    (area/'plan.md').write_text('Two actors cooperate on one artifact. Publish early output and read/ACK.\n')
    (area/'approved.txt').write_bytes(b'Authorized synthetic Native1.4 installed-package acceptance.\r\n')
    skill=project/'.pi/skills/delm';skill.parent.mkdir(parents=True);skill.symlink_to(root/'skills/delm',target_is_directory=True)
    bins=area/'bin';bins.mkdir()
    for name in ('python3','node','bash','dirname'):(bins/name).symlink_to(shutil.which(name))
    allowed_path=str(bins)+':/usr/bin:/bin';assert shutil.which('tern',path=allowed_path) is None
    setuphome=area/'setup-home';setuphome.mkdir();env=dict(PATH=allowed_path,HOME=str(setuphome),LANG='C.UTF-8',TERM='xterm-256color',PYTHONDONTWRITEBYTECODE='1')
    run=area/'run';hosts=[];pool=ThreadPoolExecutor(max_workers=2);board=None;ui=None
    def pump():
        for h in hosts:
            if h.process and h.process.poll() is None and not hasattr(h,'exit_code'):h.pump(.01)
    def execute(argv,*,environment=None,label=None,success=True):
        future=pool.submit(subprocess.run,argv,env=environment or env,cwd=project,capture_output=True,text=True,timeout=45)
        while not future.done():pump()
        answer=future.result()
        if label:(area/(label+'.log')).write_text(answer.stdout+answer.stderr)
        assert (answer.returncode==0)==success,(label,answer.stdout[-1000:],answer.stderr[-1000:])
        return json.loads(answer.stdout) if success else answer
    def cli(action,*args,success=True):return execute([sys.executable,'-B',str(tool),action,'--run-dir',str(run),*args],label=action+'-'+str(time.time_ns()),success=success)
    def rpc(h,method,**fields):
        rec=json.loads((run/'launch.json').read_text())['actors'][h.actor]
        future=pool.submit(peer.rpc,Path(rec['socket']),method,**fields)
        while not future.done():pump()
        return future.result()
    def until(predicate,label,timeout=30):
        end=time.monotonic()+timeout
        while not predicate():
            assert time.monotonic()<end,'Timed out '+label
            pump()
    def visible(h,marker):until(lambda:marker.encode() in h.raw,marker)
    def counts(h):return len([e for e in h.model_events() if e['event']=='model_request'])
    def domain(actor,payload):return execute([str(run/actor/'bin/context'),'domain',json.dumps(payload)])
    def bash(actor,body):
        text='import json,subprocess\nfrom pathlib import Path\ncli='+repr(str(run/actor/'bin/context'))+'\ndef d(p):return json.loads(subprocess.check_output([cli,"domain",json.dumps(p)],text=True))\n'+body
        return 'python3 -B -c '+shlex.quote(text)
    def notify(actor,text,key):
        f=area/(key+'.txt');f.write_text(text);return cli('notify','--actor',actor,'--input-file',str(f),'--request-id',key)
    def start_host(actor,phase,routes,previous=None,product=True,session=None,expect_skill=True):
        h=fixture.Native14Host(paths,area/phase,project,routes=routes,antigravity=Path.home()/'.pi/agent/npm/node_modules/pi-antigravity')
        h.actor=actor;h.env['PATH']=allowed_path;h.env['PI_DURABLE_DCG_EXTENSION']=str(Path.home()/'.pi/agent/durable-extensions/durable-dcg/index.ts');h.env['DCG_BIN']=str(Path.home()/'.local/bin/dcg')
        if previous:
            for k in ('HOME','PI_CODING_AGENT_DIR','XDG_CONFIG_HOME','HINDSIGHT_CONFIG','HINDSIGHT_DISABLED'):h.env[k]=previous.env[k]
        plan=dict(modelPreload=str(EVIDENCE/'model.mjs'),observer=str(EVIDENCE/'observer.mjs'),observations=str(h.area/'actual-prompt.jsonl'),
            skillLocations=[str(skill/'SKILL.md'),str(root/'skills/delm/SKILL.md')],expectSkill=expect_skill,
            draft='UNSENT_FINAL_N14_'+actor,holdRequestId='acceptance-held-after-real-admit',admitted=str(h.area/'real-admitted'),release=str(h.area/'real-release'))
        (h.area/'accept-plan.json').write_text(json.dumps(plan));h.accept_plan=plan
        h.env['N14_ACCEPT_PLAN']=str(h.area/'accept-plan.json');h.env['NODE_OPTIONS']='--import='+(EVIDENCE/'preload.mjs').as_uri()
        native=([sys.executable,'-B',str(tool),'open','--run-dir',str(run),'--actor',actor,'--native-executable',str(paths['launcher'])] if product else
            [str(paths['launcher']),'--no-mcp','--session',str(session),'--listen',str(h.socket_path)])
        h.command=['strace','-f','-e','trace=connect,execve','-o',str(h.trace),*native]
        h.master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
        h.process=subprocess.Popen(h.command,cwd=project,env=h.env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave);hosts.append(h)
        def ready():
            socketpath=(json.loads((run/'launch.json').read_text())['actors'][actor].get('socket') if product else str(h.socket_path))
            return bool(socketpath and Path(socketpath).exists() and b'\x1b[?2004h' in h.raw)
        until(ready,'real product/plain terminal '+phase,45)
        return h
    def close(h):
        if not hasattr(h,'exit_code'):h.close()
        assert h.exit_code==0,'Owned Native did not exit cleanly'
    result={};before_data={}
    try:
        prepared=execute([sys.executable,'-B',str(tool),'prepare','--workspace',str(project),'--plan',str(area/'plan.md'),
            '--prompt-file',str(area/'approved.txt'),'--global-agents',str(area/'global.md'),'--agents','2','--run-dir',str(run)],label='prepare')
        assert prepared['manual_core_commands']['observer']==[sys.executable,str(root/'scripts/delm_board.py'),str(run),'--observe']
        boardlog=(area/'board.log').open('wb');board=subprocess.Popen([sys.executable,'-B',str(root/'scripts/delm_local.py'),'serve',str(run)],env=env,stdout=boardlog,stderr=boardlog)
        end=time.monotonic()+15
        while not (run/'endpoint.json').exists():
            assert board.poll() is None and time.monotonic()<end;select.select([],[],[],.03)
        task=domain('alice',dict(op='create',request_id='final-output-create',subject='N14 final shared output',detail='COMPLETE_DETAIL_TAIL'))['task']
        claimfile=project/'claim.json';shared=project/'result.txt'
        claim=bash('alice',f"t=d(dict(op='claim',request_id='final-native-claim',item={task['id']!r},expected_revision={task['revision']}))['task']\nPath({str(claimfile)!r}).write_text(json.dumps(t))\nprint('FINAL_REAL_CLAIM')\n")
        done=bash('alice',f"t=json.loads(Path({str(claimfile)!r}).read_text())\nPath({str(shared)!r}).write_text('FINAL actual Native shared artifact\\n')\nd(dict(op='complete',request_id='final-native-done',item=t['id'],expected_revision=t['revision'],generation=t['generation'],summary='Actual installed Native shared result'))\nprint('FINAL_REAL_DONE')\n")
        ack=bash('bob',f"r=d(dict(op='pending',request_id='final-native-pending'))['receipts'][0]\ns=d(dict(op='snapshot',request_id=r['request_id']))\nassert s['receipt_id']==r['receipt_id']\nassert next(t for t in s['view']['queue'] if t['id']=={task['id']!r})['state']=='done'\nd(dict(op='ack',request_id=r['request_id']+':ack',receipt_id=r['receipt_id']))\nassert not d(dict(op='pending',request_id='final-native-after-ack'))['receipts']\nprint('FINAL_REAL_READ_ACK')\n")
        manifest=json.loads((run/'launch.json').read_text());a_marker=manifest['actors']['alice']['marker'];b_marker=manifest['actors']['bob']['marker']
        ar={a_marker:[dict(text='FINAL_BOOT_ALICE')],'FINAL_CLAIM':[dict(tool='bash',arguments=dict(command=claim)),dict(text='FINAL_CLAIMED',expectToolText='FINAL_REAL_CLAIM')],
            'FINAL_COMPLETE':[dict(tool='bash',arguments=dict(command=done)),dict(text='FINAL_PRODUCER_FINISHED',expectToolText='FINAL_REAL_DONE')],
            'FINAL_HELD_APPROVED':[dict(text='FINAL_HELD_RETRY_ACK')]}
        br={b_marker:[dict(text='FINAL_BOOT_BOB')],'FINAL_WAIT':[dict(tool='delm_wait',arguments=dict(action='wait',items=[task['id']],reason='final installed output')),dict(text='FINAL_WAIT_ARMED')],
            '[delm]':[dict(tool='bash',arguments=dict(command=ack)),dict(tool='delm_wait',arguments=dict(action='status'),expectToolText='FINAL_REAL_READ_ACK'),dict(text='FINAL_WAKE_ACKED')],
            'FINAL_CANCEL_ARM':[dict(tool='delm_wait',arguments=dict(action='wait',items=[],reason='configured below')),dict(text='FINAL_CANCEL_ARMED')],
            'FINAL_CANCEL_NOW':[dict(tool='delm_wait',arguments=dict(action='cancel',id='$USER_WAIT_ID')),dict(text='FINAL_CANCEL_ACK')]}
        # The cancellation task/owner are stable before that wait is armed.
        cancel=domain('alice',dict(op='create',request_id='final-cancel-create',subject='cancel then DONE',detail='Final cancellation proof'))['task']
        br['FINAL_CANCEL_ARM'][0]['arguments']['items']=[cancel['id']]
        alice=start_host('alice','alice',ar);bob=start_host('bob','bob',br)
        initial=cli('start');assert set(initial['results'])=={'alice','bob'}
        visible(alice,'FINAL_BOOT_ALICE');visible(bob,'FINAL_BOOT_BOB');identities=json.loads((run/'launch.json').read_text())['actors']
        ai=identities['alice']['identity'];bi=identities['bob']['identity'];assert ai['sessionPath']!=bi['sessionPath']
        assert all(v['replay'] for v in cli('start')['results'].values())
        for h in (alice,bob):
            os.write(h.master,('\x1b[200~'+h.accept_plan['draft']+'\x1b[201~').encode());visible(h,h.accept_plan['draft'])
        notify('alice','FINAL_CLAIM','final-claim');visible(alice,'FINAL_CLAIMED')
        notify('bob','FINAL_WAIT','final-wait');visible(bob,'FINAL_WAIT_ARMED')
        waits=rpc(bob,'status',identity=bi)['result']['waits'];waiting=next(w for w in waits if w['state']=='waiting');wait_id=waiting['id']
        (area/'bob-draft-before-reopen.txt').write_text(bob.screen());assert bob.accept_plan['draft'] in bob.screen()
        close(bob)
        bob2=start_host('bob','bob-reopen',br,previous=bob);assert cli('start','--actor','bob')['results']['bob']['replay']
        assert json.loads((run/'launch.json').read_text())['actors']['bob']['identity']==bi
        assert counts(bob2)==0 and next(w for w in rpc(bob2,'status',identity=bi)['result']['waits'] if w['id']==wait_id)['state']=='waiting'
        os.write(bob2.master,bob2.accept_plan['draft'].encode());visible(bob2,bob2.accept_plan['draft'])
        notify('alice','FINAL_COMPLETE','final-complete');visible(alice,'FINAL_PRODUCER_FINISHED');visible(bob2,'FINAL_WAKE_ACKED')
        delivered=next(w for w in rpc(bob2,'status',identity=bi)['result']['waits'] if w['id']==wait_id);assert delivered['state']=='sent' and delivered['acked']
        assert shared.read_text()=='FINAL actual Native shared artifact\n'
        assert bob2.accept_plan['draft'] in bob2.screen() and alice.accept_plan['draft'] in alice.screen()
        for h in (alice,bob2):(area/(h.actor+'-final-draft.txt')).write_text(h.screen())
        # Actual MODEL tool.cancel, then actual dependency DONE; consumer must stay silent.
        cancel_claim=domain('alice',dict(op='claim',request_id='final-cancel-claim',item=cancel['id'],expected_revision=cancel['revision']))['task']
        notify('bob','FINAL_CANCEL_ARM','final-cancel-arm');visible(bob2,'FINAL_CANCEL_ARMED')
        cw=next(w for w in rpc(bob2,'status',identity=bi)['result']['waits'] if w['items']==[cancel['id']])
        notify('bob','FINAL_CANCEL_NOW '+cw['id'],'final-cancel-now');visible(bob2,'FINAL_CANCEL_ACK');cancel_calls=counts(bob2)
        domain('alice',dict(op='complete',request_id='final-cancel-done',item=cancel['id'],expected_revision=cancel_claim['revision'],generation=cancel_claim['generation'],summary='DONE after actual native tool cancel'))
        end=time.monotonic()+.5
        while time.monotonic()<end:pump()
        assert counts(bob2)==cancel_calls and next(w for w in rpc(bob2,'status',identity=bi)['result']['waits'] if w['id']==cw['id'])['state']=='cancelled'
        # Real admission is completed and then scheduled behind a test barrier; stop must prevent late submit.
        held=dict(identity=ai,type='input',requestId=alice.accept_plan['holdRequestId'],text='FINAL_HELD_APPROVED',expectedSha256=hashlib.sha256(b'FINAL_HELD_APPROVED').hexdigest())
        sock=json.loads((run/'launch.json').read_text())['actors']['alice']['socket'];future=pool.submit(peer.rpc,Path(sock),'input',**held)
        until(lambda:Path(alice.accept_plan['admitted']).exists(),'REAL admission before delivery barrier')
        assert rpc(alice,'stop',identity=ai)['result']['stopped'];Path(alice.accept_plan['release']).write_text('release after actual stop')
        while not future.done():pump()
        denied=future.result();assert not denied['ok'] and denied['error']['code']=='STOPPED',denied
        before=counts(alice);assert rpc(alice,'resume',identity=ai)['result']['resumed'];assert counts(alice)==before
        accepted=rpc(alice,'input',**held);assert accepted['ok'];visible(alice,'FINAL_HELD_RETRY_ACK')
        # Before-admission type and full-identity fences through the real installed endpoint.
        assert not rpc(alice,'input',**(held|dict(type='write')))['ok']
        assert not rpc(alice,'status',identity=ai|dict(instanceId='wrong-instance'))['ok']
        assert not rpc(alice,'input',**(held|dict(text='CHANGED',expectedSha256=hashlib.sha256(b'CHANGED').hexdigest())))['ok']
        # Interactive SAME shipped curses board; snapshot remains unread before/after viewing and quitting.
        domain('alice',dict(op='publish',request_id='final-ui-note',type='FACT',task=task['id'],text='VISIBLE_FINAL_NOTE '+'details '*50+'NOTE_TAIL'))
        receipt=domain('bob',dict(op='snapshot',request_id='final-ui-unread'));assert receipt['receipt_id']
        dbs=[run/'context.sqlite',run/'context-bodies.sqlite'];before_db={p.name:fixture.digest(p) for p in dbs}
        master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
        ui=subprocess.Popen([sys.executable,'-B',str(root/'scripts/delm_board.py'),str(run),'--observe'],env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave);raw=bytearray()
        def ui_until(marker):
            end=time.monotonic()+12
            while marker not in raw:
                assert ui.poll() is None and time.monotonic()<end,'Interactive BOARD missing '+repr(marker)
                if select.select([master],[],[],.05)[0]:raw.extend(os.read(master,65536))
                pump()
        ui_until(b'READONLY');ui_until(b'VISIBLE_FINAL_NOTE');assert b'OWNER' in raw and b'RECENT FACT / FAIL' in raw
        os.write(master,b'\r');ui_until(b'DETAIL lines');os.write(master,b'\x1bOF');ui_until(b'NOTE_TAIL');os.write(master,b'\x1b');ui_until(b'Enter detail')
        os.write(master,b'\t');ui_until(b'NOTES');os.write(master,b'/no-such-final-filter\r');ui_until(b'No matches');os.write(master,b'\x1b')
        fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',8,30,0,0));ui.send_signal(signal.SIGWINCH);ui_until(b'enlarge terminal');os.write(master,b'q');assert ui.wait(timeout=5)==0;os.close(master)
        (area/'board-interactive.bin').write_bytes(raw);assert before_db=={p.name:fixture.digest(p) for p in dbs}
        assert board.poll() is None and all(h.process.poll() is None for h in (alice,bob2))
        assert any(r['receipt_id']==receipt['receipt_id'] for r in domain('bob',dict(op='pending',request_id='final-ui-still-unread'))['receipts'])
        # Stop both genuine owners before changing/removing managed package files.
        cli('stop');assert counts(alice)==6 and counts(bob)==3 and counts(bob2)==7,(counts(alice),counts(bob),counts(bob2))
        for h in (bob2,alice):close(h)
        before_data={p.name:fixture.digest(p) for p in dbs};saved_result=shared.read_bytes();old_session=ai['sessionPath']
        result=dict(schema=1,verdict='INSTALLED_CURRENT_NATIVE14_PRODUCT_FLOW_AND_BOARD_PASS',archive_sha256=meta['archive_sha256'],runtime_assets=37,
            productOpenTwoActors=True,plainTerminalNoTern=True,bootstrapReplay=True,exactPendingReopenSameIdentity=True,
            actualNativeBashSharedResult=True,actualEventWakeReadACK=True,toolCancelThenDONEConsumerSilent=True,
            realAdmissionStopBarrierDeniesLateSubmit=True,resumeNoDummyInput=True,typePayloadInstanceDenials=True,
            actualPackagedNativeSkill=True,draftsPreservedAndAbsentModelContext=True,actualInteractiveShippedBoard=True,
            boardKeysDetailSearchNotesResizeQuit=True,observerDidNotConsumeReceiptOrMutateDB=True,backendAndOwnersSurviveObserverExit=True,
            modelCallsBeforeRemoval=16,liveModelCalls=0,currentLiveBuild='NOT_RELOADED_NOT_TESTED',onlyModelSubstitution=True,
            additionalFaultInjection='Scheduling barrier AFTER genuine admission; no policy result replaced')
        (area/'flow-result.json').write_text(json.dumps(result));(area/'post-remove-input.json').write_text(json.dumps(dict(identity=ai,session=old_session,homeEnv={k:alice.env[k] for k in ('HOME','PI_CODING_AGENT_DIR','XDG_CONFIG_HOME','HINDSIGHT_CONFIG','HINDSIGHT_DISABLED')},beforeBoardHashes=before_data)))
        assert saved_result==shared.read_bytes()
        print(json.dumps(dict(verdict=result['verdict'],modelCalls=16,liveModelCalls=0,privateArea=str(area))))
    finally:
        if ui and ui.poll() is None:ui.terminate();ui.wait(timeout=5)
        for h in reversed(hosts):
            if h.process and not hasattr(h,'exit_code'):h.close()
        pool.shutdown(wait=True)
        if board and board.poll() is None:board.terminate();board.wait(timeout=10)
        if 'boardlog' in locals():boardlog.close()
        def clean(text):return text.replace(str(area),'<FIXTURE>').replace(str(root),'<INSTALLED_PACKAGE>').replace(str(paths['lane']),'<INSTALLED_HOST_LANE>').replace(str(paths['extensions']),'<INSTALLED_EXTENSIONS>').replace(str(Path.home()),'<OPERATOR_HOME>')
        for h in hosts:
            for f in (h.model_log,h.observer_log,h.trace,h.area/'actual-prompt.jsonl',h.area/'terminal.bin'):
                if f.exists():(EVIDENCE/(h.area.name+'-'+f.name+'.txt')).write_text(clean(f.read_text(errors='replace')))
        if (area/'flow-result.json').exists():(EVIDENCE/'installed-flow-result.json').write_text((area/'flow-result.json').read_text())
        (EVIDENCE/'board.log').write_text(clean((area/'board.log').read_text(errors='replace')) if (area/'board.log').exists() else '')


if __name__=='__main__':main()
