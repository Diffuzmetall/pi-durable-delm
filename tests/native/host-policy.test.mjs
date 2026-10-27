// SDK regression only, not real-host discovery or deterministic-host acceptance.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { BACKGROUND_CONTEXT as context } from '@earendil-works/chord/context';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai/providers/faux';
import { Harness, MemoryStorage, createRegistry, defineExtension, hook, ToolTask } from '@earendil-works/pi-durable';
import install, { DelmWaitDoc } from '../../extensions/delm/index.js';

test('native admission keeps the existing host beforeTool guard effective', async () => {
  const run = await mkdtemp(join(tmpdir(), 'delm-host-policy-'));
  let host;
  try {
    await writeFile(join(run, 'config.json'), JSON.stringify({ workspace: process.cwd(), actors: { bob: {} } }));
    let blocked = 0;
    const base = createRegistry();
    base.install(defineExtension({ name: 'owner-policy', hooks: [hook(ToolTask, {
      beforeTool: call => {
        if (call.name === 'delm_wait') { blocked++; return { block: 'owner host policy denied' }; }
      },
    })] }));
    // No author-private admission callback, no approval stub, no replacement coding tools.
    const registry = install(base, { run, actor: 'bob' });
    const faux = fauxProvider(), models = createModels(); models.setProvider(faux.provider);
    faux.setResponses([
      fauxAssistantMessage(fauxToolCall('delm_wait', { action: 'wait', items: ['not-read'], reason: 'guard probe' }), { stopReason: 'toolUse' }),
      fauxAssistantMessage('host guard retained'),
    ]);
    host = await Harness.open(new MemoryStorage(), { registry, models }, context);
    const root = await host.root(context, { agent: { model: { provider: 'faux', modelId: 'faux-1' } } });
    await (await root.submit({ type: 'input', content: 'check host guard' }, context)).wait(context);
    assert.equal(blocked, 1);
    assert.equal(await host.snapshot(DelmWaitDoc, root.id, context), undefined);
  } finally { if (host) await host.close(context); await rm(run, { recursive: true, force: true }); }
});
