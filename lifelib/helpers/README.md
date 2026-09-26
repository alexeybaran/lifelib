# Experimental model helpers

This helper-branch implementation owns the current author-facing lookup interface
used by MYGA. `lifelib.helpers.lookup` supplies ordinary pandas lookups for live
modelx and exported Python; `lifelib.helpers.lookups` supplies prepared curves and
real-valued `power`. Install the `helpers` extra to include their dependencies.

Functions and their argument conventions are retained from the latest minimal
helper control (`project_refs/min_helpers/support/mxcf_kernel` in the project
archive). This package does not contain the prototype compiler or its decorators.
The new namespace expresses lifelib ownership; it does not change lookup behavior.
The Cython import in `lookups.py` provides pure-Python decorators as well as native
declarations and is required even when running this retained implementation live.

Use the matching `development/helpers` branch of alexeybaran/modelx-cython with
`{'experimental_helpers': True}` in the compiler spec. Native preparation snapshots
whole tables. Replace table references instead of mutating prepared data in place;
normal modelx/export cache rules still apply. Unsupported compiler lookup shapes
keep their ordinary Python call path.

This is an experimental starting implementation, not a promotion or performance
claim. Modelx itself does not need a change for these helpers.
