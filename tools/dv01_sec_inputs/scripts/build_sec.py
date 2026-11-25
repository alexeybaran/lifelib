"""Export and compile one SEC product: python build_sec.py PRODUCT_DIR NAME OUT"""
import shutil, subprocess, sys
from pathlib import Path
product, name, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
import modelx as mx
m = mx.read_model(product / name)
try:
    m.export(out / f'{name}_nomx')
finally:
    m.close()
for f in [*product.glob('*.csv'), product / 'sample_sec.py', product / 'spec_sec.py']:
    shutil.copyfile(f, out / f.name)
sys.setrecursionlimit(20000)
r = subprocess.run([sys.executable, '-m', 'modelx_cython', f'{name}_nomx', '--sample', 'sample_sec.py', '--spec', 'spec_sec.py'],
                   cwd=out, capture_output=True, text=True)
(out / 'compile.log').write_text(r.stdout + r.stderr)
print(name, 'exit', r.returncode)
