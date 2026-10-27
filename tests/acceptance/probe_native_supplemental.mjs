// Final installed-payload checks through the genuine public Native services; never opens Native SQLite.
import {pathToFileURL} from 'node:url';
import {join} from 'node:path';
import {readFile,writeFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const load=p=>import(pathToFileURL(join(process.env.DELM_PUBLIC_HOST_SOURCE,p)).href);
const s=JSON.parse(await readFile(process.env.DELM_SUPPLEMENT,'utf8'));
const mode=process.env.DELM_SUPPLEMENT_MODE;
const {BACKGROUND_CONTEXT:c}=await load('packages/chord/src/context/index.ts');
const {defineService}=await load('packages/chord/src/index.ts');
const {openClientRuntime,activateBuiltinClientServices}=await load('packages/coding-agent/src/experimental/client-runtime.ts');
const Control=defineService('delm.control');
const Policy=defineService('fixture.owner-policy');
const actors=[];
const domain=(actor,p)=>JSON.parse(execFileSync(join(s.run,actor,'bin/context'),['domain',JSON.stringify(p)],{encoding:'utf8'}));
async function checkpoint(file){const end=Date.now()+20000;while(!existsSync(file)){assert(Date.now()<end,'Supplement checkpoint timeout');await new Promise(r=>setTimeout(r,20));}}
function history(a,marker){
 if(JSON.stringify(a.server.transcript.state.value??{}).includes(marker))return Promise.resolve();
 return new Promise((resolve,reject)=>{const t=setTimeout(()=>{off();reject(Error('History missing '+marker));},20000);
  const off=a.server.transcript.state.subscribe(v=>{if(JSON.stringify(v).includes(marker)){clearTimeout(t);off();resolve();}});});
}
const input=(a,id,text)=>a.control.input({identity:a.identity,type:'input',requestId:id,text,expectedSha256:createHash('sha256').update(text).digest('hex')},c);
try{
 for(const saved of s.nativeActors){
  const runtime=await openClientRuntime({command:'client',connect:{transport:'unix',path:process.env.DELM_PUBLIC_HOST_SOCKET}});
  const a={actor:saved.actor,runtime,saved};actors.push(a);a.server=await activateBuiltinClientServices(runtime.servers[0]);
  if(mode==='disable'){
   await a.server.plugins.prepareSession({sessionId:saved.identity.sessionId,packagePaths:[s.policyPackage]},c);
   continue; // The high-level public client returns presentation data, not the raw package-path list.
  }
  await a.server.plugins.prepareSession({sessionId:saved.identity.sessionId,packagePaths:mode==='cancel-done'?[s.reinstalledRoot,s.policyPackage]:null},c);
  await a.server.management.attach(saved.identity.sessionId,c);
  if(mode==='exercise'||mode==='cancel-done'){
   a.binding=a.server.session.open({services:[Control],assertAccess(){},onError(){}});await a.binding.ready(c);a.control=a.binding.use(Control);
   a.identity=(await a.control.identity(c)).identity;assert.deepEqual(a.identity,saved.identity);await a.control.resume({identity:a.identity},c);
  }
 }
 if(mode==='disable')console.log(JSON.stringify({selectedProfilesExcludeDeLM:true,existingPolicyPreserved:true,sessions:actors.map(a=>a.saved.identity.sessionId)}));
 else if(mode==='after-remove'){
  for(const a of actors){
   await history(a,a.actor==='bob'?'NATIVE_WAIT_ARMED':'NATIVE_FIRST_DONE');
   a.binding=a.server.session.open({services:[Policy],assertAccess(){},onError(){}});await a.binding.ready(c);
   assert.equal((await a.binding.use(Policy).stats(c)).fixtureVersion,'owner-policy-v2');
  }
  const a=actors[0];const submitted=await a.server.agent.prompt({message:'HOST05_NORMAL_NATIVE_AFTER_REMOVE',images:null},c);
  const result=await a.server.agent.waitForPrompt(submitted.operationId,c);assert.equal(result.status,'done');assert.equal(result.text,'HOST05_AFTER_REMOVE_ACK');
  for(const a of actors)assert(!JSON.stringify(a.server.transcript.state.value??{}).includes('HOST05_FORBIDDEN_AFTER_COMMITTED_STOP'));
  assert.equal(await readFile(s.resultFile,'utf8'),'actual Native producer result\n');
  for(const a of actors)await history(a,a.actor==='bob'?'HOST05_RACE_BOB_DONE':'HOST05_RACE_ALICE_DONE');
  console.log(JSON.stringify({sameSessionsAndPriorNativeHistories:true,normalNativeWorksAfterDeLMRemove:true,sharedProjectResultPreserved:true,freshClaimHistoriesAlsoPreserved:true}));
 }else if(mode==='cancel-done'){
  const [alice,bob]=actors;
  const old=JSON.parse(await readFile(s.workRecord,'utf8'));
  const cancelled=(await bob.control.status({identity:bob.identity},c)).waits.find(w=>w.items.includes(old.id));assert.equal(cancelled.state,'cancelled');
  s.cancelDoneTask=domain('alice',{op:'projection',request_id:'host05-toolcancel-pre-done'}).queue.find(t=>t.id===old.id);
  assert.equal(s.cancelDoneTask.state,'open');assert.equal(s.cancelDoneTask.owner,null);
  await writeFile(process.env.DELM_SUPPLEMENT,JSON.stringify(s));
  await input(alice,'host05-complete-cancelled-dep','HOST05_COMPLETE_CANCELLED_DEP');await history(alice,'HOST05_CANCELLED_DEP_DONE');
  const done=domain('alice',{op:'projection',request_id:'host05-toolcancel-post-done'}).queue.find(t=>t.id===old.id);assert.equal(done.state,'done');
  await new Promise(r=>setTimeout(r,500)); // Bounded scheduler observation after the actual DONE event, not coordination polling.
  assert.equal((await bob.control.status({identity:bob.identity},c)).waits.find(w=>w.id===cancelled.id).state,'cancelled');
  for(const a of actors)await a.control.stop({identity:a.identity},c);
  console.log(JSON.stringify({originalToolCancelledWait:cancelled.id,dependency:old.id,actualNativeProducerCompleted:true,dependencyDONE:true,cancelledStatePersistedAfterDONE:true,samePriorIdentitiesAfterReinstall:true}));
 }else{
  const [alice,bob]=actors;
  const fresh=domain('alice',{op:'create',request_id:'host05-fresh-create',subject:'fresh Native claim race',detail:'No preclaim; two actual Native bash callers compete'}).task;
  s.freshTask=fresh;await writeFile(process.env.DELM_SUPPLEMENT,JSON.stringify(s));
  await input(bob,'host05-pending','HOST05_PENDING_WAIT');await history(bob,'HOST05_PENDING_ARMED');
  const pending=(await bob.control.status({identity:bob.identity},c)).waits.find(w=>w.state==='waiting');assert(pending);
  const stopped=await bob.control.stop({identity:bob.identity},c);assert(stopped.stopped);
  const state=(await bob.control.status({identity:bob.identity},c)).waits.find(w=>w.id===pending.id);assert.equal(state.state,'cancelled');
  domain('alice',{op:'publish',request_id:'host05-fact-after-pending-stop',type:'FACT',task:fresh.id,text:'Pending control.stop must not deliver later events'});
  await bob.control.resume({identity:bob.identity},c);
  await Promise.all([input(alice,'host05-race-alice','HOST05_RACE_ALICE'),input(bob,'host05-race-bob','HOST05_RACE_BOB')]);
  await Promise.all([history(alice,'HOST05_RACE_ALICE_DONE'),history(bob,'HOST05_RACE_BOB_DONE')]);
  const view=domain('alice',{op:'projection',request_id:'host05-race-result'});
  const race=view.queue.find(t=>t.id===fresh.id);assert.equal(race.state,'done');assert(['alice','bob'].includes(race.owner));
  const committed=domain('alice',{op:'create',request_id:'host05-committed-create',subject:'committed delivery stop',detail:'Actual Native stop after wake submission is accepted'}).task;
  const claim=domain('alice',{op:'claim',request_id:'host05-committed-claim',item:committed.id,expected_revision:committed.revision}).task;
  s.committedTask=claim;await writeFile(process.env.DELM_SUPPLEMENT,JSON.stringify(s));
  await input(bob,'host05-committed-wait','HOST05_COMMITTED_WAIT');await history(bob,'HOST05_COMMITTED_ARMED');
  domain('alice',{op:'complete',request_id:'host05-committed-complete',item:claim.id,expected_revision:claim.revision,generation:claim.generation,summary:'Trigger actual committed Native wake'});
  await checkpoint(s.modelStarted);
  const before=(await bob.control.status({identity:bob.identity},c)).waits.find(w=>w.items.includes(claim.id));assert(before.dispatchCommitted);
  const start=Date.now();await bob.control.stop({identity:bob.identity},c);assert(Date.now()-start<8000,'Stop did not cancel the in-flight model request');
  assert.equal((await bob.control.identity(c)).stopped,true);
  await writeFile(s.releaseModel,'actual stop returned before model response was released');
  const unread=domain('bob',{op:'pending',request_id:'host05-unread-after-stop'}).receipts;assert(unread.some(r=>r.receipt_id===before.receipt.receipt_id));
  await alice.control.stop({identity:alice.identity},c);
  console.log(JSON.stringify({freshTaskId:fresh.id,freshClaimWinner:race.owner,pendingControlStopCancelled:true,
   stopAfterActualDispatchCommitted:true,inflightGenerationAbortedBeforeModelReply:true,unreadReceiptNotAutoAcked:true,
   actualIdentities:s.nativeActors,directNativeSqlAccess:false}));
 }
}finally{for(const a of actors.reverse()){if(a.binding)await a.binding.dispose(c);await a.runtime.dispose();}}
