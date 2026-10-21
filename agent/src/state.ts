// Host-side orchestration state (which step of the arm protocol is done, which session files belong to the run).
// Scientific state is never kept here; it lives in the Python store. Writes are atomic (tmp + rename).
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";
import { runDir } from "./config.ts";

export type Phase = "init" | "propose" | "evaluate" | "review" | "revision" | "conclude" | "freeze" | "done";

export interface HostData {
	runId: string;
	arm: string;
	phase: Phase;
	round: number;
	submissionsOpen: boolean;
	analysisOpen: boolean;
	roundCap: number | null;
	roundSubmitted: number;
	spacesSubmitted?: number; // propose_space arm: hypothesis spaces accepted so far
	stepsDone: string[];
	sessionFile?: string;
	reviewerSessions: string[];
	reviews: string[];
	model: { provider: string; id: string };
	thinking: string;
	concluded: boolean;
	resumes: number;
	createdAt: string;
	updatedAt?: string;
}

export class HostState {
	readonly file: string;
	data: HostData;
	constructor(file: string, data: HostData) {
		this.file = file;
		this.data = data;
	}
	static path(runId: string) {
		return path.join(runDir(runId), "pi", "host_state.json");
	}
	static exists(runId: string) {
		return existsSync(HostState.path(runId));
	}
	static load(runId: string): HostState {
		const f = HostState.path(runId);
		return new HostState(f, JSON.parse(readFileSync(f, "utf8")));
	}
	static create(init: Omit<HostData, "createdAt" | "stepsDone" | "reviewerSessions" | "reviews" | "concluded" | "resumes" | "round" | "phase" | "submissionsOpen" | "analysisOpen" | "roundCap" | "roundSubmitted">): HostState {
		const f = HostState.path(init.runId);
		const s = new HostState(f, {
			...init, phase: "init", round: 0, submissionsOpen: false, analysisOpen: false, roundCap: null, roundSubmitted: 0,
			stepsDone: [], reviewerSessions: [], reviews: [], concluded: false, resumes: 0, createdAt: new Date().toISOString(),
		});
		s.save();
		return s;
	}
	update(p: Partial<HostData>) {
		this.data = { ...this.data, ...p, updatedAt: new Date().toISOString() };
		this.save();
	}
	done(step: string) {
		if (!this.data.stepsDone.includes(step)) this.update({ stepsDone: [...this.data.stepsDone, step] });
	}
	isDone(step: string) {
		return this.data.stepsDone.includes(step);
	}
	private save() {
		mkdirSync(path.dirname(this.file), { recursive: true });
		const tmp = `${this.file}.${process.pid}.tmp`;
		writeFileSync(tmp, JSON.stringify(this.data, null, 1));
		renameSync(tmp, this.file);
	}
}
