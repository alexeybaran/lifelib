"""Explicit lazy expression helpers; Cython providers never inspect formulas."""


_DOMAIN_MISSING = object()


def periods(start, stop=_DOMAIN_MISSING, step=_DOMAIN_MISSING):
    """A reusable period domain, with range's values and index conversions."""
    if step is not _DOMAIN_MISSING:
        return range(start, stop, step)
    if stop is not _DOMAIN_MISSING:
        return range(start, stop)
    return range(start)


class _Over:
    def __init__(self, source, function, where=None, unpack=None):
        _validate_unpack(unpack)
        self.source = iter(source)
        self.function, self.where = function, where
        self.unpack, self.current = unpack, None
        self.closed = False

    def __iter__(self):
        return self

    def close(self):
        self.closed = True
        self.source = self.function = self.where = self.current = None

    def __next__(self):
        if self.closed:
            raise StopIteration
        while True:
            exhausted = False
            try:
                value = next(self.source)
            except StopIteration:
                exhausted = True
            except BaseException:
                self.close()
                raise
            if exhausted:
                self.close()
                raise StopIteration
            try:
                self.current = value
                if self.unpack is None:
                    if self.where is not None and not self.where(value):
                        continue
                    return self.function(value)
                arguments = _unpack(value, self.unpack)
                if self.where is not None and not self.where(*arguments):
                    continue
                return self.function(*arguments)
            except StopIteration as error:
                self.close()
                raise RuntimeError('generator raised StopIteration') from error
            except BaseException:
                self.close()
                raise


def _validate_unpack(count):
    if count is not None and (type(count) is not int or count < 0):
        raise ValueError('unpack must be None or a nonnegative integer')


def _unpack(value, count):
    # Fixed arities use Python's unpack primitive, including exact errors and
    # bounded consumption. Other explicit arities retain the same N+1 limit.
    if count == 2:
        first, second = value
        return first, second
    if count == 3:
        first, second, third = value
        return first, second, third
    iterator = iter(value)
    result = []
    for position in range(count):
        exhausted = False
        try:
            result.append(next(iterator))
        except StopIteration:
            exhausted = True
        if exhausted:
            raise ValueError(f'not enough values to unpack (expected {count}, got {position})')
    exhausted = False
    try:
        next(iterator)
    except StopIteration:
        exhausted = True
    if not exhausted:
        raise ValueError(f'too many values to unpack (expected {count})')
    return tuple(result)


def over(source, function, where=None, *, unpack=None):
    """Map lazily, optionally filtering inputs before evaluating the payload."""
    return _Over(source, function, where, unpack)


class _Flatten:
    def __init__(self, sources):
        self.outer, self.inner = iter(sources), None
        self.closed = False

    def __iter__(self):
        return self

    def close(self):
        self.closed = True
        self.outer = self.inner = None

    def __next__(self):
        if self.closed:
            raise StopIteration
        while True:
            if self.inner is not None:
                exhausted = False
                try:
                    return next(self.inner)
                except StopIteration:
                    exhausted = True
                except BaseException:
                    self.close()
                    raise
                if exhausted:
                    self.inner = None
            exhausted = False
            try:
                source = next(self.outer)
            except StopIteration:
                exhausted = True
            except BaseException:
                self.close()
                raise
            if exhausted:
                self.close()
                raise StopIteration
            try:
                self.inner = iter(source)
            except StopIteration as error:
                self.close()
                raise RuntimeError('generator raised StopIteration') from error
            except BaseException:
                self.close()
                raise


def flatten(sources):
    """Lazily traverse each inner iterable in one flat, ordered sequence."""
    return _Flatten(sources)


def sum_values(source):
    """Ordinary sum: empty integer zero and Python's numeric transitions."""
    return sum(source)


class _FloatTerms(_Over):
    def __init__(self, source):
        super().__init__(source, _FLOAT)


_NO_CALLBACK = object()


def sum_float(source, function=_NO_CALLBACK, where=None) -> float:
    """Sum lazily float-converted contributions with float-start arithmetic.

    With a callback, this is the shorthand for sum_float(over(source, function,
    where)). It deliberately differs from ordinary mixed-type sum; migration
    must preserve the original source's numeric and empty-result contract.
    """
    if function is not _NO_CALLBACK:
        source = _OVER(source, function, where)
    elif where is not None:
        source = _OVER(source, lambda value: value, where)
    return sum(_FloatTerms(source), 0.0)


# Private original identities survive replacement of public helper bindings.
_FLOAT = float
_PERIODS, _OVER, _FLATTEN = periods, over, flatten
_SUM_VALUES, _SUM_FLOAT = sum_values, sum_float
for _function in (_PERIODS, _OVER, _FLATTEN, _SUM_VALUES, _SUM_FLOAT):
    _function.__modelx_cython_helper__ = ('lifelib._native_streams', _function.__name__)
    _function.__modelx_native_operation__ = _function.__name__
    _function.__modelx_cython_scalar_result__ = 'object'
    _function.__modelx_cython_call_layout__ = 'keywords'
