// Dark chart chrome and the validated categorical slots (dataviz reference palette, dark steps; first three slots pass
// all-pairs CVD and normal-vision checks on #1a1a19). Colour follows the entity in every shot.
import { loadFont } from "@remotion/google-fonts/Inter";

export const { fontFamily } = loadFont("normal", { weights: ["400", "500", "600", "700"], subsets: ["latin", "latin-ext"] });

export const C = {
	page: "#0d0d0d",
	surface: "#1a1a19",
	ink: "#f0efec",
	ink2: "#c3c2b7",
	muted: "#898781",
	grid: "#2c2c2a",
	axis: "#383835",
	// entities
	rule: "#3987e5", // the selection rule's pick (lowest development AICc)
	plausible: "#d95926", // the agent's other plausible model
	ownBest: "#199e70", // best model in the run's own space (known only after the held-out test)
	baseline: "#c3c2b7", // the code-only baseline's pick
	reference: "#898781", // the 153 reference models
};

export const FPS = 30;
export const W = 1920;
export const H = 1080;

export const PHASES: { id: "anatase" | "rutile" | "Li2TiO3" | "Li4Ti5O12"; label: string }[] = [
	{ id: "anatase", label: "Anatase TiO₂" },
	{ id: "rutile", label: "Rutile TiO₂" },
	{ id: "Li2TiO3", label: "Li₂TiO₃" },
	{ id: "Li4Ti5O12", label: "Li₄Ti₅O₁₂ spinel" },
];
