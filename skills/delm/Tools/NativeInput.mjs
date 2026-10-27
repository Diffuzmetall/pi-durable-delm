// Public-SDK input component for an EXISTING host; not a host, CLI transport or admission policy.
import { createHash } from 'node:crypto';
import { realpathSync } from 'node:fs';
import { defineDoc, ROOT_CONVERSATION_ID } from '@earendil-works/pi-durable';

// Bind approval before external admission/submit so queued and lost-response
// recovery cannot confuse a different payload with an already accepted request.
export const InputBindings = defineDoc({ kind: 'delm.launch.inputs', version: 1, scope: 'conversation',
  history: 'latest', fork: 'initial', checkpointWhen: () => false, initial: () => ({ requests: {} }) });

export function createNativeInput({ host, conversation, session, expectedSession, admitInput }) {
  if (typeof admitInput !== 'function') throw Error('Real host protected-input admission capability required');
  if (!host?.commit || !conversation?.submit || conversation.id !== ROOT_CONVERSATION_ID)
    throw Error('Existing public SDK host and bound root conversation required');
  if (!session || !expectedSession || realpathSync(session) !== realpathSync(expectedSession))
    throw Error('Exact recorded Native session mismatch; no input submitted');
  return async ({ requestId, text, expectedSha256 }, context) => {
    if (typeof requestId !== 'string' || !requestId.trim() || requestId.length > 256 || typeof text !== 'string' || !text)
      throw Error('Stable requestId and approved input text required');
    const digest = createHash('sha256').update(text).digest('hex');
    if (digest !== expectedSha256) throw Error('Approved input fingerprint mismatch; reconcile before delivery');
    const accepted = await host.commit(async tx => {
      const doc = await tx.doc(InputBindings, conversation.id);
      const key = `input:${requestId}`;
      const previous = doc.requests[key];
      const submission = await tx.submissionByRequest(conversation.id, requestId);
      if (previous && (previous.type !== 'input' || previous.sha256 !== digest))
        throw Error('Request approval binding differs; reconcile instead of reporting delivery');
      if (submission && (submission.type !== 'input' || !previous))
        throw Error('Accepted request has no matching input approval binding/type; reconcile explicitly');
      if (!previous) doc.requests[key] = { type: 'input', sha256: digest };
      return Boolean(submission);
    }, context);
    if (accepted) return { accepted: true, replay: true, requestId, conversationId: conversation.id };
    await admitInput(conversation, requestId, context);
    // Same request identity reconciles submit/response loss in the existing SDK.
    await conversation.submit({ type: 'input', content: text, requestId, whenBusy: 'followUp' }, context);
    return { accepted: true, replay: false, requestId, conversationId: conversation.id };
  };
}
