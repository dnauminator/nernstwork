// Shot 9: what we found, the conclusion, credits. Numeric findings are computed from the exported run data (shot5b); the
// qualitative ones restate docs/SYNTHESIS.md (observations 4-6), the run conclusions, and for the catalysis link
// docs/VALENCY_BRIDGE_OCT22.md and docs/examples/wang2025_figS18/README.md (Wang et al., J. Hazard. Mater. 2025).
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import data from "./data/shots.json";
import { C, fontFamily } from "./theme";

export const SHOT9_FRAMES = 900;
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
	["A first link to catalysis", "found with Valency: TiO₂ made at 700 °C (anatase) or 900 °C (rutile) for nitrate-to-ammonia catalysts, rutile best; our engine fits the rutile catalyst's nitrate data"],
];

export const Shot9Close: React.FC = () => {
	const frame = useCurrentFrame();
	const titleIn = interpolate(frame, [0, 18], [0, 1], clamp);
	const closeIn = interpolate(frame, [650, 680], [0, 1], clamp);
	const creditsIn = interpolate(frame, [710, 740], [0, 1], clamp);
	return (
		<AbsoluteFill style={{ background: C.page, fontFamily, color: C.ink }}>
			<div style={{ position: "absolute", left: 96, top: 64, opacity: titleIn }}>
				<div style={{ fontSize: 28, color: C.ink2, fontWeight: 500, marginBottom: 10 }}>Chapman 750 °C test · retrospective, one chemistry, two runs per model</div>
				<div style={{ fontSize: 58, fontWeight: 700, letterSpacing: -0.5 }}>What we found</div>
			</div>
			<div style={{ position: "absolute", left: 96, top: 222, width: 1700 }}>
				{FINDINGS.map(([head, sub], k) => {
					// paced to the voiceover: the first four together, the catalysis link after its own sentence
					const start = k < 4 ? 30 + k * 40 : 330;
					const o = interpolate(frame, [start, start + 20], [0, 1], clamp);
					return (
						<div key={k} style={{ opacity: o, transform: `translateY(${(1 - o) * 14}px)`, display: "flex", gap: 26, marginBottom: 20 }}>
							<div style={{ fontSize: 30, fontWeight: 700, color: C.muted, width: 30, fontVariantNumeric: "tabular-nums" }}>{k + 1}</div>
							<div>
								<div style={{ fontSize: 34, fontWeight: 700, display: "flex", alignItems: "center", gap: 16 }}>
									{head}
									{k < 2 ? (
										<span style={{ fontSize: 18, fontWeight: 600, color: C.ink2, border: `1.5px solid ${C.axis}`, borderRadius: 999,
											padding: "3px 12px" }}>answers Q{k + 1}</span>
									) : null}
								</div>
								<div style={{ fontSize: 23, color: C.ink2, marginTop: 5 }}>{sub}</div>
							</div>
						</div>
					);
				})}
			</div>
			<div style={{ position: "absolute", left: 96, right: 96, top: 832, opacity: closeIn, fontSize: 32, fontWeight: 600, color: C.ink, borderTop: `1.5px solid ${C.axis}`, paddingTop: 26 }}>
				The AI is useful for proposing pathways. Choosing among them still takes a targeted experiment.
			</div>
			<div style={{ position: "absolute", left: 96, right: 96, top: 930, opacity: creditsIn, fontSize: 22, color: C.muted, lineHeight: 1.6 }}>
				<span style={{ color: C.ink, fontWeight: 600 }}>NernstWork</span> · Daniel Naumov and Jarrod Barnes · OSI Hackathon, October 2026
				<br />
				Data: {data.shot1.short_citation} (Chapman group). Models: {models.join(", ")}. Literature search: Valency.
			</div>
		</AbsoluteFill>
	);
};
