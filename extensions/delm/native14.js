// Current Native registry entry. Uses the existing host's real admission, never a policy substitute.
import { realpathSync } from 'node:fs';
import { AgentDoc, ROOT_CONVERSATION_ID } from '@earendil-works/pi-durable';
import install from './index.js';
import { prepareNative14Owner, Native14Binding } from './native14-owner.js';

export const HINDSIGHT_CONTROLLER = Symbol.for('pi.durable.hindsight.controller');

export default function installNative14(base, options = {}) {
  if (typeof base?.snapshot !== 'function' || typeof base?.subscribe !== 'function')
    throw Error('DeLM Native1.4 requires the existing Durable registry, not Pi ExtensionAPI');
  const controller = base[HINDSIGHT_CONTROLLER] ?? base.snapshot().extension('hindsight')?.[HINDSIGHT_CONTROLLER];
  if (typeof controller?.admit !== 'function')
    throw Error('DeLM Native1.4 requires the existing trusted Hindsight controller.admit; no fallback');
  const mcp = base.snapshot().installed().some(extension =>
    extension.name === 'configured-mcp' || extension.name.startsWith('mcp-codemode-'));
  if (!mcp) throw Error('DeLM requires MCP-enabled Native; do not start workers with --no-mcp');
  if (!base.snapshot().tools().some(({ tool }) => tool.name === 'codemode'))
    throw Error('DeLM requires the installed Native builtin CodeMode tool');
  const workspace = realpathSync(process.cwd());
  let owner;
  const registry = install(base, { ...options, admitInput: async (conversation, requestId, context, runtime) => {
    const check = async () => {
      if (conversation.id !== ROOT_CONVERSATION_ID) throw Error('DeLM Native1.4 admission is root-only');
      if (owner) await owner.active(context);
      // A task's conversation handle is not a Harness handle; read the actual root document through its runtime.
      const agent = await runtime.snapshot(AgentDoc, conversation.id, context);
      if (!agent?.cwd || realpathSync(agent.cwd) !== workspace)
        throw Error('DeLM Native1.4 effective workspace differs from the bound workspace');
    };
    await check(); await controller.admit(conversation, requestId, context); await check();
  } });
  if (options.controlSocket !== undefined) {
    owner = prepareNative14Owner(controller, { ...options, workspace });
    const module = registry.snapshot().extension('delm');
    const tool = module.tools[0]; owner.tool = tool;
    registry.install({ ...module, tools: [{ ...tool, execute: async (args, api, context) => {
      if (api.conversationId !== ROOT_CONVERSATION_ID) throw Error('DeLM Native1.4 tools are root-only');
      const starts = ['wait', 'work', 'retry'].includes(args.action);
      await owner.active(context, !starts, starts);
      return tool.execute(args, { ...api, commit: (fn, ctx) => api.commit(async tx => {
        if (starts && (await tx.doc(Native14Binding, ROOT_CONVERSATION_ID)).stopped)
          throw Error('DeLM actor is stopped');
        return fn(tx);
      }, ctx) }, context);
    } }] });
  }
  // Retain owner capabilities exactly, including non-enumerable symbols used during reload/binding.
  for (const key of Object.getOwnPropertySymbols(base))
    Object.defineProperty(registry, key, Object.getOwnPropertyDescriptor(base, key));
  return registry;
}
