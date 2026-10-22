import React from "react";
import { AbsoluteFill, Audio, Composition, Sequence, Series, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import timing from "./data/timing.json";
import { Timed } from "./time";
import { SHOT_END_FRAMES, ShotEnd } from "./ShotEnd";
import { SHOT1_FRAMES, Shot1Open } from "./Shot1Open";
import { SHOT3_FRAMES, Shot3Loop } from "./Shot3Loop";
import { SHOT4_FRAMES, Shot4Reveal } from "./Shot4Reveal";
import { SHOT5_FRAMES, Shot5Ranks } from "./Shot5Ranks";
import { SHOT5B_FRAMES, Shot5bRuns } from "./Shot5bRuns";
import { SHOT7_FRAMES, Shot7Plan } from "./Shot7Plan";
import { SHOT9_FRAMES, Shot9Close } from "./Shot9Close";
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

/** The full video: every shot in story order, timed to SCRIPT.md. */
const Draft: React.FC = () => (
	<Series>
		<Series.Sequence durationInFrames={SHOT1_FRAMES}><Faded><Shot1Open /></Faded></Series.Sequence>
		<Series.Sequence durationInFrames={SHOT3_FRAMES}><Faded><Shot3Loop /></Faded></Series.Sequence>
		<Series.Sequence durationInFrames={SHOT4_FRAMES + SHOT5_FRAMES + SHOT5B_FRAMES}><Shots4to5 /></Series.Sequence>
		<Series.Sequence durationInFrames={SHOT7_FRAMES}><Faded><Shot7Plan /></Faded></Series.Sequence>
		<Series.Sequence durationInFrames={SHOT9_FRAMES}><Faded><Shot9Close /></Faded></Series.Sequence>
	</Series>
);

const SHOT_COMPONENTS: Record<string, React.FC> = {
	Shot1Open, Shot3Loop, Shot4Reveal, Shot5Ranks, Shot5bRuns, Shot7Plan, Shot9Close, ShotEnd,
};

/** The narrated cut: each shot timed to Daniel's clip, beats anchored to his words (src/data/timing.json, make_timing.py). */
const Final: React.FC = () => (
	<Series>
		{timing.shots.map((sh) => {
			const Comp = SHOT_COMPONENTS[sh.id];
			return (
				<Series.Sequence key={sh.id} durationInFrames={sh.frames}>
					<Faded><Timed anchors={sh.anchors as [number, number][]}><Comp /></Timed></Faded>
					{(sh.audio as { src: string; from: number }[]).map((a) => (
						<Sequence key={a.src} from={a.from}><Audio src={staticFile(a.src)} /></Sequence>
					))}
					{((sh as { room_tone?: number[][] }).room_tone ?? []).map(([g0, g1]) => (
						<Sequence key={`rt${g0}`} from={g0} durationInFrames={g1 - g0}><Audio src={staticFile("audio/silence.mp3")} loop /></Sequence>
					))}
				</Series.Sequence>
			);
		})}
	</Series>
);

export const Root: React.FC = () => (
	<>
		<Composition id="Final" component={Final} durationInFrames={timing.total_frames} fps={FPS} width={W} height={H} />
		<Composition id="Shot1Open" component={Shot1Open} durationInFrames={SHOT1_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shot3Loop" component={Shot3Loop} durationInFrames={SHOT3_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shot4Reveal" component={Shot4Reveal} durationInFrames={SHOT4_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shot5Ranks" component={Shot5Ranks} durationInFrames={SHOT5_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shot5bRuns" component={Shot5bRuns} durationInFrames={SHOT5B_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shots4to5" component={Shots4to5} durationInFrames={SHOT4_FRAMES + SHOT5_FRAMES + SHOT5B_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shot7Plan" component={Shot7Plan} durationInFrames={SHOT7_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Shot9Close" component={Shot9Close} durationInFrames={SHOT9_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="ShotEnd" component={ShotEnd} durationInFrames={SHOT_END_FRAMES} fps={FPS} width={W} height={H} />
		<Composition id="Draft" component={Draft}
			durationInFrames={SHOT1_FRAMES + SHOT3_FRAMES + SHOT4_FRAMES + SHOT5_FRAMES + SHOT5B_FRAMES + SHOT7_FRAMES + SHOT9_FRAMES} fps={FPS} width={W} height={H} />
	</>
);
