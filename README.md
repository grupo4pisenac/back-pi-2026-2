# Dashboard de Monitoramento Climático e de Safra — Agronegócio (Vale do São Francisco)

Solução em nuvem para ingestão, processamento e análise preditiva de dados climáticos (IoT), voltada à otimização da janela ideal de colheita de frutas na região de Petrolina/Juazeiro.

Projeto Integrador desenvolvido para o 4º módulo de Análise e Desenvolvimento de Sistemas (ADS).

---

## 🛠️ Tecnologias e Ferramentas

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| Framework web | FastAPI (Uvicorn) - Arquitetura Assíncrona |
| Banco de dados | PostgreSQL 15 (Docker) via SQLAlchemy com asyncpg |
| Autenticação | JWT Stateless com controle de acesso RBAC (Role-Based Access Control) |
| IoT / Ingestão | ThingSpeak REST API / ESP32 |
| Testes Automatizados | pytest com FastAPI TestClient |
| Execução | Docker e Docker Compose |

---

## 📋 Arquitetura e Fluxo de Dados

1. **Camada IoT:** o microcontrolador ESP32 coleta temperatura e umidade em intervalos regulares e publica no canal do ThingSpeak via HTTP/MQTT.
2. **Camada de ingestão (back-end):** a API em FastAPI consome periodicamente os *channel feeds* do ThingSpeak, respeitando os limites da API REST pública.
3. **Persistência:** os dados de telemetria climática são higienizados e gravados no banco de dados relacional (`dados_climaticos`).
4. **Camada analítica e de apresentação:** módulos de previsão geram alertas sobre a janela ideal de safra, disponíveis no dashboard operacional com controle de acesso por perfil de usuário.

---

## 🚀 Como Executar Localmente

### Pré-requisitos

- Git
- Python 3.10+ e `venv`
- Docker e Docker Compose

### 1. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd <NOME_DA_PASTA>
```

### 2. Criar o ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto baseado no `.env.example`:

```env
DATABASE_URL=postgresql://admin:adminpassword@localhost:5432/agrotech_db
THINGSPEAK_CHANNEL_ID=seu_channel_id_aqui
THINGSPEAK_READ_KEY=sua_read_api_key_aqui
SECRET_KEY=uma_chave_secreta_longa_e_aleatoria_aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
INGEST_ENABLED=false
```

### 5. Subir o banco de dados

Inicie o contêiner PostgreSQL em segundo plano:

```bash
docker compose up -d
```

### 6. Executar a aplicação

Inicie o servidor de desenvolvimento:

```bash
uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000`.

---

## 🧪 Execução de Testes Automatizados

O projeto inclui suíte de testes com cobertura para endpoints públicos, autenticação e rotas do painel:

```bash
pytest -v
```

---

## 📖 Endpoints Principais da API

### 1. Autenticação (`/auth`)
- `POST /auth/login`: Autentica usuário e retorna tokens JWT (`accessToken`, `refreshToken`) e dados do perfil.
- `POST /auth/refresh`: Renova o token de acesso expirado.
- `GET /auth/me`: Retorna os dados do usuário logado (requer autenticação).
- `POST /auth/logout`: Rota de encerramento de sessão (HTTP 204).

### 2. Painel e Monitoramento (`/api` ou raiz)
- `GET /climate/readings?range=today`: Leituras reais da telemetria de sensores IoT (`today`, `24h`, `7d`, `30d`, `all`). Permissão: `climate:read`.
- `GET /dashboard/summary`: Sumário executivo consolidado com KPIs do agronegócio. Permissão: `dashboard:read`.
- `GET /forecasts/harvest?cropId=manga-palmer`: Previsão da janela ideal de colheita da safra. Permissão: `forecast:read`.
- `GET /plots?status=ACTIVE`: Listagem de lotes/talhões produtivos monitorados em Petrolina/Juazeiro. Permissão: `dashboard:read`.
- `GET /alerts/active`: Alerta térmico e climático em tempo real. Permissão: `autenticado`.

---

## 🔒 Segurança e Perfis de Acesso (RBAC)

O sistema implementa autenticação stateless baseada em JSON Web Tokens (JWT) e controle por perfil de acesso:
- **`PRODUTOR` (Produtor Rural):** Consulta o dashboard, previsões de safra, talhões e alertas.
- **`ANALISTA` (Analista de Dados):** Visualiza e alimenta os modelos preditivos e históricos climáticos.
- **`ADMIN` (Administrador):** Gerencia usuários, permissões e parametrizações globais do sistema.
