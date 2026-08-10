from pydantic import BaseModel, ConfigDict

from app.schemas.engineering import EngineeringQuantity


class LLCCoreProjectInput(BaseModel):
    """Minimum project data required by all Phase 1 core calculations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lr: EngineeringQuantity
    lm: EngineeringQuantity
    cr: EngineeringQuantity
    vout: EngineeringQuantity
    pout: EngineeringQuantity
    efficiency: EngineeringQuantity

