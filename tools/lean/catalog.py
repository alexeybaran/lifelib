"""The 57 regional ``*_S`` models: library, product folder and model name."""

import pathlib

LIBRARIES = ("uslib", "uklib", "delib", "frlib", "jplib", "krlib")


def discover(root):
    """[(lib, product, model)] for every ``*_S`` model folder under ``root``'s products."""
    root = pathlib.Path(root)
    out = []
    for lib in LIBRARIES:
        products = root / "lifelib" / "libraries" / lib / "products"
        for model in sorted(products.glob("*/*_S")):
            if (model / "__init__.py").exists():
                out.append((lib, model.parent.name, model.name))
    return out


def model_dir(root, lib, product, model):
    return pathlib.Path(root) / "lifelib" / "libraries" / lib / "products" / product / model


def product_dir(root, lib, product):
    return pathlib.Path(root) / "lifelib" / "libraries" / lib / "products" / product
