/**
 * Welcome to Cloudflare Workers! This is your first worker.
 *
 * - Run `npm run dev` in your terminal to start a development server
 * - Open a browser tab at http://localhost:8787/ to see your worker in action
 * - Run `npm run deploy` to publish your worker
 *
 * Bind resources to your worker in `wrangler.jsonc`. After adding bindings, a type definition for the
 * `Env` object can be regenerated with `npm run cf-typegen`.
 *
 * Learn more at https://developers.cloudflare.com/workers/
 */

interface Env {
  DB: D1Database;
  SYNC_TOKEN: string;
}

interface ExecutionLog {
  id: number;
  message: string;
  executed_at: string;
}

interface SyncRequest {
  source_id: string;
  logs: ExecutionLog[];
}

export default {
  async fetch(
    request: Request,
    env: Env,
  ): Promise<Response> {
    if (request.method !== "POST") {
      return Response.json(
        { error: "method not allowed" },
        { status: 405 },
      );
    }

    const authorization = request.headers.get("Authorization");
    if (authorization !== `Bearer ${env.SYNC_TOKEN}`) {
      return Response.json(
        { error: "unauthorized" },
        { status: 401 },
      );
    }

    let body: SyncRequest;

    try {
      body = await request.json();
    } catch {
      return Response.json(
        { error: "invalid json" },
        { status: 400 },
      );
    }

    if (
      typeof body.source_id !== "string" ||
      !Array.isArray(body.logs) ||
      body.logs.length > 500
    ) {
      return Response.json(
        { error: "invalid payload" },
        { status: 400 },
      );
    }

    const statements = body.logs.map((log) =>
      env.DB.prepare(
        `
        INSERT INTO execution_logs
        (source_id, id, message, executed_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(source_id, id) DO UPDATE SET
          message = excluded.message,
          executed_at = excluded.executed_at
        `,
      ).bind(
        body.source_id,
        log.id,
        log.message,
        log.executed_at,
      ),
    );

    if (statements.length > 0) {
      await env.DB.batch(statements);
    }

    return Response.json({
      accepted: body.logs.length,
    });
  },
};
