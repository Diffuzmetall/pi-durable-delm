// Native session facet. Requires the explicit local-only API proposal, not a private host.
import { randomUUID } from 'node:crypto';
import { realpathSync } from 'node:fs';
import { defineFacet } from '@earendil-works/chord';
import { BACKGROUND_CONTEXT } from '@earendil-works/chord/context';
import { defineDoc, section, ROOT_CONVERSATION_ID } from '@earendil-works/pi-durable';
import * as NativeAPI from '@earendil-works/pi-coding-agent/experimental/plugin';
import { createDelmWait, DelmWaitDoc, DELM_BUILD, wakeRequestId } from './index.js';
import { createNativeInput } from '../../skills/delm/Tools/NativeInput.mjs';

import { DeLMControl, HOST_PROTOCOL } from './control.js';
export { DeLMControl } from './control.js';
export const HostBinding = defineDoc({ kind: 'delm.host.binding', version: 1, scope: 'conversation',
  history: 'latest', fork: 'initial', checkpointWhen: () => false,
  initial: () => ({ instanceId: null, binding: null, registration: null, stopped: false }) });

const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export const facets = [defineFacet({ id: 'delm.native-session', setup(env) {
  if (!NativeAPI.DurableSession) throw Error('DeLM requires Native DurableSession local API v1; stock v1.0.2 needs the documented minimal API patch');
  const capability = env.use(NativeAPI.DurableSession);
  let owner, registration;

  const commit = (change, context) => owner.harness.commit(change, context);
  async function identity(context) {
    const actual = owner.binding;
    const instanceId = await commit(async tx => {
      const doc = await tx.doc(HostBinding, owner.conversation.id);
      if (!doc.instanceId) doc.instanceId = randomUUID();
      return doc.instanceId;
    }, context);
    return { sessionId: actual.sessionId, sessionPath: realpathSync(actual.sessionPath),
      workspace: realpathSync(actual.workspace), conversationId: owner.conversation.id, instanceId };
  }
  async function checkIdentity(expected, context) {
    const actual = await identity(context);
    if (!object(expected) || Object.keys(actual).some(key => expected[key] !== actual[key]))
      throw Error('DeLM exact session/workspace/instance binding mismatch');
    return actual;
  }
  async function bound(context, allowStopped = false, requireWorkspace = true) {
    const doc = await owner.harness.snapshot(HostBinding, owner.conversation.id, context);
    if (!doc?.binding || !doc.registration) throw Error('DeLM session is not bound/enabled');
    await checkIdentity(doc.binding.identity, context);
    if (requireWorkspace) {
      const agent = await owner.conversation.agent(context);
      if (!agent.cwd || realpathSync(agent.cwd) !== doc.binding.identity.workspace)
        throw Error('DeLM actual native workspace changed');
    }
    if (doc.stopped && !allowStopped) throw Error('DeLM session is stopped; resume explicitly before input');
    return doc.binding;
  }
  async function authorize(conversation, _requestId, context) {
    if (conversation.id !== owner.conversation.id) throw Error('DeLM wrong native conversation');
    await bound(context);
  }
  async function installBinding(binding, context) {
    await checkIdentity(binding.identity, context);
    const module = createDelmWait({ run: binding.run, actor: binding.actor, admitInput: authorize });
    const original = module.tools[0];
    const guarded = { ...original, execute: async (args, api, ctx) => {
      await bound(ctx, args.action === 'status' || args.action === 'cancel');
      if (api.conversationId !== owner.conversation.id) throw Error('DeLM wrong native conversation');
      const guardedApi = { ...api, commit: (fn, c) => api.commit(async tx => {
        if (['wait', 'work', 'retry'].includes(args.action)) {
          const doc = await tx.doc(HostBinding, owner.conversation.id);
          if (doc.stopped || !doc.registration) throw Error('DeLM session is stopped/disabled');
        }
        return fn(tx);
      }, c) };
      return original.execute(args, guardedApi, ctx);
    } };
    registration = randomUUID();
    await commit(async tx => {
      const doc = await tx.doc(HostBinding, owner.conversation.id);
      doc.registration = registration;
    }, context);
    const cli = `${binding.run}/${binding.actor}/bin/context`;
    const quotedCli = `'${cli.replaceAll("'", "'\\''")}'`;
    owner.registry.install({ ...module, tools: [guarded], sections: [...module.sections,
      section('delm-native-cli', () => `The bound context CLI is ${quotedCli}. Wherever frozen instructions or wake references show context, invoke this absolute CLI instead. Do not use another installation's context or change global PATH. Your exact Native session is ${binding.identity.sessionId}.`)] });
  }
  async function cancelEntries(context, all = false) {
    const doc = await owner.harness.snapshot(DelmWaitDoc, owner.conversation.id, context);
    const results = [];
    for (const entry of Object.values(doc?.waits ?? {})) {
      if (!['waiting', 'failed'].includes(entry.state)) continue;
      const accepted = await commit(tx => tx.submissionByRequest(owner.conversation.id, wakeRequestId(entry.taskId)), context);
      if (!all && (accepted || entry.dispatchCommitted)) {
        results.push({ id: entry.id, cancelRefused: true }); continue;
      }
      const taskId = entry.watcherTaskId ?? entry.taskId;
      await owner.harness.abortTask(taskId, context);
      await owner.harness.waitForTask(taskId, context);
      results.push({ id: entry.id, aborted: true });
    }
    return results;
  }

  env.provide(DeLMControl, {
    async identity(context) {
      const id = await identity(context);
      const doc = await owner.harness.snapshot(HostBinding, owner.conversation.id, context);
      return { protocol: HOST_PROTOCOL, build: DELM_BUILD, identity: id, binding: doc?.binding ?? null, stopped: Boolean(doc?.stopped) };
    },
    async bind(request, context) {
      if (!object(request) || !text(request.run) || !text(request.actor)) throw Error('DeLM bind requires run and actor');
      const id = await checkIdentity(request.identity, context);
      const run = realpathSync(request.run);
      // The same core constructor validates the actor and run before any binding is saved.
      createDelmWait({ run, actor: request.actor, admitInput: authorize });
      const { readFile } = await import('node:fs/promises');
      const { join } = await import('node:path');
      const config = JSON.parse(await readFile(join(run, 'config.json'), 'utf8'));
      if (realpathSync(config.workspace ?? join(run, request.actor, 'workspace')) !== id.workspace)
        throw Error('DeLM board workspace does not match actual native session');
      const binding = { identity: id, run, actor: request.actor };
      await commit(async tx => {
        const doc = await tx.doc(HostBinding, owner.conversation.id);
        if (doc.binding && !same(doc.binding, binding)) throw Error('DeLM actor/run binding is immutable; use its exact recorded session');
        doc.binding = binding;
      }, context);
      await installBinding(binding, context);
      return { bound: true, identity: id, run, actor: binding.actor };
    },
    async input(request, context) {
      await checkIdentity(request?.identity, context);
      const binding = await bound(context);
      if (request.type !== 'input') throw Error('DeLM control only admits approved input type');
      const deliver = createNativeInput({ host: owner.harness, conversation: owner.conversation,
        session: binding.identity.sessionPath, expectedSession: binding.identity.sessionPath, admitInput: authorize });
      return deliver(request, context);
    },
    async status(request, context) {
      await checkIdentity(request?.identity, context);
      await bound(context, true, false);
      const doc = await owner.harness.snapshot(DelmWaitDoc, owner.conversation.id, context);
      return { waits: Object.values(doc?.waits ?? {}), stopped: Boolean((await owner.harness.snapshot(HostBinding, owner.conversation.id, context))?.stopped) };
    },
    async resume(request, context) {
      await checkIdentity(request?.identity, context);
      await bound(context, true);
      await commit(async tx => { (await tx.doc(HostBinding, owner.conversation.id)).stopped = false; }, context);
      return { resumed: true }; // Reopening never manufactures a model input.
    },
    async stop(request, context) {
      await checkIdentity(request?.identity, context);
      // Cleanup remains possible after a cwd change; it touches only this bound session.
      await bound(context, true, false);
      await commit(async tx => { (await tx.doc(HostBinding, owner.conversation.id)).stopped = true; }, context);
      const waits = await cancelEntries(context, true);
      await owner.conversation.abort(context);
      await owner.conversation.waitForIdle(context);
      return { stopped: true, waits };
    },
  });
  env.onActivate(async () => {
    owner = await capability.get(BACKGROUND_CONTEXT);
    if (owner.apiVersion !== 1 || owner.conversation.id !== ROOT_CONVERSATION_ID)
      throw Error('Unsupported Native DurableSession API/root conversation');
    const doc = await owner.harness.snapshot(HostBinding, owner.conversation.id, BACKGROUND_CONTEXT);
    if (doc?.binding) await installBinding(doc.binding, BACKGROUND_CONTEXT);
  });
  env.onDeactivate(async () => {
    if (!owner || !registration) return;
    const current = await owner.harness.snapshot(HostBinding, owner.conversation.id, BACKGROUND_CONTEXT);
    // A retired facet must never uninstall the replacement installed by reload.
    if (current?.registration !== registration) return;
    // Native worker shutdown also deactivates facets. Preserve pending waits for reopen;
    // explicit stop is the operation that cancels work before disabling/uninstalling.
    owner.registry.uninstall({ name: 'delm' });
  });
} })];

// The public Chord bundle loader consumes imported.default, not a named facets export.
export default facets;
