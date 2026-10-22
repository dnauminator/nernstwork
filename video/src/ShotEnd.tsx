// End card under Daniel's closing statement (conclusion.mp3): what the work shows, the implication, credits. The text
// paraphrases his recording so the card stands without the audio.
import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import data from "./data/shots.json";
import { useFrame } from "./time";
import { C, fontFamily } from "./theme";

export const SHOT_END_FRAMES = 760;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const models = [...new Set(data.shot5b.runs.filter((r) => r.best_plausible_rank !== null).map((r) => r.name))];

export const ShotEnd: React.FC = () => {
	const frame = useFrame();
	const t = interpolate(frame, [0, 20], [0, 1], clamp);
	const l1 = interpolate(frame, [30, 55], [0, 1], clamp);
	const l2 = interpolate(frame, [340, 365], [0, 1], clamp);
	const cr = interpolate(frame, [560, 590], [0, 1], clamp);
	return (
		<AbsoluteFill style={{ background: C.page, fontFamily, color: C.ink }}>
			<div style={{ position: "absolute", left: 140, right: 140, top: 250 }}>
				<div style={{ opacity: t, fontSize: 84, fontWeight: 700, letterSpacing: -1 }}>NernstWork</div>
				<div style={{ opacity: l1, fontSize: 38, color: C.ink, lineHeight: 1.4, marginTop: 36, maxWidth: 1500 }}>
					An AI agent narrows the possible reaction pathways in a solid-state synthesis to a short list of good candidates,
					and suggests what to measure next.
				</div>
				<div style={{ opacity: l2, fontSize: 32, color: C.ink2, lineHeight: 1.4, marginTop: 30, maxWidth: 1500 }}>
					The implication: experiments chosen because they tell rival explanations apart.
				</div>
			</div>
			<div style={{ position: "absolute", left: 140, right: 140, top: 880, opacity: cr, fontSize: 23, color: C.muted, lineHeight: 1.6 }}>
				<span style={{ color: C.ink, fontWeight: 600 }}>Daniel Naumov and Jarrod Barnes</span> · OSI Hackathon, October 2026
				<br />
				Data: {data.shot1.short_citation} (Chapman group). Models: {models.join(", ")}. Literature search: Valency.
			</div>
		</AbsoluteFill>
	);
};
