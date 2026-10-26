"""Explicit compatible units. No density or passenger-occupancy guesses."""

import math

_UNITS = {}
for dimension, scale, names in [
    ("energy", 1, ["kwh", "kilowatt-hour", "kilowatt-hours"]),
    ("energy", 1000, ["mwh", "megawatt-hour", "megawatt-hours"]),
    ("energy", 0.001, ["wh"]),
    ("litre", 1, ["litre", "litres", "liter", "liters", "l"]),
    ("litre", 0.001, ["ml", "millilitre", "millilitres"]),
    ("m3", 1, ["m3", "m³", "cubicmetre", "cubicmeter", "cubicmetres"]),
    ("mass", 1, ["kg", "kilogram", "kilograms"]),
    ("mass", 1000, ["tonne", "tonnes", "metricton", "t"]),
    ("mass", 0.001, ["g", "gram", "grams"]),
    ("freight", 1, ["tonne-km", "tonnekm", "tkm"]),
    ("passenger", 1, ["passenger-km", "passengerkm", "pkm"]),
]:
    for name in names:
        _UNITS[name] = (dimension, scale)


def normalize_quantity(quantity, source_unit, target_unit):
    if isinstance(quantity, bool):
        raise ValueError("Quantity must be a finite nonnegative number")
    value = float(quantity)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Quantity must be a finite nonnegative number")

    def lookup(unit):
        key = unit.strip().lower().replace(" ", "")
        if key not in _UNITS:
            raise ValueError(
                f"Unsupported unit: {unit!r}; supply an explicit compatible unit"
            )
        return _UNITS[key]

    source, source_scale = lookup(source_unit)
    target, target_scale = lookup(target_unit)
    if source != target:
        raise ValueError(f"Incompatible units: {source_unit!r} -> {target_unit!r}")
    result = value * source_scale / target_scale
    if not math.isfinite(result):
        raise ValueError("Normalized quantity overflowed")
    return result
