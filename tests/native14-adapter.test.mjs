// SDK1.4-only focused adapter tests; actual installed-entrypoint acceptance is a separate fixture.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync, spawn } from 'node:child_process';
import { once } from 'node:events';
import { BACKGROUND_CONTEXT as context } from '@earendil-works/chord/context';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider, fauxAssistantMessage } from '@earendil-works/pi-ai/providers/faux';
import { Harness, MemoryStorage, createRegistry, defineExtension, hook, ToolTask } from '@earendil-works/pi-durable';
import install, { HINDSIGHT_CONTROLLER } from '../extensions/delm/native14.js';
import { DelmWaitDoc, wakeRequestId } from '../extensions/delm/index.js';

const project = new URL('../', import.meta.url).pathname;
async function until(check) {
  const deadline = Date.now() + 10000;
  while (!await check()) {
    if (Date.now() > deadline) throw Error('SDK fixture condition timed out');
    await new Promise(resolve => setTimeout(resolve, 15));
  }
}

test('current Native entry fails before config IO without the real capability and retains all owner descriptors/hooks', async () => {
  const base = createRegistry();
  assert.throws(() => install(base, { run: '/not-read', actor: 'bob', admitInput() {} }), /existing trusted Hindsight/);
  const directory = await mkdtemp(join(tmpdir(), 'n14-descriptors-'));
  try {
    await writeFile(join(directory, 'config.json'), JSON.stringify({workspace:process.cwd(), actors:{bob:{}}}));
    const policy = defineExtension({ name:'existing-owner', hooks:[hook(ToolTask, {beforeTool:() => ({block:'owner denied'})})] });
    base.install(policy);
    const controller = {admit:async () => { throw Error('SDK fixture policy'); }};
    Object.defineProperty(base, HINDSIGHT_CONTROLLER, {value:controller, configurable:false, enumerable:false});
    const other = Symbol.for('n14.fixture.owner-capability');
    Object.defineProperty(base, other, {get:() => controller, configurable:true, enumerable:false});
    const next = install(base, {run:directory, actor:'bob'});
    assert.equal(next.snapshot().extension('existing-owner'), policy);
    for (const key of [HINDSIGHT_CONTROLLER, other])
      assert.deepEqual(Object.getOwnPropertyDescriptor(next,key), Object.getOwnPropertyDescriptor(base,key));
    assert.equal(next.snapshot().extension('delm').tools[0].name,'delm_wait');
    const extensionBase = createRegistry();
    const hindsight = defineExtension({name:'hindsight'});
    Object.defineProperty(hindsight,HINDSIGHT_CONTROLLER,{value:controller});
    extensionBase.install(hindsight);
    assert.equal(install(extensionBase,{run:directory,actor:'bob'}).snapshot().extension('hindsight'),hindsight);
  } finally { await rm(directory,{recursive:true,force:true}); }
});

test('current Native entry keeps exact-DONE, effective-cwd denial, trusted denial and stable wake retry on SDK1.4', async () => {
  const directory = await mkdtemp(join(tmpdir(),'n14-wake-'));
  const run = join(directory,'board');
  const changedCwd = join(directory,'changed-cwd'); await mkdir(changedCwd);
  let server, host;
  try {
    execFileSync('python3',['-B',join(project,'scripts/delm_local.py'),'init',run,'--shared-workspace',process.cwd(),'--n','2','--task','SDK native14 fixture'],{stdio:'pipe'});
    server=spawn('python3',['-B',join(project,'scripts/delm_local.py'),'serve',run],{stdio:['ignore','pipe','pipe']});
    await once(server.stdout,'data');
    let number=0;
    const domain=(actor,args)=>JSON.parse(execFileSync(join(run,actor,'bin/context'),['domain',JSON.stringify({request_id:`n14-${++number}`,...args})],{encoding:'utf8'}));
    const tasks=[0,1].map(n=>domain('alice',{op:'create',subject:`output ${n}`,detail:'exact output'}) .task);
    const claims=tasks.map((t,n)=>domain(n===0?'alice':'bob',{op:'claim',item:t.id,expected_revision:t.revision}).task);
    const controller={deny:true,calls:[], async admit(conversation,id,ctx) {
      assert.equal(this,controller); assert.ok(ctx);
      this.calls.push(id); if(this.deny) throw Error('SDK fixture trusted policy denied');
    }};
    const base=createRegistry(); Object.defineProperty(base,HINDSIGHT_CONTROLLER,{value:controller});
    // A supplied policy must never override the actual host capability.
    const registry=install(base,{run,actor:'bob',admitInput:async()=>assert.fail('untrusted callback used')});
    const faux=fauxProvider(), models=createModels(); models.setProvider(faux.provider);
    faux.setResponses([fauxAssistantMessage('SDK wake accepted')]);
    host=await Harness.open(new MemoryStorage(),{registry,models},context);
    const root=await host.root(context,{agent:{cwd:process.cwd(),model:{provider:'faux',modelId:'faux-1'}}});
    const tool=registry.snapshot().extension('delm').tools[0];
    const direct=async(args,key='arm')=>(await tool.execute(args,{conversationId:root.id,taskId:key,callId:key,commit:fn=>host.commit(fn,context)},context)).structuredOutput.result;
    const doc=()=>host.snapshot(DelmWaitDoc,root.id,context);
    const armed=await direct({action:'wait',items:tasks.map(t=>t.id),reason:'BOTH outputs required'});
    host.resume();
    domain('alice',{op:'complete',item:claims[0].id,expected_revision:claims[0].revision,generation:claims[0].generation,summary:'first'});
    await new Promise(resolve=>setTimeout(resolve,120));
    assert.equal((await doc()).waits[armed.id].state,'waiting'); assert.equal(controller.calls.length,0);
    await root.configure({cwd:changedCwd},context);
    domain('bob',{op:'complete',item:claims[1].id,expected_revision:claims[1].revision,generation:claims[1].generation,summary:'second'});
    await until(async()=>(await doc()).waits[armed.id].state==='failed');
    assert.equal(controller.calls.length,0,'wrong effective cwd reached trusted admission');
    await root.configure({cwd:process.cwd()},context);
    await direct({action:'retry',id:armed.id},'policy-retry');
    await until(async()=>{
      const entry=(await doc()).waits[armed.id];
      if(entry.state==='failed') assert.equal(controller.calls.length,1,'trusted policy not reached after workspace restoration');
      return controller.calls.length===1 && entry.state==='failed';
    });
    assert.equal(await host.commit(tx=>tx.submissionByRequest(root.id,wakeRequestId(armed.taskId)),context),undefined);
    controller.deny=false;
    await direct({action:'retry',id:armed.id},'accepted-retry');
    await until(async()=>(await doc()).waits[armed.id].state==='sent');
    assert.deepEqual(controller.calls,[wakeRequestId(armed.taskId),wakeRequestId(armed.taskId)]);
    const accepted=await host.commit(tx=>tx.submissionByRequest(root.id,wakeRequestId(armed.taskId)),context);
    assert.ok(accepted);
    const status=await direct({action:'status'});
    assert.equal(status[0].requestId,wakeRequestId(armed.taskId));
    await assert.rejects(tool.execute({action:'status'},
      {conversationId:999,commit:()=>assert.fail('child committed')},context),/root conversation/);
    await root.waitForIdle(context);
  } finally {
    if(host) await host.close(context);
    if(server) {const closed=once(server,'close');server.kill('SIGTERM');await closed;}
    await rm(directory,{recursive:true,force:true});
  }
});
