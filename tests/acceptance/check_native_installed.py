#!/usr/bin/env python3
"""Run the SHIPPED Native E2E from a fresh payload install; public host source is external TEST data only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--host-fixture',type=Path,required=True)
    parser.add_argument('--evidence-dir',type=Path,required=True)
    args=parser.parse_args()
    archive=args.archive.resolve(); evidence=args.evidence_dir.resolve();evidence.mkdir(parents=True,exist_ok=True)
    base=json.loads(args.host_fixture.read_text())
    assert Path(base['source']).resolve().is_relative_to(args.host_fixture.resolve().parent), 'Only the owned disposable public fixture may be copied'
    source_record=json.loads((Path(base['evidence'])/'public-host-discovery.json').read_text())
    patch_record=json.loads((Path(base['evidence'])/'api-patch.json').read_text())
    assert source_record['revision']=='cd32f7725fdbddbaecdff5b1e68491563394e0ca'
    changed={p for p,h in source_record['source_hashes'].items() if hashlib.sha256((Path(base['source'])/p).read_bytes()).hexdigest()!=h}
    assert changed==set(patch_record['postimages'])
    for p,h in patch_record['postimages'].items(): assert hashlib.sha256((Path(base['source'])/p).read_bytes()).hexdigest()==h
    sandbox=Path(tempfile.mkdtemp(prefix='h5-'))
    source=sandbox/'u';home=sandbox/'h';workspace=sandbox/'w';prefix=sandbox/'payload'
    # Existing PUBLIC test snapshot, not a new dependency installation or any shipped host/framework.
    shutil.copytree(base['source'],source,ignore=shutil.ignore_patterns('node_modules','.git'))
    home.mkdir();workspace.mkdir()
    env=base['env']|{'HOME':str(home),'PI_CODING_AGENT_DIR':str(home/'.pi/agent'),'TMPDIR':str(sandbox),'PYTHONDONTWRITEBYTECODE':'1'}
    with tarfile.open(archive) as tar:
        bootstrap=tar.extractfile('package/packaging/install.py').read()
        assets=json.loads(tar.extractfile('package/provenance.json').read())['files']
        names=[m.name for m in tar.getmembers()]
        assert not any('vendor/pi-native/' in n or n.startswith('package/packages/coding-agent/') for n in names)
    manager=sandbox/'install.py';manager.write_bytes(bootstrap)
    subprocess.run([sys.executable,'-B',str(manager),'install',str(archive),'--prefix',str(prefix)],
                             env=env,check=True,capture_output=True,text=True)
    root=(prefix/'current').resolve()
    for a in assets:assert hashlib.sha256((root/a['target']).read_bytes()).hexdigest()==a['packaged_sha256'],a['target']
    skill=workspace/'.pi/skills/delm';skill.parent.mkdir(parents=True)
    skill.symlink_to(root/'skills/delm',target_is_directory=True)  # Atomic creation, no overwrite/global settings.
    locator=sandbox/'fixture.json'
    fixture=base|dict(source=str(source),home=str(home),project=str(workspace),env=env,evidence=str(evidence/'core'))
    Path(fixture['evidence']).mkdir()
    locator.write_text(json.dumps(fixture))
    sys.path.insert(0,str(root/'tests/host'))
    spec=importlib.util.spec_from_file_location('installed_native_case',root/'tests/host/smoke_native_board.py')
    case=importlib.util.module_from_spec(spec);spec.loader.exec_module(case)
    Model=case.DeterministicProvider
    observations=[]
    locations=[str(p) for p in (root/'skills/delm/SKILL.md',skill/'SKILL.md',prefix/'current/skills/delm/SKILL.md')]
    class ObserveActualModelRequest(Model):
        def __init__(self,replies):
            def observe(request):
                system='\n'.join(str(m['content']) for m in request['messages'] if m['role']=='system')
                matched=next((p for p in locations if p in system),None)
                assert '<name>delm</name>' in system and matched,'Actual Native prompt did not advertise the installed DeLM skill/location'
                observations.append(dict(skill='delm',location=matched.replace(str(sandbox),'<TEST_FIXTURE>'),
                                         system_sha256=hashlib.sha256(system.encode()).hexdigest()))
                return replies(request)
            super().__init__(observe)  # Observe ONLY the fake model input; host/discovery/admission remain genuine.
    case.DeterministicProvider=ObserveActualModelRequest
    previous=sys.argv
    try:
        sys.argv=[str(root/'tests/host/smoke_native_board.py'),'--fixture',str(locator)]
        case.main()
    finally:sys.argv=previous
    result=json.loads((evidence/'core/board-e2e/result.json').read_text())
    assert len(observations)==24 and result['deterministic_http_requests']==24
    report=dict(schema=1,verdict='INSTALLED_NATIVE_CORE_AND_NATIVE_SKILL_PROMPT_PASS',
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),runtime_assets=len(assets),
        runtime_assets_verified=True,actual_native_case='core/board-e2e/result.json',
        normal_native_skill_discovery='project-local .pi/skills/delm symlink before first model request',
        actual_model_request_skill_observations=observations,host_source_shipped=False,
        fake_host_or_discovery_or_admission=False,live_model_calls=0,
        limits=['This stage does not yet cover fresh claim competition, pending/committed control.stop or disable/uninstall'])
    (evidence/'installed-native.json').write_text(json.dumps(report,indent=2)+'\n')
    private=dict(fixture=str(locator),installed_root=str(root),prefix=str(prefix),archive=str(archive),evidence=str(evidence),workspace=str(workspace))
    (sandbox/'installed-locator.json').write_text(json.dumps(private))
    print(json.dumps(dict(verdict=report['verdict'],archive_sha256=report['archive_sha256'],skill_requests=len(observations),
                          private_locator=str(sandbox/'installed-locator.json'))))


if __name__=='__main__':main()
