/**
 * Xiaohongshu read bootstrap — page-context adaptation template.
 *
 * Run inside an authenticated https://www.xiaohongshu.com tab, page main world,
 * as one evaluate call. Not a Node script, not a CLI; installs nothing, writes
 * nothing, and calls only the site's own client. It captures that client, runs
 * the identity preflight, performs the single read in TASK, and returns an
 * explicit projection. Credentials stay in this block; the result has no token
 * and no raw account object.
 *
 * EDIT 1: authenticated site tab, page main world.
 * EDIT 2: replace TASK with the authorized read (references/read-api.md). For a
 * list, loop one page at a time with a fixed page cap, copy the cursor unchanged,
 * and keep any xsecToken inside this block. Task logic is yours to write.
 *
 * Timeouts belong to the browser tool; a Promise.race wrapper cannot cancel the
 * in-flight request, so do not add one that silently resends.
 */
(async () => {
  'use strict';
  function countField(data, ...keys) {
    for (const key of keys) {
      const value = data && data[key];
      if (typeof value === 'number' && Number.isFinite(value)) return value;
      if (typeof value === 'string' && /^-?\d+(\.\d+)?$/.test(value)) return value;
    }
    return null;
  }
  function fail(stage, kind) {
    return { ok: false, stage, kind };
  }
  // Fixed classes only; not an exhaustive classifier. Never return a raw message.
  function errorClass(error) {
    const status = error && (error.status || error.statusCode ||
      (error.response && error.response.status));
    if (status === 401) return 'unauthorized';
    if (status === 403) return 'forbidden';
    if (status === 406) return 'refused';
    return 'request_failed';
  }
  // EDIT 2 — the one read for this run. Default: unread counts.
  // GET: client.get(path, options). POST: client.post(path, body, options).
  const TASK = {
    id: 'unreadCount',
    request: (client) => client.get('/api/sns/web/unread_count'),
    project: (data) => {
      const counts = {
        unreadCount: countField(data, 'unreadCount', 'unread_count'),
        likes: countField(data, 'likes'),
        connections: countField(data, 'connections'),
        mentions: countField(data, 'mentions'),
      };
      if (Object.values(counts).some((value) => value === null)) {
        throw new Error('unread_count_shape');
      }
      return counts;
    },
  };
  const chunks = window.webpackChunkxhs_pc_web;
  if (!Array.isArray(chunks)) return fail('runtime', 'chunk_array_missing');
  let req;
  chunks.push([
    [`read-${Date.now()}-${Math.random().toString(36).slice(2)}`],
    {},
    (runtimeRequire) => { req = runtimeRequire; },
  ]);
  if (typeof req !== 'function') return fail('runtime', 'require_not_captured');
  // Inspect factory source strings only; do not execute the module graph.
  const ROUTES = ['/api/sns/web/v2/user/me', '/api/sns/web/v1/feed'];
  const REGISTER = /registerHttp[^]*?\}\(\w+\((\d+)\)\.([A-Za-z_$][\w$]*)\)\}/;
  const registrations = [];
  for (const factory of Object.values(req.m || {})) {
    const source = String(factory);
    if (!ROUTES.every((route) => source.includes(route))) continue;
    const match = source.match(REGISTER);
    if (match) registrations.push(match);
  }
  if (registrations.length === 0) return fail('client', 'registration_not_found');
  const clients = [];
  for (const match of registrations) {
    try {
      const candidate = req(match[1])[match[2]];
      const usable = candidate && typeof candidate.get === 'function' &&
        typeof candidate.post === 'function';
      if (usable && !clients.includes(candidate)) clients.push(candidate);
    } catch (_) { /* not a fallback reason */ }
  }
  if (clients.length !== 1) return fail('client', 'client_not_unique');
  const client = clients[0];
  let me;
  try {
    me = await client.get('/api/sns/web/v2/user/me');
  } catch (error) {
    return fail('identity', errorClass(error));
  }
  if (!me || me.guest !== false) return fail('identity', 'not_authenticated');
  let data;
  try {
    data = await TASK.request(client);
  } catch (error) {
    return fail('task', errorClass(error));
  }
  if (data === undefined || data === null) return fail('task', 'empty_payload');
  let projected;
  try {
    projected = TASK.project(data);
  } catch (_) {
    return fail('task', 'unexpected_shape');
  }
  return { ok: true, identity: { guest: false }, task: TASK.id, data: projected };
})();
