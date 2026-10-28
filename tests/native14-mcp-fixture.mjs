// SDK unit fixture only. Actual Native MCP transport is checked by the installed-host probe.
import { defineExtension, defineTool } from '@earendil-works/pi-durable';
import { createCodemodeExtension } from '@earendil-works/pi-durable/codemode';
import { CodemodeSandbox } from '@earendil-works/pi-codemode';
import { Type } from '@earendil-works/pi-ai';

export function withFixtureMcp(base) {
  const codemode = createCodemodeExtension({ sandbox: new CodemodeSandbox(), models: false });
  base.install(defineExtension({ ...codemode, name: 'configured-mcp', tools: [
    ...codemode.tools,
    defineTool({ name: 'mcp_status', description: 'Synthetic SDK fixture status, not a real connection.',
      parameters: Type.Object({}), replay: 'safe',
      execute: async () => ({ output: [{ type: 'text', text: '{"servers":[]}' }] }) }),
  ] }));
  return base;
}
