// Pi session construction with explicit, isolated resources.
//
// Nothing is discovered from the host: no AGENTS.md/CLAUDE.md context files, no user or project skills, extensions,
// packages, prompt templates or themes, and settings are in memory. The only thing taken from the user's Pi
// configuration is the credential store (auth.json), read by the host process and never exposed to tools.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
	type AgentSession,
	createAgentSession,
	createBashToolDefinition,
	createEditToolDefinition,
	createExtensionRuntime,
	createReadToolDefinition,
	createWriteToolDefinition,
	ModelRuntime,
	type ResourceLoader,
	SessionManager,
	SettingsManager,
	type ToolDefinition,
} from "@earendil-works/pi-coding-agent";
import { AGENT_DIR, runDir } from "./config.ts";
import { PathGuard, type SandboxSpec, sandboxedBash } from "./sandbox.ts";

process.env.PI_TELEMETRY = "0";
process.env.PI_SKIP_VERSION_CHECK = "1";
process.env.PI_OFFLINE = "1";
// Inherited Anthropic endpoint/credential variables (e.g. from a parent agent harness) must not silently redirect or
// authenticate the investigator: the host passes credentials explicitly below.
for (const k of ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_OAUTH_TOKEN"]) delete process.env[k];

export const ANTHROPIC_KEY_FILE = process.env.NW_ANTHROPIC_KEY_FILE ?? path.join(os.homedir(), ".config", "nernstwork", "anthropic_api_key");
export let credentialSource: Record<string, string> = {};

export async function makeRuntime(): Promise<ModelRuntime> {
	const authPath = process.env.NW_PI_AUTH ?? path.join(os.homedir(), ".pi", "agent", "auth.json");
	const rt = await ModelRuntime.create({ authPath, modelsPath: null, refreshOnCreate: true, allowModelNetwork: false });
	// A native Anthropic API key, if provided, overrides the stored (possibly expired) OAuth credential for this process
	// only. It is read from an owner-only file outside the repository and never passed to the backend or the sandbox.
	const envKey = process.env.ANTHROPIC_API_KEY;
	delete process.env.ANTHROPIC_API_KEY;
	const fileKey = existsSync(ANTHROPIC_KEY_FILE) ? readFileSync(ANTHROPIC_KEY_FILE, "utf8").trim() : "";
	const key = envKey || fileKey;
	if (key) {
		await rt.setRuntimeApiKey("anthropic", key);
		credentialSource = { anthropic: envKey ? "runtime API key (ANTHROPIC_API_KEY)" : `runtime API key (${ANTHROPIC_KEY_FILE})` };
	} else if (rt.hasConfiguredAuth("anthropic")) {
		credentialSource = { anthropic: rt.isUsingOAuth("anthropic") ? "stored OAuth (Pi auth.json)" : "stored API key (Pi auth.json)" };
	}
	return rt;
}

export function resolveModel(runtime: ModelRuntime, provider: string, id: string) {
	const m = runtime.getModel(provider, id);
	if (!m) throw new Error(`model ${provider}/${id} is not in this Pi release's registry; refusing to substitute another model`);
	if (provider !== "faux" && !runtime.hasConfiguredAuth(provider)) {
		throw new Error(`no credentials configured for provider ${provider}; live runs need them (offline: use --mock)`);
	}
	return m;
}

export function loadPrompt(name: string, vars: Record<string, string>): string {
	let s = readFileSync(path.join(AGENT_DIR, "prompts", `${name}.md`), "utf8");
	for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{{${k}}}`, v);
	return s;
}

export function isolatedResources(systemPrompt: string): ResourceLoader {
	return {
		getExtensions: () => ({ extensions: [], errors: [], runtime: createExtensionRuntime() }),
		getSkills: () => ({ skills: [], diagnostics: [] }),
		getPrompts: () => ({ prompts: [], diagnostics: [] }),
		getThemes: () => ({ themes: [], diagnostics: [] }),
		getAgentsFiles: () => ({ agentsFiles: [] }),
		getSystemPrompt: () => systemPrompt,
		getSystemPromptSource: () => undefined,
		getAppendSystemPrompt: () => [],
		getAppendSystemPromptSources: () => [],
		extendResources: () => {},
		reload: async () => {},
	};
}

export function sandboxedBuiltins(spec: SandboxSpec): ToolDefinition[] {
	const guard = new PathGuard(spec);
	const cwd = spec.workspace;
	return [
		createReadToolDefinition(cwd, { operations: guard.readOps() }),
		createWriteToolDefinition(cwd, { operations: guard.writeOps() }),
		createEditToolDefinition(cwd, { operations: guard.editOps() }),
		createBashToolDefinition(cwd, { operations: sandboxedBash(spec), exposeSessionEnvironment: false }),
	] as ToolDefinition[];
}

export interface SessionSpec {
	runId: string;
	kind: "investigator" | "reviewer";
	cwd: string;
	sessionDir: string;
	sessionFile?: string;
	systemPrompt: string;
	runtime: ModelRuntime;
	model: ReturnType<ModelRuntime["getModel"]>;
	thinking: string;
	tools: ToolDefinition[];
}

export async function openSession(spec: SessionSpec): Promise<AgentSession> {
	mkdirSync(spec.sessionDir, { recursive: true });
	const agentDir = path.join(runDir(spec.runId), "pi", "agent");
	mkdirSync(agentDir, { recursive: true });
	const sessionManager = spec.sessionFile && existsSync(spec.sessionFile)
		? SessionManager.open(spec.sessionFile, spec.sessionDir)
		: SessionManager.create(spec.cwd, spec.sessionDir);
	const settingsManager = SettingsManager.inMemory({
		compaction: { enabled: true },
		retry: { enabled: true, maxRetries: 6, baseDelayMs: 5000 }, // rides out short provider connection outages (about 3 min)
	} as any);
	const { session } = await createAgentSession({
		cwd: spec.cwd,
		agentDir,
		modelRuntime: spec.runtime,
		model: spec.model as any,
		thinkingLevel: spec.thinking as any,
		resourceLoader: isolatedResources(spec.systemPrompt),
		sessionManager,
		settingsManager,
		customTools: spec.tools,
		tools: spec.tools.map((t) => t.name),
	});
	return session;
}

export function recordUsage(runId: string, label: string, session: AgentSession, wallMs: number) {
	const p = path.join(runDir(runId), "pi", "usage.json");
	const u = existsSync(p) ? JSON.parse(readFileSync(p, "utf8")) : { sessions: {} };
	const st = session.getSessionStats();
	const key = st.sessionFile ? path.basename(st.sessionFile) : `${label}-memory`;
	const prev = u.sessions[key] ?? { wall_s: 0 };
	u.sessions[key] = {
		label, model: `${session.model?.provider}/${session.model?.id}`, tokens: st.tokens, cost_usd: st.cost,
		tool_calls: st.toolCalls, assistant_messages: st.assistantMessages, wall_s: prev.wall_s + wallMs / 1000,
	};
	const all = Object.values(u.sessions) as any[];
	u.input_tokens = all.reduce((a, s) => a + s.tokens.input, 0);
	u.output_tokens = all.reduce((a, s) => a + s.tokens.output, 0);
	u.cache_read_tokens = all.reduce((a, s) => a + s.tokens.cacheRead, 0);
	u.cache_write_tokens = all.reduce((a, s) => a + s.tokens.cacheWrite, 0);
	u.cost_usd = all.reduce((a, s) => a + (s.cost_usd ?? 0), 0);
	u.wall_s = all.reduce((a, s) => a + s.wall_s, 0);
	u.tool_calls = all.reduce((a, s) => a + s.tool_calls, 0);
	u.cost_note = "cost_usd uses the Pi model table's list prices; an API key is billed per token at the provider's rates, subscription OAuth draws on the plan instead";
	u.credential_source = { ...(u.credential_source ?? {}), ...credentialSource };
	writeFileSync(p, JSON.stringify(u, null, 1));
}
