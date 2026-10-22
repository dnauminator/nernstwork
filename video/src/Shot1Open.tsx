// Shot 1: the research question, then the test case. (A) The question and the two sub-questions the findings answer.
// (B) The test case: the measured 725 C phase amounts draw themselves beside the study design (temperatures fitted and
// held out, read from the run manifest).
import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import data from "./data/shots.json";
import { Axes, linear, niceTicks, partialPath } from "./components/chart";
import { C, PHASES, fontFamily } from "./theme";

const S = data.shot1;
const N_REF = data.shot3.n_reference;
export const SHOT1_FRAMES = 810;

// phase identity colours: categorical slots 4-7 of the reference palette (dark steps), validated as an adjacent set and
// direct-labelled; they appear only in this shot
const PHASE_COLOR: Record<string, string> = { anatase: "#c98500", rutile: "#d55181", Li2TiO3: "#008300", Li4Ti5O12: "#9085e9" };
const LABEL: Record<string, string> = { anatase: "anatase TiO₂", rutile: "rutile TiO₂", Li2TiO3: "Li₂TiO₃", Li4Ti5O12: "Li₄Ti₅O₁₂" };
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const B0 = 510; // part B (the test case) starts here
const DRAW0 = B0 + 40, DRAW1 = B0 + 200;
const X0 = 170, X1 = 1180, Y0 = 930, Y1 = 330;

const Question: React.FC = () => {
	const frame = useCurrentFrame();
	const k = interpolate(frame, [0, 15], [0, 1], clamp);
	const q = interpolate(frame, [8, 30], [0, 1], clamp);
	const s1 = interpolate(frame, [150, 170], [0, 1], clamp);
	const s2 = interpolate(frame, [300, 320], [0, 1], clamp);
	const out = interpolate(frame, [B0 - 20, B0], [1, 0], clamp);
	const sub = (n: number, text: string, o: number) => (
		<div style={{ opacity: o, display: "flex", gap: 24, marginTop: 30, transform: `translateY(${(1 - o) * 10}px)` }}>
			<div style={{ fontSize: 32, fontWeight: 700, color: C.muted, width: 30 }}>{n}</div>
			<div style={{ fontSize: 34, color: C.ink2, lineHeight: 1.35 }}>{text}</div>
		</div>
	);
	return (
		<div style={{ position: "absolute", left: 140, right: 140, top: 230, opacity: out, color: C.ink }}>
			<div style={{ opacity: k, fontSize: 28, color: C.muted, fontWeight: 600, letterSpacing: 1.5, textTransform: "uppercase" }}>
				Research question
			</div>
			<div style={{ opacity: q, fontSize: 60, fontWeight: 700, lineHeight: 1.2, letterSpacing: -0.5, marginTop: 22, maxWidth: 1500 }}>
				Can a language-model agent infer a solid-state reaction pathway from time-resolved phase data?
			</div>
			<div style={{ marginTop: 34 }}>
				{sub(1, "Does the pathway space it proposes contain a model that predicts an unseen temperature?", s1)}
				{sub(2, "Can that model be selected from the training runs alone?", s2)}
			</div>
		</div>
	);
};

const TestCase: React.FC = () => {
	const frame = useCurrentFrame();
	const series = S.series as Record<string, { t: number[]; y: number[] }>;
	const tmax = Math.max(...Object.values(series).flatMap((s) => s.t));
	const yTicks = niceTicks(Math.max(...Object.values(series).flatMap((s) => s.y)), 5);
	const x = linear(0, tmax, X0, X1);
	const y = linear(0, yTicks[yTicks.length - 1], Y0, Y1);
	const p = interpolate(frame, [DRAW0, DRAW1], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
	const tNow = p * tmax;
	const head = interpolate(frame, [B0, B0 + 20], [0, 1], clamp);
	const labelIn = interpolate(frame, [DRAW1 - 10, DRAW1 + 10], [0, 1], clamp);
	const design = [
		...S.development_C.map((T, i) => ({ T, text: "fitted", o: interpolate(frame, [B0 + 60 + i * 20, B0 + 80 + i * 20], [0, 1], clamp), sealed: false })),
		...S.heldout_C.map((T) => ({ T, text: "sealed, predicted without refitting", o: interpolate(frame, [B0 + 120, B0 + 140], [0, 1], clamp), sealed: true })),
	];
	return (
		<div style={{ opacity: head }}>
			<div style={{ position: "absolute", left: 96, top: 64, color: C.ink }}>
				<div style={{ fontSize: 28, color: C.ink2, fontWeight: 500, marginBottom: 10 }}>Test case · data {S.short_citation} (Chapman group)</div>
				<div style={{ fontSize: 52, fontWeight: 700, letterSpacing: -0.5 }}>
					TiO₂ + Li₂CO₃ → Li₄Ti₅O₁₂, a battery anode, by in situ X-ray scattering
				</div>
			</div>
			<div style={{ position: "absolute", left: X0, top: Y1 - 62, fontSize: 24, color: C.ink2 }}>
				Measured at {S.temperature_C} °C · <span style={{ fontVariantNumeric: "tabular-nums", color: C.ink, fontWeight: 600 }}>{tNow.toFixed(1)} min</span>
			</div>
			<svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
				<Axes x={x} y={y} xTicks={[0, 2, 4, 6, 8]} yTicks={yTicks} x0={X0} x1={X1} y0={Y0} y1={Y1} fontSize={21}
					xLabel="minutes after the pellet enters the furnace" />
				<text x={X0 - 70} y={(Y0 + Y1) / 2} fill={C.muted} fontSize={21} transform={`rotate(-90 ${X0 - 70} ${(Y0 + Y1) / 2})`}
					textAnchor="middle" style={{ fontFamily }}>mol per mol Ti</text>
				{PHASES.map((ph) => {
					const s = series[ph.id];
					const i = s.t.findIndex((t) => t > tNow);
					const kk = i === -1 ? s.t.length - 1 : Math.max(i - 1, 0);
					const frac = i === -1 ? 1 : (kk + (tNow - s.t[kk]) / (s.t[kk + 1] - s.t[kk])) / (s.t.length - 1);
					return (
						<g key={ph.id}>
							<path d={partialPath(s.t, s.y, x, y, tNow >= s.t[0] ? Math.max(frac, 0) : 0)} fill="none" stroke={PHASE_COLOR[ph.id]}
								strokeWidth={4} strokeLinejoin="round" strokeLinecap="round" />
							{s.t.map((t, j) => (t <= tNow ? <circle key={j} cx={x(t)} cy={y(s.y[j])} r={4.5} fill={PHASE_COLOR[ph.id]} stroke={C.page} strokeWidth={2} /> : null))}
							<text x={X1 + 16} y={y(s.y[s.y.length - 1]) + (ph.id === "Li4Ti5O12" ? -6 : ph.id === "anatase" ? 16 : ph.id === "rutile" ? 14 : 2)}
								fill={C.ink} fontSize={22} fontWeight={500} opacity={labelIn} style={{ fontFamily }}>{LABEL[ph.id]}</text>
						</g>
					);
				})}
			</svg>
			<div style={{ position: "absolute", left: 1420, top: Y1 - 10, width: 420, color: C.ink }}>
				<div style={{ fontSize: 22, color: C.muted, marginBottom: 18 }}>Study design</div>
				{design.map((d) => (
					<div key={d.T} style={{ opacity: d.o, display: "flex", alignItems: "baseline", gap: 18, padding: "16px 20px", marginBottom: 14,
						borderRadius: 12, border: `1.5px solid ${d.sealed ? C.ink2 : C.axis}`, background: C.surface }}>
						<span style={{ fontSize: 30, fontWeight: 700, minWidth: 110 }}>{d.T} °C</span>
						<span style={{ fontSize: 22, color: d.sealed ? C.ink : C.ink2, lineHeight: 1.3 }}>{d.text}</span>
					</div>
				))}
				<div style={{ opacity: interpolate(frame, [B0 + 160, B0 + 180], [0, 1], clamp), fontSize: 21, color: C.ink2, lineHeight: 1.4, marginTop: 10 }}>
					Each prediction is ranked against {N_REF} reference models built by code.
				</div>
			</div>
		</div>
	);
};

export const Shot1Open: React.FC = () => (
	<AbsoluteFill style={{ background: C.page, fontFamily }}>
		<Question />
		<TestCase />
	</AbsoluteFill>
);
