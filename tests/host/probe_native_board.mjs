// Actual Native clients + product control + model tool calls + authenticated actor CLI. No Harness/SQL.
import {pathToFileURL} from 'node:url';
import {join} from 'node:path';
import {readFile,writeFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {createHash, randomUUID} from 'node:crypto';
import assert from 'node:assert/strict';
const load = p => import(pathToFileURL(join(process.env.DELM_PUBLIC_HOST_SOURCE, p)).href);
const scenario = JSON.parse(await readFile(process.env.DELM_NATIVE_BOARD_SCENARIO, 'utf8'));
const phase = process.env.DELM_NATIVE_BOARD_PHASE;
assert(['arm','finish'].includes(phase));
const {BACKGROUND_CONTEXT: context} = await load('packages/chord/src/context/index.ts');
const {defineService} = await load('packages/chord/src/index.ts');
const {openClientRuntime, activateBuiltinClientServices} = await load('packages/coding-agent/src/experimental/client-runtime.ts');
const Control = defineService('delm.control');
const Policy = defineService('fixture.owner-policy');
const SessionPlugins = defineService('pi.session-plugins');
const actors = [];
function waitView(state, marker) {
  if (state.value !== undefined && JSON.stringify(state.value).includes(marker)) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { off(); reject(Error('Actual Native history missing ' + marker)); }, 25000);
    const off = state.subscribe(value => { if (JSON.stringify(value).includes(marker)) {clearTimeout(timer); off(); resolve();} });
  });
}
async function checkpoint(file) {
  const deadline=Date.now()+25000;
  while(!existsSync(file)) {assert(Date.now()<deadline,'Actual Native editor checkpoint missing'); await new Promise(r=>setTimeout(r,25));}
}
const rejected = p => assert.rejects(p, e => e.code === 'internal_error');
function input(identity, requestId, text) {
  return {identity, type:'input', requestId, text, expectedSha256:createHash('sha256').update(text).digest('hex')};
}
try {
  for (const actor of ['alice','bob']) {
    const runtime = await openClientRuntime({command:'client', connect:{transport:'unix',path:process.env.DELM_PUBLIC_HOST_SOCKET}});
    const entry = {actor,runtime}; actors.push(entry);
    entry.server = await activateBuiltinClientServices(runtime.servers[0]);
    const saved = scenario.nativeActors?.find(a=>a.actor===actor);
    const id = phase==='finish' ? saved.identity.sessionId : randomUUID();
    if(phase==='arm') await entry.server.management.create({id},context);
    await entry.server.plugins.prepareSession({sessionId:id,packagePaths:null},context);
    await entry.server.management.attach(id,context);
    entry.binding = entry.server.session.open({services:[Control,Policy,SessionPlugins],assertAccess(){},onError(){}});
    await entry.binding.ready(context);
    entry.control = entry.binding.use(Control);
    entry.policy = entry.binding.use(Policy);
    entry.identity = (await entry.control.identity(context)).identity;
    assert.equal(entry.identity.workspace,scenario.workspace);
    if(phase==='arm') {
      await entry.control.bind({identity:entry.identity,run:scenario.run,actor},context);
      assert.deepEqual((await entry.control.status({identity:entry.identity},context)).waits,[]);
    } else assert.deepEqual(entry.identity,saved.identity,'Restart changed exact Native identity/instance');
    assert.equal((await entry.control.identity(context)).binding.actor,actor);
  }
  const [alice,bob] = actors;
  const approved = input(bob.identity,'native-bob-wait','NATIVE_BOB_WAIT_TWO');
  if(phase==='arm') {
    assert.equal((await bob.control.input(approved,context)).replay,false);
    await waitView(bob.server.transcript.state,'NATIVE_WAIT_ARMED');
    const waits=(await bob.control.status({identity:bob.identity},context)).waits;
    assert.equal(waits.length,1); assert.equal(waits[0].state,'waiting');
    scenario.nativeActors=actors.map(a=>({actor:a.actor,identity:a.identity}));
    scenario.armedWaitId=waits[0].id;
    await writeFile(process.env.DELM_NATIVE_BOARD_SCENARIO,JSON.stringify(scenario));
    console.log(JSON.stringify({phase,actualNativeActors:scenario.nativeActors,persistedWait:waits[0].id}));
  } else {
  await waitView(bob.server.transcript.state,'NATIVE_WAIT_ARMED');
  let waits = (await bob.control.status({identity:bob.identity},context)).waits;
  assert.equal(waits.length,1); assert.equal(waits[0].state,'waiting');
  assert.equal(waits[0].id,scenario.armedWaitId,'Restart replaced pending wait');
  assert.deepEqual([...waits[0].items].sort(),[...scenario.items].sort());
  assert.equal((await bob.control.input(approved,context)).replay,true);
  await rejected(bob.control.input(input(bob.identity,approved.requestId,approved.text+' CHANGED'),context));
  await rejected(bob.control.input({...approved,type:'system'},context));
  for (const identity of [{...bob.identity,workspace:scenario.workspace+'/wrong'},alice.identity,
                         {...bob.identity,instanceId:randomUUID()}])
    await rejected(bob.control.status({identity},context));
  await rejected(bob.control.bind({identity:bob.identity,run:scenario.run,actor:'alice'},context));
  assert.equal((await bob.control.identity(context)).binding.actor,'bob');
  await writeFile(scenario.uiSession,JSON.stringify({sessionId:bob.identity.sessionId}));
  await checkpoint(scenario.uiDraftReady);
  const policySource=await readFile(scenario.policySource,'utf8');
  assert(policySource.includes('owner-policy-v1'));
  await writeFile(scenario.policySource,policySource.replace('owner-policy-v1','owner-policy-v2'));
  await bob.server.plugins.reload(context);
  await bob.binding.use(SessionPlugins).reload(context); // Same build + worker reload pair as Native's /reload.
  assert.equal((await bob.policy.stats(context)).fixtureVersion,'owner-policy-v2');
  assert.deepEqual((await bob.control.identity(context)).identity,bob.identity);
  const reloaded=(await bob.control.status({identity:bob.identity},context)).waits.find(w=>w.id===scenario.armedWaitId);
  assert.equal(reloaded.state,'waiting','Profile reload lost the existing DeLM waiter');
  await alice.control.input(input(alice.identity,'native-alice-first','NATIVE_ALICE_FIRST'),context);
  await waitView(alice.server.transcript.state,'NATIVE_FIRST_DONE');
  // Bounded real-runtime negative observation, not team/model polling or coordination sleep.
  await new Promise(resolve => setTimeout(resolve,400));
  waits = (await bob.control.status({identity:bob.identity},context)).waits;
  assert.equal(waits[0].state,'waiting','Exact woke before the second dependency completed');
  assert(!JSON.stringify(bob.server.transcript.state.value).includes('NATIVE_WAKE_ACKED'));
  await bob.control.input(input(bob.identity,'native-bob-second','NATIVE_BOB_SECOND'),context);
  await waitView(bob.server.transcript.state,'NATIVE_SECOND_DONE');
  await waitView(bob.server.transcript.state,'NATIVE_WAKE_ACKED');
  await checkpoint(scenario.uiWakeVerified);
  for(const a of actors) assert(!JSON.stringify(a.server.transcript.state.value).includes(scenario.uiDraft),'Unsent draft entered Native history');
  waits = (await bob.control.status({identity:bob.identity},context)).waits;
  assert.equal(waits[0].state,'sent'); assert.equal(waits[0].acked,true);
  assert.equal(waits[0].deliveryState,'acked');
  assert.equal(await readFile(scenario.resultFile,'utf8'),'actual Native producer result\n');
  assert.equal((await bob.control.input(approved,context)).replay,true);
  await bob.control.input(input(bob.identity,'native-work-arm','NATIVE_BOB_WORK'),context);
  await waitView(bob.server.transcript.state,'NATIVE_WORK_ARMED');
  let work=(await bob.control.status({identity:bob.identity},context)).waits.find(w=>w.mode==='work');
  assert.equal(work.state,'waiting');
  await alice.control.input(input(alice.identity,'native-create-work','NATIVE_ALICE_NEW_WORK'),context);
  await waitView(alice.server.transcript.state,'NATIVE_NEW_WORK_CREATED');
  await waitView(bob.server.transcript.state,'NATIVE_WORK_ACKED');
  work=(await bob.control.status({identity:bob.identity},context)).waits.find(w=>w.id===work.id);
  assert.equal(work.state,'sent'); assert.equal(work.acked,true); assert.equal(work.trigger.kind,'work');
  const available=JSON.parse(await readFile(scenario.workRecord,'utf8'));
  assert.equal(available.state,'open'); assert.equal(available.owner,null,'Work hint assigned ownership');
  await bob.control.input(input(bob.identity,'native-cancel-arm','NATIVE_BOB_CANCEL_ARM'),context);
  await waitView(bob.server.transcript.state,'NATIVE_CANCEL_ARMED');
  const cancellable=(await bob.control.status({identity:bob.identity},context)).waits.find(w=>w.state==='waiting');
  assert(cancellable);
  await bob.control.input(input(bob.identity,'native-cancel-now','NATIVE_BOB_CANCEL_NOW '+cancellable.id),context);
  await waitView(bob.server.transcript.state,'NATIVE_CANCELLED');
  await alice.control.input(input(alice.identity,'native-after-cancel','NATIVE_ALICE_AFTER_CANCEL'),context);
  await waitView(alice.server.transcript.state,'NATIVE_FACT_AFTER_CANCEL');
  await new Promise(resolve=>setTimeout(resolve,400));
  const cancelled=(await bob.control.status({identity:bob.identity},context)).waits.find(w=>w.id===cancellable.id);
  assert.equal(cancelled.state,'cancelled');
  assert.equal(JSON.parse(await readFile(scenario.workRecord,'utf8')).state,'open');
  await bob.control.stop({identity:bob.identity},context);
  await rejected(bob.control.input(input(bob.identity,'native-stopped-input','MUST_NOT_RUN_WHILE_STOPPED'),context));
  assert.equal((await bob.control.identity(context)).stopped,true);
  await bob.control.resume({identity:bob.identity},context);
  assert.equal((await bob.control.identity(context)).stopped,false);
  assert.deepEqual(await bob.policy.enable(context),{enabled:true});
  await bob.control.input(input(bob.identity,'native-existing-policy','NATIVE_OWNER_GUARD_PROBE'),context);
  await waitView(bob.server.transcript.state,'NATIVE_OWNER_GUARD_ACK');
  assert.deepEqual(await bob.policy.stats(context),{enabled:true,blocked:1,fixtureVersion:'owner-policy-v2'});
  assert(JSON.stringify(bob.server.transcript.state.value).includes('FIXTURE_EXISTING_OWNER_POLICY_DENIED'));
  assert.equal((await bob.control.status({identity:bob.identity},context)).waits.length,3,'Denied tool created a new waiter');
  await alice.control.stop({identity:alice.identity},context);
  console.log(JSON.stringify({actualNativeActors:actors.map(a=>({actor:a.actor,identity:a.identity})),
    actualBoundActorTools:true,claimResultEventWakeReadAck:true,exactPartialObservationMs:400,
    replayReturnedSameAcceptance:true,changedApprovedPayloadRejected:true,changedTypeRejected:true,
    wrongSessionWorkspaceInstanceRejected:true,actorRebindingRejected:true,stoppedInputRejected:true,
    resumeDidNotSubmitEditor:true,waitReceipt:waits[0].receipt,constructedHarness:false,
    exactIdentityAndPendingWaitPreservedAcrossServerRestart:true,
    actualExistingOwnerBeforeToolGuardPreserved:true,
    availableWorkHintAndReadAck:true,workDidNotAssignOwnership:true,cancelledWaitDidNotResumeOnFact:true,
    actualNativeProfileReloadPreservedPendingDeLMWait:true,actualPTYDraftPreservedAcrossReloadAndDeLMWake:true,
    draftAbsentFromBothNativeHistories:true,editorEnterNeverSent:true,
    note:'Real bound Native+restart+profile reload+DeLM-event editor+work+cancel+owner policy; installed archive/uninstall separate'}));
  }
} finally {
  for (const a of actors.reverse()) {if(a.binding) await a.binding.dispose(context); await a.runtime.dispose();}
}
