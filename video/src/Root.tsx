import React from "react";
import { AbsoluteFill, Composition, Series, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { SHOT1_FRAMES, Shot1Open } from "./Shot1Open";
import { SHOT3_FRAMES, Shot3Loop } from "./Shot3Loop";
import { SHOT4_FRAMES, Shot4Reveal } from "./Shot4Reveal";
import { SHOT5_FRAMES, Shot5Ranks } from "./Shot5Ranks";
import { SHOT5B_FRAMES, Shot5bRuns } from "./Shot5bRuns";
import { FPS, H, W } from "./theme";

/** Fades a shot in from and out to the page colour so shots cut together cleanly. */
const Faded: React.FC<{ children: React.ReactNode }> = ({ children }) => {
	const frame = useCurrentFrame();
	const { durationInFrames } = useVideoConfig();
	const o = interpolate(frame, [0, 10, durationInFrames - 12, durationInFrames], [0, 1, 1, 0], {
		extrapolateLeft: "clamp", extrapolateRight: "clamp",
	});
	return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

const Shots4to5: React.FC = () => (
	<Series>
		<Series.Sequence durationInFrames={SHOT4_FRAMES}><Faded><Shot4Reveal /></Faded></Series.Sequence>
		<Series.Sequence durationInFrames={SHOT5_FRAMES}><Faded><Shot5Ranks /></Faded></Series.Sequence>
		<Series.Sequence durationInFrames={SHOT5B_FRAMES}><Faded><Shot5bRuns /></Faded></Series.Sequence>
	</Series>
);

/** Every built shot in story order (shots 2, 6, 7, 8 and the close are still to come). */
const Draft: React.FC = () => (
	<Series>
		<Series.Sequence durationInFrames={SHOT1_FRAMES}><Faded><Shot1Open /></Faded></Series.Sequence>
		<Series.Sequence durationInFrames={SHOT3_FRAMES}><Faded><Shot3Loop /></Faded></Series.Sequence>
		<Series.Sequence durationInFrames={SHOT4_FRAMES + SHOT5_FRAMES + SHOT5B_FRAMES}><Shots4to5 /></Series.Sequence>
	</Series>
);

export const Root: React.FC = () => (
	<>
		<Composition id="Shot1Open" component={Shot1Open} durationInFrames={SHOT1_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shot3Loop" component={Shot3Loop} durationInFrames={SHOT3_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shot4Reveal" component={Shot4Reveal} durationInFrames={SHOT4_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shot5Ranks" component={Shot5Ranks} durationInFrames={SHOT5_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shot5bRuns" component={Shot5bRuns} durationInFrames={SHOT5B_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shots4to5" component={Shots4to5} durationInFrames={SHOT4_FRAMES + SHOT5_FRAMES + SHOT5B_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Draft" component={Draft} durationInFrames={SHOT1_FRAMES + SHOT3_FRAMES + SHOT4_FRAMES + SHOT5_FRAMES + SHOT5B_FRAMES} fps={FPS} width={W} height={H} />
	</>
);
