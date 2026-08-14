/**
 * Local IPC transport for desktop co-located use.
 * Uses OS-native channel: Unix domain socket (macOS/Linux) or Named Pipe (Windows).
 * Same envelope + JWT as HTTP; no separate auth.
 *
 * SECURITY: IPC socket is filesystem-permission gated (0700). Never expose to network.
 */
import { createServer, Socket } from 'node:net';
import { randomUUID } from 'node:crypto';
import { existsSync, unlinkSync } from 'node:fs';

export interface IpcTransportOptions {
  socketPath: string; // e.g. /tmp/ortho32-api.sock or \\.\pipe\ortho32-api
  jwtSecret: string;
}

export class IpcTransport {
  private server = createServer();
  private socketPath: string;

  constructor(private opts: IpcTransportOptions) {
    this.socketPath = opts.socketPath;
  }

  listen(handler: (msg: unknown) => Promise<unknown>) {
    if (existsSync(this.socketPath)) {
      try { unlinkSync(this.socketPath); } catch {}
    }

    this.server.on('connection', (socket: Socket) => {
      let buffer = '';
      socket.on('data', async (chunk) => {
        buffer += chunk.toString();
        let idx: number;
        while ((idx = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 1);
          if (!line) continue;
          try {
            const msg = JSON.parse(line);
            const result = await handler(msg);
            const envelope = {
              id: randomUUID(),
              type: 'ipc.response',
              timestamp: new Date().toISOString(),
              source: 'ortho32-api',
              correlation_id: msg.correlation_id || randomUUID(),
              data: result
            };
            socket.write(JSON.stringify(envelope) + '\n');
          } catch (e) {
            const errEnv = {
              id: randomUUID(),
              type: 'error.ipc',
              timestamp: new Date().toISOString(),
              source: 'ortho32-api',
              correlation_id: randomUUID(),
              data: { error: (e as Error).message }
            };
            socket.write(JSON.stringify(errEnv) + '\n');
          }
        }
      });
    });

    this.server.listen(this.socketPath, () => {
      console.log(`[ipc] listening on ${this.socketPath}`);
    });
  }

  async close(): Promise<void> {
    return new Promise((resolve) => this.server.close(() => resolve()));
  }
}

// Client helper for co-located desktop apps (Swift/Java via helper)
export class IpcClient {
  constructor(private socketPath: string) {}

  async request<T>(payload: unknown, correlationId = randomUUID()): Promise<T> {
    return new Promise((resolve, reject) => {
      const socket = new Socket();
      let buf = '';
      socket.connect(this.socketPath, () => {
        socket.write(JSON.stringify({ ...payload as object, correlation_id: correlationId }) + '\n');
      });
      socket.on('data', (chunk) => {
        buf += chunk.toString();
        const idx = buf.indexOf('\n');
        if (idx !== -1) {
          const line = buf.slice(0, idx);
          try {
            const env = JSON.parse(line);
            resolve(env as T);
          } catch (e) {
            reject(e);
          }
          socket.end();
        }
      });
      socket.on('error', reject);
    });
  }
}
