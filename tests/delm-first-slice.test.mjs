import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { BACKGROUND_CONTEXT as context } from '@earendil-works/chord/context';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai/providers/faux';
import { Harness, createRegistry } from '@earendil-works/pi-durable';
import { openNodeSqliteStorage } from '@earendil-works/pi-durable/storage/sqlite/node';
import { createDelmWait, DelmWaitDoc, readBoard, wakeRequestId } from '../extensions/delm/index.js';

const project = new URL('../', import.meta.url).pathname;
async function until(check) {
  const deadline = Date.now() + 8000;
  while (!await check()) {
    if (Date.now() > deadline) throw Error('condition timed out');
    await new Promise(resolve => setTimeout(resolve, 15));
  }
}

test('first slice: real native + faux consumer resumes on early output, not producer remainder; delta wake', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'delm-first-slice-'));
  let host;
  try {
    const workspace = join(directory, 'shared'), run = join(directory, 'run');
    await mkdir(workspace);
    execFileSync('python3', [join(project, 'scripts/delm_local.py'), 'init', run,
      '--shared-workspace', workspace, '--n', '4', '--task', 'first-slice fixture']);
    const profile = await readFile(join(run, 'WORKER.md'), 'utf8');
    const board = expression => JSON.parse(execFileSync('python3', ['-c',
      `import sys,json;sys.path.insert(0,${JSON.stringify(join(project, 'scripts'))});from delm_local import board;from pathlib import Path;b=board(Path(${JSON.stringify(run)}));print(json.dumps(${expression}))`], { encoding: 'utf8' }));
    const output = board("b.reserve('alice','usable profile','early output')").item;
    const second = board("b.reserve('dave','second required output','ALL-DONE check')").item;
    const faux = fauxProvider(), models = createModels(), admissions = [], transcripts = [];
    models.setProvider(faux.provider);
    const registry = createRegistry();
    registry.install(createDelmWait({ run, actor: 'carol', admitInput: async (_conversation, id) => admissions.push(id) }));
    host = await Harness.open(await openNodeSqliteStorage(join(directory, 'native.sqlite')), { registry, models }, context);
    const root = await host.root(context, { agent: { model: { provider: 'faux', modelId: 'faux-1' } } });
    host.resume();
    faux.setResponses([
      transcript => {
        transcripts.push(JSON.stringify(transcript));
        return fauxAssistantMessage(fauxToolCall('delm_wait', { action: 'wait', items: [output, second], reason: 'need two usable outputs' }), { stopReason: 'toolUse' });
      },
      fauxAssistantMessage('waiting'),
    ]);
    await (await root.submit({ type: 'input', content: 'consume contract' }, context)).wait(context);
    const doc = () => host.snapshot(DelmWaitDoc, root.id, context);
    const entry = Object.values((await doc()).waits)[0];
    assert.equal(entry.state, 'waiting');
    assert.ok(transcripts[0].includes(JSON.stringify(profile).slice(1, -1)), 'native system section contains frozen worker snapshot');
    board("b.note('bob','FACT','unrelated event','other','fixture')");
    board(`b.done('alice',${JSON.stringify(output)},'usable profile delivered')`);
    const remainder = board("b.reserve('alice','producer remainder','not required by consumer')").item;
    await new Promise(resolve => setTimeout(resolve, 100));
    assert.equal(admissions.length, 0, 'one DONE plus unrelated FACT cannot satisfy ALL-DONE');
    assert.equal((await doc()).waits[entry.id].state, 'waiting');
    faux.setResponses([transcript => {
      transcripts.push(JSON.stringify(transcript));
      return fauxAssistantMessage('resumed in same conversation');
    }]);
    board(`b.done('dave',${JSON.stringify(second)},'second output delivered')`);
    await until(async () => (await doc()).waits[entry.id].state === 'sent' && transcripts.length === 2);
    const receipt = await host.commit(tx => tx.submissionByRequest(root.id, wakeRequestId(entry.taskId)), context);
    assert.equal(receipt.conversationId, root.id);
    assert.deepEqual(admissions, [wakeRequestId(entry.taskId)]);
    assert.equal(readBoard(run).tasks[remainder].state, 'claimed');
    const wakeMessage = JSON.parse(transcripts[1]).messages.filter(message => message.role === 'user').at(-1);
    const wake = typeof wakeMessage.content === 'string' ? wakeMessage.content : wakeMessage.content.map(block => block.text ?? '').join('\n');
    assert.match(wake, /context read for the normal board delta/);
    assert.match(wake, /context read --all only for genuine recovery/);
    assert.doesNotMatch(wake, /Read your START\.md and context read --all/);
    assert.match(profile, /recovery/);
  } finally {
    if (host) await host.close(context);
    await rm(directory, { recursive: true, force: true });
  }
});
