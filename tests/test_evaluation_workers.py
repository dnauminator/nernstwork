"""The evaluation queue must finish after more than one worker lifetime."""
import os
from pathlib import Path
import subprocess
import sys


def test_parallel_evaluation_crosses_worker_recycling_boundary(tmp_path):
    # A separate interpreter gives a real spawn-pool integration check and a
    # bounded timeout if the worker-recycling deadlock is reintroduced.
    script = tmp_path / "pool_check.py"
    script.write_text(
        "from nernstwork.investigation import _batched_process_map\n"
        "if __name__ == '__main__':\n"
        "    values = list(range(-50, 51))\n"
        "    got = list(_batched_process_map(abs, values, 2))\n"
        "    assert got == list(map(abs, values))\n"
    )
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(root / "src"), OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    completed = subprocess.run([sys.executable, str(script)], cwd=root, env=env,
                               capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stdout + completed.stderr
