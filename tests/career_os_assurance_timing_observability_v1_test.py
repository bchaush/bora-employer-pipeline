"""Regression tests for CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1 (Phase H,
Recommendation A).

Verifies scripts/verify_assurance_baseline.py's new diagnostic-only timing
instrumentation without executing the full canonical Assurance suite:

  - each invoked phase (0/1/2/3) emits exactly one standardized
    PHASE_TIMING record, including a phase that fails;
  - each Phase 2 test actually executed emits exactly one standardized
    TEST_TIMING record, including a failed test;
  - short-circuit behavior after the first failed phase is unchanged
    (later phases are never called and never emit timing);
  - the exact canonical terminal success string is emitted byte-for-byte,
    only after all four phases succeed, and only once.

Timing is exercised with a fake, fully controlled monotonic clock rather
than real machine-dependent runtimes, so results are deterministic.
"""

from __future__ import annotations

import contextlib
import io
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import verify_assurance_baseline as vab  # noqa: E402


class _FakeClock:
    """Deterministic stand-in for time.perf_counter: returns 0, 1, 2, 3, ..."""

    def __init__(self) -> None:
        self._next = 0.0

    def __call__(self) -> float:
        value = self._next
        self._next += 1.0
        return value


@contextlib.contextmanager
def _fake_perf_counter():
    original = time.perf_counter
    time.perf_counter = _FakeClock()
    try:
        yield
    finally:
        time.perf_counter = original


@contextlib.contextmanager
def _patched(obj, name, value):
    original = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, original)


# ---------------------------------------------------------------------------
# 1. Stable machine-readable grammar for phase-duration and per-test records.
# ---------------------------------------------------------------------------
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    vab._emit_phase_timing(2, 0.5)
    vab._emit_test_timing("some_test.py", 1.25)
lines = buf.getvalue().splitlines()
assert lines[0] == "PHASE_TIMING phase=2 seconds=0.500000", lines[0]
assert lines[1] == "TEST_TIMING test=some_test.py seconds=1.250000", lines[1]

# ---------------------------------------------------------------------------
# 2. _run_phase_with_timing emits one PHASE_TIMING record per invocation,
#    using monotonic (fake) timing, for both a passing and a failing phase,
#    and always returns exactly what the phase function returned.
# ---------------------------------------------------------------------------
with _fake_perf_counter():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ok = vab._run_phase_with_timing(7, lambda: True)
    assert ok is True
    out = buf.getvalue()
    assert "PHASE_TIMING phase=7 seconds=1.000000" in out, out

with _fake_perf_counter():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ok = vab._run_phase_with_timing(9, lambda: False)
    assert ok is False
    out = buf.getvalue()
    assert "PHASE_TIMING phase=9 seconds=1.000000" in out, (
        "a failing phase must still emit its diagnostic phase-duration record"
    )

# ---------------------------------------------------------------------------
# 3. main(): short-circuit after first failed phase is unchanged -- later
#    phases neither run nor emit timing -- and the exact canonical terminal
#    success string is never printed on a failing run.
# ---------------------------------------------------------------------------
calls: list[str] = []


def _stub(name: str, result: bool):
    def _fn() -> bool:
        calls.append(name)
        return result
    return _fn


with _fake_perf_counter(), \
     _patched(vab, "phase_0_state_validation", _stub("phase_0", False)), \
     _patched(vab, "phase_1_compile", _stub("phase_1", True)), \
     _patched(vab, "phase_2_tests", _stub("phase_2", True)), \
     _patched(vab, "phase_3_job_analysis_golden", _stub("phase_3", True)):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = vab.main()
    out = buf.getvalue()

assert code == 1
assert calls == ["phase_0"], f"later phases must not run after phase 0 fails, got {calls}"
assert out.count("PHASE_TIMING phase=0 seconds=1.000000") == 1
assert out.count("PHASE_TIMING phase=1") == 0
assert out.count("PHASE_TIMING phase=2") == 0
assert out.count("PHASE_TIMING phase=3") == 0
assert "ALL PHASES PASSED: canonical assurance baseline verified." not in out

# ---------------------------------------------------------------------------
# 4. main(): when all four phases succeed, every phase emits its timing
#    record (diagnostic-only, ordered), and the exact canonical terminal
#    success string is emitted byte-for-byte exactly once, after all
#    timing output.
# ---------------------------------------------------------------------------
calls = []
with _fake_perf_counter(), \
     _patched(vab, "phase_0_state_validation", _stub("phase_0", True)), \
     _patched(vab, "phase_1_compile", _stub("phase_1", True)), \
     _patched(vab, "phase_2_tests", _stub("phase_2", True)), \
     _patched(vab, "phase_3_job_analysis_golden", _stub("phase_3", True)):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = vab.main()
    out = buf.getvalue()

assert code == 0
assert calls == ["phase_0", "phase_1", "phase_2", "phase_3"]
for phase in (0, 1, 2, 3):
    assert out.count(f"PHASE_TIMING phase={phase} seconds=1.000000") == 1, (
        f"phase {phase} must emit exactly one timing record"
    )
assert out.count("ALL PHASES PASSED: canonical assurance baseline verified.") == 1
success_index = out.index("ALL PHASES PASSED: canonical assurance baseline verified.")
last_timing_index = out.rindex("PHASE_TIMING phase=3")
assert success_index > last_timing_index, (
    "terminal success string must be emitted only after all phase timing output"
)

# ---------------------------------------------------------------------------
# 5. phase_2_tests(): each actually-executed test emits exactly one
#    TEST_TIMING record, including a failing test, without needing to run
#    the real repository test suite. Discovery and the mandatory-anchor
#    fail-closed check are exercised with a fully controlled fake set that
#    includes all nine real anchors plus one extra test that fails.
# ---------------------------------------------------------------------------
fake_names = list(vab.MANDATORY_PHASE_2_ANCHORS) + ["zzz_extra_test.py"]
fake_paths = [vab.TESTS_DIR / name for name in fake_names]


def _fake_run(cmd, *, label):
    name = Path(cmd[-1]).name
    if name == "zzz_extra_test.py":
        return False, "boom"
    return True, ""


with _fake_perf_counter(), \
     _patched(vab, "_discover_tests", lambda: fake_paths), \
     _patched(vab, "_run", _fake_run):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = vab.phase_2_tests()
    out = buf.getvalue()

assert result is False, "Phase 2 must still fail when a discovered test fails"
for name in fake_names:
    expected = f"TEST_TIMING test={name} seconds=1.000000"
    assert out.count(expected) == 1, (
        f"{name} must emit exactly one timing record from the fake monotonic clock"
    )
assert "TEST_TIMING test=zzz_extra_test.py seconds=" in out
assert out.count("TEST_TIMING") == len(fake_names), (
    "exactly one TEST_TIMING record per actually-executed test, no more, no less"
)

print("PASS: Career OS Phase H assurance timing observability verified.")
