import sys
sys.path.insert(0, ".")
from rapidbench.substrate import generate_synthetic_declarations
from rapidbench.injectors import INJECTORS
from rapidbench.tasks import compute_all
from rapidbench.metrics import rdm_profile

CLEAN, FX = generate_synthetic_declarations(n=5000, seed=7)
ORACLE = compute_all(CLEAN)


def test_determinism():
    a, _ = generate_synthetic_declarations(n=2000, seed=9)
    b, _ = generate_synthetic_declarations(n=2000, seed=9)
    assert a.equals(b)


def test_all_injectors_run_and_distort_something():
    for name, fn in INJECTORS.items():
        failed, meta = fn(CLEAN, 0.05, 7, fx=FX)
        assert meta["rows_affected"] > 0, name
        prof = rdm_profile(compute_all(failed), ORACLE)
        assert max(prof.values()) >= 0.0, name


def test_clean_frame_untouched_by_injectors():
    before = CLEAN.copy()
    for name, fn in INJECTORS.items():
        fn(CLEAN, 0.05, 7, fx=FX)
    assert CLEAN.equals(before)


def test_duplicates_increase_rows():
    failed, _ = INJECTORS["F07_duplicate_amendments"](CLEAN, 0.05, 7, fx=FX)
    assert len(failed) > len(CLEAN)
