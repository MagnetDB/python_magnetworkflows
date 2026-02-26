"""
MagnetType enum, configuration constants and validation.
"""

from enum import Enum


class MagnetType(Enum):
    """Enum for magnet types."""

    INSERT = "helix"
    BITTERS = "bitter"
    SUPRAS = "supra"  # Placeholder for future implementation

    @classmethod
    def from_string(cls, value: str) -> "MagnetType":
        """Convert string to MagnetType enum."""
        value_lower = value.lower()
        for member in cls:
            if member.value == value_lower:
                return member
        raise ValueError(
            f"Invalid magnet type '{value}'. "
            f"Must be one of: {', '.join([m.value for m in cls])}"
        )


# Configuration constants
DEFAULT_FUZZY_FACTOR_HELIX = 1.0
DEFAULT_FUZZY_FACTOR_BITTER = 1.7
DEFAULT_RELAX = 0
DEFAULT_INDUCTANCE = 0
DEFAULT_PEXTRA = 1


def validate_magnet_config(magnet_type: MagnetType, values: dict) -> None:
    """
    Validate magnet configuration parameters.

    Args:
        magnet_type: Type of magnet (MagnetType.INSERT or MagnetType.BITTERS)
        values: Configuration values dictionary

    Raises:
        ValueError: If configuration is invalid
    """
    # magnet_type is already validated by MagnetType.from_string()

    required_keys = ["type", "value", "flow"]
    missing_keys = [key for key in required_keys if key not in values]
    if missing_keys:
        raise ValueError(
            f"Missing required configuration keys: {', '.join(missing_keys)}"
        )

    # Validate numeric values
    if not isinstance(values["value"], (int, float)) or values["value"] <= 0:
        raise ValueError(
            f"Invalid 'value' parameter: {values['value']}. "
            "Must be a positive number."
        )

    # Validate optional numeric parameters
    if "relax" in values:
        if not isinstance(values["relax"], (int, float)) or values["relax"] < 0:
            raise ValueError(
                f"Invalid 'relax' parameter: {values['relax']}. "
                "Must be a non-negative number."
            )

    if "inductance" in values:
        if not isinstance(values["inductance"], (int, float)) or values["inductance"] < 0:
            raise ValueError(
                f"Invalid 'inductance' parameter: {values['inductance']}. "
                "Must be a non-negative number."
            )

    if "heatCorrelationFuzzyFactor" in values:
        if (
            not isinstance(values["heatCorrelationFuzzyFactor"], (int, float))
            or values["heatCorrelationFuzzyFactor"] <= 0
        ):
            raise ValueError(
                f"Invalid 'heatCorrelationFuzzyFactor' parameter: {values['heatCorrelationFuzzyFactor']}. "
                "Must be a positive number."
            )

    if "pextra" in values:
        if not isinstance(values["pextra"], (int, float)) or values["pextra"] <= 0:
            raise ValueError(
                f"Invalid 'pextra' parameter: {values['pextra']}. "
                "Must be a positive number."
            )
