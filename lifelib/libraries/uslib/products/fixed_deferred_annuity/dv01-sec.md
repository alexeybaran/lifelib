# Key-Rate DV01 and CS01 on MYGA_US_SEC

**Status:** Draft, 2026-11-25. `dv01_sec/` values a book of [`MYGA_US_SEC`](model-sec.md)
contracts on stochastic interest-rate paths, at a series of annual closes, on the base curve
and on twelve key-rate curves, and reports the interest-rate sensitivity of the book's
liability by tenor. The contracts, their formulas and their assumption tables are
MYGA_US_SEC's, unchanged; the market is the G2++ generator of
`economic/CashValue_ME_G2PP`. The same model runs in
live modelx and, compiled with modelx-cython, on several threads at once.

> **This is a mechanics demonstration, not a risk measurement.** Every behavioural and
> expense assumption is MYGA_US_SEC's **[std]** standardization (see
> [`product-spec.md`](product-spec.md)), and the G2++ parameters and the input curve are the
> economic library's examples. Replace them with company data before drawing any conclusion
> from the numbers.

## Run it

```bash
python products/fixed_deferred_annuity/run_dv01_sec.py                    # live modelx
python products/fixed_deferred_annuity/run_dv01_sec.py --compiled         # compiled, 1 and 4 workers
python products/fixed_deferred_annuity/run_dv01_sec.py --compiled --build DIR --workers 8
python products/fixed_deferred_annuity/run_dv01_sec.py --compiled --policies 1050
python products/fixed_deferred_annuity/run_dv01_sec.py --compiled --collect     # through collect
```

The first builds the model and prints the two reports of the shipped book, MYGA_US_SEC's
fourteen model points (`model_point_table_sec.csv`), on ESG path 1 for years 0, 1 and 2, with
their totals and the seconds taken: about five minutes and 1.2 GB. `--compiled` builds the
model with modelx-cython into `DIR`, or into a temporary directory, which takes about ten
minutes; a build already in `DIR` is reused when it was made from the same model, compiler,
modelx and interpreter (a stamp in `DIR` records them), and rebuilt otherwise. It then runs the report twice, each time in a
fresh process: on one worker thread, and on `--workers` threads. It prints each run's totals
and seconds and checks that the two reports are equal. `--policies N` replaces the shipped
book by N policies, MYGA_US_SEC's seven new-business points repeated; the timings below are
on that book. `--collect` computes the compiled report through `Valuation.collect` instead of
the pooled driver. `--paths` and `--years` widen the report, and `--json FILE` writes it out.

In Python:

```python
from lifelib.libraries.uslib.products.fixed_deferred_annuity.dv01_sec import build_model, report

model = build_model()
dv01, cs01 = report.live_report(model, num_scenarios=1, annual_steps=2)
model.close()
```

## What the report computes

For each ESG path `s` and year `y`, the close is month `c = 12y - 1`, the last month
completed before year `y` starts (`c = -1` at the valuation date, before any month has
closed). At that close every policy is valued in force:

* its state entering month `c + 1` (account value, Model #805 floor, accumulated premiums
  at the GMIR, interest credited, free-withdrawal allowance, tax basis, declared rate and
  locked MVA yield, and the count in force) is the state its **actual** projection on path
  `s` reached, month by month, on the rates that path's market quoted;
* from then on it is projected again on the **curve** observed on path `s` after close
  `c`: the base curve, or the curve with one key rate bumped. Renewal rates, competitor
  rates for the dynamic lapse, and MVA yields come from that curve's forwards, so a bump
  changes the cash flows as well as their discounting.

The liability is minus the present value of the policy's net cash flows (premiums less
benefits and expenses) after the close, each month's flow discounted to the close on the
same curve. The book's liability is the sum over its policies. For key `k`:

* **DV01** = base liability − liability valued on curve `k`, both projections run on their
  own curve. It is positive when the bump lowers the liability.
* **CS01** = base liability − the base projection's cash flows discounted on curve `k`.
  The cash flows are held at their base values, so CS01 is the discounting effect alone,
  and DV01 − CS01 is the effect of the bump on the cash flows.

Curve `k` adds 1 bp to the annual-effective zero rate at the `k`-th tenor of
`dv01_sec/shock_steps.csv` (12 to 120 months annually, then 180
and 240), falling linearly to zero at the neighbouring tenors and held flat beyond the first
and the last. The CSV may be edited: positive whole months, strictly increasing. Each report
has one row per path and year and one column per tenor.

On the shipped book the totals over the 36 cells are DV01 1,213.007886 and
CS01 1,532.723324.

## The model

`build_model()` assembles six Spaces:

| Space | What it holds |
| --- | --- |
| `Data` | MYGA_US_SEC's Data Space, copied, with `shock_key_months` and `book_projection_end` added. |
| `ESG` | The G2++ generator, copied, with `P_t_T_path(i, j, scen_id)`, one path's zero-coupon price, added. |
| `Market[as_of_month, scen_id, shock]` | One curve: observed after a close, on one path, with one key-rate bump (`-1` for none). Rates before the close are the fixings observed then. |
| `Actual[idx, scen_id]` | One policy on one path from the valuation date, its quotes from the market of each month (`actual.py`). |
| `Valuation[valuation_month, idx, scen_id, shock]` | The same policy restarted after the close, its opening state from `act`, its quotes from one `Market` (`valuation.py`). |
| `Outer` | The book's sums and the annual risk report (`outer.py`). |

Both projections carry every MYGA_US_SEC Projection formula but the three of its
deterministic rate scenario, which the market replaces (`contract.py`). `Valuation`'s
formula gives each item the Reference `act`, the `Actual` item of its policy and path; this
is a dynamic Space Reference, and compiling it needs a modelx that exports such References.
`Market`, `Outer` and the ESG cell come from lifelib's MYGA DV01 example on `MYGA_US_S`.

## The compiled model

`dv01_sec/compiled.py` exports the model with `ESG`, `Market`, `Data` and `Actual` locked, writes a spec of
cache sizes (MYGA_US_SEC's own, from `spec_sec.py`, for both projections),
and compiles it with `dv01_sec/sample.py` as the trace, which runs the report of the shipped
book. Nothing is written into the library tree. The compiled report is computed by
`report.pooled_report`: one task per policy values the policy at every close on every curve,
releasing each item once read, and the results are summed in policy order as `Outer` sums
them, so the totals do not depend on the number of workers.

**Through collect.** `Valuation` declares collect over the book (`model.py`, five lines):
`Valuation.collect(month, scen_id, key)` evaluates every policy at one close and curve on the
compiled collect's worker threads, adds its liability PV and, on the base curve, its cash
flows in policy order, and releases each policy's ItemSpace. `report.collect_report` (21 lines)
makes one such call per close and curve, 39 for the report below, and assembles the frames as
the pooled driver does; the two reports are equal bit for bit. Collect runs its items on
several threads only when every Space they read is locked, which is why `Data` and `Actual`
are locked here. `Actual`'s ItemSpaces stay alive from one close to the next, since every close
reads them; the report deletes them once the path is done.

**The driver.** With more than one worker the main thread submits every task and then waits
once for all of them with `concurrent.futures.wait`, instead of waiting on each result in
turn as `list(pool.map(...))` does. On free-threaded CPython 3.14 a thread waiting on a lock
spins while attached to the interpreter, which holds back the reuse of the memory the workers
free, so with `pool.map` the four workers ran on fresh pages and scaled 1.3x where a single
wait scales 2.5x or more.

Requirements: free-threaded CPython 3.14 (`python3.14t`) for the parallel run, Cython 3.3,
a C compiler, modelx with the export of dynamic Space References and with `Space.set_collect`,
and modelx-cython with the compiled collect. Under a
GIL build the workers take turns and the reports are the same.

## Speed

Compiled, books of the seven new-business points repeated, ESG path 1, years 0 to 2, so 3 × 13
valuations per policy (40,950 on 1,050 policies); each run in a fresh process, on a 4-core cloud
VM, Python 3.14.6 free-threaded, gcc 13:

| Route | Policies | Workers | Seconds | CPU seconds | Peak memory | Per policy | Speed-up |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Outer` Cells, every item kept | 140 | 1 | 3.79 | 3.8 | 5.6 GB | 27 ms, 40 MB | |
| pooled driver | 1,050 | 1 | 9.97 | 9.9 | 0.25 GB | 9.5 ms, 0.24 MB | 1.00 |
| pooled driver | 1,050 | 4 | 3.80 | 13.4 | 0.35 GB | | 2.62 |
| collect | 1,050 | 1 | 9.81 | 9.7 | 1.1 GB | 9.3 ms, 1.07 MB | 1.00 |
| collect | 1,050 | 4 | 3.75 | 12.5 | 1.1 GB | | 2.62 |

Median of five rounds (three for the `Outer` row), routes interleaved, with `Data` and `Actual` locked; the
`Outer` Cells keep all 40,950 Valuation ItemSpaces and the book's `Actual` ItemSpaces, so their book is sized to
this machine's 16 GB (on 140 policies the pooled driver takes 1.48 s and 0.18 GB, collect 1.46 s and 0.32 GB).
Collect sits between the two in memory: it releases each Valuation ItemSpace once its outputs are added, but the
`Actual` ItemSpaces belong to another Space and stay alive across the 39 collects, where the pooled driver deletes
each policy's once that policy is done. It takes the same time as the pooled driver; what it gains is less model
code: the report reads each close's total from one call instead of a per-policy task, a thread pool and its own
sums. Totals: DV01 129,960.616141 and CS01 157,856.970872 in every 1,050-policy run. Live modelx runs the 14-point
book in about 300 s.

## Tests

`tests/test_fixed_deferred_annuity_us_sec_dv01.py` holds the model's shape, the live report
of the shipped book against stored values (rel 1e-10, abs 1e-7), and, where modelx-cython and
a C compiler are installed, the compiled report at 1 and 4 workers against the live one, and
the report through collect equal to the pooled driver's and to the live one.
