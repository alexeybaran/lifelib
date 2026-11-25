"""Shared paths and helpers for the dv01-sec review scripts.

Environment: DV01SEC_ROOT holds the three detached worktrees (modelx-cython, modelx, lifelib)
and a build/ directory; DV01SEC_PY is the free-threaded interpreter.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("DV01SEC_ROOT", Path.cwd()))
PY = os.environ.get("DV01SEC_PY", sys.executable)
COMPILER, RUNTIME, LIFELIB = ROOT / "modelx-cython", ROOT / "modelx", ROOT / "lifelib"
BUILD = ROOT / "build"
PRODUCT = LIFELIB / "lifelib/libraries/uslib/products/fixed_deferred_annuity"
HERE = Path(__file__).resolve().parent
LOCK = Path(os.environ.get("DV01SEC_LOCK", ROOT.parent / "TIMING.lock"))

ENTRY = """
import sys, threading
from pathlib import Path
import modelx_cython
from modelx_cython.cli import entry_point_main
compiler = Path(sys.argv.pop(1)).resolve()
if not Path(modelx_cython.__file__).resolve().is_relative_to(compiler):
    raise RuntimeError(f"Loaded the wrong compiler: {modelx_cython.__file__}")
sys.setrecursionlimit(20_000)
threading.stack_size(268435455)
entry_point_main()
"""


def env(extra=()):
    e = dict(os.environ)
    e["PYTHONPATH"] = os.pathsep.join(map(str, [*extra, COMPILER, RUNTIME, LIFELIB]))
    e["PYTHONHASHSEED"] = "0"
    return e


def wait_for_lock():
    """Another worker measures wall time: do not build while its lock exists."""
    while LOCK.exists():
        time.sleep(60)


def run(args, cwd, log, extra=(), timeout=7200):
    with open(log, "w") as stream:
        r = subprocess.run([PY, "-B", *map(str, args)], cwd=cwd, env=env(extra), stdout=stream,
                           stderr=subprocess.STDOUT, timeout=timeout)
    if r.returncode:
        tail = Path(log).read_text(errors="replace")[-3000:]
        raise RuntimeError(f"{args[:2]} exited {r.returncode}\n{tail}")


def compile_export(folder, package, sample="sample.py", spec="spec.py"):
    wait_for_lock()
    t0 = time.perf_counter()
    run(["-c", ENTRY, COMPILER, package, "--sample", sample, "--spec", spec], folder, folder / "compile.log")
    return time.perf_counter() - t0
