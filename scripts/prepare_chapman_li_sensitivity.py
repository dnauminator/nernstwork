#!/usr/bin/env python3
"""Reproducible controlled inputs; never modify the original Chapman datasets."""
import copy
import hashlib
import json
from pathlib import Path

import chapman_to_dataset as converter

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / 'data/derived/chapman_li_sensitivity'
LOW = {700: .28, 725: .30, 750: .36}


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + '\n')


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / '.gitignore').write_text('*\n')
    source = REPO / 'data/digitized_inputs/chapman2023_sifig_s1'
    rows = converter.read_rows(source / 'extracted_phase_fractions.csv')
    meta = json.loads((source / 'meta.json').read_text())
    manifest = {'source_commit': 'd0ce7fad55c34b5b36342f5546d2906d7a89df30', 'sources': {}, 'inputs': {}}
    for p in [source / 'meta.json', source / 'extracted_phase_fractions.csv']:
        manifest['sources'][str(p.relative_to(REPO))] = hashlib.sha256(p.read_bytes()).hexdigest()
    for extraction in ('fig2', 's1'):
        for mode in ('nominal', 'lower'):
            tag = f'{extraction}_{mode}'
            paths = []
            for T in (700, 725, 750):
                original = REPO / f'data/real/chapman2023_fig2_{T}C.json'
                manifest['sources'][str(original.relative_to(REPO))] = hashlib.sha256(original.read_bytes()).hexdigest()
                ds = json.loads(original.read_text())
                if extraction == 's1':
                    clean = converter.build_one(T, rows[T], meta)
                    ds['series'] = clean['series']
                    ds['provenance'].update(figure=f'Supplement Fig. S1, {T} C panel', file='ja3c10916_si_001.pdf (not redistributed)',
                        extraction='Daniel Naumov supplement curve extraction at commit d0ce7fa, resampled with the original converter on identical 0.3–9.5 min times. Source CSV hash in campaign input manifest.',
                        verified_against_figure=False,
                        notes='Same published experiment as Fig. 2, not independent evidence. Extraction has not received an independent full visual verification. Overlapping curves and near-zero fractions remain uncertain.')
                    ds['quality'] = {'flags': ['normalised_fractions', 'extraction_unverified', 'time_origin_uncertain'],
                        'basis_note': 'Ti-bearing crystalline phases normalized using nominal molar masses. Amounts are formula units per mol Ti. This normalization cannot reveal missing crystalline or amorphous Ti. Li-deficient intermediate molar mass is approximate.'}
                if mode == 'lower':
                    ds['conditions']['c0']['Li2CO3'] = LOW[T]
                    ds['conditions']['notes'] = (f'Effective initial Li2CO3 sensitivity, {LOW[T]} mol per mol Ti, inferred approximately from the early measured frame. This is not an independent t=0 assay. Original preparation remains nominal 5:2 anatase:Li2CO3. Initial anatase stays 1.0 to isolate lithium. Heating takes about ten seconds; time zero remains insertion. Original quality notes refer to the nominal preparation.')
                    ds['quality']['flags'].append('effective_initial_lithium_sensitivity')
                # Keep IDs to preserve withholding of source claims tagged with original dataset IDs.
                if tag == 'fig2_nominal':
                    p = original  # byte-identical input preserves the original fit cache keys
                else:
                    p = OUT / 'inputs' / tag / original.name
                    write(p, ds)
                paths.append(str(p.relative_to(REPO)))
            manifest['inputs'][tag] = paths
    cfg = json.loads((REPO / 'configs/investigations/chapman750.json').read_text())
    cfg['investigation_id'] = 'chapman-li-oct22'
    cfg['question'] = ('Retrospective sensitivity of Chapman reaction networks to lower effective starting carbonate. ' + cfg['question'])
    cfg['datasets']['development'] = manifest['inputs']['fig2_lower'][:2]
    cfg['datasets']['final_holdout'] = manifest['inputs']['fig2_lower'][2:]
    cfg['datasets']['partition_policy'] = ('Development uses 700 and 725 C. The proposer does not see 750 C phase observations. The wider research team has inspected earlier 750 C results, so this is retrospective sensitivity. Freeze kinetics before predicting 750 C. Evaluation uses a common reference noise scale across candidates and also reports RMSE; do not use each candidate noise to rank predictive accuracy.')
    cfg['evidence']['conventions'][2] = ('Dataset initial species are anatase 1.0 and effective Li2CO3 0.28 at 700 C, 0.30 at 725 C, mol per mol Ti. Both must be model species. These values are hypotheses inferred from early crystalline fractions, not assayed weighed composition. Original nominal mixture was 5:2. Lithium is not measured directly. Li2CO3 must be observable=false.')
    cfg['agent']['max_cost_usd_per_run'] = 6
    write(REPO / 'configs/investigations/chapman-li-oct22.json', cfg)
    write(OUT / 'input_manifest.json', manifest)
    print(json.dumps({'inputs': manifest['inputs'], 'config': 'configs/investigations/chapman-li-oct22.json'}, indent=2))


if __name__ == '__main__':
    prepare()
