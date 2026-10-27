#!/usr/bin/env python3
"""Actual INSTALLED Native1.4 launcher/main fixture. Only its MODEL boundary is substituted."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import shlex
import signal
import socket
import struct
import subprocess
import tempfile
import termios
import time
import fcntl

ROOT=Path(__file__).resolve().parents[1]


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def installed_paths(launcher):
    launcher=Path(launcher).resolve()
    line=next(line for line in launcher.read_text().splitlines() if line.startswith('exec '))
    actual=Path(shlex.split(line)[1]);lane=actual.parent
    paths=dict(launcher=launcher,actualLauncher=actual,globalRuntime=lane/'global-runtime.mjs',
        main=lane/'host/packages/coding-agent/src/experimental/durable/main.ts',
        modelRuntime=lane/'host/packages/coding-agent/src/core/model-runtime.ts',
        extensions=lane.parent/'extensions-lane',lane=lane,
        runtime=lane/'host/packages/coding-agent/src/experimental/durable/runtime.ts',
        registryLoader=lane/'host/.pi/extensions/durable-reload/index.ts',
        sharedServer=lane/'host/packages/coding-agent/src/experimental/durable/shared-server.ts',
        sharedCommands=lane/'host/packages/coding-agent/src/experimental/durable/shared-commands.ts',
        globalHost=lane.parent/'extensions-lane/packages/local-host/src/global.ts',
        localHostAdapter=lane.parent/'extensions-lane/packages/local-host/src/adapter.ts',
        hindsightController=lane.parent/'extensions-lane/packages/hindsight/src/index.mjs')
    assert all(p.is_file() for k,p in paths.items() if k not in ('extensions','lane'))
    for name in ('pi-durable','pi-ai','chord'):
        p=lane/'node_modules/@earendil-works'/name/'package.json';assert json.loads(p.read_text())['version']=='1.4.0'
    return paths


class Native14Host:
    """A subprocess/PTY client of Native's owner. Does NOT construct a Harness or touch Native SQL."""
    def __init__(self,paths,area,workspace,*,session=None,extensions=(),routes=None,antigravity=None):
        self.paths=paths;self.area=Path(area);self.area.mkdir(mode=0o700)
        self.workspace=Path(workspace);self.home=self.area/'home';self.home.mkdir(mode=0o700)
        agent=self.home/'.pi/agent';agent.mkdir(parents=True,mode=0o700)
        (agent/'settings.json').write_text(json.dumps(dict(defaultProvider='faux',defaultModel='faux-1',
            compaction=dict(enabled=False),providerRetry=dict(maxRetries=0),httpIdleTimeoutMs=0)))
        policy_dir=self.home/'.config/pi-durable/extensions';policy_dir.mkdir(parents=True,mode=0o700)
        for p in (self.home/'.config',self.home/'.config/pi-durable',policy_dir):p.chmod(0o700)
        policy=policy_dir/'native-defaults.json';policy.write_text(json.dumps(dict(schemaVersion=1,
            authority='single-user-native-tui-root',scope='all-native-sessions',codexDefault=False,
            entrypoint=str(paths['extensions']/'packages/local-host/src/global.ts'))));policy.chmod(0o600)
        memory=self.home/'.hindsight';memory.mkdir(mode=0o700);(memory/'coding-agent.json').write_text('{"disabled":true}\n')
        self.plan=self.area/'model-plan.json';self.model_log=self.area/'model-events.jsonl';self.observer_log=self.area/'registry-events.jsonl'
        self.plan.write_text(json.dumps(dict(globalRuntime=str(paths['globalRuntime']),modelRuntime=str(paths['modelRuntime']),
            modelLog=str(self.model_log),routes=routes or {})))
        self.socket_path=self.area/'control.sock';self.trace=self.area/'connect.trace'
        self.env=dict(PATH=os.environ['PATH'],HOME=str(self.home),XDG_CONFIG_HOME=str(self.home/'.config'),
            PI_CODING_AGENT_DIR=str(agent),TERM='xterm-256color',LANG='C.UTF-8',PI_OFFLINE='1',PI_TELEMETRY='0',
            PI_ANTIGRAVITY_DIR=str(antigravity),HINDSIGHT_CONFIG=str(memory/'coding-agent.json'),HINDSIGHT_DISABLED='true',
            CONTEXT7_KEY_FILE=str(self.home/'context7-absent.env'),TMPDIR=str(self.area),PYTHONDONTWRITEBYTECODE='1',
            DELM_NATIVE14_PLAN=str(self.plan),DELM_NATIVE14_OBSERVER_LOG=str(self.observer_log),
            NODE_OPTIONS='--import='+(ROOT/'tests/native14-host-model.mjs').as_uri())
        self.command=['strace','-f','-e','trace=connect','-o',str(self.trace),str(paths['launcher']),
            '--no-mcp','--listen',str(self.socket_path),'--extension',str(ROOT/'tests/native14-host-observer.mjs')]
        for p in extensions:self.command+=['--extension',str(p)]
        if session:self.command+=['--session',str(session)]
        self.raw=bytearray();self.frames=[];self.buffer=b'';self.client=None;self.request_id=0;self.process=None

    def __enter__(self):
        self.master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
        self.process=subprocess.Popen(self.command,cwd=self.workspace,env=self.env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
        os.close(slave)
        try:self.until(lambda:self.socket_path.exists() and b'\x1b[?2004h' in self.raw,'actual main/socket/TUI ready',40)
        except BaseException:self.close();raise
        self.client=socket.socket(socket.AF_UNIX);self.client.connect(str(self.socket_path));self.client.setblocking(False)
        assert self.socket_path.stat().st_mode&0o777==0o600
        return self

    def pump(self,timeout=.05):
        streams=[self.master]+([self.client] if self.client else [])
        for stream in select.select(streams,[],[],timeout)[0]:
            if stream==self.master:
                try:self.raw.extend(os.read(self.master,65536))
                except OSError:pass
            else:
                body=self.client.recv(65536)
                if not body:raise RuntimeError('Actual shared owner disconnected')
                self.buffer+=body
                while b'\n' in self.buffer:
                    line,self.buffer=self.buffer.split(b'\n',1);self.frames.append(json.loads(line))

    def until(self,predicate,label,timeout=20):
        end=time.monotonic()+timeout
        while not predicate():
            if self.process.poll() is not None:raise RuntimeError('Native exited before '+label)
            if time.monotonic()>end:raise RuntimeError('Timed out: '+label)
            self.pump()

    def request(self,kind,**values):
        self.request_id+=1;key='fixture-transport-'+str(self.request_id)
        self.client.sendall((json.dumps(dict(id=key,type=kind,**values))+'\n').encode())
        self.until(lambda:any(f.get('id')==key for f in self.frames),'shared response '+kind)
        return next(f for f in self.frames if f.get('id')==key)

    def latest_view(self):
        for frame in reversed(self.frames):
            if 'view' in frame:return frame['view']
            if frame.get('command')=='attach' and frame.get('success'):return frame['data']
        return {}

    def wait_history(self,marker):self.until(lambda:marker in json.dumps(self.latest_view().get('conversation',{})),marker)

    def model_events(self):return [json.loads(s) for s in self.model_log.read_text().splitlines()] if self.model_log.exists() else []

    def screen(self):
        capture=self.area/'screen-source.bin';capture.write_bytes(self.raw)
        decoder=self.paths['extensions']/'packages/activity-panel/terminal-screen.mjs'
        r=subprocess.run(['node',str(decoder),str(capture),'140','40'],capture_output=True,text=True,timeout=10,env={k:v for k,v in self.env.items() if k!='NODE_OPTIONS'})
        assert r.returncode==0,r.stderr
        return '\n'.join(json.loads(r.stdout))

    def close(self):
        if self.client:self.client.close();self.client=None
        if self.process and self.process.poll() is None:
            # This fixture owns the synthetic draft; record it before clearing only that draft for /quit.
            os.write(self.master,b'\x03');end=time.monotonic()+.2
            while time.monotonic()<end:self.pump(.02)
            os.write(self.master,b'/quit\r');end=time.monotonic()+15
            while self.process.poll() is None and time.monotonic()<end:self.pump(.05)
            if self.process.poll() is None:
                os.killpg(self.process.pid,signal.SIGTERM);self.process.wait(timeout=5)
        if self.process:
            self.exit_code=self.process.wait(timeout=5);(self.area/'terminal.bin').write_bytes(self.raw);os.close(self.master)

    def __exit__(self,*exc):self.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--launcher',type=Path,default=Path.home()/'.local/bin/pi-durable')
    p.add_argument('--antigravity-dir',type=Path,default=Path.home()/'.pi/agent/npm/node_modules/pi-antigravity')
    p.add_argument('--evidence-dir',type=Path,default=ROOT/'docs/evidence/native14/fixture');args=p.parse_args()
    paths=installed_paths(args.launcher);evidence=args.evidence_dir.resolve();evidence.mkdir(parents=True,exist_ok=True)
    area=Path(tempfile.mkdtemp(prefix='n14-'));workspace=area/'work';workspace.mkdir(mode=0o700)
    (workspace/'native14-proof.txt').write_text('ACTUAL_NATIVE14_READ_RESULT\n')
    hashes={k:digest(v) for k,v in paths.items() if v.is_file()};sessions=[];results=[];model_calls=0
    for actor in ('alice','bob'):
        marker='NATIVE14_BASELINE_'+actor.upper();answer='NATIVE14_ACK_'+actor.upper();draft='UNSENT_NATIVE14_DRAFT_'+actor.upper()
        replies=([dict(tool='read',arguments=dict(path=str(workspace/'native14-proof.txt'))),dict(text=answer,expectToolText='ACTUAL_NATIVE14_READ_RESULT')]
                 if actor=='alice' else [dict(text=answer)])
        host=Native14Host(paths,area/actor,workspace,routes={marker:replies},antigravity=args.antigravity_dir)
        with host:
            assert not host.request('get_state')['success'];assert not host.request('attach',cwd=str(area))['success']
            attached=host.request('attach',cwd=str(workspace));assert attached['success'];view=attached['data'];identity=view['session']
            assert view['conversation']['conversation']['id']==1
            assert not host.request('get_state',conversationId=999999)['success']
            os.write(host.master,('\x1b[200~'+draft+'\x1b[201~').encode())
            host.until(lambda:draft.encode() in host.raw,'synthetic draft typed')
            assert not [e for e in host.model_events() if e['event']=='model_request']
            assert host.request('prompt',message=marker)['success'];host.wait_history(answer)
            host.until(lambda:answer.encode() in host.raw,'actual TUI answer')
            after=host.screen();assert draft in after and answer in after
            assert draft not in json.dumps(host.latest_view()['conversation'])
            observed=[json.loads(line) for line in host.observer_log.read_text().splitlines()]
            assert any(e['event']=='real_admission_observed_through_sdk' and e['admittedRequests'] for e in observed),'Real owner did not persist context admission'
            calls=len([e for e in host.model_events() if e['event']=='model_request']);assert calls==len(replies);model_calls+=calls
            (host.area/'after-draft.txt').write_text(after)
            sessions.append(identity);results.append(dict(actor=actor,identity=identity,realOwnerAdmission=True,
                wrongWorkspaceAndForeignConversationDenied=True,draftPreservedDuringActualInput=True,draftAbsentHistory=True))
        assert host.exit_code==0
        assert not re.search(r'connect\(.*AF_INET6?[, ]',host.trace.read_text()),'Unexpected network connect'
        # Reopen through the SAME actual executable/--session, no model input or direct SQL inspection.
        reopened=Native14Host(paths,area/(actor+'-reopen'),workspace,session=Path(identity['directory'])/'session.sqlite',
            routes={},antigravity=args.antigravity_dir)
        # The real exact-session selector requires its original owned HOME/agentDir; keep those paths on reopen.
        for key in ('HOME','PI_CODING_AGENT_DIR','XDG_CONFIG_HOME','HINDSIGHT_CONFIG','HINDSIGHT_DISABLED'):reopened.env[key]=host.env[key]
        with reopened:
            attached=reopened.request('attach',cwd=str(workspace));assert attached['success'];assert attached['data']['session']==identity
            reopened.wait_history(answer);assert not [e for e in reopened.model_events() if e['event']=='model_request']
        assert reopened.exit_code==0
        assert not re.search(r'connect\(.*AF_INET6?[, ]',reopened.trace.read_text()),'Unexpected reopen network connect'
        results[-1]['exactSessionReopenNoModelInput']=True
    assert sessions[0]['id']!=sessions[1]['id']
    assert all(digest(paths[k])==h for k,h in hashes.items()),'Installed code changed during fixture'
    def clean(value):
        text=json.dumps(value,ensure_ascii=False).replace(str(area),'<FIXTURE>').replace(str(paths['lane']),'<INSTALLED_HOST_LANE>').replace(str(paths['extensions']),'<INSTALLED_EXTENSIONS>')
        text=text.replace(str(Path.home()),'<OPERATOR_HOME>');return json.loads(text)
    report=dict(schema=1,verdict='ACTUAL_INSTALLED_NATIVE14_BASELINE_FIXTURE_PASS',actualInstalledLauncher=True,
        actualMain=True,actualGlobalRuntime=True,sdkVersion='1.4.0',hostCloneOrPatch=False,newHarnessByFixture=False,
        modelSubstitutionOnly=True,actualNativeSessions=results,modelCalls=model_calls,liveModelCalls=0,inetConnects=0,
        actualNativeReadToolResultVerified=True,
        driverHashes={p.name:digest(p) for p in (Path(__file__),ROOT/'tests/native14-host-model.mjs',ROOT/'tests/native14-host-observer.mjs')},
        entrypointHashes=hashes,entrypointPaths={k:str(v) for k,v in paths.items()},fixtureProfile=dict(memoryDisabled=True,codexDefault=False,mcp=False),
        currentLiveBuild='NOT_TESTED',deLMFinalAdapterIntegration='NOT_TESTED',stableRequestIDSocketPrompt='NOT_PROVIDED_BY_STOCK_SOCKET')
    (evidence/'result.json').write_text(json.dumps(clean(report),indent=2,ensure_ascii=False)+'\n')
    for path in area.rglob('*'):
        if path.is_file() and path.name in ('model-events.jsonl','registry-events.jsonl','connect.trace','after-draft.txt'):
            out=evidence/path.relative_to(area);out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(clean(path.read_text()))
    locator=dict(area=str(area),paths={k:str(v) for k,v in paths.items()},workspace=str(workspace),sessions=sessions,evidence=str(evidence))
    (area/'fixture-locator.json').write_text(json.dumps(locator))
    print(json.dumps(dict(verdict=report['verdict'],modelCalls=model_calls,liveModelCalls=0,privateLocator=str(area/'fixture-locator.json'))))


if __name__=='__main__':main()
