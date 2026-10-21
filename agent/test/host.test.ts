// Host integration tests. The model is Pi's faux provider driven by src/mock.ts (MOCKED MODEL RESPONSES): these tests
// exercise the real host, sandbox, Python backend and store, and say nothing about live agent performance.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, symlinkSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { REPO } from "../src/config.ts";
import { PathGuard, sandboxedBash } from "../src/sandbox.ts";

const AGENT = path.join(REPO, "agent");

function tmp(prefix: string) {
	return mkdtempSync(path.join(os.tmpdir(), prefix));
}

test("path guard confines read/write to the workspace and evidence, including through symlinks", async () => {
	const d = tmp("nw-guard-");
	const ws = path.join(d, "ws");
	const ev = path.join(d, "ev");
	mkdirSync(ws);
	mkdirSync(ev);
	writeFileSync(path.join(ev, "ok.json"), "{}");
	const secret = path.join(d, "holdout.json");
	writeFileSync(secret, "secret");
	symlinkSync(secret, path.join(ws, "link.json"));
	const g = new PathGuard({ workspace: ws, readOnly: [ev] });
	assert.equal((await g.readOps().readFile(path.join(ev, "ok.json"))).toString(), "{}");
	await assert.rejects(g.readOps().readFile(secret), /access denied/);
	await assert.rejects(g.readOps().readFile(path.join(ws, "link.json")), /access denied/);
	await assert.rejects(g.writeOps().writeFile(path.join(ev, "x.json"), "x"), /access denied/);
	await assert.rejects(g.writeOps().writeFile(path.join(ws, "link.json"), "x"), /symlink/);
	await g.writeOps().writeFile(path.join(ws, "sub", "a.txt"), "a");
	assert.equal(readFileSync(path.join(ws, "sub", "a.txt"), "utf8"), "a");
});

test("sandboxed bash sees no repository, held-out data, credentials or network", async () => {
	const d = tmp("nw-sbx-");
	const ws = path.join(d, "ws");
	const ev = path.join(d, "ev");
	mkdirSync(ws);
	mkdirSync(ev);
	writeFileSync(path.join(ev, "e.txt"), "evidence");
	let out = "";
	const cmd = [
		`cat ${path.join(ev, "e.txt")}`,
		`ls ${path.join(REPO, "data", "real")} 2>&1`,
		`cat ${path.join(os.homedir(), ".pi", "agent", "auth.json")} 2>&1`,
		`cat ${path.join(os.homedir(), ".config", "nernstwork", "anthropic_api_key")} 2>&1`,
		"env",
		`python -c "import urllib.request; urllib.request.urlopen('https://example.com', timeout=3)" 2>&1 | tail -1`,
		`echo x > ${path.join(ev, "w.txt")} 2>&1`,
		"python -c 'import numpy, scipy, matplotlib; print(\"py-ok\")'",
	].join("; ");
	const r = await sandboxedBash({ workspace: ws, readOnly: [ev] }).exec(cmd, ws, { onData: (b) => (out += b.toString()) });
	assert.equal(r.exitCode, 0, out);
	assert.match(out, /evidence/);
	assert.match(out, /real.*No such file or directory/);
	assert.match(out, /auth\.json.*No such file or directory/);
	assert.match(out, /anthropic_api_key.*No such file or directory/);
	assert.doesNotMatch(out, /sk-ant-/);
	assert.doesNotMatch(out, /ANTHROPIC|OPENAI|OPENROUTER|PI_SESSION|CLAUDE/);
	assert.match(out, /URLError|Temporary failure|Network is unreachable|Name or service not known/);
	assert.match(out, /Read-only file system/);
	assert.match(out, /py-ok/);
});

function host(args: string[], env: Record<string, string>) {
	return spawnSync(process.execPath, [path.join(AGENT, "src", "cli.ts"), ...args], {
		cwd: AGENT, env: { ...process.env, ...env }, encoding: "utf8", timeout: 900_000,
	});
}

test("investigation resumes after the host dies between a committed result and its tool response (mocked model)", () => {
	const root = tmp("nw-host-");
	const env = { NW_ROOT: root };
	const cfg = path.join(REPO, "configs", "investigations", "liao50.json");
	const first = host(["start", "--config", cfg, "--arm", "critique_revise", "--run-id", "crash1", "--mock"], { ...env, NW_HOST_FAULT: "after_evaluate_commit" });
	assert.notEqual(first.status, 0, "host should have been killed by the fault hook");
	const run = path.join(root, "runs", "crash1");
	const st = JSON.parse(readFileSync(path.join(run, "pi", "host_state.json"), "utf8"));
	assert.equal(st.phase, "revision");
	// the scientific result is in the store ...
	const evals = readdirSync(path.join(run, "evaluations"));
	const journal = readFileSync(path.join(run, "pi", "tool_journal.jsonl"), "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
	const evalCall = journal.find((j) => j.tool === "nw_evaluate" && j.event === "finish");
	assert.ok(evalCall?.ok, "backend finished the evaluation");
	// ... but its tool result never reached the session
	const session = readFileSync(st.sessionFile, "utf8");
	assert.ok(!session.includes(`"toolCallId":"${evalCall.toolCallId}"`) || !session.split("\n").some((l) => l.includes('"role":"toolResult"') && l.includes(evalCall.toolCallId)));
	const status = JSON.parse(host(["status", "--run", "crash1"], env).stdout);
	assert.ok(status.orphaned_tool_calls.some((o: any) => o.tool === "nw_evaluate" && o.backend?.ok));

	const second = host(["resume", "--run", "crash1", "--mock"], env);
	assert.equal(second.status, 0, second.stderr + second.stdout);
	assert.match(second.stdout, /never reached this conversation/);
	const fin = JSON.parse(readFileSync(path.join(run, "pi", "host_state.json"), "utf8"));
	assert.equal(fin.phase, "done");
	assert.ok(existsSync(path.join(run, "frozen.json")));
	assert.ok(readdirSync(path.join(run, "conclusions")).length >= 1);
	// no duplicate committed results: one result per fit key, and evaluation records were not rewritten
	for (const k of readdirSync(path.join(root, "cache", "fits"))) {
		const states = readdirSync(path.join(root, "cache", "fits", k, "attempts"))
			.map((f) => JSON.parse(readFileSync(path.join(root, "cache", "fits", k, "attempts", f), "utf8")).state);
		assert.equal(states.filter((s) => s === "committed").length, 1, `${k}: ${states}`);
	}
	assert.deepEqual(readdirSync(path.join(run, "evaluations")).filter((f) => evals.includes(f)).sort(), evals.sort());
	// the review path rejected a review quoting a wrong number before accepting a valid one
	const events = readFileSync(path.join(run, "events.jsonl"), "utf8");
	assert.match(events, /"type":"review_rejected"/);
	assert.match(events, /"type":"review_recorded"/);
});

test("sandbox bounds CPU, runs at lower priority, and can import the read-only toolkit", async () => {
	const root = tmp("nw-tk-");
	const init = spawnSync(path.join(REPO, ".venv", "bin", "python"), ["-m", "nernstwork.cli", "--root", root, "init",
		"--config", path.join(REPO, "configs", "investigations", "liao50.json"), "--arm", "manual", "--run-id", "tk"], {
		cwd: REPO, env: { ...process.env, PYTHONPATH: path.join(REPO, "src") }, encoding: "utf8",
	});
	assert.equal(init.status, 0, init.stderr);
	const rd = path.join(root, "runs", "tk");
	const spec = {
		workspace: path.join(rd, "workspace"), readOnly: [path.join(rd, "evidence"), path.join(rd, "toolkit")],
		env: { PYTHONPATH: path.join(rd, "toolkit"), NW_EVIDENCE: path.join(rd, "evidence") }, cpus: "0-1",
	};
	writeFileSync(path.join(spec.workspace, "c.json"), JSON.stringify({ name: "c", mechanism: { id: "c",
		species: [{ id: "NO3", N_oxidation_state: 5 }, { id: "NO2", N_oxidation_state: 3 }, { id: "NH3", N_oxidation_state: -3 }],
		reactions: [{ id: "R1", reactants: [{ species: "NO3", coeff: 1 }], products: [{ species: "NO2", coeff: 1 }], electrons: 2,
			rate_law: { family: "mass_action", params: { k: { value: 0.001 } } } },
		{ id: "R2", reactants: [{ species: "NO2", coeff: 1 }], products: [{ species: "NH3", coeff: 1 }], electrons: 6,
			rate_law: { family: "mass_action", params: { k: { value: 0.01 } } } }] } }));
	let out = "";
	const r = await sandboxedBash(spec).exec(
		"grep Cpus_allowed_list /proc/self/status; nice; python -c \"import json, nwlab; print('CHECK', nwlab.check(json.load(open('c.json')))['status'])\"",
		spec.workspace, { onData: (b) => (out += b.toString()) });
	assert.equal(r.exitCode, 0, out);
	assert.match(out, /Cpus_allowed_list:\s+0-1/);
	assert.match(out, /^10$/m);
	assert.match(out, /CHECK valid/);
});

test("candidates can be submitted from a workspace file but not from outside the guard", async () => {
	const { loadCandidatesFile } = await import("../src/tools.ts");
	const d = tmp("nw-file-");
	const ws = path.join(d, "ws");
	mkdirSync(ws);
	const g = new PathGuard({ workspace: ws, readOnly: [] });
	writeFileSync(path.join(ws, "list.json"), JSON.stringify([{ name: "a" }, { name: "b" }]));
	writeFileSync(path.join(ws, "wrapped.json"), JSON.stringify({ candidates: [{ name: "c" }] }));
	writeFileSync(path.join(ws, "one.json"), JSON.stringify({ name: "d" }));
	writeFileSync(path.join(d, "outside.json"), JSON.stringify([{ name: "x" }]));
	assert.equal((await loadCandidatesFile(g, "list.json", ws)).length, 2);
	assert.equal(((await loadCandidatesFile(g, "wrapped.json", ws))[0] as any).name, "c");
	assert.equal(((await loadCandidatesFile(g, path.join(ws, "one.json"), ws))[0] as any).name, "d");
	await assert.rejects(loadCandidatesFile(g, path.join(d, "outside.json"), ws), /access denied/);
});
