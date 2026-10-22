// Shot 7: what to measure next. The planner's ranked experiments for Claude Opus 5.5 run 1, and under the top design the
// predicted rutile of the leading model and of the agent's own rival explanation, which the design separates. (The
// agent's other leading model tracks the leading one within the noise, so it is stated, not drawn.) All values from the run's planner analysis and frozen fits (scripts/export_video_data.py).
import React from "react";
import { AbsoluteFill, Easing, interpolate} from "remotion";
import data from "./data/shots.json";
import { useFrame } from "./time";
import { Axes, LegendItem, Title, linear, niceTicks, partialPath } from "./components/chart";
import { C, fontFamily } from "./theme";

const S = data.shot7;
export const SHOT7_FRAMES = 720;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

type Spec = { c0: Record<string, number>; temperature_C: number; t_end_min: number };
const std = S.standard_c0 as Record<string, number>;
const ratioText = (r: number) => (Math.abs(r - 0.5) < 1e-9 ? "half the Li₂CO₃" : Math.abs(r - 1) < 1e-9 ? "standard mix" : `${r}× Li₂CO₃`);
const designLabel = (sp: Spec) => {
	const r = (sp.c0.Li2CO3 ?? 0) / std.Li2CO3;
	const precursor = sp.c0.rutile ? "anatase + rutile precursor" : ratioText(r);
	return `${precursor}, ${sp.temperature_C} °C, to ${sp.t_end_min} min`;
};

export const Shot7Plan: React.FC = () => {
	const frame = useFrame();
	const titleIn = interpolate(frame, [0, 18], [0, 1], clamp);
	const menuHead = interpolate(frame, [15, 35], [0, 1], clamp);
	const Umax = Math.max(...S.ranking.map((r) => r.U));
	const topIn = interpolate(frame, [95, 120], [0, 1], clamp);
	const chartIn = interpolate(frame, [110, 140], [0, 1], clamp);
	const leadP = interpolate(frame, [150, 270], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
	const rivalP = interpolate(frame, [200, 320], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
	const gapIn = interpolate(frame, [330, 360], [0, 1], clamp);
	const noteIn = interpolate(frame, [400, 430], [0, 1], clamp);
	const gap = S.separated!.largest_gap;
	const lead = S.leading_pair!.largest_gap;
	const curves = S.curves as Record<string, Record<string, number[]>>;
	const ch = gap.channel as string;
	// chart geometry (right half)
	const X0 = 960, X1 = 1790, Y0 = 830, Y1 = 330;
	const all = Object.values(curves).flatMap((c) => c[ch]);
	const yTicks = niceTicks(Math.max(...all), 4);
	const x = linear(0, S.t[S.t.length - 1], X0, X1);
	const y = linear(0, yTicks[yTicks.length - 1], Y0, Y1);
	const i2 = S.t.findIndex((t) => t >= gap.t_min);
	const yr = curves[S.rule][ch][i2], yv = curves[S.rival!][ch][i2];
	return (
		<AbsoluteFill style={{ background: C.page, fontFamily }}>
			<Title kicker={`The agent's planner · ${S.model_name}, ${S.run}`} title="What to measure next" opacity={titleIn} />
			{/* left: ranked candidate experiments */}
			<div style={{ position: "absolute", left: 96, top: 250, width: 740, color: C.ink }}>
				<div style={{ opacity: menuHead, fontSize: 24, color: C.ink2, marginBottom: 26, lineHeight: 1.35 }}>
					Candidate experiments, ranked by how far the models' predictions would split
				</div>
				{S.ranking.map((r, k) => {
					const grow = interpolate(frame, [30 + k * 12, 70 + k * 12], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
					const isTop = r.design === S.top;
					return (
						<div key={r.design} style={{ marginBottom: 22, opacity: Math.min(grow * 2, 1) }}>
							<div style={{ fontSize: 22, color: isTop ? C.ink : C.ink2, fontWeight: isTop ? 600 : 400, marginBottom: 8 }}>
								{designLabel(r.spec as Spec)}
							</div>
							<div style={{ display: "flex", alignItems: "center", gap: 14 }}>
								<div style={{ height: 14, borderRadius: 4, width: 520 * (r.U / Umax) * grow,
									background: isTop ? C.ink : C.axis, opacity: isTop ? 0.4 + 0.6 * topIn : 1 }} />
								<span style={{ fontSize: 18, color: C.muted, fontVariantNumeric: "tabular-nums" }}>
									{`${isTop ? "separates " : ""}${r.separable_pairs.replace("/", " of ")} model pairs`}
								</span>
							</div>
						</div>
					);
				})}
			</div>
			{/* right: predictions under the top design */}
			<div style={{ position: "absolute", left: X0, top: 196, opacity: chartIn, color: C.ink }}>
				<div style={{ fontSize: 26, fontWeight: 600 }}>Predicted {ch} under the top pick</div>
				<div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 14 }}>
					<LegendItem color={C.rule} label="Leading model: rutile by nucleation and growth" opacity={leadP > 0 ? 1 : 0} />
					<LegendItem color={C.rival} label="The agent's own rival: the spinel helps rutile form" opacity={rivalP > 0 ? 1 : 0} />
				</div>
			</div>
			<svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
				<g opacity={chartIn}>
					<Axes x={x} y={y} xTicks={[0, 5, 10, 15, 20, 25, 30]} yTicks={yTicks} x0={X0} x1={X1} y0={Y0} y1={Y1}
						xLabel="minutes" fontSize={20} />
				</g>
				<path d={partialPath(S.t, curves[S.rule][ch], x, y, leadP)} fill="none" stroke={C.rule} strokeWidth={3.5} strokeLinecap="round" />
				<path d={partialPath(S.t, curves[S.rival!][ch], x, y, rivalP)} fill="none" stroke={C.rival} strokeWidth={4} strokeLinecap="round" />
				<g opacity={gapIn} style={{ fontFamily }}>
					<line x1={x(gap.t_min)} x2={x(gap.t_min)} y1={y(yr) - 4} y2={y(yv) + 4} stroke={C.ink} strokeWidth={2} />
					<line x1={x(gap.t_min) - 8} x2={x(gap.t_min) + 8} y1={y(yr)} y2={y(yr)} stroke={C.ink} strokeWidth={2} />
					<line x1={x(gap.t_min) - 8} x2={x(gap.t_min) + 8} y1={y(yv)} y2={y(yv)} stroke={C.ink} strokeWidth={2} />
					<text x={x(gap.t_min) + 22} y={(y(yr) + y(yv)) / 2 + 30} fill={C.ink} fontSize={24} fontWeight={600}>
						{gap.difference.toFixed(2)} per Ti at {gap.t_min} min
					</text>
					<text x={x(gap.t_min) + 22} y={(y(yr) + y(yv)) / 2 + 60} fill={C.ink2} fontSize={21}>
						about {gap.in_noise_sigma.toFixed(0)}σ of the fitted noise
					</text>
				</g>
			</svg>
			<div style={{ position: "absolute", left: X0, top: 900, width: 860, opacity: noteIn, fontSize: 22, color: C.ink2, lineHeight: 1.4 }}>
				The agent's other leading model stays within {lead.in_noise_sigma.toFixed(1)}σ of the blue line under this design.
				The agent reports the two as indistinguishable.
			</div>
		</AbsoluteFill>
	);
};
