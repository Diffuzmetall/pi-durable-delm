#!/usr/bin/env python3
"""Close the original tool.cancel -> actual Native producer DONE negative-wake gap, after reinstall."""
import argparse
import hashlib
import json
from pathlib import Path
import selectors
import shlex
import signal
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--locator',type=Path,required=True);args=p.parse_args()
    d=json.loads(args.locator.read_text());locator=Path(d['fixture']);sandbox=locator.parent;root=Path(d['installed_root'])
    # The removal stage already proved no DeLM bytes remain. Reinstall the SAME artifact without changing any user data.
    assert not root.exists(),'Run this only after the actual successful removal stage'
    subprocess.run([sys.executable,'-B',str(sandbox/'install.py'),'install',d['archive'],'--prefix',d['prefix']],check=True,capture_output=True)
    supplement=sandbox/'supplement.json';s=json.loads(supplement.read_text());s['reinstalledRoot']=str(root);supplement.write_text(json.dumps(s))
    evidence=Path(d['evidence'])/'tool-cancel-done';evidence.mkdir()
    sys.path.insert(0,str(root/'tests/host'))
    from native_process import NativeProcess
    from deterministic_provider import DeterministicProvider
    h=NativeProcess(locator,plugins=[root,Path(s['policyPackage'])],session_directory=sandbox/'native-board-sessions',log='tool-cancel-done-server.log')
    h.env['NODE_OPTIONS']='--import='+(sandbox/'public-test-dependencies.mjs').as_uri()
    board=subprocess.Popen([sys.executable,'-B',str(root/'scripts/delm_local.py'),'serve',s['run']],env=h.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    selector=selectors.DefaultSelector();selector.register(board.stdout,selectors.EVENT_READ)
    count=0
    def reply(request):
        nonlocal count
        text=json.dumps(next(m for m in reversed(request['messages']) if m['role']=='user')['content'])
        assert 'HOST05_COMPLETE_CANCELLED_DEP' in text,'Cancelled Bob wait produced an unexpected model request'
        count+=1
        if count==1:
            current=json.loads(supplement.read_text());task=current['cancelDoneTask']
            code=f"""import json,subprocess
cli={str(Path(s['run'])/'alice/bin/context')!r}
def d(p): return json.loads(subprocess.check_output([cli,'domain',json.dumps(p)],text=True))
t=d(dict(op='claim',request_id='host05-old-cancelled-dep-claim',item={task['id']!r},expected_revision={task['revision']}))['task']
d(dict(op='complete',request_id='host05-old-cancelled-dep-complete',item=t['id'],expected_revision=t['revision'],generation=t['generation'],summary='Actual Native producer DONE after original tool.cancel'))
print('HOST05_CANCELLED_DEP_COMPLETE')
"""
            return dict(tool='bash',arguments=dict(command='python3 -B -c '+shlex.quote(code)))
        assert count==2 and 'HOST05_CANCELLED_DEP_COMPLETE' in str(request['messages'][-1]['content'])
        return dict(text='HOST05_CANCELLED_DEP_DONE')
    try:
        assert selector.select(15);board.stdout.readline()
        with DeterministicProvider(reply) as model:
            (Path(h.env['PI_CODING_AGENT_DIR'])/'models.json').write_text(json.dumps(model.models_config()))
            with h:r=h.probe(Path(__file__).with_name('probe_native_supplemental.mjs'),{'DELM_SUPPLEMENT':str(supplement),'DELM_SUPPLEMENT_MODE':'cancel-done'})
            (evidence/'client.log').write_text(h.redact(r.stdout+r.stderr));assert r.returncode==0,'See tool-cancel-done/client.log'
            assert model.requests==count==2
        report=dict(schema=1,verdict='ORIGINAL_TOOL_CANCEL_THEN_ACTUAL_NATIVE_DONE_PASS',archive_sha256=hashlib.sha256(Path(d['archive']).read_bytes()).hexdigest(),
            result=json.loads(r.stdout),actual_producer_http_requests=2,consumer_wake_http_requests=0,live_model_calls=0,
            bounded_post_done_observation_ms=500,existing_native_data_reused_after_reinstall=True)
        (evidence/'result.json').write_text(h.redact(json.dumps(report,indent=2))+'\n');print(h.redact(json.dumps(report)))
    finally:
        selector.close()
        if board.poll() is None:board.send_signal(signal.SIGTERM)
        out,err=board.communicate(timeout=10);(evidence/'board.log').write_text(h.redact((out+err).decode(errors='replace')))


if __name__=='__main__':main()
