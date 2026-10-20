// Host CLI.
//   node src/cli.ts start  --config ../configs/investigations/liao50.json --arm critique_revise [--run-id ID] [--model provider/id] [--thinking high] [--mock]
//   node src/cli.ts resume --run ID [--mock]
//   node src/cli.ts status --run ID
//   node src/cli.ts ask    --run ID --message "..." [--mock]    (extra instruction to the persistent investigator)
// --mock uses the scripted faux model (offline integration path; not a live agent).
import { parseArgs } from "node:util";
import path from "node:path";
import { backendOrThrow } from "./bridge.ts";
import { REPO } from "./config.ts";
import { MOCK_MODEL, mockRuntime } from "./mock.ts";
import { askInvestigator, orphanedToolCalls, resumeRun, startRun } from "./orchestrator.ts";
import { HostState } from "./state.ts";

async function main() {
	const [cmd, ...rest] = process.argv.slice(2);
	const { values } = parseArgs({
		args: rest,
		options: {
			config: { type: "string" }, arm: { type: "string" }, "run-id": { type: "string" }, run: { type: "string" },
			model: { type: "string" }, thinking: { type: "string" }, mock: { type: "boolean", default: false },
			message: { type: "string" },
		},
	});
	const runtime = values.mock ? await mockRuntime() : undefined;
	if (cmd === "start") {
		if (!values.config || !values.arm) throw new Error("start needs --config and --arm");
		const model = values.mock ? `${MOCK_MODEL.provider}/${MOCK_MODEL.id}` : values.model;
		const id = await startRun(path.resolve(values.config), values.arm, { runId: values["run-id"], model, thinking: values.thinking, runtime });
		console.log(JSON.stringify({ run_id: id }));
	} else if (cmd === "resume") {
		await resumeRun(req(values.run), { runtime });
	} else if (cmd === "status") {
		const id = req(values.run);
		const st = HostState.exists(id) ? HostState.load(id).data : null;
		const s = await backendOrThrow(["status", "--run", id]);
		console.log(JSON.stringify({ host: st, store: s, orphaned_tool_calls: orphanedToolCalls(id, st?.sessionFile) }, null, 1));
	} else if (cmd === "ask") {
		await askInvestigator(req(values.run), req(values.message), runtime);
	} else {
		console.log(`usage: start | resume | status | ask (repo ${REPO})`);
		process.exitCode = 2;
	}
}

function req(v: string | undefined): string {
	if (!v) throw new Error("missing required option");
	return v;
}

main().catch((e) => {
	console.error(e instanceof Error ? e.stack : e);
	process.exit(1);
});
