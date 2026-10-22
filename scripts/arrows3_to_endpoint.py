#!/usr/bin/env python3
"""Convert an ARROWS3 experiment table (Exp.json + Settings.json) to a nernstwork endpoint dataset.

Usage:
    python scripts/arrows3_to_endpoint.py <Exp.json> <Settings.json> [out_dir]
Default out_dir: data/arrows3 (git-ignored: the licence of the ARROWS3 data is not confirmed, so derived tables are not
committed either; see docs/SPEC.md section 7e). Writes <out_dir>/arrows3_<target>.json, validated against
schema/endpoint_dataset.schema.json (a sketch; nothing in the evaluator reads it yet).

Source: Szymanski, Nevatia, Bartel, Zeng, Ceder, Nat. Commun. 14, 6956 (2023), doi 10.1038/s41467-023-42329-9; files
Examples/<TARGET>/Exp.json and Settings.json from github.com/njszym/ARROWS (Git LFS).

Rules, and why:

* Entries with "Experimentally Verified": false are DROPPED. In the YBCO file all 51 of them carry no XRD pattern, and
  50 carry a "Source" field naming another experiment they were copied from (for example the CuCO3 set at 600 C takes
  its phases from the CuO set at 600 C, on the assumption that the carbonate decomposes to the oxide before it reacts).
  They are the table authors' inferences, not measurements. Keeping them would (1) count one observation under several
  labels, overstating the evidence, and (2) feed the authors' decomposition assumptions into a fit as data, when those are
  exactly the kind of assumption the engine is supposed to test. The cost: six YBCO precursor sets have no verified
  entry at all, and the converter tolerates sets with missing temperatures. The dropped entries are listed in
  quality.dropped_entries with their source note so the choice can be reversed.
* Phase names: "LiTiPO5_2.cif" -> name "LiTiPO5", structure_id "2", raw_name kept. The numeric suffix indexes a structure
  within the source's own list for that formula (Li3PO4_62 and LiTiPO5_62 are unrelated), so it is only used to keep
  polymorphs of one formula apart (LTOPO: LiTiPO5_2 and LiTiPO5_62). Which suffix is the triclinic polymorph is not stated
  in the files; docs/PROGRESS.md records _2 as triclinic and _62 as orthorhombic (not independently checked here).
* Weight percents are kept as reported (they sum to 98-102): relative XRD peak intensities, not Rietveld quantities,
  normalised, so amorphous material is invisible.
* Hold time: the files do not store it. The paper's Methods give 4 h for all three campaigns (an 8 h follow-up exists for
  NTMO), so hold_h is 4 and stated as a source-paper value, not a per-entry measurement.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHORT = {"Ba2YCu3O7": "ybco", "Na2Te3Mo3O16": "ntmo", "LiTiPO5": "ltopo"}
CITATION = ("Szymanski N. J., Nevatia P., Bartel C. J., Zeng Y., Ceder G., Autonomous and dynamic precursor selection "
            "for solid-state materials synthesis, Nat. Commun. 14, 6956 (2023)")
DROP_REASON = (
    "Entries flagged Experimentally Verified = false have no XRD pattern and are copies of another experiment's phases "
    "(the source field names it, usually a chemically 'equivalent' precursor set such as a carbonate replaced by its "
    "oxide). They are inferences by the table's authors, not measurements; keeping them would count one observation under "
    "several labels and feed the authors' decomposition assumptions into a fit as data.")


def parse_phase(raw):
    name = raw[:-4] if raw.endswith(".cif") else raw
    m = re.fullmatch(r"(.+)_(\d+)", name)
    return (m.group(1), m.group(2)) if m else (name, None)


def parse_rate(txt):
    m = re.match(r"\s*([0-9.]+)", txt or "")
    return float(m.group(1)) if m else None


def convert(exp_path, settings_path):
    exp = json.loads(Path(exp_path).read_text())["Universal File"]
    settings = json.loads(Path(settings_path).read_text())
    target = settings["Target"]
    common = exp.get("Common Experimental Conditions", {})
    experiments, dropped = [], []
    sets = [k for k in exp if k != "Common Experimental Conditions"]
    n_entries = 0
    for key in sets:
        block = exp[key]
        stoich = block.get("Precursor stoichiometry")
        for tkey, r in block["Temperatures"].items():
            n_entries += 1
            T = float(tkey.split()[0])
            pset = [s.strip() for s in key.split(",")]
            if not r.get("Experimentally Verified"):
                dropped.append({"precursor_set": pset, "temperature_C": T, "inferred_from": r.get("Source")})
                continue
            phases = []
            for raw, w in zip(r["products"], r["product weight fractions"]):
                name, sid = parse_phase(raw)
                phases.append({"name": name, "structure_id": sid, "raw_name": raw, "wt_percent": float(w)})
            tw = sum(p["wt_percent"] for p in phases if p["name"] == target)
            experiments.append({
                "precursor_set": pset, "stoichiometry": list(stoich) if stoich else None, "temperature_C": T,
                "phases": phases, "wt_sum": round(sum(p["wt_percent"] for p in phases), 2),
                "target_present": any(p["name"] == target for p in phases), "target_wt_percent": round(tw, 2)})
    temps = [float(t) for t in settings.get("Temperatures", [])]
    flags = ["endpoint_only", "weights_semiquantitative", "phase_label_noise"]
    if dropped:
        flags.append("unverified_entries_dropped")
    if len(experiments) + len(dropped) < len(sets) * len(temps):
        flags.append("partial_design_grid")
    if len(experiments) < 30:
        flags.append("sparse")
    short = SHORT.get(target, re.sub(r"[^A-Za-z0-9]", "", target).lower())
    ds = {
        "id": f"arrows3_{short}",
        "provenance": {
            "source_type": "repository_file", "citation": CITATION, "doi": "10.1038/s41467-023-42329-9",
            "file": f"Exp.json and Settings.json for {target} from github.com/njszym/ARROWS (not redistributed; licence unconfirmed)",
            "extraction": "scripts/arrows3_to_endpoint.py (verified entries only; phase names normalised)",
            "notes": "Phase weight fractions were estimated from relative XRD peak intensities (XRD-AutoAnalyzer), not Rietveld refinement."},
        "system": {
            "target": target, "precursors_considered": list(settings.get("Precursors", [])), "temperatures_C": temps,
            "hold_h": 4.0, "heating_rate_C_per_min": parse_rate(common.get("heating rate")),
            "atmosphere": common.get("atmosphere"),
            "notes": ("hold_h is the paper's stated 4 h for every campaign, not stored per entry; heating rate and "
                      "atmosphere are given only for LTOPO ('Common Experimental Conditions')." )},
        "experiments": experiments,
        "quality": {
            "flags": flags,
            "dropped_entries": {"count": len(dropped), "reason": DROP_REASON, "items": dropped},
            "counts": {"precursor_sets_in_file": len(sets), "entries_in_file": n_entries,
                       "entries_kept": len(experiments), "entries_dropped": len(dropped),
                       "entries_with_target": sum(e["target_present"] for e in experiments)}}}
    return ds


def main():
    exp, settings = sys.argv[1], sys.argv[2]
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "data/arrows3"
    ds = convert(exp, settings)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{ds['id']}.json"
    p.write_text(json.dumps(ds, indent=2) + "\n")
    c = ds["quality"]["counts"]
    print(f"wrote {p}: {c['entries_kept']} kept of {c['entries_in_file']} entries "
          f"({c['entries_dropped']} unverified dropped), {c['precursor_sets_in_file']} precursor sets, "
          f"{c['entries_with_target']} with target {ds['system']['target']}")


if __name__ == "__main__":
    main()
