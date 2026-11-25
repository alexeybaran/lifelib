"""One input book for both arms: the shipped CSVs with N copies of the seven MYGA policies, as the
handover's measure.prepare builds it (point_id 1..7N), in both spellings: model_point_table.csv for
the comparator (MYGA_US_S rows) and model_point_table_sec.csv for the SEC DV01 (the twins, rows 1..7
of MYGA_US_SEC's table, issued at the valuation date).

    python make_book.py PRODUCT_DIR OUT_DIR POLICIES
"""
import shutil
import sys
from pathlib import Path

import pandas as pd


def main(product, out, policies):
    out.mkdir(parents=True, exist_ok=True)
    for csv in product.glob('*.csv'):
        shutil.copyfile(csv, out / csv.name)
    for name, rows in (('model_point_table.csv', None), ('model_point_table_sec.csv', 7)):
        table = pd.read_csv(product / name)
        if rows:
            table = table.iloc[:rows]
            assert (table['duration_mth'] == 0).all() and (table['row_kind'] == 'twin').all()
        assert len(table) == 7
        block = pd.concat([table] * ((policies + 6) // 7), ignore_index=True).iloc[:policies]
        block['point_id'] = range(1, len(block) + 1)
        block.to_csv(out / name, index=False)


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]))
