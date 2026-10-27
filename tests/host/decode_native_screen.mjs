// Decode actual PTY output with the upstream's xterm-based test terminal, not a hand-written ANSI emulator.
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';
const { VirtualTerminal } = await import(pathToFileURL(join(process.env.DELM_PUBLIC_HOST_SOURCE,
  'packages/tui/test/virtual-terminal.ts')).href);
let input = '';
for await (const chunk of process.stdin) input += chunk;
const terminal = new VirtualTerminal(120, 38);
terminal.write(Buffer.from(input.trim(), 'base64').toString('utf8'));
await terminal.flush();
console.log(JSON.stringify(terminal.getViewport()));
