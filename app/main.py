from fastapi import FastAPI
from .models import CheckinRequest, RitmoScoreResponse
from .ritmo_service import calcular_ritmo_score_e_recomendacoes

app = FastAPI(
    title="PerifaFlow – RitmoScore Service",
    description=(
        "Microserviço de IoB/Recomendação do PerifaFlow. "
        "Recebe check-ins dos estudantes e devolve Ritmo Score, missão e insight."
    ),
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/checkin-ritmo", response_model=RitmoScoreResponse)
def post_checkin_ritmo(checkin: CheckinRequest):
    """
    Endpoint principal:
    - Entrada: dados de check-in (IoB)
    - Saída: Ritmo Score + nível + missão + insight
    """
    return calcular_ritmo_score_e_recomendacoes(checkin)
