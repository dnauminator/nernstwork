// Shot 5: the 153 reference models ranked by fit (700 + 725 C) and by prediction (750 C); the dots travel from one
// ranking to the other. The baseline's pick and the frozen picks of the first Claude Opus 5.5 run are highlighted.
import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import data from "./data/shots.json";
import { Title, linear } from "./components/chart";
import { C, fontFamily } from "./theme";

const S = data.shot5;
export const SHOT5_FRAMES = 540;

const XL = 560, XR = 1260, YTOP = 350, YBOT = 975;
const N = S.n_reference;
const yr = linear(1, N, YTOP, YBOT);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const MOVE0 = 130, MOVE_SPREAD = 0.5, MOVE_LEN = 50;
const AI_IN = 270, AI_MOVE = 300;
const AI_SLOT = YTOP - 52; // above rank 1: they fit better than every reference model

const pickColor = (role: string) => (role === "rule" ? C.rule : C.plausible);
const MODEL = S.opus_picks[0].model_name;
const pickName = (role: string) => `${MODEL} · ${role === "rule" ? "rule's pick" : "agent's other pick"}`;

export const Shot5Ranks: React.FC = () => {
	const frame = useCurrentFrame();
	const titleIn = interpolate(frame, [0, 20], [0, 1], clamp);
	const colsIn = interpolate(frame, [20, 45], [0, 1], clamp);
	const base = S.reference.find((r) => r.id === S.baseline_pick)!;
	const baseLabelIn = interpolate(frame, [100, 120], [0, 1], clamp);
	const baseMoved = interpolate(frame, [MOVE0 + MOVE_LEN, MOVE0 + MOVE_LEN + 20], [0, 1], clamp);
	const aiIn = interpolate(frame, [AI_IN, AI_IN + 20], [0, 1], clamp);
	const aiMove = interpolate(frame, [AI_MOVE, AI_MOVE + 60], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
	const aiLanded = interpolate(frame, [AI_MOVE + 55, AI_MOVE + 75], [0, 1], clamp);
	const captionIn = interpolate(frame, [400, 425], [0, 1], clamp);
	const ticks = [1, 25, 50, 75, 100, 125, N];
	// right-side label slots, spaced so close ranks do not collide; each has a leader line to its dot
	const picks = [...S.opus_picks].sort((a, b) => a.heldout_rank - b.heldout_rank);
	const rightLabels = [
		...picks.map((p, i) => ({ y: yr(p.heldout_rank), ly: YTOP - 40 + i * 64, color: pickColor(p.role), rank: p.heldout_rank,
			name: pickName(p.role), opacity: aiLanded })),
		{ y: yr(base.heldout_rank), ly: YTOP - 40 + picks.length * 64 + 8, color: C.baseline, rank: base.heldout_rank,
			name: "Baseline pick", opacity: baseMoved * (1 - 0.0 * aiLanded) },
	];
	return (
		<AbsoluteFill style={{ background: C.page, fontFamily }}>
			<Title kicker={`${N} reference models, ranked twice`} title="The best fit is not the best predictor" opacity={titleIn} />
			<svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
				<g opacity={colsIn} style={{ fontFamily }}>
					<text x={XL} y={YTOP - 96} textAnchor="middle" fill={C.ink} fontSize={30} fontWeight={600}>Fit at 700 + 725 °C</text>
					<text x={XL} y={YTOP - 64} textAnchor="middle" fill={C.muted} fontSize={22}>rank by AICc</text>
					<text x={XR} y={YTOP - 96} textAnchor="middle" fill={C.ink} fontSize={30} fontWeight={600}>Prediction at 750 °C</text>
					<text x={XR} y={YTOP - 64} textAnchor="middle" fill={C.muted} fontSize={22}>rank by held-out error</text>
					<line x1={XL} x2={XL} y1={YTOP - 8} y2={YBOT + 8} stroke={C.axis} strokeWidth={1.5} />
					<line x1={XR} x2={XR} y1={YTOP - 8} y2={YBOT + 8} stroke={C.axis} strokeWidth={1.5} />
					{ticks.map((t) => (
						<g key={t}>
							<text x={XL - 26} y={yr(t) + 7} textAnchor="end" fill={C.muted} fontSize={20} style={{ fontVariantNumeric: "tabular-nums" }}>#{t}</text>
							<text x={XR - 26} y={yr(t) + 7} textAnchor="end" fill={C.muted} fontSize={20} style={{ fontVariantNumeric: "tabular-nums" }}>#{t}</text>
						</g>
					))}
				</g>
				{S.reference.map((r) => {
					const appear = interpolate(frame, [40 + r.dev_rank * 0.35, 48 + r.dev_rank * 0.35], [0, 1], clamp);
					const start = MOVE0 + r.dev_rank * MOVE_SPREAD;
					const m = interpolate(frame, [start, start + MOVE_LEN], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
					const x = XL + (XR - XL) * m, y = yr(r.dev_rank) + (yr(r.heldout_rank) - yr(r.dev_rank)) * m;
					const isBase = r.id === S.baseline_pick;
					return (
						<g key={r.id} opacity={appear}>
							{m > 0 ? <line x1={XL} y1={yr(r.dev_rank)} x2={x} y2={y} stroke={isBase ? C.baseline : C.reference}
								strokeWidth={isBase ? 2.5 : 1} opacity={isBase ? 0.9 : 0.22} /> : null}
							{isBase ? null : <circle cx={x} cy={y} r={3.5} fill={C.reference} opacity={0.85} />}
						</g>
					);
				})}
				{(() => {
					const start = MOVE0 + base.dev_rank * MOVE_SPREAD;
					const m = interpolate(frame, [start, start + MOVE_LEN], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
					const x = XL + (XR - XL) * m, y = yr(base.dev_rank) + (yr(base.heldout_rank) - yr(base.dev_rank)) * m;
					return <circle cx={x} cy={y} r={10} fill={C.baseline} stroke={C.page} strokeWidth={2.5} opacity={baseLabelIn} />;
				})()}
				{picks.map((p, i) => {
					const x0 = XL + (i - (picks.length - 1) / 2) * 30;
					const x = x0 + (XR - x0) * aiMove, y = AI_SLOT + (yr(p.heldout_rank) - AI_SLOT) * aiMove;
					return (
						<g key={p.candidate_id} opacity={aiIn}>
							{aiMove > 0 ? <line x1={x0} y1={AI_SLOT} x2={x} y2={y} stroke={pickColor(p.role)} strokeWidth={2.5} opacity={0.9} /> : null}
							<circle cx={x} cy={y} r={11} fill={pickColor(p.role)} stroke={C.page} strokeWidth={2.5} />
						</g>
					);
				})}
				{rightLabels.map((l, i) => (
					<g key={i} opacity={l.opacity}>
						<line x1={XR + 14} y1={l.y} x2={XR + 70} y2={l.ly} stroke={C.muted} strokeWidth={1} />
						<rect x={XR + 78} y={l.ly - 13} width={6} height={26} rx={3} fill={l.color} />
						<text x={XR + 96} y={l.ly + 9} fill={C.ink} fontSize={28} fontWeight={700} style={{ fontVariantNumeric: "tabular-nums" }}>#{l.rank}</text>
						<text x={XR + 166} y={l.ly + 8} fill={C.ink2} fontSize={22}>{l.name}</text>
					</g>
				))}
				<g opacity={baseLabelIn * (1 - aiIn)} style={{ fontFamily }}>
					<text x={XL - 120} y={yr(1) - 26} textAnchor="end" fill={C.ink2} fontSize={24}>Baseline pick: its best fit</text>
				</g>
				<g opacity={aiIn} style={{ fontFamily }}>
					<text x={XL - 90} y={AI_SLOT - 6} textAnchor="end" fill={C.ink2} fontSize={24}>{MODEL} picks</text>
					<text x={XL - 90} y={AI_SLOT + 24} textAnchor="end" fill={C.muted} fontSize={22}>better fit than all {N}</text>
				</g>
			</svg>
			<div style={{ position: "absolute", left: 96, top: 1024, opacity: captionIn, fontSize: 24, color: C.ink2 }}>
				Gray lines: each reference model's move between the two rankings
			</div>
		</AbsoluteFill>
	);
};
