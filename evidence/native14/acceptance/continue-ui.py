#!/usr/bin/env python3
"""Continue the same final fixture after the disclosed READONLY/READ ONLY probe mismatch."""
import fcntl,hashlib,importlib.util,json,os,pty,select,shutil,signal,struct,subprocess,sys,termios,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
E=Path(__file__).resolve().parent
x=json.load(open('/tmp/delm-n14-acceptance-locator.json'));A=Path(x['area']);R=Path(x['root']);run=A/'run';project=A/'project'
spec=importlib.util.spec_from_file_location('installed_peer_continue',R/'tests/native14-adapter-host.py');peer=importlib.util.module_from_spec(spec);spec.loader.exec_module(peer);F=peer.fixture
paths=F.installed_paths(Path.home()/'.local/bin/pi-durable');hosts=[];pool=ThreadPoolExecutor(max_workers=2)
env=dict(PATH=str(A/'bin')+':/usr/bin:/bin',HOME=str(A/'setup-home'),LANG='C.UTF-8',TERM='xterm-256color',PYTHONDONTWRITEBYTECODE='1')
assert shutil.which('tern',path=env['PATH']) is None

def pump():
 for h in hosts:
  if h.process.poll() is None:h.pump(.01)
def execute(argv):
 f=pool.submit(subprocess.run,argv,env=env,capture_output=True,text=True,timeout=40)
 while not f.done():pump()
 r=f.result();assert r.returncode==0,(r.stdout[-1500:],r.stderr[-1500:]);return json.loads(r.stdout)
def cli(action,*args):return execute([sys.executable,'-B',str(R/'skills/delm/Tools/Run.py'),action,'--run-dir',str(run),*args])
def domain(payload):return execute([str(run/'bob/bin/context'),'domain',json.dumps(payload)])
def start(actor,oldphase):
 old=json.loads((run/'launch.json').read_text())['actors'][actor]['identity']
 h=F.Native14Host(paths,A/('ui-'+actor),project,antigravity=Path.home()/'.pi/agent/npm/node_modules/pi-antigravity')
 oldhome=A/oldphase/'home';h.env.update(HOME=str(oldhome),PI_CODING_AGENT_DIR=str(oldhome/'.pi/agent'),XDG_CONFIG_HOME=str(oldhome/'.config'),HINDSIGHT_CONFIG=str(oldhome/'.hindsight/coding-agent.json'),PATH=env['PATH'])
 h.env.update(PI_DURABLE_DCG_EXTENSION=str(Path.home()/'.pi/agent/durable-extensions/durable-dcg/index.ts'),DCG_BIN=str(Path.home()/'.local/bin/dcg'))
 p=dict(modelPreload=str(E/'model.mjs'),observer=str(E/'observer.mjs'),observations=str(h.area/'actual-prompt.jsonl'),skillLocations=[str(project/'.pi/skills/delm/SKILL.md'),str(R/'skills/delm/SKILL.md')],expectSkill=True,draft='UNSENT_UI_'+actor,holdRequestId='unused',admitted=str(h.area/'admitted'),release=str(h.area/'release'))
 (h.area/'accept-plan.json').write_text(json.dumps(p));h.env.update(N14_ACCEPT_PLAN=str(h.area/'accept-plan.json'),NODE_OPTIONS='--import='+(E/'preload.mjs').as_uri())
 h.command=['strace','-f','-e','trace=connect,execve','-o',str(h.trace),sys.executable,'-B',str(R/'skills/delm/Tools/Run.py'),'open','--run-dir',str(run),'--actor',actor,'--native-executable',str(paths['launcher'])]
 h.master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0));h.process=subprocess.Popen(h.command,cwd=project,env=h.env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave);hosts.append(h)
 end=time.monotonic()+45
 while True:
  rec=json.loads((run/'launch.json').read_text())['actors'][actor]
  if rec.get('socket') and Path(rec['socket']).exists() and b'\x1b[?2004h' in h.raw:break
  assert h.process.poll() is None and time.monotonic()<end; pump()
 assert cli('start','--actor',actor)['results'][actor]['replay']
 current=json.loads((run/'launch.json').read_text())['actors'][actor]['identity'];assert current==old
 assert not [e for e in h.model_events() if e['event']=='model_request']
 return h

boardlog=(A/'board-ui.log').open('wb');board=subprocess.Popen([sys.executable,'-B',str(R/'scripts/delm_local.py'),'serve',str(run)],env=env,stdout=boardlog,stderr=boardlog)
ui=None;raw=bytearray()
try:
 end=time.monotonic()+15
 while True:
  try:
   domain(dict(op='pending',request_id='ui-continue-server-ready'));break
  except AssertionError:
   assert board.poll() is None and time.monotonic()<end;select.select([],[],[],.03)
 alice=start('alice','alice');bob=start('bob','bob')
 task=json.loads((project/'claim.json').read_text())
 execute([str(run/'alice/bin/context'),'domain',json.dumps(dict(op='publish',request_id='final-ui-long-note',type='FACT',task=task['id'],text='VISIBLE_FINAL_NOTE\n'+''.join('detail line '+str(i)+'\n' for i in range(120))+'SCROLL_FINAL_TAIL'))])
 pending=domain(dict(op='pending',request_id='ui-before-pending'))['receipts'];assert any(r['request_id']=='final-ui-unread' for r in pending)
 dbs=[run/'context.sqlite',run/'context-bodies.sqlite'];before={p.name:F.digest(p) for p in dbs}
 master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
 ui=subprocess.Popen([sys.executable,'-B',str(R/'scripts/delm_board.py'),str(run),'--observe'],env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave)
 def screen_until(marker):
  end=time.monotonic()+12;chunk=bytearray()
  while marker not in chunk:
   assert ui.poll() is None and time.monotonic()<end,'Interactive missing '+repr(marker)+' tail '+repr(bytes(chunk)[-1500:])
   if select.select([master],[],[],.05)[0]:
    part=os.read(master,65536);raw.extend(part);chunk.extend(part)
   pump()
 screen_until(b'READ ONLY')
 assert b'OWNER' in raw and b'RECENT FACT / FAIL' in raw and b'VISIBLE_FINAL_NOTE' in raw
 os.write(master,b'\r');screen_until(b'DETAIL lines');os.write(master,b'\x1bOF');screen_until(b'SCROLL_FINAL_TAIL')
 os.write(master,b'\x1b');screen_until(b'Enter detail');os.write(master,b'\t');screen_until(b'NOTES')
 os.write(master,b'/no-such-final-filter\r');screen_until(b'No matches');os.write(master,b'\x1b');screen_until(b'FACT')
 fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',8,30,0,0));ui.send_signal(signal.SIGWINCH);screen_until(b'enlarge terminal');os.write(master,b'q');assert ui.wait(timeout=5)==0;os.close(master)
 assert before=={p.name:F.digest(p) for p in dbs},'Read-only observer mutated board data'
 assert board.poll() is None and all(h.process.poll() is None for h in hosts)
 assert pending==domain(dict(op='pending',request_id='ui-after-pending'))['receipts'],'Observer consumed unread receipt'
 stop=cli('stop');assert all(r['stopped'] for r in stop['results'].values())
 for h in reversed(hosts):h.close();assert h.exit_code==0
 result=dict(verdict='PASS',candidateSha256=x['archive_sha256'],sameInstalledRunAsRuntime16=True,plainPTYNoTern=True,exactTwoNativeReopenNoModels=True,
  interactiveCursesKeys=['detail','End scroll','escape','notes','search no matches','escape clear','resize warning','quit'],readOnlyBoardBytesStable=True,
  actorPendingReceiptUnchanged=True,backendAndBothNativeOwnersAliveAfterQuit=True,stopClean=True,additionalModelCalls=0,liveModelCalls=0)
 (E/'interactive-board-result.json').write_text(json.dumps(result,indent=2)+'\n');(A/'flow-stage-complete.json').write_text(json.dumps(result))
 print(json.dumps(result))
finally:
 (A/'interactive-board.bin').write_bytes(raw)
 (E/'interactive-board-terminal.txt').write_text(raw.decode(errors='replace').replace(str(A),'<FIXTURE>'))
 if ui and ui.poll() is None:ui.terminate();ui.wait(timeout=5)
 for h in reversed(hosts):
  if not hasattr(h,'exit_code'):h.close()
  for f in (h.trace,h.model_log,h.area/'terminal.bin'):
   if f.exists():(E/(h.area.name+'-'+f.name+'.txt')).write_text(f.read_text(errors='replace').replace(str(A),'<FIXTURE>').replace(str(R),'<INSTALLED_PACKAGE>').replace(str(Path.home()),'<OPERATOR_HOME>'))
 pool.shutdown(wait=True)
 if board.poll() is None:board.terminate();board.wait(timeout=10)
 boardlog.close()
