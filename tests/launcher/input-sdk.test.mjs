// TEST ONLY: existing public SDK host + disposable SQLite/faux, never production admission.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { BACKGROUND_CONTEXT as context } from '@earendil-works/chord/context';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider, fauxAssistantMessage } from '@earendil-works/pi-ai/providers/faux';
import { Harness, createRegistry } from '@earendil-works/pi-durable';
import { openNodeSqliteStorage } from '@earendil-works/pi-durable/storage/sqlite/node';
import { createNativeInput } from '../../skills/delm/Tools/NativeInput.mjs';

async function fixture() {
  const directory = await mkdtemp(join(tmpdir(), 'delm-input-'));
  const session = join(directory, 'session.sqlite');
  const faux = fauxProvider(), models = createModels();
  models.setProvider(faux.provider);
  faux.setResponses([fauxAssistantMessage('fixture approved input received')]);
  let host, root;
  async function open() {
    host = await Harness.open(await openNodeSqliteStorage(session), { registry: createRegistry(), models }, context);
    root = await host.root(context, { agent: { model: { provider: 'faux', modelId: 'faux-1' } } });
    host.resume();
  }
  await open();
  const text = '[bootstrap-fixture] original approved request, not a conversation dump';
  return { get host() { return host; }, get root() { return root; }, session,
    async reopen() { await host.close(context); await open(); },
    input: { requestId: 'bootstrap-fixture', text, expectedSha256: createHash('sha256').update(text).digest('hex') },
    async close() { await host.close(context); await rm(directory, { recursive: true, force: true }); },
  };
}

test('actual SDK input delivery replays accepted request without duplicate admission', async () => {
  const f = await fixture();
  let calls = 0;
  try {
    const deliver = createNativeInput({ host: f.host, conversation: f.root, session: f.session,
      expectedSession: f.session, admitInput: async () => { calls++; } });
    const first = await deliver(f.input, context);
    assert.equal(first.accepted, true); assert.equal(first.replay, false);
    const replay = await deliver(f.input, context);
    assert.equal(replay.replay, true); assert.equal(calls, 1);
    const accepted = await f.host.commit(tx => tx.submissionByRequest(f.root.id, f.input.requestId), context);
    assert.equal(accepted.conversationId, f.root.id);
  } finally { await f.close(); }
});

test('lost accepted response is reconciled from public durable receipt', async () => {
  const f = await fixture();
  let admissions = 0;
  try {
    const wrapper = { id: f.root.id, submit: async (input, ctx) => {
      await f.root.submit(input, ctx);
      throw Error('fixture loses response after accepted input');
    } };
    const deliver = createNativeInput({ host: f.host, conversation: wrapper, session: f.session,
      expectedSession: f.session, admitInput: async () => { admissions++; } });
    await assert.rejects(deliver(f.input, context), /loses response/);
    const exactSession = f.session;
    await f.reopen();
    const resumed = createNativeInput({ host: f.host, conversation: f.root, session: f.session,
      expectedSession: exactSession, admitInput: async () => { admissions++; } });
    assert.equal((await resumed(f.input, context)).replay, true);
    assert.equal(admissions, 1);
  } finally { await f.close(); }
});

test('changed approved payload with correct new digest cannot reuse an accepted request after reopen', async () => {
  const f = await fixture();
  let admissions = 0;
  try {
    const bind = () => createNativeInput({ host: f.host, conversation: f.root, session: f.session,
      expectedSession: f.session, admitInput: async () => { admissions++; } });
    await bind()(f.input, context);
    await f.reopen();
    const changed = 'different original approved prompt B';
    await assert.rejects(bind()({ ...f.input, text: changed,
      expectedSha256: createHash('sha256').update(changed).digest('hex') }, context), /binding|different|reconcile/i);
    assert.equal((await bind()(f.input, context)).replay, true);
    assert.equal(admissions, 1);
  } finally { await f.close(); }
});

test('existing external request without approved binding or with write type is not certified as input delivery', async () => {
  const f = await fixture();
  try {
    await f.root.submit({ type: 'input', requestId: f.input.requestId, content: f.input.text }, context);
    const deliver = createNativeInput({ host: f.host, conversation: f.root, session: f.session,
      expectedSession: f.session, admitInput: async () => { throw Error('must not admit'); } });
    await assert.rejects(deliver(f.input, context), /binding|reconcile/i);
    await f.host.commit(tx => tx.createSubmission({ type: 'write', conversationId: f.root.id,
      requestId: 'external-write', status: 'queued' }), context);
    await assert.rejects(deliver({ ...f.input, requestId: 'external-write' }, context), /type|binding|reconcile/i);
  } finally { await f.close(); }
});

test('actual native SDK admission does not require a private extra host policy', async () => {
  const f = await fixture();
  try {
    const deliver = createNativeInput({ host: f.host, conversation: f.root, session: f.session,
      expectedSession: f.session });
    assert.equal((await deliver(f.input, context)).accepted, true);
    await f.reopen();
    const reopened = createNativeInput({ host: f.host, conversation: f.root, session: f.session,
      expectedSession: f.session });
    assert.equal((await reopened(f.input, context)).replay, true);
  } finally { await f.close(); }
});

test('invalid extra policy, wrong exact session, edited input and real extra denial fail closed', async () => {
  const f = await fixture();
  try {
    const binding = { host: f.host, conversation: f.root, session: f.session, expectedSession: f.session };
    assert.throws(() => createNativeInput({ ...binding, admitInput: true }), /admission/);
    assert.throws(() => createNativeInput({ ...binding, expectedSession: join(f.session, '..'), admitInput: async () => {} }), /session mismatch/);
    const deliver = createNativeInput({ ...binding, admitInput: async () => { throw Error('fixture denied'); } });
    await assert.rejects(deliver({ ...f.input, text: 'changed' }, context), /fingerprint/);
    await assert.rejects(deliver(f.input, context), /denied/);
    assert.equal(await f.host.commit(tx => tx.submissionByRequest(f.root.id, f.input.requestId), context), undefined);
  } finally { await f.close(); }
});
