// Isolation for the investigator's built-in tools.
//
// bash runs inside bubblewrap: new user/pid/net/ipc namespaces, cleared environment (no provider credentials, no
// PI_* variables), no network, a read-only view of the evidence pack and the Python runtime, and a writable run
// workspace. The repository, the held-out data, the fit cache and the home directory are not mounted.
// read/write/edit run in the host process, so they get path guards that resolve symlinks before checking that the
// target lies inside the permitted roots (otherwise a symlink created in the sandbox could point the host-side read
// tool at a held-out file).
import { spawn } from "node:child_process";
import { constants as fsc, promises as fs, realpathSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { type BashOperations, detectSupportedImageMimeTypeFromFile } from "@earendil-works/pi-coding-agent";
import { REPO } from "./config.ts";

export interface SandboxSpec {
	workspace: string; // read-write
	readOnly: string[]; // e.g. the evidence pack and the toolkit
	env?: Record<string, string>; // extra variables inside the sandbox (no secrets)
	cpus?: string; // taskset CPU list, e.g. "16-19"; bounds exploratory compute so it cannot starve the evaluator
}

export function defaultSandboxCpus(): string | undefined {
	if (process.env.NW_SANDBOX_CPUS) return process.env.NW_SANDBOX_CPUS;
	const n = os.cpus().length;
	return n >= 8 ? `${n - 4}-${n - 1}` : undefined; // the last four cores
}

function pythonRoots(): string[] {
	const venv = path.join(REPO, ".venv");
	const roots = [venv];
	try {
		const real = realpathSync(path.join(venv, "bin", "python"));
		// .../uv/python/cpython-3.12.x-.../bin/python3.12 -> bind the whole uv python directory (aliases point into it)
		const pyDir = path.resolve(real, "..", "..", "..");
		roots.push(pyDir);
	} catch {
		/* system python only */
	}
	return roots;
}

export function bwrapArgs(spec: SandboxSpec, command: string, cwd: string): string[] {
	const a = [
		"--die-with-parent",
		"--new-session",
		"--unshare-all",
		"--ro-bind", "/usr", "/usr",
		"--symlink", "usr/bin", "/bin",
		"--symlink", "usr/lib", "/lib",
		"--symlink", "usr/sbin", "/sbin",
		"--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
		"--proc", "/proc",
		"--dev", "/dev",
		"--tmpfs", "/tmp",
	];
	for (const r of pythonRoots()) a.push("--ro-bind", r, r);
	for (const r of spec.readOnly) a.push("--ro-bind", r, r);
	a.push("--bind", spec.workspace, spec.workspace);
	const inside = cwd.startsWith(spec.workspace) ? cwd : spec.workspace;
	a.push(
		"--chdir", inside,
		"--clearenv",
		"--setenv", "PATH", `${path.join(REPO, ".venv", "bin")}:/usr/bin:/bin`,
		"--setenv", "HOME", spec.workspace,
		"--setenv", "MPLCONFIGDIR", path.join(spec.workspace, ".cache", "matplotlib"),
		"--setenv", "LANG", "C.UTF-8",
		"--setenv", "PYTHONDONTWRITEBYTECODE", "1",
		"--setenv", "OMP_NUM_THREADS", "1",
		"--hostname", "sandbox",
	);
	for (const [k, v] of Object.entries(spec.env ?? {})) a.push("--setenv", k, v);
	if (spec.cpus) a.push("/usr/bin/taskset", "-c", spec.cpus, "/usr/bin/nice", "-n", "10");
	a.push("/bin/bash", "-c", `ulimit -t 1800; ${command}`);
	return a;
}

export function sandboxedBash(spec: SandboxSpec): BashOperations {
	return {
		exec: async (command, cwd, { onData, signal, timeout }) => {
			if (signal?.aborted) throw new Error("aborted");
			const child = spawn("/usr/bin/bwrap", bwrapArgs(spec, command, cwd), {
				stdio: ["ignore", "pipe", "pipe"],
				detached: true,
				env: {}, // the sandbox sets its own environment; nothing from the host leaks through bwrap itself
			});
			let timedOut = false;
			const kill = () => {
				try {
					if (child.pid) process.kill(-child.pid, "SIGKILL");
				} catch {
					/* already gone */
				}
			};
			const timer = timeout ? setTimeout(() => ((timedOut = true), kill()), timeout * 1000) : undefined;
			signal?.addEventListener("abort", kill, { once: true });
			child.stdout.on("data", onData);
			child.stderr.on("data", onData);
			const code: number | null = await new Promise((res) => {
				child.on("error", (e) => {
					onData(Buffer.from(`sandbox failed to start: ${e.message}\n`));
					res(127);
				});
				child.on("close", (c, sig) => res(c ?? (sig ? 137 : 1)));
			});
			if (timer) clearTimeout(timer);
			signal?.removeEventListener("abort", kill);
			if (signal?.aborted) throw new Error("aborted");
			if (timedOut) throw new Error(`timeout:${timeout}`);
			return { exitCode: code };
		},
	};
}

export class PathGuard {
	readonly readRoots: string[];
	readonly writeRoots: string[];
	constructor(spec: SandboxSpec) {
		const real = (p: string) => realpathSync(p);
		this.writeRoots = [real(spec.workspace)];
		this.readRoots = [...this.writeRoots, ...spec.readOnly.map(real)];
	}
	private static within(p: string, roots: string[]): boolean {
		return roots.some((r) => p === r || p.startsWith(r + path.sep));
	}
	private static isPiTemp(p: string): boolean {
		return path.dirname(p) === realpathSync(os.tmpdir()) && path.basename(p).startsWith("pi-bash");
	}
	async checkRead(abs: string): Promise<string> {
		const real = await fs.realpath(abs).catch(() => {
			throw new Error(`not found: ${abs}`);
		});
		if (!PathGuard.within(real, this.readRoots) && !PathGuard.isPiTemp(real)) {
			throw new Error(`access denied: ${abs} is outside the workspace and evidence pack`);
		}
		return real;
	}
	async checkWrite(abs: string): Promise<string> {
		const parent = path.dirname(abs);
		await fs.mkdir(parent, { recursive: true }).catch(() => undefined);
		const realParent = await fs.realpath(parent);
		if (!PathGuard.within(realParent, this.writeRoots)) {
			throw new Error(`access denied: ${abs} is outside the workspace (evidence is read-only)`);
		}
		const target = path.join(realParent, path.basename(abs));
		const st = await fs.lstat(target).catch(() => undefined);
		if (st?.isSymbolicLink()) throw new Error(`refusing to write through a symlink: ${abs}`);
		return target;
	}
	readOps() {
		return {
			readFile: async (p: string) => fs.readFile(await this.checkRead(p)),
			access: async (p: string) => fs.access(await this.checkRead(p), fsc.R_OK),
			detectImageMimeType: async (p: string) => detectSupportedImageMimeTypeFromFile(await this.checkRead(p)),
		};
	}
	writeOps() {
		return {
			writeFile: async (p: string, c: string) => fs.writeFile(await this.checkWrite(p), c),
			mkdir: async (d: string) => {
				await this.checkWrite(path.join(d, ".probe"));
				await fs.mkdir(d, { recursive: true });
			},
		};
	}
	editOps() {
		return {
			readFile: async (p: string) => fs.readFile(await this.checkWrite(p)),
			writeFile: async (p: string, c: string) => fs.writeFile(await this.checkWrite(p), c),
			access: async (p: string) => fs.access(await this.checkWrite(p), fsc.R_OK | fsc.W_OK),
		};
	}
}
