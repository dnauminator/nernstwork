// Shot 3: how NernstWork works, shown for one real run. (1) The AI proposes the parts of a search space; (2) code
// builds and fits every combination; (3) everything is frozen and tested on a sealed temperature; (4) the AI reports
// what the data cannot settle and plans the next experiment. Content comes from the run's own files.
import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import data from "./data/shots.json";
import { designText, rateLaw, species } from "./components/chem";
import { C, fontFamily } from "./theme";

const S = data.shot3;
export const SHOT3_FRAMES = 1020;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const CARD_W = 405, GAP = 40, LEFT = 96, TOP = 250, CARD_H = 650;
const STAGES = [
	{ start: 20, end: 270, title: "The AI proposes the parts", who: S.model_name },
	{ start: 270, end: 520, title: "Code checks and fits every combination", who: "deterministic code" },
	{ start: 520, end: 700, title: "Frozen, then tested", who: "sealed temperature" },
	{ start: 700, end: 1020, title: "The AI says what's unresolved", who: S.model_name },
];
const cardX = (i: number) => LEFT + i * (CARD_W + GAP);

// Plain-language versions of the agent's own conclusion for this run (investigations/runs/chapman750-propose_space-opus1/
// conclusions/): its two leading pathways are observationally equivalent; the rutile-to-spinel activation energy sits at
// the protocol bound; Ti-only bookkeeping beats a Li-balanced version, so the plotted phases do not balance lithium.
const UNRESOLVED = [
	"Its two leading pathways can't be told apart on these runs",
	"The rutile → spinel activation energy hits its bound",
	"The plotted phases don't balance lithium",
];

const Card: React.FC<{ i: number; children: React.ReactNode }> = ({ i, children }) => {
	const frame = useCurrentFrame();
	const st = STAGES[i];
	const appear = interpolate(frame, [st.start, st.start + 18], [0, 1], clamp);
	const active = frame >= st.start && frame < st.end;
	return (
		<div style={{
			position: "absolute", left: cardX(i), top: TOP, width: CARD_W, height: CARD_H, opacity: appear,
			transform: `translateY(${(1 - appear) * 24}px)`, background: C.surface, borderRadius: 18, padding: "28px 28px",
			boxSizing: "border-box", border: `1.5px solid ${active ? C.ink2 : C.axis}`, fontFamily, color: C.ink,
		}}>
			<div style={{ display: "flex", alignItems: "center", gap: 14 }}>
				<div style={{ width: 40, height: 40, borderRadius: 20, background: active ? C.ink : C.axis, color: active ? C.page : C.ink,
					display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, fontWeight: 700 }}>{i + 1}</div>
				<div style={{ fontSize: 17, color: C.muted, textTransform: "uppercase", letterSpacing: 1.2 }}>{st.who}</div>
			</div>
			<div style={{ fontSize: 29, fontWeight: 700, marginTop: 16, lineHeight: 1.2 }}>{st.title}</div>
			<div style={{ marginTop: 22 }}>{children}</div>
		</div>
	);
};

const Proposal: React.FC = () => {
	const frame = useCurrentFrame();
	const sp = S.spaces.find((s) => s.space_id === S.shown_space)!;
	return (
		<div>
			<div style={{ fontSize: 19, color: C.ink2, marginBottom: 14 }}>
				{S.spaces.length} search spaces. Steps, rate-law options and a cited reason for each:
			</div>
			{sp.steps.map((stp, k) => {
				const o = interpolate(frame, [50 + k * 26, 64 + k * 26], [0, 1], clamp);
				return (
					<div key={stp.id} style={{ opacity: o, marginBottom: 11, transform: `translateX(${(1 - o) * 12}px)` }}>
						<div style={{ fontSize: 20, fontWeight: 500 }}>
							{stp.reactants.map(species).join(" + ")} → {stp.products.map(species).join(" + ")}
						</div>
						<div style={{ fontSize: 16, color: C.muted, marginTop: 2 }}>
							{stp.rate_laws.map(rateLaw).join(" | ")} · {stp.support.join(", ")}
						</div>
					</div>
				);
			})}
		</div>
	);
};

const FitGrid: React.FC = () => {
	const frame = useCurrentFrame();
	const st = STAGES[1];
	const n = S.n_candidates, nFit = S.n_fitted;
	const cols = 16, cell = 18, gap = 3;
	const doneN = interpolate(frame, [st.start + 20, st.end - 60], [0, n], { ...clamp, easing: Easing.inOut(Easing.quad) });
	const highlight = interpolate(frame, [st.end - 50, st.end - 30], [0, 1], clamp);
	// Two fixed permutations (multipliers coprime to n): which candidate each cell stands for (by development AICc rank;
	// ranks >= nFit are the candidates whose fit failed), and the order cells finish, as parallel fits do. Brightness
	// follows fit quality, not finishing order.
	const coprime = (m: number): number => { let a = m, b = n; while (b) [a, b] = [b, a % b]; return a === 1 ? m : coprime(m + 2); };
	const m1 = coprime(37), m2 = coprime(101);
	const rankOf = (k: number) => (k * m1 + 11) % n;
	const finishOf = (k: number) => (k * m2 + 5) % n;
	const shown = Array.from({ length: n }, (_, k) => rankOf(k) < nFit && finishOf(k) < doneN).filter(Boolean).length;
	return (
		<div>
			<div style={{ fontSize: 46, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
				{shown}<span style={{ fontSize: 22, color: C.muted, fontWeight: 400 }}> of {n} pathways fitted</span>
			</div>
			<div style={{ fontSize: 18, color: C.ink2, margin: "6px 0 18px" }}>each checked for element balance, then fitted to the 700 and 725 °C runs with one protocol</div>
			<svg width={cols * (cell + gap)} height={Math.ceil(n / cols) * (cell + gap)}>
				{Array.from({ length: n }, (_, k) => {
					const aiccRank = rankOf(k);
					const fitted = aiccRank < nFit && finishOf(k) < doneN;
					// brightness by development AICc rank of the candidate this cell stands for (best = brightest)
					const shade = fitted ? 0.25 + 0.75 * (1 - aiccRank / nFit) : 0;
					const cid = aiccRank < nFit ? S.fitted_by_aicc[aiccRank] : null;
					const isRule = cid === S.rule_pick, isPlaus = cid !== null && S.plausible.includes(cid) && !isRule;
					const fill = highlight > 0 && isRule ? C.rule : highlight > 0 && isPlaus ? C.plausible : `rgba(240,239,236,${shade.toFixed(3)})`;
					return (
						<rect key={k} x={(k % cols) * (cell + gap)} y={Math.floor(k / cols) * (cell + gap)} width={cell} height={cell} rx={4}
							fill={fitted ? fill : "none"} stroke={fitted ? "none" : C.axis} strokeWidth={1.5} />
					);
				})}
			</svg>
			<div style={{ fontSize: 17, color: C.muted, marginTop: 12, opacity: highlight }}>
				<span style={{ color: C.ink2 }}>brighter = better fit</span> · the agent's frozen picks in colour
			</div>
		</div>
	);
};

const Sealed: React.FC = () => {
	const frame = useCurrentFrame();
	const st = STAGES[2];
	const o = interpolate(frame, [st.start + 20, st.start + 40], [0, 1], clamp);
	const o2 = interpolate(frame, [st.start + 60, st.start + 80], [0, 1], clamp);
	return (
		<div>
			<svg width={64} height={78} viewBox="0 0 40 48" style={{ opacity: o }}>
				<rect x={4} y={20} width={32} height={24} rx={5} fill="none" stroke={C.ink} strokeWidth={2.5} />
				<path d="M11 20 V13 a9 9 0 0 1 18 0 V20" fill="none" stroke={C.ink} strokeWidth={2.5} />
			</svg>
			<div style={{ opacity: o, fontSize: 24, lineHeight: 1.4, marginTop: 18 }}>
				Parameters and picks are frozen before the 750 °C data are loaded.
			</div>
			<div style={{ opacity: o2, fontSize: 22, color: C.ink2, lineHeight: 1.45, marginTop: 26 }}>
				The frozen models predict 750 °C without refitting, and are ranked against {S.n_reference} reference models built by code.
			</div>
		</div>
	);
};

const Report: React.FC = () => {
	const frame = useCurrentFrame();
	const st = STAGES[3];
	const next = S.next_experiments[0];
	return (
		<div>
			<div style={{ fontSize: 18, color: C.muted, marginBottom: 12 }}>What the data can't settle</div>
			{UNRESOLVED.map((u, k) => {
				const o = interpolate(frame, [st.start + 25 + k * 30, st.start + 40 + k * 30], [0, 1], clamp);
				return (
					<div key={k} style={{ opacity: o, display: "flex", gap: 12, fontSize: 21, lineHeight: 1.35, marginBottom: 14 }}>
						<span style={{ color: C.muted }}>?</span><span>{u}</span>
					</div>
				);
			})}
			<div style={{ opacity: interpolate(frame, [st.start + 130, st.start + 150], [0, 1], clamp), marginTop: 26 }}>
				<div style={{ fontSize: 18, color: C.muted, marginBottom: 10 }}>Most informative next experiment</div>
				<div style={{ fontSize: 23, fontWeight: 600, lineHeight: 1.35 }}>{designText(next)}</div>
			</div>
		</div>
	);
};

export const Shot3Loop: React.FC = () => {
	const frame = useCurrentFrame();
	const titleIn = interpolate(frame, [0, 18], [0, 1], clamp);
	const loopP = interpolate(frame, [900, 950], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
	const yLoop = TOP + CARD_H + 56, xa = cardX(3) + CARD_W / 2, xb = cardX(0) + CARD_W / 2;
	const loopLen = 2 * 40 + (xa - xb);
	return (
		<AbsoluteFill style={{ background: C.page, fontFamily }}>
			<div style={{ position: "absolute", left: 96, top: 64, opacity: titleIn, color: C.ink }}>
				<div style={{ fontSize: 28, color: C.ink2, fontWeight: 500, marginBottom: 10 }}>
					One run, start to finish: {S.model_name}, {S.run}
				</div>
				<div style={{ fontSize: 58, fontWeight: 700, letterSpacing: -0.5 }}>How NernstWork works</div>
			</div>
			{[0, 1, 2].map((i) => {
				const o = interpolate(frame, [STAGES[i + 1].start - 12, STAGES[i + 1].start + 4], [0, 1], clamp);
				return (
					<svg key={i} width={GAP} height={30} style={{ position: "absolute", left: cardX(i) + CARD_W, top: TOP + CARD_H / 2 - 15, opacity: o }}>
						<path d="M4 15 H30 M22 7 L31 15 L22 23" fill="none" stroke={C.ink2} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
					</svg>
				);
			})}
			<Card i={0}><Proposal /></Card>
			<Card i={1}><FitGrid /></Card>
			<Card i={2}><Sealed /></Card>
			<Card i={3}><Report /></Card>
			<svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
				<path d={`M${xa} ${TOP + CARD_H + 8} V${yLoop} H${xb} V${TOP + CARD_H + 14}`} fill="none" stroke={C.ink2} strokeWidth={2.5} opacity={loopP > 0 ? 1 : 0}
					strokeDasharray={loopLen} strokeDashoffset={loopLen * (1 - loopP)} strokeLinejoin="round" />
				{loopP > 0.98 ? <path d={`M${xb - 8} ${TOP + CARD_H + 24} L${xb} ${TOP + CARD_H + 12} L${xb + 8} ${TOP + CARD_H + 24}`} fill="none"
					stroke={C.ink2} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" /> : null}
				<text x={(xa + xb) / 2} y={yLoop + 36} textAnchor="middle" fill={C.ink2} fontSize={22} opacity={loopP} style={{ fontFamily }}>
					the new measurement feeds the next round
				</text>
			</svg>
		</AbsoluteFill>
	);
};
