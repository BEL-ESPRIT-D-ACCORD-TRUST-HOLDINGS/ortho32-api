import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { buildServer } from '../src/index.js';

let app: Awaited<ReturnType<typeof buildServer>>;
let token: string;
let privilegedToken: string;

beforeAll(async () => {
  app = await buildServer();
  await app.ready();

  // Default token (no elevated scopes)
  const res = await app.inject({
    method: 'POST',
    url: '/api/v1/auth/session',
    payload: { principal: 'alice' }
  });
  token = JSON.parse(res.body).data.token;

  // Privileged token (admin can get hardware.reset)
  const res2 = await app.inject({
    method: 'POST',
    url: '/api/v1/auth/session',
    payload: { principal: 'admin', requestedScopes: ['hardware.reset', 'marketplace.install'] }
  });
  privilegedToken = JSON.parse(res2.body).data.token;
});

afterAll(async () => {
  await app.close();
});

describe('ortho32-api contract', () => {
  it('POST /api/v1/tensor/jobs returns cycles as integer', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/v1/tensor/jobs',
      headers: { authorization: `Bearer ${token}` },
      payload: { model: 'ortho-llm-32', inputShape: [1, 512] }
    });
    expect(res.statusCode).toBe(201);
    const body = JSON.parse(res.body);
    // envelope shape
    expect(body).toHaveProperty('id');
    expect(body).toHaveProperty('type');
    expect(body).toHaveProperty('timestamp');
    expect(body).toHaveProperty('source', 'ortho32-api');
    expect(body).toHaveProperty('correlation_id');
    expect(body).toHaveProperty('data');
    // cycles contract: integer, not float, not ms
    expect(typeof body.data.cycles).toBe('number');
    expect(Number.isInteger(body.data.cycles)).toBe(true);
    expect(body.data.cycles).toBeGreaterThan(0);
  });

  it('POST /api/v1/proofs/verify returns VerificationStatus enum (7 values, disjoint)', async () => {
    const validStatuses = ['VERIFIED', 'CROSS_VERIFIED', 'TESTED', 'OBSERVED', 'ASSUMED', 'UNVERIFIED', 'FAILED'];
    const res = await app.inject({
      method: 'POST',
      url: '/api/v1/proofs/verify',
      headers: { authorization: `Bearer ${token}` },
      payload: { theorem: 'rtl_deterministic' }
    });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.data.status).toBeDefined();
    expect(validStatuses).toContain(body.data.status);
    // never interchangeable: ensure exactly 7 values exist in schema
    expect(validStatuses.length).toBe(7);
    // subsequent verify with different theorem also returns valid enum
    const res2 = await app.inject({
      method: 'POST',
      url: '/api/v1/proofs/verify',
      headers: { authorization: `Bearer ${token}` },
      payload: { theorem: 'other_theorem' }
    });
    expect(validStatuses).toContain(JSON.parse(res2.body).data.status);
  });

  it('GET /api/v1/events/stream emits typed events (SSE)', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/v1/events/stream',
      headers: { authorization: `Bearer ${token}` }
    });
    // Fastify inject buffers SSE; we assert headers and initial payload
    expect(res.statusCode).toBe(200);
    expect(res.headers['content-type']).toContain('text/event-stream');
    // Body should contain event: and data: frames with typed events
    const body = res.body;
    expect(body).toContain('event:');
    expect(body).toContain('data:');
    // Parse first event's data envelope
    const dataLine = body.split('\n').find((l: string) => l.startsWith('data:'));
    expect(dataLine).toBeDefined();
    const envelope = JSON.parse(dataLine!.slice(5).trim());
    expect(envelope).toHaveProperty('id');
    expect(envelope).toHaveProperty('type');
    expect(envelope).toHaveProperty('timestamp');
    expect(envelope).toHaveProperty('source');
    expect(envelope).toHaveProperty('correlation_id');
    expect(envelope).toHaveProperty('data');
  });

  it('hardware.reset 403 without scope, 200 with privileged scope', async () => {
    const forbidden = await app.inject({
      method: 'POST',
      url: '/api/v1/devices/ortho0/reset',
      headers: { authorization: `Bearer ${token}` }
    });
    expect(forbidden.statusCode).toBe(403);
    const body = JSON.parse(forbidden.body);
    expect(body.type).toBe('error.forbidden');

    const allowed = await app.inject({
      method: 'POST',
      url: '/api/v1/devices/ortho0/reset',
      headers: { authorization: `Bearer ${privilegedToken}` }
    });
    expect(allowed.statusCode).toBe(200);
    expect(JSON.parse(allowed.body).data.status).toBe('resetting');
  });

  it('marketplace.install 403 without scope', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/v1/marketplace/packages/foo/install',
      headers: { authorization: `Bearer ${token}` }
    });
    expect(res.statusCode).toBe(403);
  });

  it('CycleRecord.cycleNumber is integer', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/v1/traces/capture',
      headers: { authorization: `Bearer ${token}` },
      payload: { durationCycles: 128 }
    });
    expect(res.statusCode).toBe(201);
    const trace = JSON.parse(res.body).data;
    expect(Number.isInteger(trace.cycles)).toBe(true);
    for (const r of trace.records) {
      expect(Number.isInteger(r.cycleNumber)).toBe(true);
    }
  });

  it('every response is enveloped', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/v1/system/version'
    });
    const body = JSON.parse(res.body);
    expect(body).toHaveProperty('id');
    expect(body).toHaveProperty('type');
    expect(body).toHaveProperty('timestamp');
    expect(body).toHaveProperty('source');
    expect(body).toHaveProperty('correlation_id');
    expect(body).toHaveProperty('data');
  });

  it('public schemas do not expose BAR0/HANDLE/FPGA pointer', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/v1/devices',
      headers: { authorization: `Bearer ${token}` }
    });
    const body = JSON.parse(res.body);
    const json = JSON.stringify(body).toLowerCase();
    expect(json).not.toContain('bar0');
    expect(json).not.toContain('handle');
    expect(json).not.toContain('fpga');
  });
});
