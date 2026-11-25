# C5: shared held items, the 2.5x gate, and the SEC DV01's dynamic reference

Governing decision (owner, given in the C5 brief, 25 Nov): the SEC DV01 ships only when it scales at least 2.5x at four
workers (final measurement on the owner's 8-core desktop; here an idle 4-core VM); generic mechanisms only, no option one
example switches on; the model's dynamic reference must work as written, through modelx's export. This package adds files
under `c5/` only, so the coordinator records it as a K-row in [`../OPERATIONS.md`](../OPERATIONS.md). Input: [D0](../d0/D0-SEC-DV01.md).

## Pins and deliverables
| Repository | Base | Delivered here |
|---|---|---|
| compiler (fast SEC) | `r4/s2-layer1-trial` 56e01f9 | `compiler/0001` borrowed held items; `0002` fast item construction with dynamic references |
| modelx | upstream main fec516d | `modelx/0001` = development 2097f7b cherry-picked unchanged; `0002` its `{'base': _space}` regression fixed |
| lifelib | upstream main 20d4dae + the DV01 package and `shock_steps.csv` from 04d69db (new files only, as D0 row 5) | none |
| full tree (reference only) | `r4/s1-zeroing` 3bc7be5, modelx df3ced9, lifelib 04d69db | none |

Machine: cloud VM, 4 cores (1 thread per core), 15 GiB, no hardware counters (no PMU: `perf stat` cache misses are not
available; cache behaviour from callgrind's simulation instead). Free-threaded CPython 3.14.6 (GIL off), Cython 3.3.1,
gcc 13. Book 1,050 (25 x D0's 42), 1 ESG path, closes -1/11/23, 13 curves; fresh process per run, warm tables, 1 worker on
core 0, 4 workers on cores 0-3, load below 0.7 before each run. This VM is about 1.6x faster than D0's at one worker and
noisy: 1-worker spread up to 20% between rounds. Pure-Python control (4 threads / 4 processes): 3.6-4.1x / 3.3-3.5x.
Model text `dv01_sec/` = A2's `../../dv01-sec/dv01_sec/` byte for byte (D0's patch reverted). Scripts in `scripts/`
(paths are this session's), result JSON in `results/`.

## 1. Why collect with the seven options was faster at one worker
Callgrind, book 1,050, report minus setup, per policy (`results/attribution-1w.json`): direct 102.6M, collect 90.9M.
| Cause | Ir gap | Measured wall at 1w | Generic recovery |
|---|---:|---|---|
| Flag zeroing of 42 fresh Valuation items per policy (collect resets one reused root) | 8.1M (69%) | all item construction, zeroing and release: 0.27 s for 44,100 items (churn test) | per-class item recycling: ~200 lines inside the free-threaded GC heap; not small or safe |
| The driver's per-offset Python cash-flow reads (gate object, getattr, interpreter) | 0.8M + part of 3.3M | 0.53 s (with against without the reads); 284 ns a call against 45 ns typed | cheaper gate: measured upper bound 0.36 s at 1w, under 0.14 s at 4w; not applied |
| Item construction and release on the Python path | rest of 3.3M, 1.2M | inside the 0.27 s | kept on the fast path for dynamic references (`0002`) |
| Market reads | 0.06M | none | none needed |
| Collect's own machinery and runtime | -2.3M | | |
`rep stosb` zeroing counts one instruction per byte, so the 13% instruction gap overstates the wall gap. Measured here:
direct 7.7 s (attribution driver) or 8.0-8.3 s (pool driver), collect with options 6.7 s: 1.16-1.2x, not D0's 1.29x
(D0's spreads were 9-18%). Page faults at 1 worker: 15-42K, negligible. D0's 2.5 s CPU "memory" gap is not visible at one worker.

## 2. Four workers: the driver, then shared items
**The main finding.** D0's 1.64x is mostly its driver. `list(pool.map(...))` makes the main thread wait on each of 1,050
futures in turn; on free-threaded 3.14 a lock waiter spins with `sched_yield` while attached (gdb: 7 of 8 samples; strace
27K `sched_yield`). An attached thread holds back QSBR, which delays the reuse of every freed mimalloc page, so the
workers' 1.4 MB items land on fresh memory: 1.2 GB peak, 1.5M minor faults, 2.9 s system and twice the worker CPU.
One `concurrent.futures.wait(futures)` (or threads with `join`, or a sleeping main thread) removes it, with the same
results in the same order (`results/driver-4w-variants.json`): layer 1 unchanged goes 6.2 s -> 3.0-3.3 s at 4 workers.
Not the cause: OpenBLAS threads, mimalloc purging (`MIMALLOC_PURGE_DELAY=-1` cuts faults to 0.29M, wall unchanged), a
detach/attach per item (tried in the allocator and in the driver: no effect; dropped). The compiler cannot fix a
driver's wait; CPython's spin-while-attached is the root and belongs upstream. `scripts/pool_run_c5.py` is D0's driver with that one change (`--map` restores D0's).

**Borrowed held items (`compiler/0001`, space_results.py +17/-5).** `_mx_pin_held_item_N` returns the held item's field
as a borrowed `void *` (no `exceptval` check); the call site casts it. Why it is safe, on free-threaded and ordinary builds:
the pin runs only after the guard (receiver exactly the class, flag set, field exactly the target class); the receiver is
the running formula's `self`, alive for the call; a zero-argument cache field of an exclusively owned item is written once,
before its flag, and never again while the item lives (an exported model has no cache clearing; release clears Cells,
roots and `_space`; pickling writes copies); only unlocked producers are pinned (locked ones keep the owned walrus local).
Replacing a shared Space (deleting its items) or dropping the model drops the Space's references only: the holder's field
keeps the item. The borrowed read writes nothing to the shared item, so it no longer bounces its cache line. Effect: shared
reference drops at 4 workers (book 42) 3.84M -> 2.59M; the compiled-module part 2.51M -> 1.22M. What remains is the
driver's Python-level Cell calls (gate object 1.7M Py_DECREF) and Market's own wrappers (`results/decref-4w.json`).
Tests: `test_space_item_results` now asserts no reference is taken across the argument Cell (C source), the held item's
count is unchanged while the argument Cell runs (fails on the old pin: 16 vs 15), and the held item survives losing every
other reference meanwhile; new `test_shared_item_reads`: 4 threads over Policy items holding Market items of a locked
Space, with a fifth thread emptying the Market Space under them and each model instance dropped after its run, equal to
1 thread and the export bit for bit, with no reference leaked. Remaining 4-worker waits (gdb, 47 samples, C5 build): 55%
compiled formulas, about 20% the model lock on Market misses and its release, a few in the shared item dictionary.

## 3. Generic recoveries applied
Applied: borrowed held items (step 2); the dynamic-reference fast construction (`compiler/0002`, transformer.py
+19/-2): the exported `_mx_root._mx_apply_formula(...)` after the walk no longer drops the item to the generic walk; it
is called on the typed root after the parameters, as in the walk. Not applied (table above): item recycling (not small or
safe), a cheaper Python-level gate (at most 4% at 1w, within noise at 4w), a finer Market lock (lock-order deadlock risk).
No option was added; no option key is read.

## 4. The dynamic reference `act`, as written
`modelx/0001` is 2097f7b unchanged (+138/-4, +86 test). Regression: it refused every Space formula whose dict had a key
other than `refs`, so `{'base': _space}`, `{'bases': _space}` and `{'bases': [_space]}`, which upstream exported (it
ignores Space formulas, and the Space itself is the default base), stopped exporting. `modelx/0002` (+28/-2, +60 test)
accepts those three spellings, alone or with `refs`, when `_space` is the global name, and checks the same at run time
(`base is self._parent._space`); any other base, two bases, a rebound or parameter `_space` is still refused at export
(upstream exported those with wrong values). Tests: 12 identity-base cases equal live (8 of them pass on upstream too; the
4 with `refs` fail there), 4 refusal cases; export suite 161 passed, 1 failed as on upstream (`test_assets`, QuantLib not
installed); 3.14t, 3.14 and 3.10. The SEC DV01 exports with `act` per item; the compiler types it as a public object
Reference; values equal live.

## 5. Results (final: compiler `0001`+`0002`, modelx `0001`+`0002`, A2's text, spec without the seven keys)
Book 1,050, wait driver; 5 interleaved rounds, median [range] (`results/timing-final-5rounds.json`):
| Build | Ir/policy | 1w wall s | 4w wall s | scaling | CPU 1w/4w s | RSS 1w/4w MiB | faults 4w |
|---|---:|---:|---:|---:|---:|---:|---:|
| **C5 final** | 102.6M | 8.01 [7.80-9.26] | 3.06 [2.86-3.50] | **2.62** | 8.0 / 10.9 | 267 / 359 | 70K |
| layer 1 (D0 row 1 build) | 102.6M | 8.35 [7.48-9.19] | 3.31 [2.87-3.44] | 2.52 | 8.3 / 11.8 | 267 / 368 | 76K |
| C5 final, D0's `pool.map` driver | | 8.11 | 6.36 | 1.28 | 8.1 / 23.9 | 267 / 1,147 | 1.47M |
| collect + 7 options (full tree, 3 rounds) | 90.9M | 7.00 | 7.34 | 0.95 | 7.0 / 25.1 | 173 / 185 | 30K |
Pooled over every round of this session (10 per cell): C5 2.62x (min/min 2.73), layer 1 2.63x (2.61). So on this VM
the gate is met by the driver change; the borrowed reads cut 4-worker CPU by about 8% and shared reference drops by a
third, but their wall effect is inside the noise with 4 threads. They should matter more with 8 workers on the owner's
desktop; measure there with `scripts/pool_run_c5.py`. Compile: 413 s (export 7 s).
Values (rule rel 1e-10 / abs 1e-7): book 42, 1 and 4 workers, against live modelx running the original text: DV01 and
CS01 bit for bit; live original text equals live D0 text bit for bit; book 1,050: 68 direct-route runs (both builds,
both drivers, 1 and 4 workers) give one total pair. Term_US_SEC 7.4046M / 7.4030M = 1.0002 and MYGA_US_SEC 8.5757M /
8.5754M = 1.0000 instructions per point against the trial (S2's method, 3 runs each; limit 1.005); both equal live (max
abs 0 and 2.8e-14). Layer-1 unit tests 437 passed, 8 skipped (as S2); compiled and integration tests 120 passed,
11 failed: S2's eleven, all building models with development modelx's `new_space(collect_over=...)`; the two new pass.

## Not tested, open
Clang and MSVC builds (gcc only; the change is plain Cython, no compiler-specific C); Windows; macOS; the owner's
8-core desktop; a GIL build of the SEC DV01 itself (the four new or changed compiled tests pass on 3.14 and 3.10 with
the GIL). Open: the model lock taken on Market misses serialises the first fill; the shared item dictionaries of
Valuation and Actual take their critical section on every insert and delete; collect at 4 workers suffers the same
waiting pattern (0.95x here).
