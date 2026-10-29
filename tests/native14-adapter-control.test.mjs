// Focused real SDK1.4/SQLite + private in-owner endpoint. Controller/model doubles are TEST ONLY.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, lstat, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createConnection } from 'node:net';
import { randomUUID, createHash } from 'node:crypto';
import { BACKGROUND_CONTEXT as context } from '@earendil-works/chord/context';
import { Harness, createRegistry } from '@earendil-works/pi-durable';
import { openNodeSqliteStorage } from '@earendil-works/pi-durable/storage/sqlite/node';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider, fauxAssistantMessage } from '@earendil-works/pi-ai/providers/faux';
import install, { HINDSIGHT_CONTROLLER } from '../extensions/delm/native14.js';
import { NATIVE14_OWNER } from '../extensions/delm/native14-owner.js';
import { withFixtureMcp } from './native14-mcp-fixture.mjs';

const digest=text=>createHash('sha256').update(text).digest('hex');
function rpc(path,request) {
  return new Promise((resolve,reject)=>{
    const socket=createConnection(path); let buffer='';
    socket.setTimeout(10000,()=>socket.destroy(Error('SDK control timeout')));
    socket.on('error',reject);
    socket.on('connect',()=>socket.write(JSON.stringify({id:randomUUID(),...request})+'\n'));
    socket.on('data',chunk=>{buffer+=chunk;const end=buffer.indexOf('\n');if(end>=0){socket.destroy();resolve(JSON.parse(buffer.slice(0,end)));}});
  });
}
async function fixture({unsafe=false,actor='bob',title}={}) {
  const directory=await mkdtemp(join(tmpdir(),'n14-owner-'));
  const run=join(directory,'run'), native=join(directory,'session'), privateDir=join(directory,'ipc');
  await mkdir(run);await mkdir(native);await mkdir(privateDir,{mode:unsafe?0o755:0o700});
  await writeFile(join(run,'config.json'),JSON.stringify({workspace:process.cwd(),actors:{[actor]:{}}}));
  if(title!==undefined) await writeFile(join(native,'title.txt'),title);
  const faux=fauxProvider(),models=createModels();models.setProvider(faux.provider);
  faux.setResponses(Array.from({length:8},()=>fauxAssistantMessage('SDK owner received approved input')));
  let controller,host,root,socket,generation=0;
  async function open() {
    controller={binds:0,closes:0,admissions:[],onAdmit:async()=>{},
      async bind(){this.binds++;},async close(){this.closes++;},
      async admit(conversation,id,ctx){this.admissions.push(id);await this.onAdmit(conversation,id,ctx);}};
    const base=withFixtureMcp(createRegistry());Object.defineProperty(base,HINDSIGHT_CONTROLLER,{value:controller});
    socket=join(privateDir,`g${++generation}.sock`);
    const options={run,actor,controlSocket:socket};
    const registry=install(base,options);
    host=await Harness.open(await openNodeSqliteStorage(join(native,'session.sqlite')),{registry,models},context);
    root=await host.root(context,{agent:{cwd:process.cwd(),model:{provider:'faux',modelId:'faux-1'}}});
    await controller.bind({session:host,directory:native,context});host.resume();
    return {base,options};
  }
  const opened=await open();
  return {directory,run,native,opened,get host(){return host;},get root(){return root;},get controller(){return controller;},
    get socket(){return socket;},call:request=>rpc(socket,request),
    async reopen(){await controller.close();await host.close(context);return open();},
    async close(){await controller.close();await host.close(context);await rm(directory,{recursive:true,force:true});}};
}

test('current owner endpoint preserves bind/close, approval identity/type/SHA, replay, stopped state, reload and exact reopen',async()=>{
  const f=await fixture();
  try {
    assert.equal(f.controller.binds,1);
    assert.equal((await lstat(f.socket)).mode&0o777,0o600);
    const first=await f.call({method:'identity'});assert.equal(first.ok,true);
    const identity=first.result.identity;
    assert.equal(identity.protocol,'delm.native14.control.v1');assert.equal(identity.sdkVersion,'1.4.0');
    assert.equal(identity.sessionPath,join(f.native,'session.sqlite'));assert.equal(identity.actor,'bob');
    const text='[n14-sdk-input] approved исходный текст';
    const input={method:'input',identity,type:'input',requestId:'n14-stable',text,expectedSha256:digest(text)};
    assert.equal((await f.call(input)).result.replay,false);
    assert.equal((await f.call(input)).result.replay,true);
    assert.equal(f.controller.admissions.length,1);
    await f.root.waitForIdle(context);
    const changed={...input,text:text+' changed',expectedSha256:digest(text+' changed')};
    assert.equal((await f.call(changed)).ok,false);
    assert.equal((await f.call({...input,type:'write'})).error.code,'INVALID_REQUEST');
    for(const [key,value] of Object.entries({run:'/wrong',actor:'alice',workspace:'/wrong',sessionPath:'/wrong',sessionId:'wrong',instanceId:randomUUID(),conversationId:2,protocol:'wrong',sdkVersion:'0'}))
      assert.equal((await f.call({method:'status',identity:{...identity,[key]:value}})).error.code,'SCOPE_MISMATCH',key);
    const oldBind=f.controller.bind,oldClose=f.controller.close;
    const again=install(f.opened.base,f.opened.options);
    assert.equal(f.controller.bind,oldBind);assert.equal(f.controller.close,oldClose);
    assert.equal(again.snapshot().extension('delm').tools[0].name,'delm_wait');
    assert.equal((await f.call({method:'stop',identity})).result.stopped,true);
    assert.equal((await f.call({...input,requestId:'stopped'})).error.code,'STOPPED');
    assert.equal((await f.call({method:'resume',identity})).result.resumed,true);
    assert.equal(f.controller.admissions.length,1,'resume submitted a prompt');
    await f.reopen();
    const resumed=(await f.call({method:'identity'})).result.identity;
    assert.deepEqual(resumed,identity);
    assert.equal((await f.call(input)).result.replay,true);
    assert.equal(f.controller.admissions.length,0,'reopen replay re-admitted input');
    assert.deepEqual((await f.call({method:'status',identity})).result.waits,[]);
  } finally {await f.close();}
});

test('actor names become persistent Native titles before the TUI starts; reopen preserves custom titles',async()=>{
  for(const actor of ['alice','bob','carol','dave']) {
    const f=await fixture({actor});
    try {
      assert.equal(await readFile(join(f.native,'title.txt'),'utf8'),`DeLM ${actor[0].toUpperCase()}${actor.slice(1)}\n`);
      await writeFile(join(f.native,'title.txt'),'My review session\n');
      await f.reopen();
      assert.equal(await readFile(join(f.native,'title.txt'),'utf8'),'My review session\n');
      assert.equal(f.controller.admissions.length,0,'naming must not submit model input');
    } finally {await f.close();}
  }
  const f=await fixture({title:'Existing user title\n'});
  try {assert.equal(await readFile(join(f.native,'title.txt'),'utf8'),'Existing user title\n');}
  finally {await f.close();}
});

test('stop racing a held real admission prevents subsequent submit without touching approved bytes or original owner close',async()=>{
  const f=await fixture();
  try {
    const identity=(await f.call({method:'identity'})).result.identity;
    let entered,release;
    const started=new Promise(resolve=>{entered=resolve;});
    const held=new Promise(resolve=>{release=resolve;});
    f.controller.onAdmit=async()=>{entered();await held;};
    const text='approved but held at policy boundary';
    const pending=f.call({method:'input',identity,type:'input',requestId:'held-policy',text,expectedSha256:digest(text)});
    await started;
    assert.equal((await f.call({method:'stop',identity})).result.stopped,true);
    release();assert.equal((await pending).error.code,'STOPPED');
    assert.equal(await f.host.commit(tx=>tx.submissionByRequest(f.root.id,'held-policy'),context),undefined);
    assert.equal(f.controller.closes,0,'actor stop closed the existing Native owner');
    f.controller.onAdmit=async()=>{};
    await f.call({method:'resume',identity});
    assert.equal((await f.call({method:'input',identity,type:'input',requestId:'held-policy',text,expectedSha256:digest(text)})).ok,true);
    await f.root.waitForIdle(context);
  } finally {await f.close();}
});

test('insecure control parent disables DeLM only, retaining the original successful owner bind',async()=>{
  const f=await fixture({unsafe:true});
  try {
    assert.equal(f.controller.binds,1);assert.equal(f.controller.closes,0);
    assert.equal(f.controller[NATIVE14_OWNER].failure.code,'SCOPE_MISMATCH');
    await f.controller.admit(f.root,'unrelated-native-owner-policy',context);
    assert.equal(f.controller.admissions.length,1);
  } finally {await f.close();}
});
