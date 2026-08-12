from pathlib import Path

from scripts.run_release_gate import (
    _find_new_summary,
    _find_summary_files,
)

import pytest




def test_find_new_summary(
    tmp_path: Path,
):
    reports_root = (
        tmp_path
        / "evaluation"
    )

    old_dir = (
        reports_root
        / "old"
    )

    old_dir.mkdir(
        parents=True
    )

    old_summary = (
        old_dir
        / "summary.json"
    )

    old_summary.write_text(
        "{}",
        encoding="utf-8",
    )

    before = _find_summary_files(
        reports_root
    )

    new_dir = (
        reports_root
        / "new"
    )

    new_dir.mkdir()

    new_summary = (
        new_dir
        / "summary.json"
    )

    new_summary.write_text(
        "{}",
        encoding="utf-8",
    )

    found = _find_new_summary(
        reports_root=reports_root,
        before=before,
        evaluation_started_at=0.0,
    )

    assert (
        found
        == new_summary.resolve()
    )



def test_missing_new_summary_raises(
    tmp_path: Path,
):
    reports_root = (
        tmp_path
        / "evaluation"
    )

    reports_root.mkdir()

    before = _find_summary_files(
        reports_root
    )

    with pytest.raises(
        RuntimeError,
    ):
        _find_new_summary(
            reports_root=reports_root,
            before=before,
            evaluation_started_at=(
                99999999999.0
            ),
        )



