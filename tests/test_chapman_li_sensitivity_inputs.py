"""Guard the experimental contrast and evidence boundary, not converter internals."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

from nernstwork import schemas

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import prepare_chapman_li_sensitivity as prepare


def test_factorial_inputs_preserve_observations_and_nominal_cache(tmp_path, monkeypatch):
    sources = [f'data/real/chapman2023_fig2_{T}C.json' for T in (700, 725, 750)]
    sources += ['data/digitized_inputs/chapman2023_sifig_s1/meta.json',
                'data/digitized_inputs/chapman2023_sifig_s1/extracted_phase_fractions.csv',
                'configs/investigations/chapman750.json']
    before = {p: (REPO / p).read_bytes() for p in sources}
    for p in sources:
        target = tmp_path / p
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / p, target)
    monkeypatch.setattr(prepare, 'REPO', tmp_path)
    monkeypatch.setattr(prepare, 'OUT', tmp_path / 'data/derived/chapman_li_sensitivity')
    prepare.prepare()
    manifest = json.loads((prepare.OUT / 'input_manifest.json').read_text())
    for extraction in ('fig2', 's1'):
        for i, (T, amount) in enumerate(((700, .28), (725, .30), (750, .36))):
            nominal = json.loads((tmp_path / manifest['inputs'][f'{extraction}_nominal'][i]).read_text())
            lower = json.loads((tmp_path / manifest['inputs'][f'{extraction}_lower'][i]).read_text())
            assert lower['series'] == nominal['series']
            assert lower['id'] == nominal['id'] == f'chapman2023_fig2_{T}C'
            assert lower['conditions']['c0'] == {'anatase': 1., 'Li2CO3': amount}
            assert nominal['conditions']['c0'] == {'anatase': 1., 'Li2CO3': .4}
            assert not schemas.errors('dataset', lower)
            assert not schemas.errors('dataset', nominal)
            assert min(lower['series'][0]['t_min']) == .3
    for p, old_bytes in before.items():
        assert (tmp_path / p).read_bytes() == old_bytes
        if p in manifest['sources']:
            assert manifest['sources'][p] == hashlib.sha256(old_bytes).hexdigest()
    cfg = json.loads((tmp_path / 'configs/investigations/chapman-li-oct22.json').read_text())
    assert cfg['datasets']['development'] == manifest['inputs']['fig2_lower'][:2]
    assert cfg['datasets']['final_holdout'] == manifest['inputs']['fig2_lower'][2:]
    # Existing source-claim withholding matches on these unchanged dataset IDs.
    assert all('750C' not in p for p in cfg['datasets']['development'])
