from app.models import CheckinRequest
from app.ritmo_service import calcular_ritmo_score_e_recomendacoes


def test_calculo_ritmo_basico():
    checkin = CheckinRequest(
        usuario_id="teste-1",
        humor="cansado",
        foco=2,
        horas_sono=4.0,
        ambiente="casa",
        condicoes=["barulho", "cansaco"],
        texto_livre="Dia puxado, muita gente falando e pouco espaço."
    )

    resp = calcular_ritmo_score_e_recomendacoes(checkin)

    assert resp.usuario_id == "teste-1"
    assert 0 <= resp.score <= 100
    assert resp.nivel in ["flow", "neutro", "alerta", "critico"]
    assert isinstance(resp.missao_sugerida, str)
    assert isinstance(resp.insight_sugerido, str)
    assert resp.sentimento_texto in ["positivo", "neutro", "negativo"]
    assert 0.0 <= resp.intensidade_sentimento <= 1.0
    assert isinstance(resp.palavras_chave, list)
    assert resp.tendencia_score in ["subindo", "caindo", "estavel", "primeira_medicao"]
    assert resp.total_checkins_usuario >= 1
    assert isinstance(resp.perfil_estudo, str)
