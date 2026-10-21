#!/usr/bin/env python3
"""Forward-citation pass on OpenAlex: who cites the seed papers, and which citing works touch
solid-state synthesis, kinetics / in situ XRD and uncertainty or reaction networks.

Uses only the standard library and the unauthenticated OpenAlex API (no key, no email sent).
Page-number paging is used because cursor paging beyond the first page returned HTTP 401 without a key.

Usage: python scripts/openalex_citation_pass.py [out.json]
Writes the citing works (title, year, DOI, abstract, which seeds they cite) and prints a ranked shortlist.
Results depend on OpenAlex coverage on the day it is run; a hit here is a lead to open, not a finding.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

API = "https://api.openalex.org"
SEEDS = {
    "ARROWS3 (Szymanski 2023)": "10.1038/s41467-023-42329-9",
    "Miura 2021 pairwise": "10.1002/adma.202100312",
    "Chapman/Hu 2023": "10.1021/jacs.3c10916",
    "McDermott 2021 network": "10.1038/s41467-021-23339-x",
    "Bianchini 2020": "10.1038/s41563-020-0688-6",
    "Kamm 2022": "10.1021/jacs.2c05043",
    "Zeng 2024 polymorphs": "10.1126/sciadv.adj5431",
    "A-Lab 2023": "10.1038/s41586-023-06734-w",
    "Gao 2022 CuPd NO3RR": "10.1038/s41467-022-29926-w",
    "Rosser 2024 NRR ML": "10.1039/d3dd00151b",
    "Precursor Genome 2026": "10.48550/arxiv.2607.09903",
}
FIELDS = "id,title,publication_year,doi,cited_by_count,abstract_inverted_index,primary_location,type"
TOPICS = {
    "synth": r"solid[- ]state (synthesis|reaction)|precursor|ceramic|inorganic (materials )?synthesis|solid-state|calcin|sinter",
    "kin": r"kinetic|in[- ]situ|time[- ]resolved|avrami|rate constant|operando|nucleation",
    "bayes": r"bayesian|uncertaint|posterior|identifiab|likelihood|mcmc|probabilistic|information gain|experimental design|design of experiments|active learning",
    "net": r"reaction network|reaction pathway|pathways?|intermediate|pairwise|reaction mechanism",
    "xrd": r"x-ray diffraction|\bxrd\b|phase fraction|rietveld|diffraction",
    "no3": r"nitrate|\bno3|nitrite|ammonia",
}


def get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nernstwork-lit-pass"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # network or HTTP error: retry, then give up on this page
            if attempt == 3:
                print("FAIL", url[:110], e, file=sys.stderr)
                return None
            time.sleep(2 * (attempt + 1))


def abstract(inv):
    if not inv:
        return ""
    pos = {p: w for w, ps in inv.items() for p in ps}
    return " ".join(pos[i] for i in sorted(pos))


def collect(max_pages=8):
    works, seed_meta = {}, {}
    for name, doi in SEEDS.items():
        w = get(f"{API}/works/doi:{urllib.parse.quote(doi)}?select=id,title,cited_by_count")
        if not w:
            seed_meta[name] = None
            continue
        sid = w["id"].rsplit("/", 1)[-1]
        seed_meta[name] = {"id": sid, "title": w["title"], "cited_by_count": w["cited_by_count"]}
        fetched = 0
        for page in range(1, max_pages + 1):
            d = get(f"{API}/works?filter=cites:{sid}&per-page=200&page={page}&select={FIELDS}")
            if not d or not d["results"]:
                break
            for x in d["results"]:
                wid = x["id"].rsplit("/", 1)[-1]
                if wid not in works:
                    loc = (x.get("primary_location") or {}).get("source") or {}
                    works[wid] = {"id": wid, "title": x["title"], "year": x["publication_year"], "doi": x["doi"],
                                  "venue": loc.get("display_name"), "cited_by": x["cited_by_count"], "type": x["type"],
                                  "abstract": abstract(x.get("abstract_inverted_index")), "seeds": []}
                if name not in works[wid]["seeds"]:
                    works[wid]["seeds"].append(name)
            fetched += len(d["results"])
        print(f"{name}: {seed_meta[name]['cited_by_count']} citing works listed, fetched {fetched}", flush=True)
    return works, seed_meta


def tag(w):
    text = ((w["title"] or "") + " " + (w["abstract"] or "")).lower()
    return {k for k, p in TOPICS.items() if re.search(p, text)}


def show(title, sel, n=20):
    sel = sorted(sel, key=lambda w: (-len(w["tags"]), -len(w["seeds"]), -(w["cited_by"] or 0)))
    print(f"\n### {title}: {len(sel)} matches, top {n}")
    for w in sel[:n]:
        print(f"- {w['year']} | {(w['title'] or '')[:100]} | {(w['venue'] or '')[:28]} | "
              f"{','.join(sorted(w['tags']))} | {len(w['seeds'])} seeds | {w['doi'] or w['id']}")


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "openalex_citing_works.json")
    works, seeds = collect()
    for w in works.values():
        w["tags"] = tag(w)
    out.write_text(json.dumps({"seeds": seeds, "works": [{**w, "tags": sorted(w["tags"])} for w in works.values()]}))
    rows = list(works.values())
    print("unique citing works:", len(rows))
    show("synthesis + kinetics/in situ + (uncertainty or network)",
         [w for w in rows if {"synth", "kin"} <= w["tags"] and {"bayes", "net"} & w["tags"]])
    show("strict: synthesis + kinetics + uncertainty + XRD",
         [w for w in rows if {"synth", "kin", "bayes", "xrd"} <= w["tags"]], 15)


if __name__ == "__main__":
    main()
