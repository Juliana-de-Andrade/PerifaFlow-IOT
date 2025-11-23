# PerifaFlow – Microserviço de RitmoScore (IoT/IoB & IA de Bem-Estar)

Este repositório contém o **microserviço Python** responsável por calcular o RitmoScore, analisar texto, gerar missão sugerida e insight, além de manter histórico e detectar tendência de bem-estar.

## 🚀 1. Estrutura do Projeto
```
perifaflow-ritmoscore-ia/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   └── ritmo_service.py
├── data/
├── tests/
└── requirements.txt
```

## 📦 2. Pré-requisitos
- Python 3.10+
- pip
- (opcional) venv

## 🛠️ 3. Preparando o ambiente
### Criar ambiente virtual
Windows:
```
python -m venv .venv
.venv\Scripts\activate
```
Linux/macOS:
```
python -m venv .venv
source .venv/bin/activate
```

### Instalar dependências
```
pip install -r requirements.txt
```

## ▶️ 4. Rodar o servidor
```
uvicorn app.main:app --reload
```
Acesse:
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## 📤 5. Exemplo de requisição `/checkin-ritmo`
```
{
  "usuario_id": "user-001",
  "humor": "cansado",
  "foco": 2,
  "horas_sono": 4.0,
  "ambiente": "casa",
  "condicoes": ["barulho", "cansaco"],
  "texto_livre": "Dia difícil, muito barulho em casa."
}
```

## 📥 6. Exemplo de resposta
```
{
  "usuario_id": "user-001",
  "score": 42.0,
  "nivel": "alerta",
  "missao_sugerida": "...",
  "insight_sugerido": "...",
  "sentimento_texto": "negativo",
  "intensidade_sentimento": 0.63,
  "palavras_chave": ["dificil","barulho","casa"],
  "tendencia_score": "primeira_medicao",
  "total_checkins_usuario": 1,
  "perfil_estudo": "sobrecarregado"
}
```

## 🔗 7. Integração com Java
A aplicação Java deve enviar um POST para:
```
http://localhost:8000/checkin-ritmo
```
Com o mesmo JSON acima.

## 📝 8. Encerrar o servidor
CTRL + C no terminal.

## Integrantes:
Gabriel Gomes Mancera — RM: 555427
Juliana de Andrade Sousa — RM: 558834
Victor Hugo Carvalho Pereira — RM: 558550

