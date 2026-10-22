// Per-shot timing. A shot is built on its own nominal frame clock; in the narrated cut each shot's clock is driven by
// anchor points (real frame -> nominal frame) taken from the narration's timestamps, so each visual beat lands on the
// words that describe it. Shots read time through useFrame() instead of useCurrentFrame().
import React, { createContext, useContext } from "react";
import { interpolate, useCurrentFrame } from "remotion";

type Anchors = [number, number][];
const TimeMap = createContext<Anchors | null>(null);

export const useFrame = () => {
	const f = useCurrentFrame();
	const a = useContext(TimeMap);
	if (!a) return f;
	return interpolate(f, a.map((p) => p[0]), a.map((p) => p[1]), { extrapolateLeft: "clamp", extrapolateRight: "extend" });
};

export const Timed: React.FC<{ anchors: Anchors | null; children: React.ReactNode }> = ({ anchors, children }) => (
	<TimeMap.Provider value={anchors}>{children}</TimeMap.Provider>
);
