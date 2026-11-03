"""Engineering unit normalization and conversion for the Aegis Knowledge System.

Handles standardization of engineering units, parsing raw value-unit text strings,
and converting compatible physical units.
"""

import logging
import re
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Canonical unit mapping for hydraulic, mechanical, electrical, and thermal parameters
_UNIT_ALIASES: Dict[str, str] = {
    # Pressure
    "psi": "PSI",
    "p.s.i.": "PSI",
    "lb/in²": "PSI",
    "lb/in2": "PSI",
    "psig": "PSIG",
    "psia": "PSIA",
    "bar": "bar",
    "barg": "barg",
    "kpa": "kPa",
    "mpa": "MPa",
    "pa": "Pa",
    # Temperature
    "°c": "°C",
    "deg c": "°C",
    "degc": "°C",
    "degrees c": "°C",
    "degrees celsius": "°C",
    "c": "°C",
    "℃": "°C",
    "°f": "°F",
    "deg f": "°F",
    "degf": "°F",
    "degrees f": "°F",
    "degrees fahrenheit": "°F",
    "f": "°F",
    "℉": "°F",
    "k": "K",
    "kelvin": "K",
    # Flow Rate
    "gpm": "GPM",
    "gal/min": "GPM",
    "gallons per minute": "GPM",
    "gallons/min": "GPM",
    "l/min": "L/min",
    "lpm": "L/min",
    "litres per minute": "L/min",
    "liters per minute": "L/min",
    "l/s": "L/s",
    "m3/h": "m³/h",
    "m³/h": "m³/h",
    # Rotational speed
    "rpm": "RPM",
    "rev/min": "RPM",
    "revolutions per minute": "RPM",
    # Electrical
    "v": "V",
    "volt": "V",
    "volts": "V",
    "vdc": "VDC",
    "v dc": "VDC",
    "vac": "VAC",
    "v ac": "VAC",
    "mv": "mV",
    "millivolt": "mV",
    "millivolts": "mV",
    "a": "A",
    "amp": "A",
    "amps": "A",
    "ampere": "A",
    "amperes": "A",
    "ma": "mA",
    "milliamp": "mA",
    "milliamps": "mA",
    "w": "W",
    "watt": "W",
    "watts": "W",
    "kw": "kW",
    "kilowatt": "kW",
    "kilowatts": "kW",
    "hz": "Hz",
    "hertz": "Hz",
    "khz": "kHz",
    "ohm": "Ω",
    "ohms": "Ω",
    "ω": "Ω",
    # Dimension / Distance
    "mm": "mm",
    "millimeter": "mm",
    "millimeters": "mm",
    "cm": "cm",
    "centimeter": "cm",
    "centimeters": "cm",
    "m": "m",
    "meter": "m",
    "meters": "m",
    "in": "in",
    "inch": "in",
    "inches": "in",
    "ft": "ft",
    "foot": "ft",
    "feet": "ft",
    "micron": "µm",
    "microns": "µm",
    "µm": "µm",
    "um": "µm",
    # Mass / Force / Torque
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "g": "g",
    "gram": "g",
    "grams": "g",
    "lb": "lb",
    "lbs": "lb",
    "pound": "lb",
    "pounds": "lb",
    "n": "N",
    "newton": "N",
    "newtons": "N",
    "kn": "kN",
    "nm": "Nm",
    "n*m": "Nm",
    "n-m": "Nm",
    "n m": "Nm",
    "newton-meter": "Nm",
    "ft-lb": "ft-lb",
    "ft-lbs": "ft-lb",
    "lbf-ft": "ft-lb",
    # Time
    "ms": "ms",
    "millisecond": "ms",
    "milliseconds": "ms",
    "s": "s",
    "sec": "s",
    "second": "s",
    "seconds": "s",
    "min": "min",
    "minute": "min",
    "minutes": "min",
    "h": "h",
    "hr": "h",
    "hour": "h",
    "hours": "h",
    # Percentage / Ratio
    "%": "%",
    "percent": "%",
    "percentage": "%",
    "cst": "cSt",  # Viscosity
    "ssu": "SSU",
}

# Regex to match numeric values with optional comma separators and decimals
_NUMBER_PATTERN = r"([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
_VALUE_UNIT_REGEX = re.compile(
    r"^\s*" + _NUMBER_PATTERN + r"\s*([a-zA-Z°℃℉Ωµ%\/\*\-\^0-9\.]+)?\s*$",
    re.IGNORECASE,
)


def normalize_unit(unit_str: Optional[str]) -> Optional[str]:
    """Standardize an engineering unit string to its canonical representation.

    Args:
        unit_str: Raw unit string (e.g., 'p.s.i.', 'deg C', 'gpm').

    Returns:
        Canonical unit string (e.g., 'PSI', '°C', 'GPM'), or stripped input if unmapped.
    """
    if not unit_str:
        return None

    cleaned = unit_str.strip()
    key = cleaned.lower()

    if key in _UNIT_ALIASES:
        return _UNIT_ALIASES[key]

    # Handle double quotes as inches
    if cleaned in ('"', "''", "”"):
        return "in"

    return cleaned


def parse_value_unit(raw_value: str) -> Tuple[Optional[float], Optional[str], str]:
    """Parse a raw string containing a numeric value and an optional unit.

    Examples:
        '3000 PSI' -> (3000.0, 'PSI', '3000 PSI')
        '3,000psi' -> (3000.0, 'PSI', '3000 PSI')
        '-40°C' -> (-40.0, '°C', '-40 °C')
        '12.5 GPM' -> (12.5, 'GPM', '12.5 GPM')
        'Redundant' -> (None, None, 'Redundant')

    Args:
        raw_value: The unparsed text string.

    Returns:
        Tuple of (numeric_float, normalized_unit, clean_formatted_str).
    """
    if not raw_value:
        return None, None, ""

    trimmed = raw_value.strip()

    # Match numeric part and trailing unit
    match = _VALUE_UNIT_REGEX.match(trimmed)
    if match:
        num_str = match.group(1).replace(",", "")
        unit_str = match.group(2)
        try:
            val = float(num_str)
            norm_unit = normalize_unit(unit_str) if unit_str else None
            formatted = f"{val:g} {norm_unit}".strip() if norm_unit else f"{val:g}"
            return val, norm_unit, formatted
        except ValueError:
            pass

    # If not a single number+unit, return as clean string
    return None, None, trimmed


def convert_unit(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    """Convert a numeric value between compatible engineering units.

    Supports Pressure (PSI, bar, MPa, kPa), Temperature (°C, °F, K),
    Flow Rate (GPM, L/min), Dimension (in, mm), and Mass (lb, kg).

    Args:
        value: Numeric value in source unit.
        from_unit: Source unit string.
        to_unit: Target unit string.

    Returns:
        Converted float value, or None if conversion is not supported/compatible.
    """
    u_from = normalize_unit(from_unit)
    u_to = normalize_unit(to_unit)

    if not u_from or not u_to:
        return None

    if u_from == u_to:
        return value

    # Pressure conversions (Base: bar)
    pressure_to_bar = {
        "bar": 1.0,
        "barg": 1.0,
        "PSI": 0.0689476,
        "PSIG": 0.0689476,
        "kPa": 0.01,
        "MPa": 10.0,
        "Pa": 0.00001,
    }
    if u_from in pressure_to_bar and u_to in pressure_to_bar:
        in_bar = value * pressure_to_bar[u_from]
        return in_bar / pressure_to_bar[u_to]

    # Temperature conversions
    if u_from in ("°C", "°F", "K") and u_to in ("°C", "°F", "K"):
        # Convert to Celsius first
        if u_from == "°C":
            celsius = value
        elif u_from == "°F":
            celsius = (value - 32.0) * (5.0 / 9.0)
        else:  # K
            celsius = value - 273.15

        # Convert Celsius to target
        if u_to == "°C":
            return celsius
        elif u_to == "°F":
            return (celsius * 9.0 / 5.0) + 32.0
        else:  # K
            return celsius + 273.15

    # Flow rate (Base: GPM)
    flow_to_gpm = {
        "GPM": 1.0,
        "L/min": 0.264172,
        "L/s": 15.8503,
        "m³/h": 4.40287,
    }
    if u_from in flow_to_gpm and u_to in flow_to_gpm:
        in_gpm = value * flow_to_gpm[u_from]
        return in_gpm / flow_to_gpm[u_to]

    # Dimension (Base: mm)
    dim_to_mm = {
        "mm": 1.0,
        "cm": 10.0,
        "m": 1000.0,
        "in": 25.4,
        "ft": 304.8,
        "µm": 0.001,
    }
    if u_from in dim_to_mm and u_to in dim_to_mm:
        in_mm = value * dim_to_mm[u_from]
        return in_mm / dim_to_mm[u_to]

    # Mass (Base: kg)
    mass_to_kg = {
        "kg": 1.0,
        "g": 0.001,
        "lb": 0.453592,
    }
    if u_from in mass_to_kg and u_to in mass_to_kg:
        in_kg = value * mass_to_kg[u_from]
        return in_kg / mass_to_kg[u_to]

    logger.warning("No unit conversion path found from %s to %s", from_unit, to_unit)
    return None
