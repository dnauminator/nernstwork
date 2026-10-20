// Live smoke check: one short prompt through the configured model with the same isolated session setup as the
// investigator (no tools, no context files, no skills). Verifies the provider/model id and credentials only.
//   node src/smoke.ts [provider/model]
import os from "node:os";
import path from "node:path";
import { createAgentSession, SessionManager, SettingsManager } from "@earendil-works/pi-coding-agent";
import { isolatedResources, makeRuntime, resolveModel } from "./sessions.ts";

const [provider, id] = (process.argv[2] ?? "anthropic/claude-opus-5-5").split(/\/(.*)/s);
const runtime = await makeRuntime();
const model = resolveModel(runtime, provider, id);
const cwd = path.join(os.tmpdir(), "nw-smoke");
const { session } = await createAgentSession({
	cwd, agentDir: cwd, modelRuntime: runtime, model, thinkingLevel: "low",
	resourceLoader: isolatedResources("You are a connectivity check. Answer exactly as asked."),
	sessionManager: SessionManager.inMemory(cwd), settingsManager: SettingsManager.inMemory({}), tools: [],
});
const t0 = Date.now();
await session.prompt("Reply with the single word OK.");
const last = session.messages.at(-1) as any;
console.log(JSON.stringify({ credential: (await import("./sessions.ts")).credentialSource,
	requested: `${provider}/${id}`, responded_model: last?.model, provider: last?.provider, stop: last?.stopReason,
	error: last?.errorMessage, text: session.getLastAssistantText(), oauth: runtime.isUsingOAuth(provider),
	usage: session.getSessionStats().tokens, cost_list_usd: session.getSessionStats().cost, wall_ms: Date.now() - t0,
}, null, 1));
session.dispose();
