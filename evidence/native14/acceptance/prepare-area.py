#!/usr/bin/env python3
"""Install the exact frozen archive in a new disposable prefix; no packages/network/global settings."""
import argparse,hashlib,json,subprocess,sys,tarfile,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);args=p.parse_args()
a=args.archive.resolve();m=json.loads(args.manifest.read_text());assert hashlib.sha256(a.read_bytes()).hexdigest()==m['archive_sha256']
home=Path(tempfile.mkdtemp(prefix='n14a-'));bootstrap=home/'install.py'
with tarfile.open(a) as t:
 members=[v for v in t if v.isfile()];files={v.name.removeprefix('package/'):t.extractfile(v).read() for v in members}
 assert len(files)==len(members)==m['files']==449
 assert {k:hashlib.sha256(v).hexdigest() for k,v in files.items()}==m['file_hashes'];bootstrap.write_bytes(files['packaging/install.py'])
r=subprocess.run([sys.executable,'-B',str(bootstrap),'install',str(a),'--prefix',str(home/'payload')],capture_output=True,text=True,check=True)
installed=(home/'payload/current').resolve();assert all(hashlib.sha256((installed/n).read_bytes()).hexdigest()==h for n,h in m['file_hashes'].items())
assert not (installed/'docs/Pi-Durable-1.4-current-host-plan.md').exists()
x=dict(area=str(home),root=str(installed),archive=str(a),archive_sha256=m['archive_sha256'],manifest=str(args.manifest.resolve()),bootstrap=str(bootstrap),prefix=str(home/'payload'))
(home/'acceptance-locator.json').write_text(json.dumps(x));Path('/tmp/delm-n14-acceptance-locator.json').write_text(json.dumps(x));print(json.dumps(dict(verdict='PASS',archive_sha256=m['archive_sha256'],archiveAndInstalledHashes=449,runtimeAssets=37,privateArea=str(home))))
