"""VISTA (V): contratos JSON de entrada y salida del servicio."""
from pydantic import BaseModel, Field


class QItem(BaseModel):
    id: int | None = None
    service: str
    preferential: bool = False
    key: float = 0.0  # menor = se atiende antes


class InService(BaseModel):
    service: str
    preferential: bool = False
    elapsed_min: float = 0.0


class PointIn(BaseModel):
    id: int
    name: str = ""
    services: list[str] = []
    active: bool = True
    queue: list[QItem] = []
    in_service: InService | None = None


class SuggestIn(BaseModel):
    service: str
    preferential: bool = False
    new_key: float
    prior_minutes: dict[str, float]
    points: list[PointIn]


class Option(BaseModel):
    point_id: int
    name: str
    est_wait_min: float
    est_service_min: float
    queue_ahead: int
    score: float
    reason: str
    recommended: bool = False


class SuggestOut(BaseModel):
    options: list[Option]
    model: str = "ema-shrinkage-v1"


class EstimateIn(BaseModel):
    prior_minutes: dict[str, float]
    point: PointIn


class EstimateOut(BaseModel):
    waits: dict[int, float]
    service_minutes: dict[int, float]


class LearnIn(BaseModel):
    service: str
    point_id: int
    preferential: bool = False
    minutes: float = Field(gt=0)
