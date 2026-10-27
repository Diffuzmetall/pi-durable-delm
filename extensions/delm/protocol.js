import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { join } from 'node:path';
const execute = promisify(execFile);

/** Pure protocol-v2 event projection. No actor read cursor or native storage access. */
export function projectEvents(rows, actors = []) {
  const tasks = new Map(), notes = [], sessions = new Map(), statuses = new Map(), resolved = new Set(), attached = new Map();
  const events = rows.map(row => {
    let payload = typeof row.payload === 'string' ? JSON.parse(row.payload) : structuredClone(row.payload);
    if (row.kind === 'read') payload = { via: payload.via ?? null };
    return { sequence: row.sequence, actor: row.actor, kind: row.kind, payload };
  });
  for (const { sequence, actor, kind, payload: p } of events) {
    if (kind === 'item') tasks.set(p.id, { ...p, state: 'open', owner: null, generation: 0, revision: sequence,
      deps: [], criteria: [], parent: null, outputs: [], mapping: {} });
    else if (kind === 'task') tasks.set(p.task.id, { ...structuredClone(p.task), revision: sequence });
    else if (kind === 'claim' && tasks.has(p.item)) {
      const task = tasks.get(p.item);
      Object.assign(task, { state: 'claimed', owner: actor, generation: task.generation + 1, revision: sequence });
    } else if (kind === 'done' && tasks.has(p.item)) Object.assign(tasks.get(p.item), {
      state: 'done', owner: actor, summary: p.summary, publication_id: p.publication_id ?? p.item, revision: sequence });
    else if (kind === 'note' || kind === 'publication') {
      notes.push({ ...p, actor, sequence });
      if (['CORRECTION', 'RESOLUTION'].includes(p.type)) for (const id of p.resolves ?? []) resolved.add(id);
    } else if (kind === 'lifecycle') sessions.set(p.actor, { ...p });
    else if (kind === 'session' && (sessions.get(p.actor)?.generation ?? 0) === 0)
      sessions.set(p.actor, { actor: p.actor, state: p.state, generation: 0 });
    else if (kind === 'status') statuses.set(actor, p.text);
    else if (kind === 'body') attached.set(p.id, p.files);
  }
  for (const task of tasks.values()) {
    const id = task.publication_id ?? task.id;
    if (attached.has(id)) task.files = attached.get(id);
  }
  for (const note of notes) if (attached.has(note.id)) note.files = attached.get(note.id);
  const blockers = notes.filter(note => note.type === 'FAIL' && !resolved.has(note.id));
  const dependencies = (id, seen = new Set()) => {
    if (seen.has(id)) return seen;
    seen.add(id);
    for (const dep of [...(tasks.get(id)?.deps ?? []), ...(tasks.get(id)?.outputs ?? [])]) dependencies(dep, seen);
    return seen;
  };
  const queue = [...tasks.values()].map(task => {
    const ids = dependencies(task.id);
    const relevant = blockers.filter(note => [note.task, note.output, ...(note.related ?? [])].some(id => ids.has(id)));
    return { ...task, blockers: relevant, readiness: task.state === 'open' &&
      (task.deps ?? []).every(id => tasks.get(id)?.state === 'done') && relevant.length === 0 };
  });
  return { protocol: 2, sequence: events.reduce((maximum, row) => Math.max(maximum, row.sequence), 0), agents: [...actors], queue, notes, blockers,
    sessions: [...actors].map(actor => sessions.get(actor) ?? { actor, state: 'starting', generation: 0 }),
    status: [...statuses].map(([actor, text]) => ({ actor, text })), events };
}

/** Successful dependency readiness is separate from information requiring reevaluation. */
export function waitTrigger(entry, snapshot) {
  if (entry.mode === 'work') {
    const own = snapshot.queue.filter(task => task.owner === entry.actor && ['claimed', 'blocked'].includes(task.state));
    const lifecycle = snapshot.sessions?.find(session => session.actor === entry.actor);
    if (['blocked', 'ended'].includes(lifecycle?.state) || own.some(task => task.state === 'blocked' || task.blockers?.length))
      return { kind: 'reevaluate', reason: 'bound actor or assigned work is blocked/ended; reconcile before taking work', tasks: own.map(task => task.id) };
    // A direct handoff after arming must not strand the newly assigned owner.
    const candidates = own.length ? own : snapshot.queue.filter(task => task.state === 'open' && task.readiness);
    return candidates.length ? { kind: 'work', reason: own.length ? 'work was assigned to this actor; inspect checkpoint' :
      'claimable work exists; inspect current board and claim atomically', tasks: candidates.slice(0, 20).map(task => task.id) } : null;
  }
  const relevant = new Set(entry.items);
  const addDependencies = id => {
    for (const dep of [...(snapshot.tasks[id]?.deps ?? []), ...(snapshot.tasks[id]?.outputs ?? [])]) if (!relevant.has(dep)) { relevant.add(dep); addDependencies(dep); }
  };
  entry.items.forEach(addDependencies);
  const linked = note => [note.task, note.output, ...(note.related ?? [])].some(id => relevant.has(id));
  const blockers = (snapshot.blockers ?? []).filter(linked);
  if (blockers.length) return { kind: 'reevaluate', reason: 'unresolved dependency FAIL', publications: blockers.map(x => x.id) };
  for (const id of relevant) {
    const task = snapshot.tasks[id];
    if (task?.state === 'blocked') return { kind: 'reevaluate', reason: `dependency ${id} is blocked` };
    const producer = snapshot.sessions?.find(x => x.actor === task?.owner);
    if (task?.state !== 'done' && producer?.state === 'ended') return { kind: 'reevaluate', reason: `producer ${task.owner} ended; salvage/reclaim or a concrete blocker is required` };
    const previous = entry.dependencies?.[id];
    if (task?.state !== 'done' && previous && (previous.owner !== task?.owner || previous.generation !== task?.generation))
      return { kind: 'reevaluate', reason: `dependency ${id} ownership changed; inspect handoff` };
  }
  const correction = (snapshot.notes ?? []).find(note => note.sequence > entry.sequence && linked(note) &&
    ['CORRECTION', 'RESOLUTION'].includes(note.type));
  if (correction) return { kind: 'reevaluate', reason: 'dependency evidence corrected', publications: [correction.id] };
  if (entry.items.every(id => snapshot.tasks[id]?.state === 'done')) return { kind: 'ready', reason: 'all exact dependencies are done' };
  return null;
}

/** Actor identity and credentials are bound by the existing local CLI, not model input. */
export async function domainCommand(run, actor, payload) {
  const { stdout } = await execute(join(run, actor, 'bin', 'context'), ['domain', JSON.stringify(payload)],
    { maxBuffer: 16 * 1024 * 1024, timeout: 30000 });
  const result = JSON.parse(stdout);
  if (result.error) throw Error(`DeLM domain ${result.code ?? 'ERROR'}: ${result.error}`);
  return result;
}
