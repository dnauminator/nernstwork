// JSON subprocess bridge to the Python backend (`python -m nernstwork.cli`). The backend owns all scientific state;
// this module only moves JSON across the process boundary. The child gets a minimal environment: no provider
// credentials, no Pi session variables.
import { spawn } from "node:child_process";
import path from "node:path";
import { NW_ROOT, PYTHON, REPO } from "./config.ts";

export interface BackendResult<T = any> {
	ok: boolean;
	result?: T;
	error?: string;
	kind?: string;
	wallMs: number;
}

const PASS_ENV = ["PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "NW_FAULT"];
// Fits now carry deterministic compute budgets, so this is a last-resort ceiling, not a normal limit.
const DEFAULT_TIMEOUT_MS = 6 * 3_600_000;

export function backendEnv(): NodeJS.ProcessEnv {
	const env: NodeJS.ProcessEnv = { PYTHONPATH: path.join(REPO, "src"), NW_ROOT, OMP_NUM_THREADS: "1" };
	for (const k of PASS_ENV) if (process.env[k] !== undefined) env[k] = process.env[k];
	return env;
}

export async function backend<T = any>(
	args: string[],
	input?: unknown,
	opts: { timeoutMs?: number; signal?: AbortSignal } = {},
): Promise<BackendResult<T>> {
	const t0 = Date.now();
	return await new Promise((resolve) => {
		const child = spawn(PYTHON, ["-m", "nernstwork.cli", "--root", NW_ROOT, ...args], {
			cwd: REPO,
			env: backendEnv(),
			stdio: ["pipe", "pipe", "pipe"],
			detached: true, // own process group, so a timeout or abort also stops the evaluator's worker processes
		});
		const killGroup = (sig: NodeJS.Signals) => {
			try {
				if (child.pid) process.kill(-child.pid, sig);
			} catch {
				/* already gone */
			}
		};
		const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
		let out = "";
		let err = "";
		let done = false;
		const finish = (r: Omit<BackendResult<T>, "wallMs">) => {
			if (done) return;
			done = true;
			clearTimeout(timer);
			opts.signal?.removeEventListener("abort", onAbort);
			resolve({ ...r, wallMs: Date.now() - t0 });
		};
		const onAbort = () => {
			killGroup("SIGTERM");
			finish({ ok: false, error: "aborted", kind: "aborted" });
		};
		const timer = setTimeout(() => {
			killGroup("SIGKILL");
			finish({ ok: false, error: `backend timed out after ${timeoutMs} ms`, kind: "timeout" });
		}, timeoutMs);
		opts.signal?.addEventListener("abort", onAbort, { once: true });
		child.stdout.on("data", (d) => (out += d));
		child.stderr.on("data", (d) => (err += d));
		child.on("error", (e) => finish({ ok: false, error: `failed to start backend: ${e.message}`, kind: "bridge" }));
		child.on("close", (code) => {
			const line = out.trim().split("\n").pop() ?? "";
			try {
				const parsed = JSON.parse(line);
				finish({ ok: Boolean(parsed.ok), result: parsed.result, error: parsed.error, kind: parsed.kind });
			} catch {
				finish({
					ok: false,
					error: `backend exited ${code} without a JSON result. stderr tail: ${err.slice(-1500)}`,
					kind: "bridge",
				});
			}
		});
		child.stdin.end(input === undefined ? "" : JSON.stringify(input));
	});
}

export async function backendOrThrow<T = any>(args: string[], input?: unknown, opts = {}): Promise<T> {
	const r = await backend<T>(args, input, opts);
	if (!r.ok) throw new Error(`backend ${args[0]} failed (${r.kind}): ${r.error}`);
	return r.result as T;
}
