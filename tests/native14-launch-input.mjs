// Unit-only input fences using the existing SDK resolver; NOT Native execution/admission proof.
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { ROOT_CONVERSATION_ID } from '@earendil-works/pi-durable';
import { createNativeInput, InputBindings } from '../skills/delm/Tools/NativeInput.mjs';

const directory = mkdtempSync(join(tmpdir(), 'delm-input-unit-'));
const session = join(directory, 'synthetic-session.fixture');
writeFileSync(session, 'Not a Native database. Unit identity fixture only.');
const checks = [];
const payload = (text = 'approved\r\ninput\n') => ({ requestId: 'approved-request', text,
  expectedSha256: createHash('sha256').update(text).digest('hex') });
function owner({ deny = false, loseResponse = false } = {}) {
  const doc = { requests: {} }, submissions = new Map();
  const calls = { admit: 0, submit: 0 };
  const conversation = { id: ROOT_CONVERSATION_ID, async submit(input) {
    calls.submit++;
    submissions.set(input.requestId, { type: input.type });
    if (loseResponse) throw Error('Synthetic response loss after acceptance');
  } };
  const host = { async commit(body) { return body({
    async doc(definition, id) { assert.equal(definition, InputBindings); assert.equal(id, ROOT_CONVERSATION_ID); return doc; },
    async submissionByRequest(id, request) { assert.equal(id, ROOT_CONVERSATION_ID); return submissions.get(request); },
  }); } };
  const admitInput = async () => { calls.admit++; if (deny) throw Error('Synthetic admission denied'); };
  const options = { host, conversation, session, expectedSession: session, admitInput };
  return { doc, submissions, calls, options, input: createNativeInput(options) };
}
async function check(name, body) { await body(); checks.push(name); }
try {
  await check('approved CRLF input accepts once and replays same request', async () => {
    const o = owner();
    assert.equal((await o.input(payload(), {})).replay, false);
    assert.equal((await o.input(payload(), {})).replay, true);
    assert.deepEqual(o.calls, { admit: 1, submit: 1 });
  });
  await check('matching new SHA cannot change accepted request bytes', async () => {
    const o = owner(); await o.input(payload(), {});
    await assert.rejects(o.input(payload('changed input'), {}), /approval binding differs/);
    assert.deepEqual(o.calls, { admit: 1, submit: 1 });
  });
  await check('bad approval SHA refuses before admission or submission', async () => {
    const o = owner(); await assert.rejects(o.input({ ...payload(), expectedSha256: '0'.repeat(64) }, {}), /fingerprint mismatch/);
    assert.deepEqual(o.calls, { admit: 0, submit: 0 });
  });
  await check('admission denial propagates and no submission follows', async () => {
    const o = owner({ deny: true }); await assert.rejects(o.input(payload(), {}), /admission denied/);
    assert.deepEqual(o.calls, { admit: 1, submit: 0 });
    assert.equal(o.doc.requests['input:approved-request'].sha256, payload().expectedSha256);
  });
  await check('changed payload after denied admission still refuses', async () => {
    const o = owner({ deny: true }); await assert.rejects(o.input(payload(), {}), /admission denied/);
    await assert.rejects(o.input(payload('changed'), {}), /approval binding differs/);
    assert.deepEqual(o.calls, { admit: 1, submit: 0 });
  });
  await check('lost acceptance response reconciles without second submit', async () => {
    const o = owner({ loseResponse: true }); await assert.rejects(o.input(payload(), {}), /response loss/);
    const reopened = createNativeInput(o.options);
    assert.equal((await reopened(payload(), {})).replay, true);
    assert.deepEqual(o.calls, { admit: 1, submit: 1 });
  });
  await check('accepted request without approval binding refuses', async () => {
    const o = owner(); o.submissions.set('approved-request', { type: 'input' });
    await assert.rejects(o.input(payload(), {}), /no matching input approval/);
    assert.deepEqual(o.calls, { admit: 0, submit: 0 });
  });
  await check('different accepted request type refuses', async () => {
    const o = owner(); await o.input(payload(), {}); o.submissions.set('approved-request', { type: 'interrupt' });
    await assert.rejects(o.input(payload(), {}), /binding\/type/);
    assert.deepEqual(o.calls, { admit: 1, submit: 1 });
  });
  await check('non-root or wrong physical session refuses at construction', async () => {
    const o = owner();
    assert.throws(() => createNativeInput({ ...o.options, conversation: { ...o.options.conversation, id: 2 } }), /root conversation/);
    const other = join(directory, 'other.fixture'); writeFileSync(other, 'Other unit fixture');
    assert.throws(() => createNativeInput({ ...o.options, expectedSession: other }), /session mismatch/);
  });
  console.log(JSON.stringify({ kind: 'SDK_MODULE_UNIT_ONLY', passed: checks.length, checks,
    models: 0, nativeHarnessCreated: false, realAdmissionPolicyTested: false,
    note: 'Admission spy and in-memory transaction are unit fixtures, never a runtime policy substitute.' }));
} finally { rmSync(directory, { recursive: true, force: true }); }
