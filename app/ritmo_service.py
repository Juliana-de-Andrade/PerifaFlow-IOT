import json
import os
from datetime import datetime
from typing import List, Tuple

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .models import (
    CheckinRequest,
    RitmoScoreResponse,
    SentimentoLiteral,
    TendenciaLiteral,
)

# Analisador de sentimento (PLN local)
_analyzer = SentimentIntensityAnalyzer()

# Arquivo simples para histórico local
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
HISTORICO_PATH = os.path.join(DATA_DIR, "historico_ritmo.json")


# ----------------------------
# 1. Cálculo base do RitmoScore
# ----------------------------
def _pontuar_humor(humor: str) -> int:
    mapa = {
        "muito_bem": 25,
        "bem": 20,
        "ok": 15,
        "cansado": 10,
        "sobrecarregado": 5,
    }
    return mapa.get(humor, 15)


def _ajuste_foco(foco: int) -> int:
    # foco 1–5 => -10 a +10
    return (foco - 3) * 5


def _ajuste_sono(horas_sono: float | None) -> int:
    if horas_sono is None:
        return 0
    if horas_sono < 4:
        return -15
    if 4 <= horas_sono < 6:
        return -8
    if 6 <= horas_sono < 8:
        return 0
    if 8 <= horas_sono <= 9:
        return 5
    return -3  # muito sono também pesa


def _ajuste_ambiente(ambiente: str) -> int:
    if ambiente in ("ong", "escola"):
        return 5
    if ambiente in ("casa", "trabalho"):
        return 0
    if ambiente in ("rua", "transporte"):
        return -10
    return 0


def _ajuste_condicoes(condicoes: list[str]) -> int:
    score = 0
    if "barulho" in condicoes:
        score -= 8
    if "falta_espaco" in condicoes:
        score -= 6
    if "falta_internet" in condicoes:
        score -= 10
    if "cansaco" in condicoes:
        score -= 6
    if "estresse" in condicoes:
        score -= 8
    if "seguro" in condicoes:
        score += 4
    # "ok" não altera nada
    return score


def _classificar_nivel(score: float) -> str:
    if score >= 75:
        return "flow"
    if score >= 55:
        return "neutro"
    if score >= 35:
        return "alerta"
    return "critico"


# -----------------------------------------
# 2. Análise de texto (sentimento + termos)
# -----------------------------------------

_STOPWORDS_SIMPLIFICADAS = {
    "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas", "um", "uma",
    "que", "pra", "para", "com", "sem", "por", "e", "ou", "mas", "muito", "pouco",
    "isso", "aquilo", "tudo", "nada", "ontem", "hoje", "amanha", "aqui", "ali",
    "tá", "ta", "to", "tô", "tava", "estou", "essa", "esse", "isso"
}


def _analisar_texto(texto: str | None) -> Tuple[SentimentoLiteral, float, List[str]]:
    if not texto or not texto.strip():
        return "neutro", 0.0, []

    scores = _analyzer.polarity_scores(texto)
    compound = scores["compound"]

    if compound > 0.2:
        sentimento: SentimentoLiteral = "positivo"
    elif compound < -0.2:
        sentimento = "negativo"
    else:
        sentimento = "neutro"

    intensidade = float(abs(compound))

    # Extração simples de "palavras-chave"
    tokens = []
    palavra = []
    for ch in texto.lower():
        if ch.isalnum():
            palavra.append(ch)
        else:
            if palavra:
                tokens.append("".join(palavra))
                palavra = []
    if palavra:
        tokens.append("".join(palavra))

    # Filtra stopwords e palavras muito curtas
    keywords = []
    for t in tokens:
        if len(t) < 4:
            continue
        if t in _STOPWORDS_SIMPLIFICADAS:
            continue
        if t not in keywords:
            keywords.append(t)

    return sentimento, intensidade, keywords[:10]


# --------------------------------------
# 3. Histórico local + tendência do score
# --------------------------------------
def _carregar_historico() -> list[dict]:
    if not os.path.exists(HISTORICO_PATH):
        return []
    try:
        with open(HISTORICO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def _salvar_historico(registros: list[dict]) -> None:
    with open(HISTORICO_PATH, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)


def _atualizar_historico_e_tendencia(
    usuario_id: str, score: float, nivel: str, sentimento: str
) -> Tuple[TendenciaLiteral, int]:
    historico = _carregar_historico()
    agora = datetime.utcnow().isoformat()

    registro = {
        "usuario_id": usuario_id,
        "timestamp": agora,
        "score": score,
        "nivel": nivel,
        "sentimento": sentimento,
    }

    historico.append(registro)
    _salvar_historico(historico)

    # Filtra histórico do usuário
    do_usuario = [r for r in historico if r.get("usuario_id") == usuario_id]
    do_usuario.sort(key=lambda x: x.get("timestamp", ""))

    total = len(do_usuario)
    if total <= 1:
        return "primeira_medicao", total

    # Compara último score com score anterior
    ultimo = do_usuario[-1]["score"]
    anterior = do_usuario[-2]["score"]
    delta = ultimo - anterior

    if delta > 5:
        tendencia: TendenciaLiteral = "subindo"
    elif delta < -5:
        tendencia = "caindo"
    else:
        tendencia = "estavel"

    return tendencia, total


# ------------------------------------
# 4. Perfil de estudo + recomendações
# ------------------------------------
def _determinar_perfil(
    nivel: str,
    sentimento: SentimentoLiteral,
    tendencia: TendenciaLiteral,
    checkin: CheckinRequest,
) -> str:
    """
    Cria um "perfil" baseado em nível, sentimento, tendência e contexto.
    """
    # Perfis baseados em sinais mais críticos
    if nivel == "critico" or tendencia == "caindo":
        if sentimento == "negativo" or "estresse" in checkin.condicoes:
            return "sobrecarregado"
        if "falta_internet" in checkin.condicoes or "falta_espaco" in checkin.condicoes:
            return "contexto_dificil"
        return "critico"

    if nivel == "alerta":
        if "rua" in checkin.ambiente or "transporte" in checkin.ambiente:
            return "nomade"
        if sentimento == "negativo":
            return "sensivel"
        return "em_alerta"

    if nivel == "flow":
        if sentimento == "positivo":
            return "produtivo"
        return "alto_potencial"

    # nivel neutro
    if tendencia == "subindo":
        return "em_evolucao"

    return "neutro"


def _gerar_missao(perfil: str, nivel: str, checkin: CheckinRequest) -> str:
    base_inicio = "Sua missão de hoje no PerifaFlow é: "

    if perfil == "produtivo" or perfil == "alto_potencial":
        return (
            base_inicio
            + "criar um mini-projeto de IA completo. Escolha um dataset simples "
              "(por exemplo, sentimentos de frases ou previsões simples), treine "
              "um modelo básico e publique o código em um repositório com um README "
              "curto explicando sua ideia e resultado."
        )

    if perfil == "nomade":
        return (
            base_inicio
            + "fazer uma missão totalmente mobile friendly. Use o celular para "
              "anotar ideias de projetos em IA, desenhar um fluxo de dados ou "
              "escrever pseudocódigo de um modelo. Foque em algo que você consiga "
              "começar e pausar facilmente enquanto se desloca."
        )

    if perfil == "sobrecarregado" or perfil == "sensivel":
        return (
            base_inicio
            + "pegar leve. Reabra um projeto antigo e apenas melhore comentários, "
              "organize arquivos e ajuste o README. Não há necessidade de começar "
              "algo novo hoje: sua missão é deixar o que já existe mais claro e "
              "apresentável para o futuro."
        )

    if perfil == "contexto_dificil":
        return (
            base_inicio
            + "focar em uma missão que dependa pouco de internet e equipamentos. "
              "Por exemplo, escrever em um caderno (ou bloco de notas) uma ideia "
              "de solução em IA para um problema da sua quebrada, detalhando dados, "
              "entradas, saídas e impacto social."
        )

    if perfil == "em_evolucao":
        return (
            base_inicio
            + "escolher um conteúdo ligeiramente acima do que você já domina. "
              "Replique um código de IA que você viu em aula ou tutorial e faça "
              "uma pequena modificação para aprender algo novo (por exemplo, mudar "
              "o tipo de modelo ou a métrica analisada)."
        )

    # neutro / em_alerta / fallback
    if nivel == "alerta":
        return (
            base_inicio
            + "fazer uma missão de 20 a 30 minutos: revise um conceito importante "
              "de IA e anote exemplos práticos. Hoje o foco é consolidar, não "
              "forçar produtividade."
        )

    return (
        base_inicio
        + "separar entre 30 e 45 minutos para estudar um exemplo de IA, replicar "
          "o código e salvar o resultado em um lugar seguro (como seu GitHub ou "
          "uma pasta organizada)."
    )


def _gerar_insight(
    perfil: str,
    nivel: str,
    sentimento: SentimentoLiteral,
    tendencia: TendenciaLiteral,
) -> str:
    if perfil == "produtivo" or perfil == "alto_potencial":
        return (
            "Você está em um bom momento de aprendizado. Aproveite para registrar "
            "bem seus projetos, porque isso vira prova concreta das suas habilidades "
            "em futuros processos seletivos ou oportunidades na área de tecnologia."
        )

    if perfil == "nomade":
        return (
            "Seu estudo acontece em movimento, e isso é uma realidade de muita gente "
            "na quebrada. Pequenos avanços consistentes contam muito: use pequenos "
            "intervalos para pensar projetos, rascunhar ideias e se manter conectado "
            "com a IA, mesmo sem um espaço fixo de estudo."
        )

    if perfil == "sobrecarregado" or perfil == "sensivel":
        return (
            "Seu Ritmo Score indica sobrecarga. Isso não é fraqueza: é um alerta. "
            "Se for possível, busque apoio em pessoas ou espaços seguros, como ONGs "
            "parceiras. Respeitar seus limites hoje pode te permitir seguir na jornada "
            "de IA de forma mais sustentável amanhã."
        )

    if perfil == "contexto_dificil":
        return (
            "Seu contexto de estudo traz desafios materiais. Mesmo assim, sua visão "
            "sobre problemas reais da periferia é extremamente valiosa. Use essa "
            "experiência para imaginar soluções em IA conectadas à sua realidade: "
            "isso é diferencial, não limitação."
        )

    if perfil == "em_evolucao":
        return (
            "Seu ritmo está evoluindo. Pequenos passos constantes estão te levando "
            "para um nível cada vez mais avançado. Valorize o que você já conquistou "
            "e mantenha um compromisso realista consigo mesma(o)."
        )

    if tendencia == "caindo" and sentimento == "negativo":
        return (
            "Seu Ritmo Score vem caindo e seu texto indica momentos difíceis. "
            "Considere reduzir a cobrança sobre desempenho agora e, se fizer sentido, "
            "buscar apoio emocional ou social. A tecnologia pode esperar: você é mais importante."
        )

    if nivel == "flow":
        return (
            "Você está em estado de flow. Use esse momento para avançar em algo que "
            "faça sentido para o seu futuro no trabalho: um projeto que você teria "
            "orgulho de mostrar em uma entrevista ou processo seletivo."
        )

    if nivel == "critico":
        return (
            "Seu Ritmo Score está crítico. Antes de qualquer missão ou meta, cuide de "
            "você. Se possível, busque apoio em pessoas, serviços públicos ou ONGs. "
            "Quando as coisas estiverem mais estáveis, o PerifaFlow continua aqui para te apoiar."
        )

    # neutro / alerta / fallback
    return (
        "Seu Ritmo Score indica um momento intermediário. Isso é normal. Aproveite "
        "para fazer uma missão possível hoje, sem comparação com outras pessoas. "
        "Sua jornada em IA é sua, no seu tempo."
    )


# ------------------------------
# 5. Função principal do serviço
# ------------------------------
def calcular_ritmo_score_e_recomendacoes(
    checkin: CheckinRequest,
) -> RitmoScoreResponse:
    """
    - Calcula o Ritmo Score (base heurística)
    - Analisa o texto livre (sentimento + palavras-chave)
    - Atualiza histórico e calcula tendência
    - Define perfil de estudo
    - Gera missão e insight personalizados
    """
    base = 50
    base += _pontuar_humor(checkin.humor)
    base += _ajuste_foco(checkin.foco)
    base += _ajuste_sono(checkin.horas_sono)
    base += _ajuste_ambiente(checkin.ambiente)
    base += _ajuste_condicoes(checkin.condicoes)

    # Análise de texto influencia um pouco o score
    sentimento, intensidade, keywords = _analisar_texto(checkin.texto_livre)
    if sentimento == "positivo":
        base += 3
    elif sentimento == "negativo":
        base -= 5

    score = max(0, min(100, float(base)))
    nivel = _classificar_nivel(score)

    tendencia, total_checkins = _atualizar_historico_e_tendencia(
        checkin.usuario_id, score, nivel, sentimento
    )

    perfil = _determinar_perfil(nivel, sentimento, tendencia, checkin)
    missao = _gerar_missao(perfil, nivel, checkin)
    insight = _gerar_insight(perfil, nivel, sentimento, tendencia)

    return RitmoScoreResponse(
        usuario_id=checkin.usuario_id,
        score=score,
        nivel=nivel,
        missao_sugerida=missao,
        insight_sugerido=insight,
        sentimento_texto=sentimento,
        intensidade_sentimento=intensidade,
        palavras_chave=keywords,
        tendencia_score=tendencia,
        total_checkins_usuario=total_checkins,
        perfil_estudo=perfil,
    )
