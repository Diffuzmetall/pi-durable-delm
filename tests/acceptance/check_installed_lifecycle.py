#!/usr/bin/env python3
"""Supplement the installed Native case: real fresh claim race, pending/committed stop and safe removal."""
import argparse
import hashlib
import json
from pathlib import Path
import selectors
import shlex
import signal
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--locator',type=Path,required=True)
    parser.add_argument('--resume-removal',action='store_true',help='Continue from the already verified exercise checkpoint; never repeat model/claim actions')
    args=parser.parse_args()
    install=json.loads(args.locator.read_text());locator=Path(install['fixture']);fixture=json.loads(locator.read_text())
    sandbox=locator.parent;root=Path(install['installed_root']);evidence=Path(install['evidence'])/'lifecycle';evidence.mkdir(exist_ok=True)
    sys.path.insert(0,str(root/'tests/host'))
    from native_process import NativeProcess
    from deterministic_provider import DeterministicProvider
    supplement=sandbox/'supplement.json'
    if args.resume_removal:
        scenario=json.loads(supplement.read_text())
    else:
        scenario=json.loads((sandbox/'native-board-scenario.json').read_text())
        scenario.update(policyPackage=str(Path(scenario['policySource']).parent),modelStarted=str(sandbox/'committed-model-started'),releaseModel=str(sandbox/'committed-model-release'))
        supplement.write_text(json.dumps(scenario))
    private_hook=sandbox/'public-test-dependencies.mjs';private_hook.write_bytes((root/'tests/host/public-dependencies.mjs').read_bytes())
    node_probe=Path(__file__).with_name('probe_native_supplemental.mjs').resolve()
    counts={};race_results={};gate_released=[]
    def claim_command(actor):
        current=json.loads(supplement.read_text());task=current['freshTask'];result_file=Path(current['workspace'])/'host05-fresh-result.txt'
        code=f"""import json,subprocess
from pathlib import Path
cli={str(Path(current['run'])/actor/'bin/context')!r}
p=dict(op='claim',request_id='host05-fresh-claim-{actor}',item={task['id']!r},expected_revision={task['revision']})
r=subprocess.run([cli,'domain',json.dumps(p)],capture_output=True,text=True)
if r.returncode==0:
 t=json.loads(r.stdout)['task']
 Path({str(result_file)!r}).write_text({actor!r}+'\\n')
 p=dict(op='complete',request_id='host05-fresh-complete-{actor}',item=t['id'],expected_revision=t['revision'],generation=t['generation'],summary='Actual fresh Native claim winner')
 subprocess.run([cli,'domain',json.dumps(p)],check=True,capture_output=True,text=True)
 print('HOST05_CLAIM_WON={actor}')
else:
 assert json.loads(r.stdout)['code'] in ('STALE','CONFLICT','BLOCKED','OWNED')
 print('HOST05_CLAIM_LOST={actor}')
"""
        return 'python3 -B -c '+shlex.quote(code)
    def reply(request):
        user=next(m for m in reversed(request['messages']) if m['role']=='user');text=json.dumps(user['content'])
        key=next((k for k in ('HOST05_PENDING_WAIT','HOST05_RACE_ALICE','HOST05_RACE_BOB','HOST05_COMMITTED_WAIT') if k in text),'committed-wake')
        n=counts.get(key,0);counts[key]=n+1
        current=json.loads(supplement.read_text())
        if key in ('HOST05_PENDING_WAIT','HOST05_COMMITTED_WAIT'):
            item=current['freshTask' if key=='HOST05_PENDING_WAIT' else 'committedTask']['id']
            return dict(tool='delm_wait',arguments=dict(action='wait',items=[item],reason='actual pending/committed control stop')) if n==0 else dict(text='HOST05_PENDING_ARMED' if key=='HOST05_PENDING_WAIT' else 'HOST05_COMMITTED_ARMED')
        if key.startswith('HOST05_RACE_'):
            actor='alice' if key.endswith('ALICE') else 'bob'
            if n==0:return dict(tool='bash',arguments=dict(command=claim_command(actor)))
            tool=str(request['messages'][-1]['content'])
            won='HOST05_CLAIM_WON='+actor;lost='HOST05_CLAIM_LOST='+actor
            assert won in tool or lost in tool,'Actual Native bash did not return a valid claim outcome'
            race_results[actor]=won in tool
            return dict(text=key+'_DONE')
        assert n==0,'Committed delivery generated duplicate model work'
        Path(current['modelStarted']).write_text('Actual Native generation requested the model after dispatch commit')
        end=time.monotonic()+20
        while not Path(current['releaseModel']).exists():
            assert time.monotonic()<end,'Native stop did not return before the held model reply'
            time.sleep(.02)  # Model-response gate in a bounded test, not team/model polling.
        gate_released.append(True)
        return dict(text='HOST05_FORBIDDEN_AFTER_COMMITTED_STOP')
    def host_for(label):
        selected=[Path(scenario['policyPackage'])] if label=='after-remove' else [root,Path(scenario['policyPackage'])]
        h=NativeProcess(locator,plugins=selected,session_directory=sandbox/'native-board-sessions',log='lifecycle-'+label+'-server.log')
        h.env['NODE_OPTIONS']='--import='+private_hook.as_uri()  # Test dependency hook survives payload removal.
        return h
    def probe(host,mode):
        result=host.probe(node_probe,{'DELM_SUPPLEMENT':str(supplement),'DELM_SUPPLEMENT_MODE':mode})
        (evidence/(mode+'-client.log')).write_text(host.redact(result.stdout+result.stderr))
        assert result.returncode==0,'Installed lifecycle '+mode+' failed; see evidence'
        return json.loads(result.stdout)
    h=host_for('exercise')
    board=subprocess.Popen([sys.executable,'-B',str(root/'scripts/delm_local.py'),'serve',scenario['run']],
        cwd=fixture['project'],env=h.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    selector=selectors.DefaultSelector();selector.register(board.stdout,selectors.EVENT_READ)
    try:
        assert selector.select(15),'Existing test board failed to resume';board.stdout.readline()
        checkpoint=sandbox/'lifecycle-exercise.json'
        if args.resume_removal:
            saved=json.loads(checkpoint.read_text());exercise=saved['exercise'];race_results.update(saved['race_results'])
            assert saved['http_requests']==9 and sorted(race_results.values())==[False,True]
        else:
            with DeterministicProvider(reply) as model:
                (Path(h.env['PI_CODING_AGENT_DIR'])/'models.json').write_text(json.dumps(model.models_config()))
                with h:exercise=probe(h,'exercise')
                assert counts=={'HOST05_PENDING_WAIT':2,'HOST05_RACE_ALICE':2,'HOST05_RACE_BOB':2,'HOST05_COMMITTED_WAIT':2,'committed-wake':1},counts
                assert sorted(race_results.values())==[False,True],race_results
                assert model.requests==9 and gate_released
                checkpoint.write_text(json.dumps(dict(exercise=exercise,race_results=race_results,http_requests=9)))
        h=host_for('disable')
        with h:disabled=probe(h,'disable')
        skill=Path(fixture['project'])/'.pi/skills/delm'
        assert skill.is_symlink() and skill.resolve()==root/'skills/delm'
        skill.unlink()  # Only the exact project-local link this acceptance created.
        env=h.env
        board_files=[p for p in Path(scenario['run']).glob('context*.sqlite*') if p.is_file()]
        before_board={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in board_files}
        removed=subprocess.run([sys.executable,'-B',str(sandbox/'install.py'),'uninstall','--prefix',install['prefix']],env=env,check=True,capture_output=True,text=True)
        uninstall=json.loads(removed.stdout);assert not (Path(install['prefix'])/'current').exists()
        assert Path(scenario['run']).is_dir() and Path(scenario['workspace']).is_dir()
        after_requests=[]
        def after_reply(request):
            tools=[t['function']['name'] for t in request.get('tools',[])];assert 'delm_wait' not in tools and 'bash' in tools
            system='\n'.join(str(m['content']) for m in request['messages'] if m['role']=='system')
            assert '<name>delm</name>' not in system
            after_requests.append(tools)
            return dict(text='HOST05_AFTER_REMOVE_ACK')
        h=host_for('after-remove')
        with DeterministicProvider(after_reply) as model:
            (Path(h.env['PI_CODING_AGENT_DIR'])/'models.json').write_text(json.dumps(model.models_config()))
            with h:after=probe(h,'after-remove')
            assert model.requests==1
        assert before_board=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in board_files},'Removal changed preserved board data/receipts'
        report=dict(schema=1,verdict='INSTALLED_NATIVE_FRESH_CLAIM_STOP_AND_REMOVE_PASS',archive_sha256=hashlib.sha256(Path(install['archive']).read_bytes()).hexdigest(),
            exercise=exercise,race_outcomes=race_results,model_requests_exercise=9,model_requests_after_remove=1,
            actual_profiles_disabled=disabled,uninstall=uninstall,after_remove=after,
            model_response_held_until_real_stop_returned=True,unread_receipt_not_autoacked=True,
            current_link_removed=True,project_skill_link_only_exact_owned_link_removed=True,
            preserved_board_file_hashes=before_board,managed_version_removed=not root.exists(),
            native_framework_modified_or_removed=False,live_model_calls=0)
        (evidence/'result.json').write_text(h.redact(json.dumps(report,indent=2))+'\n')
        print(h.redact(json.dumps(report)))
    finally:
        selector.close()
        if board.poll() is None:board.send_signal(signal.SIGTERM)
        out,err=board.communicate(timeout=10)
        (evidence/'board.log').write_text(h.redact((out+err).decode(errors='replace')))


if __name__=='__main__':main()
