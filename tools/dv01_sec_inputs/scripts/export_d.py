"""Export the SEC DV01 (dv01_sec) for compilation, as the handover's driver exports the comparator:
ESG and Market locked, the shipped CSVs beside it (the sample runs on MYGA_US_SEC's shipped
14-point table), sample_sec_dv01.py as the trace, and a spec of the comparator's Market/ESG/Outer
sizes with MYGA_US_SEC's own Projection sizes (spec_sec.py) for Actual and Valuation.

    python export_sec.py OUT_DIR ROUTE
"""
import ast
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.setrecursionlimit(20000)

import importlib, os  # noqa: E402
build_model = importlib.import_module(os.environ.get('DV01_PKG', 'dv01_sec')).build_model
from lifelib.libraries.uslib.products.fixed_deferred_annuity.dv01.native_spec import native_spec  # noqa: E402


def spec_for(model, product):
    spec = native_spec(model)          # the comparator's sizes for ESG, Market, Outer, Valuation options
    if os.environ.get('DV01_OPTIONS', '1') == '0':   # the seven DV01-only options off, ranges unchanged
        for k in [k for k in spec['spaces']['Valuation'] if k.startswith('factory_collect_')]:
            spec['spaces']['Valuation'].pop(k)
        spec['spaces']['Market'].pop('native_locked_result_calls')
        spec['spaces']['Market']['cells'].pop('shock_weight')
    sec = ast.literal_eval((product / 'spec_sec.py').read_text())['spaces']['Projection']['cells_param_size']
    t = sec['t']
    spec['spaces']['Actual']['cells_param_size'] = dict(sec)
    valuation = spec['spaces']['Valuation']
    valuation['cells_param_size'] = {**sec, 'k': (-1, t), 'month': valuation['cells_param_size']['month']}
    return spec


def main(out, route):
    out.mkdir(parents=True, exist_ok=True)
    model = build_model(route=route)
    try:
        product = Path(model.path).parent
        for table in product.glob('*.csv'):
            shutil.copyfile(table, out / table.name)
        model.export(out / 'model', locked_spaces=['ESG', 'Market'])
        (out / 'spec.py').write_text(repr(spec_for(model, product)) + '\n', encoding='utf-8')
    finally:
        model.close()
    shutil.copyfile(HERE / 'sample_sec_dv01.py', out / 'sample.py')


if __name__ == '__main__':
    main(Path(sys.argv[1]), sys.argv[2])
