"""Markdown reports for one run and for a comparison of arms. Every number comes from stored artifacts."""
from __future__ import annotations

import json
import math
from pathlib import Path

from . import investigation as inv
from . import plots
from .model import FITTED
from .store import Run, read_json


def _fmt(x, nd=3):
    if x is None:
        return "-"
    if isinstance(x, float):
        if not math.isfinite(x):
            return str(x)
        return f"{x:.{nd}g}"
    return str(x)


def reaction_text(mech: dict, params: dict | None = None) -> list[str]:
    out = []
    for r in mech["reactions"]:
        lhs = " + ".join(f"{'' if t['coeff'] == 1 else _fmt(t['coeff']) + ' '}{t['species']}" for t in r["reactants"])
        rhs = " + ".join(f"{'' if t['coeff'] == 1 else _fmt(t['coeff']) + ' '}{t['species']}" for t in r["products"])
        rl = r["rate_law"]
        bits = [rl["family"]]
        if rl.get("time_modulation"):
            tm = rl["time_modulation"]
            prm = tm.get("n") if tm["kind"] == "avrami" else tm["tau_min"]
            bits.append(f"{tm['kind']}({'n' if tm['kind'] == 'avrami' else 'tau'}{' tie=' + prm['tie'] if prm.get('tie') else ''})")
        if rl.get("temperature_dependence"):
            bits.append(f"Arrhenius(T_ref {_fmt(rl['temperature_dependence']['T_ref_C'])} C)")
        if "K" in rl["params"]:
            bits.append("K" + (f" tie={rl['params']['K']['tie']}" if rl["params"]["K"].get("tie") else ""))
        if rl.get("potential_dependence"):
            bits.append("E-dependent")
        if rl.get("ph_dependence"):
            bits.append("pH-dependent")
        if "k_mt" in rl["params"]:
            bits.append("k_mt")
        line = f"{r['id']}: {lhs} -> {rhs} [{', '.join(bits)}" + (f"; e={r.get('electrons')}]" if "electrons" in r else "]")
        if params:
            ps = [f"{n}={_fmt(v['value'])} (95% Wald {_fmt(v['wald_ci95'][0])}-{_fmt(v['wald_ci95'][1])}, {v['determinacy']})"
                  for n, v in params.items() if n.startswith(r["id"] + ".")]
            if ps:
                line += "; " + "; ".join(ps)
        out.append(line)
    if params:
        ties = [f"{n}={_fmt(v['value'])} (95% Wald {_fmt(v['wald_ci95'][0])}-{_fmt(v['wald_ci95'][1])}, {v['determinacy']})"
                for n, v in params.items() if n.startswith("tie:")]
        if ties:
            out.append("shared: " + "; ".join(ties))
    return out


def usage(run: Run) -> dict:
    numerics = {"fits_committed_by_this_run": 0, "fits_reused": 0, "fit_cpu_s": 0.0, "profile_wall_s": 0.0,
                "note": "current evaluator code only; earlier code versions' records are excluded"}
    for rec in inv.current_records(run).values():
        fk = rec.get("fit_key")
        if not fk:
            continue
        body = run.cache.result(fk)
        if not body:
            continue
        if body["result"].get("timing") and rec.get("fit_outcome") == "committed":
            numerics["fits_committed_by_this_run"] += 1
            numerics["fit_cpu_s"] += body["result"]["timing"]["cpu_s"]
        else:
            numerics["fits_reused"] += 1
        prof = run.cache.dir(fk) / "profile.json"
        if prof.exists():
            numerics["profile_wall_s"] += read_json(prof).get("wall_s", 0.0)
    llm = None
    p = run.dir / "pi" / "usage.json"
    if p.exists():
        u = read_json(p)
        sessions = list(u.get("sessions", {}).values())
        llm = {"models": sorted({s.get("model") for s in sessions if s.get("model")}),
               "sessions": {lab: sum(1 for s in sessions if s.get("label", "").split("-")[0] == lab)
                            for lab in sorted({s.get("label", "").split("-")[0] for s in sessions})},
               **{k: u.get(k) for k in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
                                        "cost_usd", "wall_s", "tool_calls")},
               "cost_note": "list prices from the Pi model table"}
    return {"numerics": numerics, "llm": llm}


def _rmse(rmse: dict | None):
    return {k: round(v, 2) for k, v in rmse.items()} if isinstance(rmse, dict) else rmse


def _llm_line(llm: dict | None) -> str:
    if not llm:
        return "none recorded"
    sessions = ", ".join(f"{n} {lab}" for lab, n in llm["sessions"].items())
    return (f"{', '.join(llm['models'])}; sessions: {sessions}; tokens in {llm['input_tokens']:,}, out "
            f"{llm['output_tokens']:,}, cache read {llm['cache_read_tokens']:,}, cache write {llm['cache_write_tokens']:,}; "
            f"${llm['cost_usd']:.2f} ({llm['cost_note']}); {llm['wall_s']:.0f} s wall; {llm['tool_calls']} tool calls")


def write_report(run: Run, out: Path | None = None) -> dict:
    out = out or (run.dir / "report.md")
    pdir = out.parent / (out.stem + "_plots")
    pdir.mkdir(parents=True, exist_ok=True)
    rc, m, proto = run.config(), run.manifest(), run.protocol()
    cmp = inv.compare(run)
    ss = {s["candidate_id"]: s for s in inv.summaries(run)}
    cands = {c["candidate_id"]: c for c in run.candidates()}
    obs = inv._dev_obs(run)
    L = [f"# Investigation report: {run.id}", "",
         f"- Investigation: `{m['investigation_id']}`; arm: `{rc['arm']}`; phase: `{run.state().get('phase')}`",
         (f"- Protocol: `{proto['protocol_id']}` (sha256 `{rc['protocol_sha256'][:16]}`); manifest sha256 "
         f"`{rc['manifest_sha256'][:16]}`; evaluator code sha256 `{m['code']['sha256'][:16]}` ({m['code']['versions']})"),
         (f"- Development data: `{obs.dataset_id}` (sha256 `{obs.sha256[:16]}`, {obs.source_type}); {obs.n_obs} observations "
         f"({'; '.join(obs.notes)})"), "",
         "## Question", m["question"], "", "## System boundary", m["system_boundary"], "",
         "## Evidence status", f"- Partition: {m['partition_policy']}",
         f"- Contamination: {m['contamination_audit'].get('honest_label', 'not audited')}", ""]
    rk = cmp["ranking"]
    L += ["## Ranked candidates (development data, computed in code)", "", rk["note"], ""]
    for g in rk["groups"]:
        chans = g["channels"]
        L.append("| candidate | name | source | v | k | AICc | dAICc | weight | band | adequacy | " +
                 " | ".join(f"RMSE {c}" for c in chans) + " | unobserved N end | in declared space | flags |")
        L.append("|" + "---|" * (11 + len(chans) + 1))
        max_rows = 25
        for row in g["rows"][:max_rows]:
            s = ss[row["candidate_id"]]
            L.append(f"| {row['candidate_id']} | {row['name']} | {row['source']} | {s['version']} | {row['k_total']} | "
                     f"{row['aicc']:.2f} | {row['delta_aicc']:.2f} | {row['weight']:.3f} | {row['band']} | {row['adequacy']} | " +
                     " | ".join(_fmt(s['rmse'].get(c)) for c in chans) +
                     f" | {_fmt(s.get('unobserved_N_end_mM'))} | {', '.join(row['in_enumeration_spaces']) or 'no'} | "
                     f"{'; '.join(row['plausibility_flags']) or ''} |")
        if len(g["rows"]) > max_rows:
            L.append(f"\n{len(g['rows']) - max_rows} lower-ranked fitted candidates omitted here; "
                     f"`python -m nernstwork.cli compare --run {run.id}` lists all of them.")
        L.append("")
    not_ranked = [s for s in ss.values() if s["status"] != FITTED]
    if not_ranked:
        L += ["## Candidates that were not fitted (recorded, with status)", ""]
        for s in not_ranked:
            L.append(f"- {s['candidate_id']} `{s['name']}` ({s['source']}): **{s['status']}** -- "
                     f"{'; '.join(s.get('errors') or []) or json.dumps(s.get('numerics'))[:300]}")
        L.append("")
    if cmp["observationally_equivalent_groups"]:
        L += ["## Observationally equivalent candidates", "",
              ("Same dynamics on the measured channels, different chemistry (e.g. electron count or identity of an "
              "unmeasured product): these data cannot separate them."), ""]
        for gr in cmp["observationally_equivalent_groups"]:
            L.append(f"- {', '.join(gr)}")
        L.append("")
    top = [r["candidate_id"] for g in rk["groups"] for r in g["rows"]][:4]
    if top:
        L += ["## Top candidates in detail", ""]
        fits = []
        for cid in top:
            c = cands[cid]
            s = ss[cid]
            L += [f"### {cid} `{c['name']}` (source {c['origin']['source']}, version {c['version']}"
                  + (f", parent {c['parent_id']}" if c["parent_id"] else "") + ")", ""]
            if c["submission"].get("rationale"):
                L += [f"Rationale (proposer): {c['submission']['rationale']}", ""]
            L += [f"    {x}" for x in reaction_text(c["submission"]["mechanism"], s.get("params"))]
            L.append("")
            sup = c["validation"].get("support", {})
            L.append(f"- Support entries: {sup.get('counts')}; reactions without support: "
                     f"{sup.get('reactions_without_support')}")
            for sp in c["submission"].get("support", [])[:12]:
                L.append(f"  - {sp['target']}: {sp['basis']} -- {sp.get('source', '')} {sp.get('note', '')}")
            if c["submission"].get("assumptions"):
                L.append(f"- Assumptions (proposer): {c['submission']['assumptions']}")
            L.append(f"- sigma (profiled): {', '.join(f'{k}={_fmt(v)}' for k, v in s['sigma'].items())}; "
                     f"adequacy: {s['adequacy']} {s['adequacy_reasons']}")
            if s.get("sloppy_directions"):
                L.append(f"- Locally unidentifiable combinations: {s['sloppy_directions']}")
            _, _, _rec, fr, prof = inv.fit_view(run, cid)
            if prof:
                pr = prof["params"]
                L.append("- Profile likelihood: " + "; ".join(
                    f"{n}: {d['classification']}" + (f" (95% {_fmt(d['ci95'][0])}-{_fmt(d['ci95'][1])})" if d["ci95"] else "")
                    for n, d in pr.items()))
                plots.plot_profiles(prof, pdir / f"{cid}_profile.png", title=cid)
                L.append(f"  ![profile]({pdir.name}/{cid}_profile.png)")
            else:
                L.append("- Profile likelihood: not computed (identifiability beyond the local Fisher screen is unassessed)")
            L.append("")
            fits.append((cid, dict(fr, _mapping=c["validation"]["observation_map"])))
        plots.plot_fits(obs, fits, pdir / "top_fits.png", title=f"{run.id}: top candidates on {obs.dataset_id}")
        L += [f"![top fits]({pdir.name}/top_fits.png)", ""]
    adir = run.dir / "analyses"
    if adir.exists():
        for p in sorted(adir.glob("discrimination-*.json")):
            d = read_json(p)
            L += [f"## Discrimination analysis ({p.name})", "", d["note"], ""]
            for des in d["designs"]:
                L.append(f"- Design `{des['design'].get('name')}` {json.dumps(des['design'])}:")
                for row in des["comparisons"][:5]:
                    L.append(f"  - {row['quantity']}: max spread {_fmt(row['max_spread_mM_N'])} mM-N at "
                             f"{_fmt(row['at_t_min'])} min ({_fmt(row['spread_in_dev_sigma'])} dev sigma); "
                             f"{ {k: round(v, 2) for k, v in row['values_at_t'].items()} }")
            L.append("")
    rdir = run.dir / "reviews"
    if rdir.exists():
        for rp in sorted(rdir.glob("*/review-*.json")):
            rv = read_json(rp)
            L += [f"## Review {rv['review_id']} (bundle {rv['bundle_id']}; reviewer {rv['reviewer'].get('model', '?')})", "",
                  "An interpretation of the frozen bundle, not experimental validation.", "",
                  rv["review"]["summary"], ""]
            for f in rv["review"]["findings"]:
                L.append(f"- **{f['id']}** [{f['severity']}/{f['category']}] {f['claim']} (targets: "
                         f"{', '.join(f['targets'])}; check: {f['check']['type']}; action: {f['action']['type']} -- "
                         f"{f['action']['description']})")
            a = rv["review"]["assessment"]
            L += ["", (f"Assessment: plausible {a.get('plausible_candidates')}; adequate candidate exists: "
                      f"{a.get('adequate_candidate_exists')}; ambiguities: {a.get('ambiguities')}"), ""]
            resp = rp.parent / rp.name.replace("review-", "response-")
            if resp.exists():
                L.append("Investigator response:")
                for r in read_json(resp)["response"]["responses"]:
                    L.append(f"- {r['finding_id']}: {r['action']} {r.get('candidate_ids', [])} -- {r['note']}")
                L.append("")
    cdir = run.dir / "conclusions"
    if cdir.exists():
        for cp in sorted(cdir.glob("*.json")):
            c = read_json(cp)["conclusion"]
            L += [f"## Investigator conclusion ({cp.name}; an interpretation, numbers above are authoritative)", "",
                  c["narrative"], "", f"- Plausible: {c['plausible']}", f"- Adequacy: {c['adequacy']}",
                  f"- Rejected: {c['rejected']}", f"- Ambiguities: {c['ambiguities']}"]
            for e in c.get("recommended_experiments", []):
                L.append(f"- Experiment: {e['design']} -- discriminates {e['discriminates']}: {e.get('rationale', '')}")
            L.append("")
    if (run.dir / "frozen.json").exists():
        fz = read_json(run.dir / "frozen.json")
        L += ["## Frozen selection", "", f"- Rule: {fz['rule']}", f"- Selected: {fz['selected_by_rule']}",
              f"- Agent-concluded plausible: {fz['agent_concluded_plausible']}", f"- Frozen at {fz['frozen_at']}", ""]
    which = "latest" if final_file(run, "latest") else "first"
    fe = final_file(run, which)
    if fe:
        f = read_json(fe)
        predict = any(d.get("mode") == "predict" for d in f["datasets"])
        ho = {} if predict else {h["candidate_id"]: h for h in heldout_table(run, which=which)}
        version = ("current evaluator code" if which == "latest" else "pre-registered evaluation; evaluator code has "
                   "changed since")
        first = final_file(run, "first")
        if which == "latest" and first and read_json(first).get("code_sha256") != f.get("code_sha256"):
            version += "; the pre-registered evaluation (earlier code) is kept in final/final_evaluation.json"
        for d in f["datasets"]:
            if d.get("mode") == "predict":
                L += _predict_section(d, version)
                continue
            L += [f"## Final held-out evaluation: {d['dataset_id']}", "", f"Version: {version}.", "", d["interpretation"],
                  ("Sensitivity: AICc at the lowest NLL any start reached (flags fits whose reported optimum is beaten by "
                  "replicated unconverged starts). See docs/examples/arm_comparison.md for ranks in a shared reference set."), ""]
            for r in d["frozen_candidates"]:
                h = ho.get(r["candidate_id"], {})
                L.append(f"- {r['candidate_id']}: {r['status']}; AICc {_fmt(r.get('aicc'))}, delta to best "
                         f"{_fmt(r.get('delta_aicc_to_best_overall'))}, rank {r.get('rank_among_space')}/{r.get('n_space')} "
                         f"among this run's declared-space members; numerically unreliable: {h.get('numerically_unreliable')}; "
                         f"sensitivity AICc {_fmt(h.get('sensitivity_aicc'))} (rank {h.get('sensitivity_rank')}); "
                         f"adequacy {r.get('adequacy')}; RMSE {_rmse(r.get('rmse'))}")
            L.append(f"- Best declared-space members on the held-out run: "
                     f"{[(b['candidate_id'], round(b['aicc'], 2), b.get('structure')) for b in d['best_in_spaces'][:3]]}")
            L.append("")
    u = usage(run)
    n = u["numerics"]
    L += ["## Cost and runtime", "",
          (f"- Numerics: {n['fits_committed_by_this_run']} fits run, {n['fits_reused']} reused from the shared cache, "
          f"{n['fit_cpu_s']:.0f} CPU s fitting, {n['profile_wall_s']:.0f} s profiles ({n['note']})"),
          f"- LLM: {_llm_line(u['llm'])}", ""]
    unresolved = []
    for d in m["datasets"]:
        if d["role"] == "development":
            unresolved += [f"{d['dataset_id']}: verified_against_figure={d['provenance'].get('verified_against_figure')}"]
    for lit in m["literature"]:
        for c in lit["claims"]:
            if c["status"] not in ("stated",):
                unresolved.append(f"[{c['id']}] {c['topic']}: {c['status']}")
    L += ["## Unresolved assumptions and metadata", ""] + [f"- {x}" for x in unresolved] + [
        ("- Noise model: independent Gaussian errors per channel (profiled sigma); no replicate information exists for these "
        "runs, so sigma is estimated from misfit and includes model error."),
        "- AICc differences assume independent errors; clustered residual signs (adequacy 'poor') make them optimistic.", ""]
    out.write_text("\n".join(L) + "\n")
    return {"report": str(out), "plots_dir": str(pdir)}


def _predict_section(d: dict, version: str) -> list[str]:
    """Held-out section for parameter-transfer (predict-mode) evaluations."""
    L = [f"## Final held-out evaluation: {d['dataset_id']} (predicted without refitting)", "", f"Version: {version}.", "",
         d["interpretation"], "", f"Common noise scale per phase (development sigma of {d.get('common_sigma_from')}): "
         f"{ {k: round(v, 4) for k, v in d['common_sigma'].items()} }", ""]
    for r in d["frozen_candidates"]:
        role = "+".join(t for t, on in (("selected", r["selected_by_rule"]), ("agent-plausible", r["agent_concluded_plausible"])) if on)
        L.append(f"- {r['candidate_id']} ({role}): {r['status']}; held-out score {_fmt(r.get('heldout_score'), 4)}, rank "
                 f"{r.get('rank_among_space')}/{r.get('n_space')} (by RMSE {r.get('rank_by_rmse')}, by own-sigma "
                 f"log-likelihood {r.get('rank_by_predictive_nll')}); RMSE {_rmse(r.get('rmse'))} (all {_fmt(r.get('rmse_all'))}); "
                 f"development AICc {_fmt(r.get('development_aicc'), 5)}")
    rc = d.get("run_candidates") or {}
    if rc.get("best_predicting"):
        b, a = rc["best_predicting"], rc["best_development_aicc"]
        L.append(f"- This run's own candidates ({rc['n_scored']} scored): best predictor {b['candidate_id']} ranks "
                 f"{b['rank_among_space']}; the run's best development-AICc member {a['candidate_id']} ranks {a['rank_among_space']}")
    L.append("- Best reference-space members on the held-out run: " +
             ", ".join(f"{b['candidate_id']} (score {_fmt(b['heldout_score'], 4)}, RMSE {_fmt(b['rmse_all'])})"
                       for b in d["best_in_spaces"][:3]))
    for b in d.get("development_aicc_best_in_spaces", []):
        L.append(f"- The reference member with the best development AICc, {b['candidate_id']}, ranks {b['rank_among_space']} "
                 f"(by own-sigma log-likelihood {b['rank_by_predictive_nll']})")
    return L + [""]


def compare_arms_predict(runs: list[Run], out: Path, which: str = "first") -> dict:
    """Arm comparison for parameter-transfer investigations (fit development temperatures, predict the reserved one)."""
    rows, ref = [], None
    for r in runs:
        ss = inv.summaries(r)
        fitted = [s for s in ss if s["status"] == FITTED]
        best = min(fitted, key=lambda s: s["aicc"]) if fitted else None
        ff = final_file(r, which)
        fd = read_json(ff)["datasets"][0] if ff else None
        fz = read_json(r.dir / "frozen.json") if (r.dir / "frozen.json").exists() else {}
        spaces = sorted((r.dir / "spaces").glob("space-*.json")) if (r.dir / "spaces").exists() else []
        sources = {}
        for c in r.candidates():
            sources[c["origin"]["source"]] = sources.get(c["origin"]["source"], 0) + 1
        u = usage(r)
        top1 = next((x for x in (fd or {}).get("frozen_candidates", []) if x["candidate_id"] == fz.get("top1")), None)
        if fd and ref is None:
            ref = {"dataset_id": fd["dataset_id"], "n_space": fd["n_space_fitted"], "best": fd["best_in_spaces"][:3],
                   "dev_best": fd.get("development_aicc_best_in_spaces", [])}
        rows.append({"run_id": r.id, "arm": r.config()["arm"], "models": (u["llm"] or {}).get("models"),
                     "candidates": len(ss), "sources": sources, "n_spaces": len(spaces),
                     "n_fitted": len(fitted), "best_dev": best["candidate_id"] if best else None,
                     "best_dev_aicc": best["aicc"] if best else None, "frozen_top1": fz.get("top1"),
                     "heldout_top1": top1, "heldout_frozen": (fd or {}).get("frozen_candidates", []),
                     "own_space": (fd or {}).get("run_candidates"), "llm": u["llm"], "numerics": u["numerics"]})
    L = ["# Arm comparison: Chapman 2023, fit 700 + 725 C, predict 750 C", "",
         ("Every arm shares the protocol, the development data and the reference space. The 750 C run is predicted with "
          "development parameters (no refitting). Held-out score: squared error weighted by one common noise scale per "
          "phase, the development sigma of the reference member with the lowest development AICc (lower is better). "
          "Ranks are among the "
          f"{ref['n_space'] if ref else '-'} reference-space members scored the same way; the own-sigma log-likelihood rank "
          "measures calibration (it penalizes models whose development noise estimate understates the extrapolation error)."), "",
         "| run | arm | model | candidates (by source) | spaces | best development AICc | frozen top-1 | held-out score | "
         "held-out rank | rank by RMSE | rank by own-sigma NLL | RMSE all | own space: best predictor rank | "
         "own space: dev-best rank | LLM cost, list USD |",
         "|" + "---|" * 15]
    for x in rows:
        h, o, llm = x["heldout_top1"] or {}, x["own_space"] or {}, x["llm"] or {}
        bp, bd = o.get("best_predicting") or {}, o.get("best_development_aicc") or {}
        L.append(f"| {x['run_id']} | {x['arm']} | {', '.join(x['models'] or ['-'])} | {x['candidates']} {x['sources']} | "
                 f"{x['n_spaces']} | {_fmt(x['best_dev_aicc'], 5)} | {x['frozen_top1']} | {_fmt(h.get('heldout_score'), 4)} | "
                 f"{h.get('rank_among_space')}/{h.get('n_space')} | {h.get('rank_by_rmse')} | {h.get('rank_by_predictive_nll')} | "
                 f"{_fmt(h.get('rmse_all'))} | {bp.get('rank_among_space', '-')} | "
                 f"{bd.get('rank_among_space', '-')} | {_fmt(llm.get('cost_usd'))} |")
    if ref:
        L += ["", "Reference space on the held-out run: best members " +
              ", ".join(f"{b['candidate_id']} ({_fmt(b['heldout_score'], 4)})" for b in ref["best"]) +
              "; the member with the best development AICc ranks " +
              ", ".join(str(b["rank_among_space"]) for b in ref["dev_best"]) + "."]
    res = {"rows": rows, "reference": ref}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    (out.with_suffix(".json")).write_text(json.dumps(res, indent=1, default=str) + "\n")
    return {"report": str(out), **res}


def min_nll_aicc(fit_res: dict) -> float | None:
    """Sensitivity score: AICc at the lowest NLL any start reached (converged or not), same k and n as the fit."""
    if not fit_res or fit_res.get("status") != FITTED:
        return None
    nlls = [x for x in fit_res["multistart"]["nll_by_start"] if isinstance(x, (int, float))]
    if not nlls:
        return None
    k, n = fit_res["k_total"], fit_res["n_obs"]
    return 2 * min(nlls) + 2 * k + (2 * k * (k + 1) / (n - k - 1) if n - k - 1 > 0 else math.inf)


def unreliable(fit_res: dict, tol: float = 0.5) -> bool:
    """True when unconverged starts reached a clearly lower NLL than the reported optimum."""
    if not fit_res or fit_res.get("status") != FITTED:
        return False
    nlls = [x for x in fit_res["multistart"]["nll_by_start"] if isinstance(x, (int, float))]
    return bool(nlls) and min(nlls) < fit_res["nll"] - tol


def final_file(run: Run, which: str = "first") -> Path | None:
    """'first': the pre-registered final evaluation; 'latest': the one made with the current evaluator code."""
    if which == "first":
        p = run.dir / "final" / "final_evaluation.json"
    else:
        from .evaluate import code_identity

        p = run.dir / "final" / f"final_evaluation__{code_identity()['sha256'][:12]}.json"
    return p if p.exists() else None


def heldout_reference(runs: list[Run], which: str = "first") -> dict:
    """Union of every declared-space member fitted to the held-out run(s), keyed by fit key (shared reference set)."""
    ref = {}
    for run in runs:
        ff = final_file(run, which)
        if not ff:
            continue
        code = read_json(ff).get("code_sha256")
        for d in (run.dir / "final").glob("*/evaluations"):
            for p in d.glob("S:*.json"):
                r = read_json(p)
                if code and r.get("code_sha256") != code:
                    continue
                body = run.cache.result(r["fit_key"]) if r.get("fit_key") else None
                if body and body["result"].get("status") == FITTED:
                    ref[(d.parent.name, r["fit_key"])] = body["result"]
    return ref


def heldout_table(run: Run, reference: dict | None = None, which: str = "first") -> list[dict]:
    """Frozen candidates on the held-out run: protocol score and rank, and the min-NLL sensitivity score and rank.
    With `reference`, ranks are among that shared set of declared-space members instead of this run's own spaces."""
    fe = final_file(run, which)
    if not fe:
        return []
    fdata = read_json(fe)
    code = fdata.get("code_sha256")
    rows = []
    for ds in fdata["datasets"]:
        recs = {}
        for p in (run.dir / "final" / ds["dataset_id"] / "evaluations").glob("*.json"):
            r = read_json(p)
            if code and r.get("code_sha256") != code:
                continue
            fr = run.cache.result(r["fit_key"])["result"] if r.get("fit_key") and run.cache.result(r["fit_key"]) else None
            recs[r["candidate_id"]] = (r, fr)
        if reference is not None:
            space = {k[1]: fr for k, fr in reference.items() if k[0] == ds["dataset_id"]}
        else:
            space = {cid: fr for cid, (r, fr) in recs.items() if cid.startswith("S:") and fr and fr.get("status") == FITTED}
        prot_space = sorted(fr["aicc"] for fr in space.values())
        sens_space = sorted(v for v in (min_nll_aicc(fr) for fr in space.values()) if v is not None)
        best_protocol = min(fr["aicc"] for fr in space.values())
        for f in ds["frozen_candidates"]:
            r, fr = recs.get(f"F:{f['candidate_id']}", (None, None))
            sens = min_nll_aicc(fr)
            if reference is not None and f.get("aicc") is not None:
                f = dict(f, rank_among_space=1 + sum(1 for v in prot_space if v < f["aicc"] - 1e-9), n_space=len(prot_space))
            rows.append(dict(f, dataset_id=ds["dataset_id"], numerically_unreliable=unreliable(fr),
                             replicates=(fr or {}).get("multistart", {}).get("replicates"),
                             best_space_aicc_protocol=best_protocol, sensitivity_aicc=sens,
                             sensitivity_rank=(1 + sum(1 for v in sens_space if v < sens - 1e-9)) if sens is not None else None,
                             sensitivity_best_space=sens_space[0] if sens_space else None, n_space_fitted=len(sens_space)))
    return rows


def compare_arms(runs: list[Run], out: Path, which: str = "first") -> dict:
    """Compare arms that share protocol and development data. Numbers only; interpretation is left to the reader."""
    if runs and runs[0].config()["config_snapshot"].get("final_evaluation", {}).get("mode") == "predict":
        return compare_arms_predict(runs, out, which)
    base = None
    for r in runs:
        rc = r.config()
        key = (rc["protocol_sha256"], next(d["sha256"] for d in r.manifest()["datasets"] if d["role"] == "development"))
        if base is None:
            base = key
        elif key != base:
            raise inv.InvestigationError(f"{r.id} uses a different protocol or development data; not comparable")
    per = []
    for r in runs:
        ss = inv.summaries(r)
        recs = inv.current_records(r)
        cands = {c["candidate_id"]: c for c in r.candidates()}
        fitted = [s for s in ss if s["status"] == FITTED]
        fits = {s["candidate_id"]: r.cache.result(recs[s["candidate_id"]]["fit_key"])["result"] for s in fitted}
        per.append((r, ss, cands, fitted, fits))
    reference = heldout_reference(runs, which)
    best_overall = min((s["aicc"] for _, _, _, f, _ in per for s in f), default=math.inf)
    sens_overall = min((v for *_, fits in per for v in (min_nll_aicc(fr) for fr in fits.values()) if v is not None),
                       default=math.inf)
    rows = []
    for r, ss, cands, fitted, fits in per:
        idx = inv.space_index(r)
        counts = {}
        for s in ss:
            counts[s["status"]] = counts.get(s["status"], 0) + 1
        in_space = [s for s in fitted if idx.get(cands[s["candidate_id"]]["validation"].get("dynamics_hash"))]
        out_space = [s for s in fitted if s not in in_space]
        best = min(fitted, key=lambda s: s["aicc"]) if fitted else None
        sens = {cid: min_nll_aicc(fr) for cid, fr in fits.items()}
        sens_best = min(sens.items(), key=lambda kv: kv[1]) if sens else None
        u = usage(r)
        ho = heldout_table(r, reference, which)
        fz = read_json(r.dir / "frozen.json") if (r.dir / "frozen.json").exists() else {}
        top1 = next((x for x in ho if x["candidate_id"] == fz.get("top1")), None)
        rows.append({
            "run_id": r.id, "arm": r.config()["arm"], "candidates": len(ss), "status_counts": counts,
            "best_candidate": best["candidate_id"] if best else None,
            "best_name": cands[best["candidate_id"]]["name"] if best else None,
            "best_aicc": best["aicc"] if best else None,
            "best_delta_to_overall": (best["aicc"] - best_overall) if best else None,
            "best_in_declared_space": bool(best and idx.get(cands[best["candidate_id"]]["validation"].get("dynamics_hash"))),
            "best_in_space_aicc": min((s["aicc"] for s in in_space), default=None),
            "best_outside_space_aicc": min((s["aicc"] for s in out_space), default=None),
            "dev_fits_numerically_unreliable": sum(1 for fr in fits.values() if unreliable(fr)),
            "sensitivity_best": {"candidate_id": sens_best[0], "aicc": sens_best[1]} if sens_best else None,
            "numerics": u["numerics"], "llm": u["llm"],
            "frozen_top1": fz.get("top1"), "frozen_selected": fz.get("selected_by_rule"),
            "agent_plausible": fz.get("agent_concluded_plausible"),
            "heldout_top1": top1, "heldout_frozen": ho,
        })
    res = {"rows": rows, "best_overall_aicc": best_overall, "sensitivity_best_overall_aicc": sens_overall,
           "note": "All arms share the protocol, development data, validator and fitter (same deterministic multistart). "
                   "Candidates outside the declared enumeration spaces enlarge the model space; compare best_in_space_aicc "
                   "with the enumeration arm to separate discovery within the space from expansion of the space. "
                   "'Sensitivity' scores every fit by the lowest NLL any start reached, applied identically to all arms "
                   "and all space members; it exposes fits where unconverged starts replicated a better optimum than the "
                   "one the protocol reports."}
    version = ("pre-registered (first) final evaluation of each run" if which == "first" else
               "final evaluation with the current evaluator code (runs frozen under earlier code are re-scored; "
               "their frozen candidates are unchanged)")
    L = ["# Arm comparison: Liao Fig. 50b (development) and Fig. 50a (held out)", "",
         f"Held-out results: {version}.",
         "", res["note"], "",
         "## Development data (Fig. 50b, MoS2)", "",
         ("| run | arm | candidates | statuses | best (AICc) | in declared space? | best in-space | best out-of-space | "
         "unreliable fits | sensitivity best | fits run / reused | fit CPU s | LLM tokens in/out (cache read/write) | "
         "LLM cost, list USD | LLM wall s |"), "|" + "---|" * 15]
    for x in rows:
        llm = x["llm"] or {}
        tok = (f"{llm.get('input_tokens', '-')}/{llm.get('output_tokens', '-')} "
               f"({llm.get('cache_read_tokens', '-')}/{llm.get('cache_write_tokens', '-')})") if llm else "-"
        L.append(f"| {x['run_id']} | {x['arm']} | {x['candidates']} | {x['status_counts']} | {x['best_name']} "
                 f"({_fmt(x['best_aicc'], 5)}) | {x['best_in_declared_space']} | {_fmt(x['best_in_space_aicc'], 5)} | "
                 f"{_fmt(x['best_outside_space_aicc'], 5)} | {x['dev_fits_numerically_unreliable']} | "
                 f"{_fmt((x['sensitivity_best'] or {}).get('aicc'), 5)} | "
                 f"{x['numerics']['fits_committed_by_this_run']} / {x['numerics']['fits_reused']} | "
                 f"{_fmt(x['numerics']['fit_cpu_s'])} | {tok} | {_fmt(llm.get('cost_usd'))} | {_fmt(llm.get('wall_s'))} |")
    L += ["", "## Held-out run (Fig. 50a): frozen candidates refit with the same protocol", "",
          ("Structure transfer: parameters are refit on the held-out run (different catalyst). Ranks are among one shared "
          f"reference set: every member of every declared enumeration space ({len(reference)} fits, pre-declared and "
          "post-hoc) fitted to the same held-out data."), "",
          ("| run | candidate | role | protocol AICc | protocol rank | numerically unreliable | sensitivity AICc | "
          "sensitivity rank | adequacy | RMSE |"), "|" + "---|" * 10]
    for x in rows:
        for h in x["heldout_frozen"]:
            role = "+".join(t for t, on in (("selected", h["selected_by_rule"]), ("agent-plausible", h["agent_concluded_plausible"])) if on)
            L.append(f"| {x['run_id']} | {h['candidate_id']} | {role} | {_fmt(h.get('aicc'), 5)} | "
                     f"{h.get('rank_among_space')}/{h.get('n_space')} | {h['numerically_unreliable']} | "
                     f"{_fmt(h['sensitivity_aicc'], 5)} | {h['sensitivity_rank']}/{h['n_space_fitted']} | "
                     f"{h.get('adequacy')} | { {k: round(v, 2) for k, v in (h.get('rmse') or {}).items()} } |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    (out.with_suffix(".json")).write_text(json.dumps(res, indent=1, default=str) + "\n")
    return {"report": str(out), **res}
