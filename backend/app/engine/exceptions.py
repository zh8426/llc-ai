class EngineeringCalculationError(ValueError):
    """Base error for deterministic engineering calculation failures."""


class InvalidEngineeringQuantityError(EngineeringCalculationError):
    """Raised when an input value or unit is invalid for a formula."""


class CalculationRangeError(EngineeringCalculationError):
    """Raised when finite inputs cannot produce a finite positive result."""

