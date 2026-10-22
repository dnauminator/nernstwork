// Shot 4: the models were fitted at 700 and 725 C and frozen; they predict 750 C, then the sealed measurements land.
import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import data from "./data/shots.json";
import { Axes, LegendItem, Title, linear, niceTicks, partialPath } from "./components/chart";
import { C, PHASES, fontFamily } from "./theme";

const S = data.shot4;
type Role = "baseline" | "rule" | "plausible";
const COLOR: Record<Role, string> = { baseline: C.baseline, rule: C.rule, plausible: C.plausible };
const MODEL = (role: Role) => S.models.find((m) => m.role === role)!.model_name;
// [legend and scoreboard title, scoreboard detail]; the model name comes from the run's recorded investigator model
const NAME: Record<Role, [string, string]> = {
	plausible: [`${MODEL("plausible")} · agent's other pick`, "kept as plausible before the test"],
	rule: [`${MODEL("rule")} · rule's pick`, "best fit (AICc) at 700 + 725 °C"],
	baseline: ["Baseline pick", "code-only space, same rule"],
};
// draw order: baseline first so the AI curves sit on top
const ORDER: Role[] = ["baseline", "rule", "plausible"];
const DRAW_START: Record<Role, number> = { baseline: 50, rule: 72, plausible: 94 };
const REVEAL = 215;
const BOARD = 330;

export const SHOT4_FRAMES = 600;

const Panel: React.FC<{ phase: (typeof PHASES)[number]; x0: number; y0: number; w: number; h: number; showX: boolean }> = ({
	phase, x0, y0, w, h, showX,
}) => {
	const frame = useCurrentFrame();
	const { fps } = useVideoConfig();
	const ml = 78, mb = showX ? 74 : 40, mt = 62;
	const obs = (S.observations as Record<string, { t: number[]; y: number[] }>)[phase.id];
	const ymaxData = Math.max(...obs.y, ...S.models.flatMap((m) => (m.curves as Record<string, number[]>)[phase.id]));
	const yTicks = niceTicks(ymaxData, 4);
	const ymax = yTicks[yTicks.length - 1];
	const x = linear(0, 9.5, x0 + ml, x0 + w);
	const y = linear(0, ymax, y0 + h - mb, y0 + mt);
	const axesIn = interpolate(frame, [12, 36], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
	return (
		<g>
			<text x={x0 + ml} y={y0 + 22} fill={C.ink} fontSize={28} fontWeight={600} opacity={axesIn} style={{ fontFamily }}>
				{phase.label}
			</text>
			<Axes x={x} y={y} xTicks={[0, 2, 4, 6, 8]} yTicks={yTicks} x0={x0 + ml} x1={x0 + w} y0={y0 + h - mb} y1={y0 + mt}
				opacity={axesIn} xLabel={showX ? "minutes after the pellet enters the furnace" : undefined} />
			{ORDER.map((role) => {
				const m = S.models.find((mm) => mm.role === role)!;
				const p = interpolate(frame, [DRAW_START[role], DRAW_START[role] + 90], [0, 1], {
					extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic),
				});
				return (
					<path key={role} d={partialPath(S.t, (m.curves as Record<string, number[]>)[phase.id], x, y, p)} fill="none"
						stroke={COLOR[role]} strokeWidth={role === "baseline" ? 3 : 4} strokeDasharray={role === "baseline" ? "10 8" : undefined}
						strokeLinecap="round" strokeLinejoin="round" />
				);
			})}
			{obs.t.map((t, i) => {
				const s = spring({ frame: frame - REVEAL - i * 3, fps, config: { damping: 12, stiffness: 160 } });
				const drop = interpolate(s, [0, 1], [-40, 0]);
				return s > 0.01 ? (
					<circle key={i} cx={x(t)} cy={y(obs.y[i]) + drop} r={7 * Math.min(s, 1.15)} fill={C.ink} stroke={C.page} strokeWidth={2.5}
						opacity={Math.min(s * 1.5, 1)} />
				) : null;
			})}
		</g>
	);
};

const ScoreRow: React.FC<{ role: Role; start: number }> = ({ role, start }) => {
	const frame = useCurrentFrame();
	const { fps } = useVideoConfig();
	const m = S.models.find((mm) => mm.role === role)!;
	const s = spring({ frame: frame - start, fps, config: { damping: 200 } });
	const count = Math.round(interpolate(frame, [start, start + 40], [m.n_space, m.rank], {
		extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic),
	}));
	return (
		<div style={{ opacity: s, transform: `translateX(${(1 - s) * 40}px)`, display: "flex", gap: 20, alignItems: "stretch", marginBottom: 34 }}>
			<div style={{ width: 8, borderRadius: 4, background: COLOR[role] }} />
			<div style={{ flex: 1 }}>
				<div style={{ fontSize: 26, fontWeight: 600, color: C.ink, lineHeight: 1.25 }}>{NAME[role][0]}</div>
				<div style={{ fontSize: 21, color: C.muted, marginTop: 4 }}>{NAME[role][1]}</div>
				<div style={{ display: "flex", alignItems: "baseline", gap: 14, marginTop: 10 }}>
					<span style={{ fontSize: 64, fontWeight: 700, color: C.ink, fontVariantNumeric: "tabular-nums", minWidth: 132 }}>#{count}</span>
					<span style={{ fontSize: 22, color: C.ink2 }}>
						RMSE {m.rmse_all.toFixed(3)}
					</span>
				</div>
			</div>
		</div>
	);
};

export const Shot4Reveal: React.FC = () => {
	const frame = useCurrentFrame();
	const titleIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
	const sealed = interpolate(frame, [30, 45, REVEAL - 20, REVEAL], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
	const revealedNote = interpolate(frame, [REVEAL, REVEAL + 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
	const boardHead = interpolate(frame, [BOARD - 20, BOARD], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
	const legendIn = (start: number) => interpolate(frame, [start, start + 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
	const panelsX = 96, panelsY = 268, pw = 610, ph = 360, gx = 56, gy = 26;
	const ranked = [...ORDER].sort((a, b) => S.models.find((m) => m.role === a)!.rank - S.models.find((m) => m.role === b)!.rank);
	const nSpace = S.models[0].n_space;
	return (
		<AbsoluteFill style={{ background: C.page, fontFamily }}>
			<Title kicker="Fitted at 700 and 725 °C, frozen, then asked about 750 °C" title={`Predicting ${S.temperature_C} °C without refitting`} opacity={titleIn} />
			<div style={{ position: "absolute", left: panelsX, top: 200, display: "flex", gap: 40 }}>
				{ORDER.slice().reverse().map((r) => (
					<LegendItem key={r} color={COLOR[r]} label={NAME[r][0]} kind={r === "baseline" ? "dash" : "line"} opacity={legendIn(DRAW_START[r])} />
				))}
				<LegendItem color={C.ink} label={`measured at ${S.temperature_C} °C`} kind="dot" opacity={revealedNote} />
			</div>
			<svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
				{PHASES.map((p, i) => (
					<Panel key={p.id} phase={p} x0={panelsX + (i % 2) * (pw + gx)} y0={panelsY + Math.floor(i / 2) * (ph + gy)} w={pw} h={ph} showX={i >= 2} />
				))}
			</svg>
			<div style={{ position: "absolute", left: panelsX + 78, top: 1030, fontSize: 20, color: C.muted }}>
				mol of each phase per mol Ti · data {S.short_citation}
			</div>
			<div style={{
				position: "absolute", left: 1440, top: 268, width: 400, opacity: sealed, padding: "34px 34px", borderRadius: 16,
				border: `1.5px solid ${C.axis}`, background: C.surface, color: C.ink2,
			}}>
				<svg width={40} height={48} viewBox="0 0 40 48">
					<rect x={4} y={20} width={32} height={24} rx={5} fill="none" stroke={C.ink2} strokeWidth={3} />
					<path d="M11 20 V13 a9 9 0 0 1 18 0 V20" fill="none" stroke={C.ink2} strokeWidth={3} />
				</svg>
				<div style={{ fontSize: 30, fontWeight: 600, color: C.ink, marginTop: 16 }}>{S.temperature_C} °C measurements sealed</div>
				<div style={{ fontSize: 22, color: C.muted, marginTop: 10, lineHeight: 1.4 }}>
					No model or agent saw them while fitting or choosing
				</div>
			</div>
			<div style={{ position: "absolute", left: 1440, top: 268, width: 400, color: C.ink }}>
				<div style={{ opacity: boardHead, fontSize: 24, color: C.ink2, marginBottom: 30, lineHeight: 1.35 }}>
					Rank at {S.temperature_C} °C among {nSpace} reference models
				</div>
				{ranked.map((r, i) => (
					<ScoreRow key={r} role={r} start={BOARD + i * 40} />
				))}
			</div>
		</AbsoluteFill>
	);
};
