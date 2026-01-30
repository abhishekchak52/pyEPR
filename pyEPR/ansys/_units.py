"""
Unit and expression helpers for pyEPR Ansys interface (pyaedt path).
"""

from collections.abc import Iterable
from numbers import Number

from sympy.parsing import sympy_parser

try:
    from pint import UnitRegistry
    ureg = UnitRegistry()
    Q = ureg.Quantity
except (ImportError, ModuleNotFoundError):
    ureg = None
    Q = None

BASIS_ORDER = {"Zero Order": 0, "First Order": 1, "Second Order": 2, "Mixed Order": -1}
LENGTH_UNIT = "meter"
LENGTH_UNIT_ASSUMED = "mm"


def simplify_arith_expr(expr):
    try:
        return repr(sympy_parser.parse_expr(str(expr)))
    except Exception:
        print("Couldn't parse", expr)
        raise


def increment_name(base, existing):
    if base not in existing:
        return base
    n = 1
    def make_name():
        return base + str(n)
    while make_name() in existing:
        n += 1
    return make_name()


def extract_value_unit(expr, units):
    try:
        return Q(expr).to(units).magnitude
    except Exception:
        try:
            return float(expr)
        except Exception:
            return expr


def extract_value_dim(expr):
    return str(Q(expr).dimensionality)


def parse_entry(entry, convert_to_unit=LENGTH_UNIT):
    if not isinstance(entry, (list, tuple)):
        return extract_value_unit(entry, convert_to_unit)
    return [parse_entry(e, convert_to_unit=convert_to_unit) for e in entry]


def fix_units(x, unit_assumed=None):
    unit_assumed = LENGTH_UNIT_ASSUMED if unit_assumed is None else unit_assumed
    if isinstance(x, str):
        if x and (x[-1].isdigit() or x[-1] == "."):
            return x + unit_assumed
        return x
    if isinstance(x, Number):
        return fix_units(str(x) + unit_assumed, unit_assumed=unit_assumed)
    if isinstance(x, Iterable):
        return [fix_units(y, unit_assumed=unit_assumed) for y in x]
    return x


def parse_units(x):
    return parse_entry(fix_units(x))


def unparse_units(x):
    return parse_entry(fix_units(x, unit_assumed=LENGTH_UNIT), LENGTH_UNIT_ASSUMED)


def parse_units_user(x):
    return parse_entry(fix_units(x, LENGTH_UNIT_ASSUMED), LENGTH_UNIT_ASSUMED)


class VariableString(str):
    def __add__(self, other):
        return var("(%s) + (%s)" % (self, other))
    def __radd__(self, other):
        return var("(%s) + (%s)" % (other, self))
    def __sub__(self, other):
        return var("(%s) - (%s)" % (self, other))
    def __rsub__(self, other):
        return var("(%s) - (%s)" % (other, self))
    def __mul__(self, other):
        return var("(%s) * (%s)" % (self, other))
    def __rmul__(self, other):
        return var("(%s) * (%s)" % (other, self))
    def __truediv__(self, other):
        return var("(%s) / (%s)" % (self, other))
    def __rtruediv__(self, other):
        return var("(%s) / (%s)" % (other, self))
    def __pow__(self, other):
        return var("(%s) ^ (%s)" % (self, other))
    def __rpow__(self, other):
        return var("(%s) ^ (%s)" % (other, self))
    def __neg__(self):
        return var("-(%s)" % self)
    def __abs__(self):
        return var("abs(%s)" % self)


def var(x):
    if isinstance(x, str):
        return VariableString(simplify_arith_expr(x))
    return x
