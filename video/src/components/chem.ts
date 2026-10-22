// Display helpers for species ids and rate-law names on screen.
const SUB: Record<string, string> = { "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉" };

/** Li2TiO3 -> Li₂TiO₃ (digits after a letter become subscripts). */
export const formula = (s: string) => s.replace(/([A-Za-z)])(\d+)/g, (_, a: string, d: string) => a + d.split("").map((c) => SUB[c]).join(""));

const PHASE_NAMES: Record<string, string> = { anatase: "anatase", rutile: "rutile" };
export const species = (id: string) => PHASE_NAMES[id] ?? formula(id);

const LAWS: Record<string, string> = { first_order: "first order", avrami: "Avrami", mass_action: "mass action", langmuir_saturation: "saturating" };
export const rateLaw = (id: string) => LAWS[id] ?? id.replace(/_/g, " ");

/** "Li2CO3_x0.5_T725_long30: half the Li2CO3 (anatase 1.0, ...), 725 C, sampled to 30 min" -> readable design text. */
export const designText = (design: string) =>
	formula((design.split(": ").slice(1).join(": ") || design).replace(/\s*\([^)]*\)/g, "").replace(/(\d) C\b/g, "$1 °C"));
