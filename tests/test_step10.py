import subprocess
import sys

import pandas as pd

from framebudget.experiment import Setup, cells
from scripts.step9_run_experiments import run_cell


def test_analysis_runs_end_to_end(tmp_path):
    rows = [run_cell(Setup(), c) for c in cells(["rules", "blocking", "async", "prefetch"],
                                                 [33.0, 250.0], ["weak", "strong"], 2)]
    pd.DataFrame(rows).to_csv(tmp_path / "d.csv", index=False)
    subprocess.run([sys.executable, "-m", "scripts.step10_analyze", "--dataset", str(tmp_path / "d.csv"),
                    "--consistency", str(tmp_path / "none.csv"), "--out", str(tmp_path / "o")], check=True,
                   capture_output=True)
    table = (tmp_path / "o" / "main_table.md").read_text()
    assert "prefetch" in table and (tmp_path / "o" / "main_table.tex").exists()
    assert (tmp_path / "o" / "fig_deadline.png").exists()
