// Arm protocols as resumable steps. Each step is idempotent given the store: rerunning a finished backend step reuses
// stored results, and an interrupted conversational step is resumed in the same persisted Pi session with a host
// notice built from the store (not from conversation memory).
import { appendFileSync, existsSync, mkdirSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { type AgentSession, defineTool, type ModelRuntime } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { backend, backendOrThrow } from "./bridge.ts";
import { runDir } from "./config.ts";
import { PathGuard, type SandboxSpec, defaultSandboxCpus } from "./sandbox.ts";
import { loadPrompt, makeRuntime, openSession, recordUsage, resolveModel, sandboxedBuiltins } from "./sessions.ts";
import { HostState } from "./state.ts";
import { readJournal, scientificTools, type ToolContext } from "./tools.ts";

export interface RunOptions {
	runtime?: ModelRuntime; // injected for mocked integration tests
	log?: (line: string) => void;
	maxNudges?: number;
}

interface Ctx {
	runId: string;
	state: HostState;
	runCfg: any;
	runtime: ModelRuntime;
	log: (s: string) => void;
	investigator?: AgentSession;
	resumeNote?: string;
	maxNudges: number;
	capHit?: boolean;
}

// Hard spending cap per run (list-price estimate from Pi's model table, summed over every session of the run).
// When it is reached the active session is aborted; the host stops at a resumable point.
function costCap(ctx: Ctx): number {
	return Number(process.env.NW_MAX_COST_USD ?? ctx.runCfg.config_snapshot.agent?.max_cost_usd_per_run ?? 10);
}

function priorCost(runId: string, exceptFile?: string): number {
	const p = path.join(runDir(runId), "pi", "usage.json");
	if (!existsSync(p)) return 0;
	const u = JSON.parse(readFileSync(p, "utf8"));
	return Object.entries(u.sessions ?? {}).filter(([k]) => !exceptFile || k !== path.basename(exceptFile))
		.reduce((a, [, s]: [string, any]) => a + (s.cost_usd ?? 0), 0);
}

function watchCost(ctx: Ctx, session: AgentSession, label: string) {
	session.subscribe((e: any) => {
		if (e.type !== "message_end" || e.message?.role !== "assistant") return;
		recordUsage(ctx.runId, label, session, 0); // keep usage current even if the process dies mid-prompt
		if (ctx.capHit) return;
		const total = priorCost(ctx.runId, session.sessionFile) + session.getSessionStats().cost;
		if (total > costCap(ctx)) {
			ctx.capHit = true;
			ctx.log(`[host] cost cap reached (${total.toFixed(2)} > ${costCap(ctx)} USD list price); aborting the session`);
			void session.abort();
		}
	});
}

export function plan(arm: string, reviewRounds = 1): string[] {
	if (arm === "propose_only") return ["propose:1", "evaluate:1", "conclude", "freeze"];
	if (arm === "self_revise") return ["propose:1", "evaluate:1", "revise:2", "evaluate:2", "conclude", "freeze"];
	if (arm === "critique_revise") {
		const s = ["propose:1", "evaluate:1"];
		for (let r = 1; r <= reviewRounds; r++) s.push(`review:${r}`, `revise:${r + 1}`, `evaluate:${r + 1}`);
		return [...s, "conclude", "freeze"];
	}
	throw new Error(`unknown agent arm ${arm} (enumeration runs through the Python CLI)`);
}

function hostLog(runId: string, line: string, echo: (s: string) => void) {
	const p = path.join(runDir(runId), "pi", "host.log");
	mkdirSync(path.dirname(p), { recursive: true });
	appendFileSync(p, `${new Date().toISOString()} ${line}\n`);
	echo(line);
}

export async function startRun(configPath: string, arm: string, opts: RunOptions & { runId?: string; model?: string; thinking?: string } = {}) {
	const init = await backendOrThrow(["init", "--config", configPath, "--arm", arm, ...(opts.runId ? ["--run-id", opts.runId] : [])]);
	const runCfg = JSON.parse(readFileSync(path.join(init.run_dir, "run.json"), "utf8"));
	const m = runCfg.config_snapshot.agent.model;
	const [provider, id] = opts.model ? opts.model.split(/\/(.*)/s) : [m.provider, m.id];
	HostState.create({ runId: init.run_id, arm, model: { provider, id }, thinking: opts.thinking ?? runCfg.config_snapshot.agent.thinking ?? "high" });
	await runSteps(init.run_id, opts);
	return init.run_id;
}

export async function resumeRun(runId: string, opts: RunOptions = {}) {
	if (!HostState.exists(runId)) throw new Error(`run ${runId} has no host state (was it started by the agent host?)`);
	await runSteps(runId, opts, true);
}

async function runSteps(runId: string, opts: RunOptions, resumed = false) {
	const state = HostState.load(runId);
	const runCfg = JSON.parse(readFileSync(path.join(runDir(runId), "run.json"), "utf8"));
	const runtime = opts.runtime ?? (await makeRuntime());
	const echo = opts.log ?? ((s: string) => process.stdout.write(s + "\n"));
	const ctx: Ctx = { runId, state, runCfg, runtime, log: (s) => hostLog(runId, s, echo), maxNudges: opts.maxNudges ?? 2 };
	if (resumed) {
		state.update({ resumes: state.data.resumes + 1 });
		ctx.resumeNote = await recoveryNote(ctx);
		ctx.log(`[host] resume #${state.data.resumes}; recovery note:\n${ctx.resumeNote}`);
	}
	const steps = plan(state.data.arm, runCfg.arm_config.review_rounds ?? 1);
	try {
		for (const step of steps) {
			if (state.isDone(step)) continue;
			ctx.log(`[host] step ${step}`);
			await doStep(ctx, step);
			state.done(step);
		}
		state.update({ phase: "done", submissionsOpen: false });
		ctx.log(`[host] run ${runId} complete`);
	} finally {
		ctx.investigator?.dispose();
	}
}

async function investigator(ctx: Ctx): Promise<AgentSession> {
	if (ctx.investigator) return ctx.investigator;
	const rd = runDir(ctx.runId);
	const toolkit = path.join(rd, "toolkit");
	const hasToolkit = existsSync(toolkit);
	const spec: SandboxSpec = {
		workspace: path.join(rd, "workspace"),
		readOnly: hasToolkit ? [path.join(rd, "evidence"), toolkit] : [path.join(rd, "evidence")],
		env: hasToolkit ? { PYTHONPATH: toolkit, NW_EVIDENCE: path.join(rd, "evidence") } : {},
		cpus: defaultSandboxCpus(),
	};
	const tctx: ToolContext = { runId: ctx.runId, state: ctx.state, fetchPolicy: ctx.runCfg.config_snapshot.fetch_policy, guard: new PathGuard(spec) };
	const tools = [...sandboxedBuiltins(spec), ...scientificTools(tctx)];
	const system = loadPrompt("investigator", {
		WORKSPACE: spec.workspace, EVIDENCE: spec.readOnly[0], BUDGET: String(ctx.runCfg.budget.candidate_budget ?? "unlimited"),
		TOOLKIT: hasToolkit ? `\n- An exploratory toolkit is importable in the sandbox: \`import nwlab\` (read-only, ${toolkit}). \`nwlab.check(c)\`, \`nwlab.simulate(c)\`, \`nwlab.quick_fit(c)\` and \`nwlab.plot(c, fit, path)\` take a candidate dict and run the official validator and a lighter version of the fitter in seconds. Its numbers are exploratory; official results come only from nw_evaluate.` : "",
	});
	const { provider, id } = ctx.state.data.model;
	const session = await openSession({
		runId: ctx.runId, kind: "investigator", cwd: spec.workspace, sessionDir: path.join(rd, "pi", "investigator"),
		sessionFile: ctx.state.data.sessionFile, systemPrompt: system, runtime: ctx.runtime,
		model: resolveModel(ctx.runtime, provider, id), thinking: ctx.state.data.thinking, tools,
	});
	if (!ctx.state.data.sessionFile) ctx.state.update({ sessionFile: session.sessionFile });
	session.subscribe((e: any) => {
		if (e.type === "tool_execution_start") ctx.log(`[investigator] tool ${e.toolName} ${JSON.stringify(e.args).slice(0, 300)}`);
		if (e.type === "tool_execution_end") ctx.log(`[investigator] tool ${e.toolName} done${e.isError ? " (error)" : ""}`);
		if (e.type === "message_end" && e.message?.role === "assistant") {
			const t = (e.message.content ?? []).filter((c: any) => c.type === "text").map((c: any) => c.text).join("\n");
			if (t.trim()) ctx.log(`[investigator] ${t.slice(0, 2000)}`);
		}
	});
	watchCost(ctx, session, "investigator");
	ctx.investigator = session;
	return session;
}

async function prompt(ctx: Ctx, text: string) {
	const s = await investigator(ctx);
	const body = ctx.resumeNote ? `${ctx.resumeNote}\n\n---\n\n${text}` : text;
	ctx.resumeNote = undefined;
	const t0 = Date.now();
	const before = s.messages.length;
	try {
		await s.prompt(body);
	} finally {
		recordUsage(ctx.runId, "investigator", s, Date.now() - t0);
	}
	if (ctx.capHit) throw new Error("cost cap reached; resume with a higher NW_MAX_COST_USD to continue");
	// A turn that ended on provider errors did not do its work: stop at a resumable point instead of advancing the
	// protocol (in particular, never freeze a run because the model could not be reached).
	const fresh = (s.messages.slice(before) as any[]).filter((m) => m.role === "assistant");
	const last = fresh[fresh.length - 1];
	if (last?.stopReason === "error") {
		throw new Error(`model call failed (${String(last.errorMessage ?? "error").slice(0, 200)}); the step is not marked done, resume later`);
	}
}

async function status(ctx: Ctx) {
	return await backendOrThrow(["status", "--run", ctx.runId]);
}

async function compareText(ctx: Ctx): Promise<string> {
	const d = await backendOrThrow(["compare", "--run", ctx.runId]);
	const lines = [d.ranking.note];
	for (const g of d.ranking.groups)
		for (const r of g.rows)
			lines.push(`${r.candidate_id} ${r.name} AICc=${r.aicc.toFixed(2)} dAICc=${r.delta_aicc.toFixed(2)} ${r.band} adequacy=${r.adequacy} in_declared_space=${r.in_enumeration_spaces.join(",") || "no"}${r.plausibility_flags.length ? ` flags=${r.plausibility_flags.join("; ")}` : ""}`);
	if (d.ranking.not_ranked.length) lines.push(`not fitted: ${JSON.stringify(d.ranking.not_ranked)}`);
	return lines.join("\n");
}

async function doStep(ctx: Ctx, step: string) {
	const [kind, nStr] = step.split(":");
	const n = Number(nStr ?? 0);
	const st = ctx.state;
	const budget: number | null = ctx.runCfg.budget.candidate_budget ?? null;
	const arm = st.data.arm;
	if (kind === "propose") {
		if (st.data.phase !== "propose" || st.data.round !== n) {
			const cap = arm === "propose_only" ? budget : (ctx.runCfg.arm_config.initial_round_max ?? budget);
			st.update({ phase: "propose", round: n, submissionsOpen: true, analysisOpen: false, roundCap: cap, roundSubmitted: 0 });
		}
		const after = arm === "propose_only"
			? "In this run there is no revision round: after submissions close you will see the fits and write a conclusion, but you cannot add candidates."
			: arm === "self_revise"
				? "After submissions close, every candidate is fitted and you get one revision round with the numerical results."
				: "After submissions close, every candidate is fitted, an independent reviewer examines a frozen bundle of definitions and results, and you get a revision round to address the review.";
		await prompt(ctx, `Phase: proposal, round ${n}. Read the evidence (nw_evidence, the plots, the dataset), explore with your own code if useful, then submit up to ${st.data.roundCap} candidate mechanisms with nw_submit_candidates: distinct hypotheses about the network, the rate laws and the fate of the unmeasured nitrogen, each with support metadata. Fitted results stay hidden until submissions close. ${after} End with a short note on what each candidate tests.`);
		for (let k = 0; k < ctx.maxNudges && st.data.roundSubmitted === 0; k++) {
			ctx.log("[host] no candidates stored this round; nudging");
			await prompt(ctx, `No candidate has been stored in this round yet (submissions: ${st.data.roundSubmitted}/${st.data.roundCap}). Submit your candidates with nw_submit_candidates now; fix any validation errors it reports.`);
		}
		st.update({ submissionsOpen: false });
		return;
	}
	if (kind === "evaluate") {
		st.update({ phase: "evaluate", submissionsOpen: false });
		const s = await status(ctx);
		const ids: string[] = s.not_evaluated;
		if (ids.length) {
			const r = await backendOrThrow(["evaluate", "--run", ctx.runId, "--ids", ...ids]);
			ctx.log(`[host] evaluated ${ids.length} candidate(s); fits run ${r.n_fits_run}`);
		}
		return;
	}
	if (kind === "review") {
		st.update({ phase: "review" });
		await runReview(ctx, n);
		return;
	}
	if (kind === "revise") {
		const s = await status(ctx);
		const remaining = budget === null ? null : Math.max(0, budget - s.agent_candidates_used);
		if (st.data.phase !== "revision" || st.data.round !== n) {
			st.update({ phase: "revision", round: n, submissionsOpen: (remaining ?? 1) > 0, analysisOpen: true, roundCap: remaining, roundSubmitted: 0 });
		}
		const results = await compareText(ctx);
		if (arm === "critique_revise") {
			const rid = st.data.reviews[st.data.reviews.length - 1];
			const rv = JSON.parse(readFileSync(reviewFile(ctx.runId, rid), "utf8")).review;
			await prompt(ctx, `Submissions for round ${n - 1} are closed and every candidate has been fitted with the shared evaluator. Code-computed ranking:\n${results}\n\nAn independent reviewer examined a frozen bundle of your candidates, the evidence and these results. Review ${rid}:\n${JSON.stringify(rv, null, 1)}\n\nAddress each finding: run additional analysis (nw_candidate_details, nw_profile, nw_discriminate, your own code) and/or submit new candidate versions (set "parent" to the candidate you revise; up to ${remaining ?? "unlimited"} new candidates this round), then evaluate them with nw_evaluate. Original candidates and results are kept. Finally record a response to every finding with nw_respond_to_review (review_id "${rid}"). You may dispute a finding if the numbers support you.`);
			for (let k = 0; k < ctx.maxNudges && !(await responded(ctx, rid)); k++) {
				ctx.log("[host] review not yet answered; nudging");
				await prompt(ctx, `Record a response to every finding of review ${rid} with nw_respond_to_review before this phase ends.`);
			}
		} else {
			await prompt(ctx, `Submissions for round ${n - 1} are closed and every candidate has been fitted with the shared evaluator. Code-computed ranking:\n${results}\n\nThis is your revision round: inspect the fits (nw_candidate_details, nw_profile, nw_discriminate, your own code) and submit up to ${remaining ?? "unlimited"} new candidates (set "parent" when revising one), then evaluate them with nw_evaluate. Original candidates and results are kept.`);
		}
		st.update({ submissionsOpen: false });
		return;
	}
	if (kind === "conclude") {
		st.update({ phase: "conclude", submissionsOpen: false, analysisOpen: true });
		const results = await compareText(ctx);
		await prompt(ctx, `Final phase. Code-computed ranking of every candidate:\n${results}\n\nRecord your conclusion with nw_record_conclusion: which candidates remain plausible and why (tie reasons to the computed numbers and diagnostics), which are rejected and why, what remains ambiguous (including observationally equivalent candidates and unresolved metadata), whether any candidate is adequate, and which feasible experiments would discriminate the survivors (nw_discriminate quantifies this at the fitted parameters). No new candidates can be submitted. Several plausible candidates, or none adequate, are acceptable conclusions.`);
		for (let k = 0; k < ctx.maxNudges && !st.data.concluded; k++) {
			ctx.log("[host] no conclusion recorded; nudging");
			await prompt(ctx, "Record your conclusion now with nw_record_conclusion.");
		}
		return;
	}
	if (kind === "freeze") {
		st.update({ phase: "freeze", analysisOpen: false });
		const f = await backendOrThrow(["freeze", "--run", ctx.runId]);
		ctx.log(`[host] frozen: selected ${JSON.stringify(f.selected_by_rule)}; agent plausible ${JSON.stringify(f.agent_concluded_plausible)}`);
		return;
	}
	throw new Error(`unknown step ${step}`);
}

const lit = (xs: string[]) => Type.Union(xs.map((x) => Type.Literal(x)));
const REF = Type.String({ description: "<artifact id>#<JSON pointer>, e.g. evaluation:C1234567890#/summary/aicc" });
export const REVIEW_SCHEMA = Type.Object({
	summary: Type.String(),
	findings: Type.Array(Type.Object({
		id: Type.String(),
		severity: lit(["blocker", "major", "minor", "note"]),
		category: lit(["chemistry", "statistics", "numerics", "data", "coverage", "interpretation"]),
		claim: Type.String(),
		targets: Type.Array(REF, { minItems: 1 }),
		evidence: Type.Array(Type.Object({
			ref: REF,
			value: Type.Optional(Type.Union([Type.Number(), Type.String()])),
			note: Type.Optional(Type.String()),
		}), { minItems: 1 }),
		check: Type.Object({ type: lit(["numerical", "literature", "assumption", "consistency"]), description: Type.String() }),
		action: Type.Object({ type: lit(["new_candidate", "additional_analysis", "experiment", "reinterpret", "none"]), description: Type.String() }),
	}), { minItems: 1 }),
	assessment: Type.Object({
		plausible_candidates: Type.Array(Type.String()),
		not_supported: Type.Array(Type.Object({ candidate_id: Type.String(), reason: Type.String() })),
		ambiguities: Type.Array(Type.String()),
		adequate_candidate_exists: lit(["yes", "no", "uncertain"]),
	}),
});

// Models sometimes serialize a nested object as a JSON string; parse such strings before schema validation so the
// content is judged, not the encoding.
export function parseJsonStrings(args: unknown): unknown {
	if (typeof args === "string") {
		const t = args.trim();
		if ((t.startsWith("{") && t.endsWith("}")) || (t.startsWith("[") && t.endsWith("]"))) {
			try {
				return parseJsonStrings(JSON.parse(t));
			} catch {
				return args;
			}
		}
		return args;
	}
	if (Array.isArray(args)) return args.map(parseJsonStrings);
	if (args && typeof args === "object") return Object.fromEntries(Object.entries(args).map(([k, v]) => [k, parseJsonStrings(v)]));
	return args;
}

function reviewFile(runId: string, rid: string) {
	const [bid, k] = rid.split("-R");
	return path.join(runDir(runId), "reviews", bid, `review-${k}.json`);
}

async function responded(ctx: Ctx, rid: string): Promise<boolean> {
	const [bid, k] = rid.split("-R");
	return existsSync(path.join(runDir(ctx.runId), "reviews", bid, `response-${k}.json`));
}

async function runReview(ctx: Ctx, round: number) {
	const b = await backendOrThrow(["bundle", "--run", ctx.runId]);
	const bid: string = b.bundle_id;
	const rd = runDir(ctx.runId);
	const bdir = path.join(rd, "reviews", bid);
	const existing = ctx.state.data.reviews.find((r) => r.startsWith(bid));
	if (existing) {
		ctx.log(`[host] review ${existing} already recorded for bundle ${bid}`);
		return;
	}
	// the store is authoritative: a review recorded before a crash (or by hand) is adopted, not repeated
	const stored = existsSync(bdir) ? readdirSync(bdir).filter((f) => /^review-\d+\.json$/.test(f)).sort() : [];
	if (stored.length) {
		const rid = JSON.parse(readFileSync(path.join(bdir, stored[stored.length - 1]), "utf8")).review_id;
		ctx.state.update({ reviews: [...ctx.state.data.reviews, rid] });
		ctx.log(`[host] adopted review ${rid} already in the store for bundle ${bid}`);
		return;
	}
	const maxAttempts = 2;
	for (let attempt = 1; attempt <= maxAttempts; attempt++) {
		let accepted: string | undefined;
		let tries = 0;
		const submit = defineTool({
			name: "submit_review",
			label: "Submit review",
			description: "Submit the review (summary, findings, assessment) as structured objects (not JSON strings). It is validated against the bundle; errors are returned for you to fix.",
			parameters: REVIEW_SCHEMA,
			prepareArguments: parseJsonStrings as any,
			async execute(_id, p) {
				tries++;
				const r = await backend(["record-review", "--run", ctx.runId, "--bundle", bid],
					{ review: p, reviewer: { model: `${ctx.state.data.model.provider}/${ctx.state.data.model.id}`, round, attempt } });
				if (!r.ok) return { content: [{ type: "text" as const, text: `error: ${r.error}` }], details: undefined, isError: true };
				if (!r.result.accepted) {
					return { content: [{ type: "text" as const, text: `review rejected (${r.result.errors.length} problems), fix and resubmit:\n- ${r.result.errors.join("\n- ")}` }], details: undefined, isError: true };
				}
				accepted = r.result.review_id;
				return { content: [{ type: "text" as const, text: `review ${accepted} recorded` }], details: undefined, terminate: true };
			},
		});
		const scratch = path.join(bdir, "reviewer_scratch");
		mkdirSync(scratch, { recursive: true });
		const readOnly = [bdir];
		const tools = [sandboxedBuiltins({ workspace: scratch, readOnly })[0], submit];
		const system = loadPrompt("reviewer", { BUNDLE: path.join(bdir, "bundle.json"), PLOTS: path.join(bdir, "plots") });
		const session = await openSession({
			runId: ctx.runId, kind: "reviewer", cwd: scratch, sessionDir: path.join(rd, "pi", "reviews", bid),
			systemPrompt: system, runtime: ctx.runtime,
			model: resolveModel(ctx.runtime, ctx.state.data.model.provider, ctx.state.data.model.id), thinking: ctx.state.data.thinking, tools,
		});
		ctx.state.update({ reviewerSessions: [...ctx.state.data.reviewerSessions, session.sessionFile ?? "memory"] });
		watchCost(ctx, session, `reviewer-${bid}`);
		session.subscribe((e: any) => {
			if (e.type === "tool_execution_start") ctx.log(`[reviewer] tool ${e.toolName}`);
			if (e.type === "tool_execution_end" && e.isError) ctx.log(`[reviewer] tool ${e.toolName} error`);
		});
		const t0 = Date.now();
		try {
			const plotFiles = existsSync(path.join(bdir, "plots")) ? readdirSync(path.join(bdir, "plots")).sort().map((f) => path.join(bdir, "plots", f)) : [];
			await session.prompt(`Review bundle ${bid} (${b.artifact_ids.length} artifacts: ${b.artifact_ids.join(", ")}). Read ${path.join(bdir, "bundle.json")} and the plots, then call submit_review.\nPlot files (fits_k.png overlays up to four candidates each; <id>_residuals.png are standardized residuals):\n${plotFiles.join("\n") || "(none)"}`);
			for (let k = 0; k < 3 && !accepted && tries > 0; k++) {
				await session.prompt("The review was not accepted yet. Fix the reported problems and call submit_review again.");
			}
			if (!accepted && tries === 0) await session.prompt("Call submit_review now.");
		} finally {
			recordUsage(ctx.runId, `reviewer-${bid}`, session, Date.now() - t0);
			session.dispose();
		}
		if (ctx.capHit) throw new Error("cost cap reached during review; resume with a higher NW_MAX_COST_USD to continue");
		if (accepted) {
			ctx.state.update({ reviews: [...ctx.state.data.reviews, accepted] });
			ctx.log(`[host] review ${accepted} accepted`);
			return;
		}
		ctx.log(`[host] reviewer attempt ${attempt} produced no valid review`);
	}
	throw new Error(`no valid review for bundle ${bid} after ${maxAttempts} reviewer sessions`);
}

// Tool calls whose results were stored by the backend but never reached the conversation (host died in between).
export function orphanedToolCalls(runId: string, sessionFile?: string): any[] {
	const delivered = new Set<string>();
	if (sessionFile && existsSync(sessionFile)) {
		for (const line of readFileSync(sessionFile, "utf8").split("\n")) {
			if (!line.trim()) continue;
			try {
				const e = JSON.parse(line);
				if (e.type === "message" && e.message?.role === "toolResult") delivered.add(e.message.toolCallId);
			} catch {
				/* torn final line */
			}
		}
	}
	const j = readJournal(runId);
	const finished = new Map(j.filter((x) => x.event === "finish").map((x) => [x.toolCallId, x]));
	return j.filter((x) => x.event === "start" && !delivered.has(x.toolCallId))
		.map((x) => ({ toolCallId: x.toolCallId, tool: x.tool, args: x.args, input: x.input, backend: finished.get(x.toolCallId) ?? null }));
}

async function recoveryNote(ctx: Ctx): Promise<string> {
	const s = await status(ctx);
	const orphans = orphanedToolCalls(ctx.runId, ctx.state.data.sessionFile);
	const lines = [`[Host notice] The host process restarted (resume #${ctx.state.data.resumes}). The store below is authoritative; anything you remember that disagrees with it is out of date.`,
		`Store status: ${JSON.stringify({ phase: s.phase, candidates: s.candidates, status_counts: s.status_counts, agent_candidates_used: s.agent_candidates_used, budget: s.candidate_budget, reviews: s.reviews, review_responses: s.review_responses, conclusions: s.conclusions, reconciled_attempts: s.reconciled_attempts })}`,
		`Host phase: ${ctx.state.data.phase}, round ${ctx.state.data.round}, submissions ${ctx.state.data.submissionsOpen ? "open" : "closed"} (${ctx.state.data.roundSubmitted}/${ctx.state.data.roundCap ?? "unlimited"} this round).`];
	if (orphans.length) {
		lines.push("These tool calls reached the backend but their results never reached this conversation:");
		for (const o of orphans) {
			lines.push(`- ${o.tool} (call ${o.toolCallId}) args=${JSON.stringify(o.args)}: ${o.backend ? `backend finished ok=${o.backend.ok}; its outcome is in the store` : "no completion record; it may not have finished"}`);
			if (o.tool === "nw_evaluate") {
				const ids = o.args.slice(o.args.indexOf("--ids") + 1);
				const sm = await backend(["summaries", "--run", ctx.runId]);
				for (const x of (sm.result ?? []).filter((y: any) => ids.includes(y.candidate_id)))
					lines.push(`    ${x.candidate_id}: ${x.status}${x.aicc !== undefined ? ` AICc=${x.aicc.toFixed(2)} adequacy=${x.adequacy}` : ""}`);
			}
		}
		lines.push("Do not repeat them blindly: repeated evaluations return the stored result, and duplicate submissions are detected.");
	}
	return lines.join("\n");
}

// Send one extra instruction to a run's persistent investigator (for people steering an investigation by hand).
// Phase gates still apply: submissions are only accepted while the host has them open.
export async function askInvestigator(runId: string, message: string, runtime?: ModelRuntime) {
	const state = HostState.load(runId);
	const runCfg = JSON.parse(readFileSync(path.join(runDir(runId), "run.json"), "utf8"));
	const ctx: Ctx = { runId, state, runCfg, runtime: runtime ?? (await makeRuntime()), log: (s) => hostLog(runId, s, (x) => process.stdout.write(x + "\n")), maxNudges: 0 };
	const orphans = orphanedToolCalls(runId, state.data.sessionFile);
	if (orphans.length) ctx.resumeNote = await recoveryNote(ctx);
	// read-only analysis tools stay usable for questions about a finished run; submission gates are unchanged
	const prevAnalysis = state.data.analysisOpen;
	state.update({ analysisOpen: true });
	try {
		await prompt(ctx, message);
	} finally {
		state.update({ analysisOpen: prevAnalysis });
		ctx.investigator?.dispose();
	}
}
