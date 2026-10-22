// Shot 5b: across the baseline and the four AI runs, where three models land among the reference models at 750 C:
// the best model in the run's own space (known only after the test), the agent's best plausible model, and the rule's
// pick. The caption is computed from the same data.
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import data from "./data/shots.json";
import { LegendItem, Title, linear } from "./components/chart";
import { C, fontFamily } from "./theme";

const R = data.shot5b.runs;
export const SHOT5B_FRAMES = 480;

const X0 = 520, X1 = 1780, Y0 = 330, ROW = 118;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const MARKS = [
	{ key: "own_space_best_rank", color: C.ownBest, label: "Best in the run's search space", dy: -22 },
	{ key: "best_plausible_rank", color: C.plausible, label: "Agent's best plausible model", dy: 0 },
	{ key: "rule_pick_rank", color: C.rule, label: "Rule's pick (best fit)", dy: 22 },
] as const;

export const Shot5bRuns: React.FC = () => {
	const frame = useCurrentFrame();
	const { fps } = useVideoConfig();
	const nSpace = R[0].n_space;
	const maxRank = Math.max(...R.flatMap((r) => [r.rule_pick_rank, r.best_plausible_rank ?? 0, r.own_space_best_rank]));
	const xmax = Math.ceil((maxRank + 2) / 10) * 10;
	const x = linear(1, xmax, X0, X1);
	const ticks = [1, ...Array.from({ length: xmax / 10 }, (_, i) => (i + 1) * 10)];
	const titleIn = interpolate(frame, [0, 20], [0, 1], clamp);
	const axisIn = interpolate(frame, [15, 40], [0, 1], clamp);
	const ai = R.filter((r) => r.best_plausible_rank !== null);
	const worstOwn = Math.max(...ai.map((r) => r.own_space_best_rank));
	const rules = ai.map((r) => r.rule_pick_rank);
	const captionIn = interpolate(frame, [330, 355], [0, 1], clamp);
	const yBottom = Y0 + (R.length - 1) * ROW + 60;
	return (
		<AbsoluteFill style={{ background: C.page, fontFamily }}>
			<Title kicker={`Rank at 750 °C among ${nSpace} reference models, for the baseline and four AI runs`}
				title={`Every AI run's search space held a top-${worstOwn} predictor`} opacity={titleIn} />
			<div style={{ position: "absolute", left: X0, top: 200, display: "flex", gap: 40, opacity: axisIn }}>
				{MARKS.map((m) => <LegendItem key={m.key} color={m.color} label={m.label} kind="dot" />)}
			</div>
			<svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
				<g opacity={axisIn} style={{ fontFamily, fontVariantNumeric: "tabular-nums" }}>
					{ticks.map((t) => (
						<g key={t}>
							<line x1={x(t)} x2={x(t)} y1={Y0 - 50} y2={yBottom} stroke={t === 1 ? C.axis : C.grid} strokeWidth={t === 1 ? 1.5 : 1} />
							<text x={x(t)} y={yBottom + 34} textAnchor="middle" fill={C.muted} fontSize={22}>#{t}</text>
						</g>
					))}
					<text x={(X0 + X1) / 2} y={yBottom + 72} textAnchor="middle" fill={C.muted} fontSize={22}>
						rank at 750 °C among {nSpace} reference models (left is better)
					</text>
				</g>
				{R.map((r, i) => {
					const start = 45 + i * 45;
					const rowIn = interpolate(frame, [start, start + 15], [0, 1], clamp);
					const y = Y0 + i * ROW;
					const vals = MARKS.map((m) => (r[m.key] as number | null)).filter((v): v is number => v !== null);
					const s = spring({ frame: frame - start - 10, fps, config: { damping: 18, stiffness: 120 } });
					return (
						<g key={r.run_id} opacity={rowIn}>
							<text x={X0 - 40} y={y - 2} textAnchor="end" fill={C.ink} fontSize={30} fontWeight={600} style={{ fontFamily }}>{r.name}</text>
							<text x={X0 - 40} y={y + 30} textAnchor="end" fill={C.muted} fontSize={22} style={{ fontFamily }}>{r.detail}</text>
							<line x1={x(Math.min(...vals))} x2={x(Math.min(...vals)) + (x(Math.max(...vals)) - x(Math.min(...vals))) * s} y1={y} y2={y}
								stroke={C.axis} strokeWidth={6} strokeLinecap="round" />
							{MARKS.map((m) => {
								const v = (r[m.key] as number | null);
								if (v === null) return null;
								const cx = x(xmax) + (x(v) - x(xmax)) * s;
								return (
									<g key={m.key}>
										<circle cx={cx} cy={y + m.dy} r={11} fill={m.color} stroke={C.page} strokeWidth={2.5} />
										<text x={cx + 20} y={y + m.dy + 7} fill={C.ink2} fontSize={20} opacity={s} style={{ fontFamily, fontVariantNumeric: "tabular-nums" }}>
											#{v}
										</text>
									</g>
								);
							})}
						</g>
					);
				})}
			</svg>
			<div style={{ position: "absolute", left: X0, top: 1000, opacity: captionIn, fontSize: 26, color: C.ink }}>
				Picking by best fit chose #{Math.min(...rules)} to #{Math.max(...rules)}.
			</div>
		</AbsoluteFill>
	);
};
