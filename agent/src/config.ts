import path from "node:path";
import { fileURLToPath } from "node:url";

export const AGENT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const REPO = path.resolve(AGENT_DIR, "..");
export const PYTHON = process.env.NW_PYTHON ?? path.join(REPO, ".venv", "bin", "python");
export const NW_ROOT = path.resolve(process.env.NW_ROOT ?? path.join(REPO, "investigations"));

export function runDir(runId: string): string {
	return path.join(NW_ROOT, "runs", runId);
}
