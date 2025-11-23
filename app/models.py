from typing import List, Optional, Literal
from pydantic import BaseModel, Field


HumorLiteral = Literal[
    "muito_bem",
    "bem",
    "ok",
    "cansado",
    "sobrecarregado"
]

AmbienteLiteral = Literal[
    "casa",
    "trabalho",
    "ong",
    "escola",
    "rua",
    "transporte"
]

CondicaoLiteral = Literal[
    "barulho",
    "falta_espaco",
    "falta_internet",
    "cansaco",
    "estresse",
    "seguro",
    "ok"
]

SentimentoLiteral = Literal["positivo", "neutro", "negativo"]
TendenciaLiteral = Literal["subindo", "caindo", "estavel", "primeira_medicao"]


class CheckinRequest(BaseModel):
    """
    Check-in do estudante no PerifaFlow:
    representa o 'IoB' (comportamento + contexto).
    Este JSON é exatamente o que a API .NET poderá enviar depois.
    """
    usuario_id: str = Field(..., description="Identificador interno do usuário")
    humor: HumorLiteral
    foco: int = Field(..., ge=1, le=5, description="Autoavaliação de foco de 1 a 5")
    horas_sono: Optional[float] = Field(
        None, ge=0, le=24, description="Horas de sono aproximadas na última noite"
    )
    ambiente: AmbienteLiteral
    condicoes: List[CondicaoLiteral] = Field(
        default_factory=list,
        description="Condições marcadas pelo usuário (barulho, falta de espaço etc.)"
    )
    texto_livre: Optional[str] = Field(
        None,
        description="Descrição opcional de como o estudante está se sentindo"
    )


class RitmoScoreResponse(BaseModel):
    """
    Resposta do motor de IoB/Recomendação:
    - score numérico do Ritmo
    - nível (flow/neutro/alerta/critico)
    - missão sugerida
    - insight/apoio
    - análise básica de sentimento do texto
    - palavras-chave extraídas
    - tendência do score no histórico
    - perfil de estudo detectado
    """
    usuario_id: str
    score: float = Field(..., ge=0, le=100)
    nivel: Literal["flow", "neutro", "alerta", "critico"]

    # Antes já existiam:
    missao_sugerida: str
    insight_sugerido: str

    # Novos campos (mais robustos):
    sentimento_texto: SentimentoLiteral
    intensidade_sentimento: float = Field(..., ge=0.0, le=1.0)
    palavras_chave: List[str]

    tendencia_score: TendenciaLiteral
    total_checkins_usuario: int
    perfil_estudo: str
