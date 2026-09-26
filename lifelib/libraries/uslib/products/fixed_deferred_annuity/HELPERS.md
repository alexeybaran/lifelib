# MYGA on the helper branch

`MYGA_US_S` is the helper-adjusted model on `development/helpers`. It is updated in
place, not maintained as a second product. The original is available at the
`project-base` commit `76684674a7ef2ca93c53101a68816ef2697f4370`.

The starting formulas and serialized input tables come from the retained
`project_refs/models/adjusted/MYGA_US_S/model` snapshot. Generic lookup functions
now live in `lifelib.helpers`; public category Enums live in
`lifelib.libraries.uslib.myga_enums`. Serialized references were relocated to those
modules, removing the dependency on the prototype's `models.myga` module.

The retained adjustment replaces pandas selection expressions with explicit
helper calls, uses typed categories/timing/claim arguments, and allows
`Projection[policy, scenario]`. Omitting scenario (or passing -1) keeps the policy's
supplied string scenario: base for policy 1, stress for 2–6, differential for 7.
Use `AccountTiming`, `CountTiming`, and `Claim` members for timing/claim arguments;
category cells return their declared Enums. Scenario and withdrawal labels remain
strings. These are the current experimental model interfaces.

Input tables are serialized shared Data references with trivial getter cells,
which permit the compiler to prepare full tables without policy preselection.
They match the adjacent CSVs, as checked by tests. Editing a CSV alone does not
update this snapshot: update the corresponding `Data.*_data` reference and save the
model with the changed inputs. Reports continue to cover `proj_len()` months.

Integration preserves the fork's original actuarial documentation, six public
utility cells omitted by the retained snapshot, and explicit int/float/bool casts
at the original scalar input boundaries. Existing numerical golden tests retain
their values and tolerances; interface assertions now use the category Enums.

Run `python -m pytest lifelib/libraries/uslib/tests/test_fixed_deferred_annuity_us.py
lifelib/libraries/uslib/tests/test_myga_helpers.py` from the repository root.
The second file verifies all seven policies in live/exported Python, table parity,
full-projection cash flows, report structure/dtypes, and scenario/Enum interfaces.

Import verification on native Windows (2026-09-26): **68 tests passed**, using
Python 3.13.5, modelx fork project-base
`4fa720f53776f20c5a07c6d5025f705dc3c9ce0e`, NumPy 2.3.5 and pandas 2.2.3.
No benchmarks or compiled MYGA campaign were run for this import.

Treat this model and the matching modelx-cython helper branch as one experiment.
Pin both commit IDs in any future campaign. Historical timings belong to their
recorded sources; they are not acceptance evidence for this imported fork revision.
