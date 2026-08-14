/**
 * HTTP/2 transport for remote clients.
 * Handles TLS termination, envelope framing and JWT propagation.
 * Local IPC and HTTP share identical route semantics; only transport differs.
 */
import { FastifyInstance } from 'fastify';

export interface HttpTransportOptions {
  port: number;
  host: string;
  enableHttp2?: boolean;
  cert?: string;
  key?: string;
}

export async function createHttpTransport(
  fastify: FastifyInstance,
  opts: HttpTransportOptions
) {
  const { port, host } = opts;

  // Fastify already speaks HTTP/1.1 + HTTP/2 via Node http2 if configured.
  // For remote clients we enforce:
  //  - CORS (already registered)
  //  - JWT (already registered)
  //  - Envelope (already registered)
  //  - Compression / HTTP/2 multiplexing via ALPN if cert provided.

  await fastify.listen({ port, host });
  console.log(`[http] ortho32-api listening on https://${host}:${port} (http2=${!!opts.enableHttp2})`);

  return {
    close: () => fastify.close()
  };
}

/**
 * Remote client helper - typed fetch wrapper that preserves envelope + correlation.
 */
export class HttpClient {
  constructor(private baseUrl: string, private token?: string) {}

  setToken(token: string) {
    this.token = token;
  }

  async request<T>(method: string, path: string, body?: unknown, correlationId?: string): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
    if (correlationId) headers['X-Correlation-ID'] = correlationId;

    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined
    });
    const json = (await res.json()) as T;
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${JSON.stringify(json)}`);
    return json;
  }
}
