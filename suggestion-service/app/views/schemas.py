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
    base_key: float               # clave de orden de un turno que llega ahora, SIN bonificacion
    bonus_min: float = 0.0        # bonificacion minima de prioridad (minutos de adelanto)
    max_bonus_min: float = 0.0    # tope que el modelo puede otorgar para cumplir la meta
    target_wait_min: float | None = None  # meta de espera para prioritarios
    hour: int | None = Field(default=None, ge=0, le=23)  # hora local (franja horaria del modelo)
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
    bonus_min: float = 0.0               # bonificacion de prioridad que el modelo aplicaria
    est_wait_normal_min: float = 0.0     # espera que tendria sin prioridad
    saved_min: float = 0.0               # minutos que ahorra la prioridad
    meets_target: bool = True            # cumple la meta de espera (solo prioritarios)


class SuggestOut(BaseModel):
    options: list[Option]
    model: str = "ema-shrinkage-v1"


class EstimateIn(BaseModel):
    prior_minutes: dict[str, float]
    hour: int | None = Field(default=None, ge=0, le=23)
    point: PointIn


class EstimateOut(BaseModel):
    waits: dict[int, float]
    service_minutes: dict[int, float]


class LearnIn(BaseModel):
    service: str
    point_id: int
    preferential: bool = False
    minutes: float = Field(gt=0)
    prior_minutes: float | None = None  # valor inicial del servicio: linea base para medir efectividad
    hour: int | None = Field(default=None, ge=0, le=23)  # hora local en que termino la atencion


class ReportIn(BaseModel):
    prior_minutes: dict[str, float] = {}


class PredictIn(BaseModel):
    service: str
    point_id: int
    preferential: bool = False
    prior_minutes: float
    hour: int | None = Field(default=None, ge=0, le=23)


class Level(BaseModel):
    label: str
    samples: int
    mean: float
    estimate: float


class PredictOut(BaseModel):
    service: str
    point_id: int
    group: str
    minutes: float
    margin: float
    low: float
    high: float
    samples: int
    confidence_pct: int
    levels: list[Level]
