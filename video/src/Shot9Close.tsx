// Shot 9: what we found, then the closing line and credits. Numeric findings are computed from the exported run data
// (shot5b); the qualitative ones restate docs/SYNTHESIS.md (observations 4-6) and the run conclusions.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import data from "./data/shots.json";
import { C, fontFamily } from "./theme";

export const SHOT9_FRAMES = 540;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const ai = data.shot5b.runs.filter((r) => r.best_plausible_rank !== null);
const worstOwn = Math.max(...ai.map((r) => r.own_space_best_rank));
const nTop1 = ai.filter((r) => r.own_space_best_rank === 1).length;
const rules = ai.map((r) => r.rule_pick_rank);
const models = [...new Set(ai.map((r) => r.name))];

const FINDINGS: [string, string][] = [
	[`Every AI search space held a top-${worstOwn} predictor`, `#1 of ${data.shot5b.runs[0].n_space} reference models in ${nTop1} of ${ai.length} runs, at a temperature no model saw`],
	["Picking by best fit is the weak point", `the selection rule's picks ranked #${Math.min(...rules)} to #${Math.max(...rules)}`],
	["The chemistry agrees", `the same network and similar activation energies from ${models.join(" and ")}`],
	["It says what's unresolved, and what to measure next", "including a data inconsistency in lithium, and an experiment that splits a rival explanation"],
];

export const Shot9Close: React.FC = () => {
	const frame = useCurrentFrame();
	const titleIn = interpolate(frame, [0, 18], [0, 1], clamp);
	const closeIn = interpolate(frame, [230, 260], [0, 1], clamp);
	const creditsIn = interpolate(frame, [280, 310], [0, 1], clamp);
	return (
		<AbsoluteFill style={{ background: C.page, fontFamily, color: C.ink }}>
			<div style={{ position: "absolute", left: 96, top: 64, opacity: titleIn }}>
				<div style={{ fontSize: 28, color: C.ink2, fontWeight: 500, marginBottom: 10 }}>Chapman 750 °C test · retrospective, one chemistry, two runs per model</div>
				<div style={{ fontSize: 58, fontWeight: 700, letterSpacing: -0.5 }}>What we found</div>
			</div>
			<div style={{ position: "absolute", left: 96, top: 236, width: 1700 }}>
				{FINDINGS.map(([head, sub], k) => {
					const o = interpolate(frame, [30 + k * 40, 50 + k * 40], [0, 1], clamp);
					return (
						<div key={k} style={{ opacity: o, transform: `translateY(${(1 - o) * 14}px)`, display: "flex", gap: 26, marginBottom: 30 }}>
							<div style={{ fontSize: 30, fontWeight: 700, color: C.muted, width: 30, fontVariantNumeric: "tabular-nums" }}>{k + 1}</div>
							<div>
								<div style={{ fontSize: 36, fontWeight: 700 }}>{head}</div>
								<div style={{ fontSize: 25, color: C.ink2, marginTop: 6 }}>{sub}</div>
							</div>
						</div>
					);
				})}
			</div>
			<div style={{ position: "absolute", left: 96, right: 96, top: 800, opacity: closeIn, fontSize: 34, fontWeight: 600, color: C.ink, borderTop: `1.5px solid ${C.axis}`, paddingTop: 30 }}>
				Propose broadly. Test on data the models never saw. Say what's unresolved. Plan the next experiment.
			</div>
			<div style={{ position: "absolute", left: 96, right: 96, top: 905, opacity: creditsIn, fontSize: 22, color: C.muted, lineHeight: 1.6 }}>
				<span style={{ color: C.ink, fontWeight: 600 }}>NernstWork</span> · Daniel Naumov and Jarrod Barnes · OSI Hackathon, October 2026
				<br />
				Data: {data.shot1.short_citation} (Chapman group). Models: {models.join(", ")}. Literature search: Valency.
			</div>
		</AbsoluteFill>
	);
};
