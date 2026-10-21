// Scripted model for offline integration tests and demos (Pi's faux provider). It exercises the real host, tools,
// sandbox, backend and store; only the model's words are canned. Results produced with it say nothing about live
// agent performance.
import { readFileSync } from "node:fs";
import { fauxAssistantMessage, fauxProvider, fauxText, fauxToolCall } from "@earendil-works/pi-ai";
import type { ModelRuntime } from "@earendil-works/pi-coding-agent";
import { makeRuntime } from "./sessions.ts";

export const MOCK_MODEL = { provider: "faux", id: "scripted-investigator" };

const sp = (id: string, ox: number | null, extra: Record<string, unknown> = {}) => ({ id, N_oxidation_state: ox, ...extra });
const rx = (id: string, a: string, b: string, e: number | null, extra: Record<string, unknown> = {}) => ({
	id, reactants: [{ species: a, coeff: 1 }], products: [{ species: b, coeff: 1 }], electrons: e,
	rate_law: { family: "mass_action", params: { k: { value: 0.001 } }, ...extra },
});
const deact = { time_modulation: { kind: "deactivation", tau_min: { value: 300, tie: "tau_cat" } } };
const SPECIES = [sp("NO3", 5), sp("NO2", 3), sp("NH3", -3), sp("SINK", 0, { observable: false, role: "sink" })];

export const MOCK_CANDIDATES = [
	{
		name: "mock_series_sinkNO2_deact",
		mechanism: { id: "m1", species: SPECIES, reactions: [rx("R1", "NO3", "NO2", 2, deact), rx("R2", "NO2", "NH3", 6, deact), rx("R3", "NO2", "SINK", 3, deact)] },
		support: [{ target: "R1", basis: "data", source: "NO2 rises then plateaus" }, { target: "R3", basis: "data", source: "closure deficit lags" }],
		rationale: "scripted",
	},
	{ // deliberately violates N balance: must come back invalid_chemistry
		name: "mock_bad_balance",
		mechanism: { id: "m2", species: SPECIES, reactions: [{ ...rx("R1", "NO3", "NO2", 2), products: [{ species: "NO2", coeff: 2 }] }, rx("R2", "NO2", "NH3", 6)] },
	},
	{ // reversible is not representable: must come back unsupported_representation
		name: "mock_reversible",
		mechanism: { id: "m3", species: SPECIES.slice(0, 3), reactions: [{ ...rx("R1", "NO3", "NO2", 2), reversible: true }, rx("R2", "NO2", "NH3", 6)] },
	},
];

const REVISION = {
	name: "mock_series_sinkNO2_deact_v2",
	mechanism: { id: "m1b", species: SPECIES, reactions: [rx("R1", "NO3", "NO2", 2, deact), rx("R2", "NO2", "NH3", 6, deact), rx("R3", "NO2", "SINK", 3, deact), rx("R4", "NO3", "NH3", 8, deact)] },
	support: [{ target: "R4", basis: "data", source: "review finding F1" }],
	rationale: "adds a direct NO3->NH3 branch in response to review",
};

function lastUser(messages: any[]): string {
	for (let i = messages.length - 1; i >= 0; i--) {
		const m = messages[i];
		if (m.role === "user") return typeof m.content === "string" ? m.content : m.content.map((c: any) => c.text ?? "").join("");
	}
	return "";
}

function toolsSinceUser(messages: any[]): any[] {
	const out = [];
	for (let i = messages.length - 1; i >= 0 && messages[i].role !== "user"; i--) if (messages[i].role === "toolResult") out.unshift(messages[i]);
	return out;
}

function systemText(messages: any[]): string {
	const s = messages.find((m: any) => m.role === "system");
	if (!s) return "";
	const base = typeof s.content === "string" ? s.content : s.content.map((c: any) => c.text).join("");
	return [base, ...Object.values(s.sections ?? {}).filter(Boolean)].join("\n");
}

function resultText(m: any): string {
	return (m.content ?? []).map((c: any) => c.text ?? "").join("");
}

function investigatorStep(messages: any[]) {
	const user = lastUser(messages);
	const done = toolsSinceUser(messages).map((m) => m.toolName);
	if (user.includes("Phase: proposal") || user.includes("No candidate has been stored")) {
		if (!done.includes("nw_evidence") && !user.includes("No candidate")) return fauxAssistantMessage([fauxToolCall("nw_evidence", {})], { stopReason: "toolUse" });
		if (!done.includes("bash") && !user.includes("No candidate")) return fauxAssistantMessage([fauxToolCall("bash", { command: "ls; python -c 'import numpy; print(numpy.__version__)'; cat /etc/hostname 2>/dev/null; ls ~ ; env | sort" })], { stopReason: "toolUse" });
		if (!done.includes("nw_submit_candidates")) return fauxAssistantMessage([fauxToolCall("nw_submit_candidates", { candidates: MOCK_CANDIDATES, note: "scripted" } as any)], { stopReason: "toolUse" });
		return fauxAssistantMessage(fauxText("Submitted three scripted candidates (one valid, one N-imbalanced, one reversible)."));
	}
	if (user.includes("Review ") && user.includes("nw_respond_to_review")) {
		const rid = /review_id "([^"]+)"/.exec(user)?.[1] ?? "";
		if (!done.includes("nw_submit_candidates")) {
			const parent = /(C[0-9a-f]{10}) mock_series_sinkNO2_deact/.exec(user)?.[1];
			return fauxAssistantMessage([fauxToolCall("nw_submit_candidates", { candidates: [{ ...REVISION, parent }] } as any)], { stopReason: "toolUse" });
		}
		if (!done.includes("nw_evaluate")) {
			const sub = toolsSinceUser(messages).find((m) => m.toolName === "nw_submit_candidates");
			const id = /(C[0-9a-f]{10})/.exec(resultText(sub))?.[1];
			return fauxAssistantMessage([fauxToolCall("nw_evaluate", { candidate_ids: [id] } as any)], { stopReason: "toolUse" });
		}
		if (!done.includes("nw_respond_to_review")) {
			const findings = [...user.matchAll(/"id": "([^"]+)",\s*"severity"/g)].map((m) => m[1]);
			return fauxAssistantMessage([fauxToolCall("nw_respond_to_review", { review_id: rid, responses: findings.map((f) => ({ finding_id: f, action: "revised", note: "scripted response" })) })], { stopReason: "toolUse" });
		}
		return fauxAssistantMessage(fauxText("Revision done."));
	}
	if (user.includes("Final phase") || user.includes("Record your conclusion")) {
		if (!done.includes("nw_compare")) return fauxAssistantMessage([fauxToolCall("nw_compare", {})], { stopReason: "toolUse" });
		if (!done.includes("nw_record_conclusion")) {
			const ids = [...resultText(toolsSinceUser(messages).find((m) => m.toolName === "nw_compare")).matchAll(/^\s+(C[0-9a-f]{10})/gm)].map((m) => m[1]);
			return fauxAssistantMessage([fauxToolCall("nw_record_conclusion", {
				plausible: ids.slice(0, 2), rejected: [], ambiguities: ["scripted: sink placement not resolved"], adequacy: "uncertain",
				recommended_experiments: [{ design: "nitrite feed", discriminates: ids.slice(0, 2), rationale: "scripted" }],
				narrative: "Scripted conclusion from the mock model; not a scientific result.",
			})], { stopReason: "toolUse" });
		}
		return fauxAssistantMessage(fauxText("Conclusion recorded."));
	}
	if (user.includes("[Host notice]")) {
		if (!done.includes("nw_status")) return fauxAssistantMessage([fauxToolCall("nw_status", {})], { stopReason: "toolUse" });
	}
	return fauxAssistantMessage(fauxText("Nothing to do."));
}

function reviewerStep(messages: any[]) {
	const sys = systemText(messages);
	const bundlePath = /Bundle: (\S+bundle\.json)/.exec(sys)?.[1];
	const results = messages.filter((m: any) => m.role === "toolResult" && m.toolName === "submit_review");
	if (results.length && !results[results.length - 1].isError) return fauxAssistantMessage(fauxText("Review submitted."));
	const bundle = JSON.parse(readFileSync(bundlePath!, "utf8"));
	const ev = bundle.candidate_ids.filter((c: string) => bundle.artifacts[`evaluation:${c}`]?.summary?.status === "fitted");
	const c = ev[0] ?? bundle.candidate_ids[0];
	const aicc = bundle.artifacts[`evaluation:${c}`]?.summary?.aicc;
	// first attempt quotes a wrong number on purpose, so the validator's rejection path is exercised
	const wrong = results.length === 0;
	return fauxAssistantMessage([fauxToolCall("submit_review", {
		summary: "Scripted review (mock model).",
		findings: [{
			id: "F1", severity: "major", category: "coverage", claim: "No direct NO3->NH3 branch was tested.",
			targets: [`candidate:${c}#/submission/mechanism/reactions`],
			evidence: [{ ref: `evaluation:${c}#/summary/aicc`, value: wrong ? (aicc ?? 0) + 100 : aicc }],
			check: { type: "consistency", description: "compare with a candidate that has the branch" },
			action: { type: "new_candidate", description: "add NO3->NH3" },
		}],
		assessment: { plausible_candidates: ev.slice(0, 1), not_supported: [], ambiguities: ["scripted"], adequate_candidate_exists: "uncertain" },
	})], { stopReason: "toolUse" });
}

export async function mockRuntime(): Promise<ModelRuntime> {
	const rt = await makeRuntime();
	const faux = fauxProvider({ provider: MOCK_MODEL.provider, models: [{ id: MOCK_MODEL.id, reasoning: false }] });
	faux.setResponses(Array.from({ length: 500 }, () => (context: any) =>
		systemText(context.messages).includes("independent reviewer") ? reviewerStep(context.messages) : investigatorStep(context.messages)));
	rt.registerNativeProvider(faux.provider);
	return rt;
}
