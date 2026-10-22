// Shot 1: cold open. The measured 725 C phase amounts draw themselves, then the research question.
import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import data from "./data/shots.json";
import { Axes, linear, niceTicks, partialPath } from "./components/chart";
import { C, PHASES, fontFamily } from "./theme";

const S = data.shot1;
export const SHOT1_FRAMES = 600;

// phase identity colours: categorical slots 4-7 of the reference palette (dark steps), validated as an adjacent set and
// direct-labelled; distinct from the model colours used from shot 4 on
const PHASE_COLOR: Record<string, string> = { anatase: "#c98500", rutile: "#d55181", Li2TiO3: "#008300", Li4Ti5O12: "#9085e9" };
const LABEL: Record<string, string> = { anatase: "anatase TiO₂", rutile: "rutile TiO₂", Li2TiO3: "Li₂TiO₃", Li4Ti5O12: "Li₄Ti₅O₁₂, a battery anode" };
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const DRAW0 = 24, DRAW1 = 300, QUESTION = 330;
const X0 = 170, X1 = 1460, Y0 = 900, Y1 = 250;

export const Shot1Open: React.FC = () => {
	const frame = useCurrentFrame();
	const series = S.series as Record<string, { t: number[]; y: number[] }>;
	const tmax = Math.max(...Object.values(series).flatMap((s) => s.t));
	const ymax = niceTicks(Math.max(...Object.values(series).flatMap((s) => s.y)), 5);
	const x = linear(0, tmax, X0, X1);
	const y = linear(0, ymax[ymax.length - 1], Y0, Y1);
	const p = interpolate(frame, [DRAW0, DRAW1], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
	const tNow = p * tmax;
	const chartIn = interpolate(frame, [0, 18], [0, 1], clamp);
	const dim = interpolate(frame, [QUESTION, QUESTION + 30], [1, 0.22], clamp);
	const q1 = interpolate(frame, [QUESTION + 15, QUESTION + 40], [0, 1], clamp);
	const q2 = interpolate(frame, [QUESTION + 55, QUESTION + 80], [0, 1], clamp);
	return (
		<AbsoluteFill style={{ background: C.page, fontFamily }}>
			<div style={{ opacity: chartIn * dim }}>
				<div style={{ position: "absolute", left: 96, top: 70, color: C.ink2, fontSize: 28, fontWeight: 500 }}>
					Watching a battery material form · in situ X-ray scattering at {S.temperature_C} °C
				</div>
				<div style={{ position: "absolute", left: 96, top: 116, color: C.muted, fontSize: 22 }}>data {S.short_citation}</div>
				<div style={{ position: "absolute", left: X1 - 220, top: 170, color: C.ink, fontSize: 44, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
					{tNow.toFixed(1)} min
				</div>
				<svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
					<Axes x={x} y={y} xTicks={[0, 2, 4, 6, 8]} yTicks={ymax} x0={X0} x1={X1} y0={Y0} y1={Y1} fontSize={22}
						xLabel="minutes after the pellet enters the furnace" />
					<text x={X0 - 70} y={(Y0 + Y1) / 2} fill={C.muted} fontSize={22} transform={`rotate(-90 ${X0 - 70} ${(Y0 + Y1) / 2})`}
						textAnchor="middle" style={{ fontFamily }}>mol of each phase per mol Ti</text>
					{p > 0 && p < 1 ? <line x1={x(tNow)} x2={x(tNow)} y1={Y1 - 10} y2={Y0} stroke={C.axis} strokeWidth={1.5} /> : null}
					{PHASES.map((ph) => {
						const s = series[ph.id];
						// draw up to the current time: the share of points with t <= tNow, interpolating the last segment
						const i = s.t.findIndex((t) => t > tNow);
						const k = i === -1 ? s.t.length - 1 : Math.max(i - 1, 0);
						const frac = i === -1 ? 1 : (k + (tNow - s.t[k]) / (s.t[k + 1] - s.t[k])) / (s.t.length - 1);
						const last = i === -1 ? s.t.length - 1 : k;
						const labelIn = interpolate(frame, [DRAW1 - 10, DRAW1 + 10], [0, 1], clamp);
						return (
							<g key={ph.id}>
								<path d={partialPath(s.t, s.y, x, y, tNow >= s.t[0] ? Math.max(frac, 0) : 0)} fill="none" stroke={PHASE_COLOR[ph.id]}
									strokeWidth={4} strokeLinejoin="round" strokeLinecap="round" />
								{s.t.slice(0, last + 1).map((t, j) => (t <= tNow ? (
									<circle key={j} cx={x(t)} cy={y(s.y[j])} r={5} fill={PHASE_COLOR[ph.id]} stroke={C.page} strokeWidth={2} />
								) : null))}
								<text x={X1 + 18} y={y(s.y[s.y.length - 1]) + (ph.id === "Li4Ti5O12" ? -8 : ph.id === "anatase" ? 18 : 8)} fill={C.ink}
									fontSize={24} fontWeight={500} opacity={labelIn} style={{ fontFamily }}>{LABEL[ph.id]}</text>
							</g>
						);
					})}
				</svg>
			</div>
			<div style={{ position: "absolute", left: 0, right: 0, top: 360, textAlign: "center", color: C.ink }}>
				<div style={{ opacity: q1, fontSize: 84, fontWeight: 700, letterSpacing: -1, transform: `translateY(${(1 - q1) * 16}px)` }}>
					How does a material form?
				</div>
				<div style={{ opacity: q2, fontSize: 38, color: C.ink2, marginTop: 34, lineHeight: 1.45, transform: `translateY(${(1 - q2) * 12}px)` }}>
					Can an AI infer the reaction pathway from data like this,
					<br />
					and prove it on a temperature it never saw?
				</div>
			</div>
		</AbsoluteFill>
	);
};
