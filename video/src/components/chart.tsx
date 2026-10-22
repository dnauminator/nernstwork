import React from "react";
import { C, fontFamily } from "../theme";

export type Scale = (v: number) => number;

export const linear = (d0: number, d1: number, r0: number, r1: number): Scale => (v) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);

export function niceTicks(max: number, count = 4): number[] {
	const raw = max / count;
	const mag = 10 ** Math.floor(Math.log10(raw));
	const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
	const out: number[] = [];
	const top = Math.ceil(max / step - 1e-9) * step; // the last tick covers the maximum
	for (let v = 0; v <= top + 1e-9; v += step) out.push(Number(v.toFixed(6)));
	return out;
}

/** SVG path through the first `progress` share of the points (0..1), interpolating the last segment. */
export function partialPath(xs: number[], ys: number[], x: Scale, y: Scale, progress: number): string {
	const n = xs.length;
	if (progress <= 0 || n < 2) return "";
	const end = Math.min(progress, 1) * (n - 1);
	const whole = Math.floor(end);
	let d = `M${x(xs[0]).toFixed(2)},${y(ys[0]).toFixed(2)}`;
	for (let i = 1; i <= whole; i++) d += `L${x(xs[i]).toFixed(2)},${y(ys[i]).toFixed(2)}`;
	const f = end - whole;
	if (f > 0 && whole + 1 < n) {
		const xi = xs[whole] + (xs[whole + 1] - xs[whole]) * f;
		const yi = ys[whole] + (ys[whole + 1] - ys[whole]) * f;
		d += `L${x(xi).toFixed(2)},${y(yi).toFixed(2)}`;
	}
	return d;
}

/** Recessive axes: hairline grid, baseline, muted tick labels. */
export const Axes: React.FC<{
	x: Scale; y: Scale; xTicks: number[]; yTicks: number[]; x0: number; x1: number; y0: number; y1: number;
	opacity?: number; xLabel?: string; fontSize?: number;
}> = ({ x, y, xTicks, yTicks, x0, x1, y0, y1, opacity = 1, xLabel, fontSize = 20 }) => (
	<g opacity={opacity} style={{ fontFamily, fontVariantNumeric: "tabular-nums" }}>
		{yTicks.map((t) => (
			<g key={`y${t}`}>
				<line x1={x0} x2={x1} y1={y(t)} y2={y(t)} stroke={t === 0 ? C.axis : C.grid} strokeWidth={t === 0 ? 1.5 : 1} />
				<text x={x0 - 12} y={y(t) + fontSize * 0.35} textAnchor="end" fill={C.muted} fontSize={fontSize}>
					{t}
				</text>
			</g>
		))}
		{xTicks.map((t) => (
			<text key={`x${t}`} x={x(t)} y={y0 + fontSize + 10} textAnchor="middle" fill={C.muted} fontSize={fontSize}>
				{t}
			</text>
		))}
		{xLabel ? (
			<text x={(x0 + x1) / 2} y={y0 + fontSize * 2 + 22} textAnchor="middle" fill={C.muted} fontSize={fontSize}>
				{xLabel}
			</text>
		) : null}
		<line x1={x0} x2={x0} y1={y1} y2={y0} stroke={C.axis} strokeWidth={1} opacity={0} />
	</g>
);

export const Title: React.FC<{ kicker?: string; title: string; opacity: number; dy?: number }> = ({ kicker, title, opacity, dy = 0 }) => (
	<div style={{ position: "absolute", left: 96, top: 64 + dy, opacity, fontFamily, color: C.ink }}>
		{kicker ? <div style={{ fontSize: 28, color: C.ink2, fontWeight: 500, marginBottom: 10 }}>{kicker}</div> : null}
		<div style={{ fontSize: 58, fontWeight: 700, letterSpacing: -0.5 }}>{title}</div>
	</div>
);

/** Legend swatch: a 2px line (optionally dashed) or a dot, followed by the label in text ink. */
export const LegendItem: React.FC<{ color: string; label: string; kind?: "line" | "dash" | "dot"; opacity?: number }> = ({
	color, label, kind = "line", opacity = 1,
}) => (
	<div style={{ display: "flex", alignItems: "center", gap: 12, opacity, fontFamily, fontSize: 24, color: C.ink2 }}>
		<svg width={36} height={18}>
			{kind === "dot" ? (
				<circle cx={18} cy={9} r={6} fill={color} stroke={C.page} strokeWidth={2} />
			) : (
				<line x1={2} x2={34} y1={9} y2={9} stroke={color} strokeWidth={4} strokeLinecap="round" strokeDasharray={kind === "dash" ? "7 6" : undefined} />
			)}
		</svg>
		<span>{label}</span>
	</div>
);
