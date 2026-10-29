import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { BACKGROUND_CONTEXT as context } from '@earendil-works/chord/context';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai/providers/faux';
import { Harness, createRegistry } from '@earendil-works/pi-durable';
import { openNodeSqliteStorage } from '@earendil-works/pi-durable/storage/sqlite/node';
import { createDelmWait } from '../extensions/delm/index.js';

const project = new URL('../', import.meta.url).pathname;

// Inspect the actual provider request, including positional system deltas, not section.render alone.
function sections(request) {
  const result = new Map();
  for (const message of request.messages) if (message.role === 'system') {
    for (const [key, value] of Object.entries(message.sections ?? {})) {
      if (value === null) result.delete(key); else result.set(key, value);
    }
  }
  return result;
}

test('frozen contract reaches real SDK requests across tools, turns, compaction and reopen without extra generation', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'delm-contract-'));
  let host;
  try {
    const workspace = join(directory, 'workspace'), run = join(directory, 'run');
    await mkdir(workspace);
    execFileSync('python3', [join(project, 'scripts/delm_local.py'), 'init', run,
      '--shared-workspace', workspace, '--n', '2', '--task', 'contract delivery fixture']);
    const frozen = await readFile(join(run, 'WORKER.md'), 'utf8');
    assert.equal(frozen, await readFile(join(project, 'prompts/delm-worker.md'), 'utf8'));
    for (const text of ['REAL end-to-end', 'minimal executable contract', 'small explicit interfaces',
      'Affinity is not permanent', 'skill body and required references', 'Recovery after resume/compaction',
      'Claim/decomposition/handoff', 'Milestone acceptance', 'Before waiting', 'ONE candidate']) {
      assert.ok(frozen.includes(text), `missing principle: ${text}`);
    }
    const starts = await Promise.all(['alice', 'bob'].map(actor => readFile(join(run, actor, 'START.md'), 'utf8')));
    const faux = fauxProvider(), models = createModels(); models.setProvider(faux.provider);
    const requests = [], reports = [];
    const capture = response => request => {
      requests.push(structuredClone(request));
      return response;
    };
    const open = async () => {
      const registry = createRegistry();
      registry.install(createDelmWait({ run, actor: 'bob' }));
      host = await Harness.open(await openNodeSqliteStorage(join(directory, 'native.sqlite')), {
        registry, models, settings: { retry: { maxRetries: 0 }, compaction: { enabled: false, keepRecentTokens: 1 } },
        onReport: (error, info) => reports.push({ message: String(error), type: info.type }),
      }, context);
      const root = await host.root(context, { agent: { model: { provider: 'faux', modelId: 'faux-1' }, cwd: workspace } });
      host.resume();
      return root;
    };
    let root = await open();
    assert.equal(requests.length, 0, 'opening does not generate a model turn');
    faux.setResponses([
      capture(fauxAssistantMessage(fauxToolCall('delm_wait', { action: 'status' }), { stopReason: 'toolUse' })),
      capture(fauxAssistantMessage('status checked')),
      ...Array.from({ length: 3 }, () => capture(fauxAssistantMessage('checked increment'))),
    ]);
    for (let turn = 0; turn < 4; turn++) {
      const result = await (await root.submit({ type: 'input', content: `turn ${turn}: ${'fixture context '.repeat(100)}` }, context)).wait(context);
      assert.equal(result.status, 'done');
    }
    assert.equal(requests.length, 5, 'four inputs plus one tool continuation only');
    const expected = sections(requests[0]).get('delm');
    assert.ok(expected.includes(frozen));
    for (const request of requests) assert.equal(sections(request).get('delm'), expected);
    assert.ok(requests[0].messages.some(message => message.toolsAdded?.some(tool =>
      tool.name === 'delm_wait' && tool.description.includes('Before waiting'))));

    // This is real SDK compaction with a deterministic summary, not a helper-only head simulation.
    faux.setResponses([capture(fauxAssistantMessage('Fixture summary: preserve ownership and original criteria.'))]);
    const id = await root.compact('Preserve the current fixture task', context);
    const { outcome } = (await host.waitForTask(id, context)).state;
    assert.equal(outcome.status, 'completed');
    assert.ok(outcome.result.submissionId, 'compaction must actually place a context head');
    assert.equal((await (await host.submission(outcome.result.submissionId, context)).wait(context)).status, 'done');
    assert.equal(requests.length, 6, 'one explicit summary request, no automatic generation');
    faux.setResponses([capture(fauxAssistantMessage('after compaction'))]);
    assert.equal((await (await root.submit({ type: 'input', content: 'continue after compaction' }, context)).wait(context)).status, 'done');
    assert.equal(sections(requests[6]).get('delm'), expected, 'complete contract restored after the new context head');
    assert.ok(!JSON.stringify(requests[6]).includes('turn 0:'), 'old context was actually removed');

    await host.close(context); host = undefined;
    root = await open();
    assert.equal(requests.length, 7, 'reopen/resume is not a model input');
    faux.setResponses([capture(fauxAssistantMessage('after reopen'))]);
    assert.equal((await (await root.submit({ type: 'input', content: 'continue recovered task' }, context)).wait(context)).status, 'done');
    assert.equal(sections(requests[7]).get('delm'), expected);
    await root.waitForIdle(context);
    assert.equal(requests.length, 8);
    assert.deepEqual(reports, []);
    assert.equal(await readFile(join(run, 'WORKER.md'), 'utf8'), frozen);
    assert.deepEqual(await Promise.all(['alice', 'bob'].map(actor => readFile(join(run, actor, 'START.md'), 'utf8'))), starts);
  } finally {
    await host?.close(context);
    await rm(directory, { recursive: true, force: true });
  }
});

test('loading a historical run preserves its frozen contract rather than substituting the new template', async () => {
  const run = await mkdtemp(join(tmpdir(), 'delm-old-contract-'));
  try {
    await writeFile(join(run, 'config.json'), JSON.stringify({ actors: { alice: {} } }));
    const old = '# Historical contract\nOriginal authorized scope only.\n';
    await writeFile(join(run, 'WORKER.md'), old);
    for (let reload = 0; reload < 2; reload++) {
      const extension = createDelmWait({ run, actor: 'alice' });
      assert.ok(extension.sections[0].render().endsWith(old));
      assert.ok(!extension.sections[0].render().includes('Working discipline and lifecycle checkpoints'));
      assert.equal(await readFile(join(run, 'WORKER.md'), 'utf8'), old);
    }
  } finally { await rm(run, { recursive: true, force: true }); }
});
