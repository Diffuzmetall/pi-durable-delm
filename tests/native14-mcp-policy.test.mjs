import test from 'node:test';
import assert from 'node:assert/strict';
import { createRegistry, defineExtension } from '@earendil-works/pi-durable';
import { createCodemodeExtension } from '@earendil-works/pi-durable/codemode';
import { CodingTools } from '@earendil-works/pi-durable/tools';
import { CodemodeSandbox } from '@earendil-works/pi-codemode';
import install, { HINDSIGHT_CONTROLLER } from '../extensions/delm/native14.js';

test('original SDK CodeMode registers coding tools without an MCP client', () => {
  const base = createRegistry();
  base.install(CodingTools);
  base.install(createCodemodeExtension({ sandbox: new CodemodeSandbox(), models: false }));
  const names = base.snapshot().tools().map(({ tool }) => tool.name);
  for (const name of ['read', 'write', 'edit', 'bash', 'codemode']) assert.ok(names.includes(name));
  assert.ok(!names.includes('mcp_status'));
});

test('production DeLM refuses Native without MCP before board/config IO', () => {
  const base = createRegistry();
  Object.defineProperty(base, HINDSIGHT_CONTROLLER, { value: { admit: async () => {} } });
  base.install(createCodemodeExtension({ sandbox: new CodemodeSandbox(), models: false }));
  assert.throws(() => install(base, { run: '/not-read', actor: 'alice' }), /MCP-enabled Native/);
});

test('production DeLM refuses an MCP registry missing builtin CodeMode', () => {
  const base = createRegistry();
  Object.defineProperty(base, HINDSIGHT_CONTROLLER, { value: { admit: async () => {} } });
  base.install(defineExtension({ name: 'configured-mcp' }));
  assert.throws(() => install(base, { run: '/not-read', actor: 'alice' }), /CodeMode/);
});
