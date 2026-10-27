// Client only: the authorized endpoint belongs to the existing Native process.
import { readFileSync, lstatSync, realpathSync } from 'node:fs';
import { dirname, isAbsolute } from 'node:path';
import { createConnection } from 'node:net';
import { randomUUID } from 'node:crypto';

try {
  const { socket, method, identity, payload = {} } = JSON.parse(readFileSync(0, 'utf8'));
  if (typeof socket !== 'string' || !isAbsolute(socket)) throw Error('Absolute private control socket required');
  const parent = lstatSync(dirname(socket)), endpoint = lstatSync(socket);
  if (!parent.isDirectory() || parent.isSymbolicLink() || parent.uid !== process.getuid() || (parent.mode & 0o077) ||
      realpathSync(dirname(socket)) !== dirname(socket) || !endpoint.isSocket() || endpoint.isSymbolicLink() ||
      endpoint.uid !== process.getuid() || (endpoint.mode & 0o077)) throw Error('Unsafe Native control endpoint');
  if (!['identity', 'input', 'status', 'stop', 'resume'].includes(method)) throw Error('Unsupported control method');
  const id = randomUUID();
  const request = JSON.stringify({ ...payload, id, method, ...(identity ? { identity } : {}) }) + '\n';
  if (Buffer.byteLength(request) > 1048576) throw Error('Approved control request exceeds transport bound');
  const result = await new Promise((resolve, reject) => {
    const connection = createConnection(socket);
    let buffer = Buffer.alloc(0);
    connection.setTimeout(20000, () => connection.destroy(Error('Native control timed out; retain exact request')));
    connection.once('connect', () => connection.write(request));
    connection.once('error', reject);
    connection.once('end', () => reject(Error('Native response lost; retain exact request')));
    connection.on('data', chunk => {
      buffer = Buffer.concat([buffer, chunk]);
      if (buffer.length > 1048576) { connection.destroy(Error('Native response exceeds bound')); return; }
      const end = buffer.indexOf(10);
      if (end < 0) return;
      try {
        const frame = JSON.parse(buffer.subarray(0, end).toString('utf8'));
        if (frame.id !== id || typeof frame.ok !== 'boolean') throw Error('Mismatched Native response');
        if (!frame.ok) throw Error(`Native refused control: ${String(frame.error?.code ?? 'CONTROL_ERROR')}`);
        resolve(frame.result);
      } catch (error) { reject(error); }
      finally { connection.destroy(); }
    });
  });
  console.log(JSON.stringify({ delm_control: 14, result }));
} catch (error) {
  console.error(error instanceof Error ? error.message : 'Native control failed');
  process.exitCode = 1;
}
