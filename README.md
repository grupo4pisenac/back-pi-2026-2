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
3. **Persistência:** os dados de telemetria climática são higienizados e gravados no banco de dados relacional (`dados_climaticos`, `stations`, `usuarios`).
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
INGEST_ENABLED=true
INGEST_INTERVAL_SECONDS=20
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### 5. Subir o banco de dados

Inicie o contêiner PostgreSQL em segundo plano:

```bash
docker compose up -d
```

> **Atualizando de uma versão anterior?** O esquema das tabelas mudou (usuários ganharam nome e datas, e estações usam o ID do dispositivo, ex.: `ESP-PTR-01`). Como não há migrações, recrie o banco de desenvolvimento com `docker compose down -v && docker compose up -d`. **Isso apaga todos os dados locais.**

### 6. Popular dados iniciais (seed)

Cria um usuário por perfil e as 5 estações de demonstração. O script é idempotente:

```bash
python -m app.seed
```

| E-mail | Perfil | Senha |
|---|---|---|
| `admin@barto.io` | `ADMIN` | `barto@2026` |
| `analista@barto.io` | `ANALISTA_DADOS` | `barto@2026` |
| `produtor@barto.io` | `PRODUTOR_EXPORTADOR` | `barto@2026` |

A senha pode ser alterada com a variável `SEED_PASSWORD`.

### 7. Executar a aplicação

Inicie o servidor de desenvolvimento:

```bash
uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000` (documentação interativa em `/docs`).

---

## 🔗 Integração com o Front-end (`barto-io`)

O front-end React/Vite consome esta API pelo proxy do Vite: as chamadas para `/api/*` são repassadas para `http://localhost:8000`.

1. Suba esta API seguindo os passos acima (banco, seed e uvicorn).
2. No projeto `barto-io`, confira o `.env`:
   ```env
   VITE_USE_MOCKS=false
   VITE_API_BASE_URL=/api
   VITE_API_PROXY_TARGET=http://localhost:8000
   ```
3. Rode `npm install` e `npm run dev`, abra `http://localhost:5173` e entre com um dos usuários do seed.

Contratos seguidos pela API:

- **JSON em camelCase**, idêntico aos tipos de `barto-io/src/types`.
- **Erros padronizados** no formato `{ "message": "...", "detail": ... }`. O front exibe `message`.
- **Datas em ISO 8601 com fuso** (UTC).
- **Enums em maiúsculo**: `ADMIN | ANALISTA_DADOS | PRODUTOR_EXPORTADOR`, `ATIVO | INATIVO`, `ATIVO | ATENCAO | INATIVO`.
- **CORS** liberado para as origens de `CORS_ORIGINS`, para acesso direto sem o proxy.

### Origem dos dados

| Recurso | Fonte |
|---|---|
| Usuários, estações | Banco PostgreSQL (CRUD real) |
| Leituras climáticas, KPIs de clima do resumo, alerta térmico | Tabela `dados_climaticos`, alimentada pela ingestão do ThingSpeak |
| Produção projetada, série de previsão, talhões | Valores de referência fixos, ainda sem fonte de dados |

### Ingestão do ThingSpeak

O ESP32 publica no canal do ThingSpeak usando as credenciais MQTT do dispositivo. Elas ficam só no firmware e a API não precisa delas. A API lê o canal pela API REST com a **Read API Key**:

```
ESP32 ──MQTT──▶ ThingSpeak ◀──REST (a cada 20 s)── API ──▶ PostgreSQL ──▶ front (gráfico, atualiza a cada 30 s)
```

- **Configuração:** `THINGSPEAK_CHANNEL_ID`, `THINGSPEAK_READ_KEY` e `INGEST_ENABLED=true` no `.env`. O intervalo é definido por `INGEST_INTERVAL_SECONDS` (padrão 60, recomendado 20).
- **Primeiro ciclo:** importa o histórico do canal (até 8000 leituras, o limite da API). Os ciclos seguintes buscam as últimas 100. Leituras repetidas são ignoradas pelo `entry_id`.
- **Campos:** `field1` = temperatura (°C) e `field2` = umidade do ar (%). Opcionalmente, `field3` = umidade do solo (%) e `field4` = chuva (mm). Campo ausente vira `null` na API, nunca `0`.
- **Leituras inválidas** (fora da faixa ou `nan`, comum com o DHT desconectado) são descartadas.
- **Estação no mapa:** as leituras aparecem na estação cujo `thingSpeakChannelId` é igual a `THINGSPEAK_CHANNEL_ID`. O `python -m app.seed` vincula a `ESP-PTR-01` ao canal configurado.
- **Sincronização manual:** `POST /api/ingestion/run?results=8000`, exclusiva para ADMIN. No front, é o botão **Sincronizar agora** da página Clima.
- **Gráfico:** `GET /climate/readings?range=7d&maxPoints=240` agrega a série por média em janelas de tempo. Sem isso, 7 dias de leituras a cada 2 min somam cerca de 790 KB; com isso, cerca de 37 KB.

O **status da estação** é calculado na API:
- sem leitura → `INATIVO` ("Aguardando 1ª leitura");
- última leitura há mais de 24 h → `INATIVO` ("Sem sinal");
- bateria abaixo de 20% → `ATENCAO`;
- última leitura há mais de 30 min → `ATENCAO`;
- caso contrário → `ATIVO`.

---

## 🧪 Execução de Testes Automatizados

O projeto inclui suíte de testes com cobertura para endpoints públicos, autenticação, painel e CRUDs administrativos:

```bash
pytest -v
```

---

## 📖 Endpoints Principais da API

Todas as rotas abaixo respondem sob `/api` (usado pelo front-end) e também na raiz.

### 1. Autenticação (`/auth`)
- `POST /auth/login`: recebe `{ email, password }` e retorna `{ accessToken, refreshToken, user }`. Também atualiza o `lastAccessAt`.
- `POST /auth/refresh`: recebe `{ refreshToken }` e retorna `{ accessToken, refreshToken }`.
- `GET /auth/me`: retorna o `User` logado (requer autenticação).
- `POST /auth/logout`: recebe `{ refreshToken }` e responde `204`.

### 2. Painel e Monitoramento
- `GET /climate/readings?range=today`: `ClimateReading[]` em ordem cronológica. Aceita `range` (`today` começa à meia-noite do Vale, UTC−3; `24h`, `7d`, `30d`, `all`) ou `from`/`to` (ISO 8601), além de `stationId` e `maxPoints` (2–2000, reduz a série por média em janelas). `soilMoisture` e `rainfall` vêm `null` quando o canal não publica esses campos. Permissão: `climate:read`.
- `GET /dashboard/summary`: `DashboardSummary`. Permissão: `dashboard:read`.
- `GET /climate/aggregates?bucket=day&days=14`: `ClimateAggregate[]` com mínima, média e máxima de temperatura e umidade do ar por dia (`bucket=day`) ou por hora (`bucket=hour`), cortados no horário do Vale (UTC−3), e `heatStressHours` (tempo com temperatura ≥ 35 °C). `days` vai de 1 a 31 e inclui hoje. Permissão: `climate:read`.
- `GET /forecasts/harvest?cropId=UVA_SUGRAONE`: `HarvestForecast`. O `cropId` aceita `UVA_SUGRAONE`, `MANGA_PALMER`, `UVA_ARRA` ou `GOIABA_PALUMA`. Cada mês traz a normal climatológica (`avgTemperatureC`) e a média medida pela estação (`measuredTemperatureC`, `null` sem leituras ou em mês projetado). Permissão: `forecast:read`.
- `GET /plots?status=ACTIVE`: `Plot[]`. Permissão: `dashboard:read`.
- `GET /alerts/active`: `ThermalAlert` ou `null`. Usa o pico das últimas 24 h: 35 °C ou mais gera `atencao` e 38 °C ou mais gera `critico`. Permissão: autenticado.

### 3. Sensores e Estações (`/stations`)
- `GET /stations`: `Station[]`. Permissão: `sensors:read`.
- `GET /stations/health`: `NetworkHealth`, com `online = active + attention`. Permissão: `sensors:read`.
- `POST /stations`: recebe `StationInput` e retorna `201` com a `Station`, ou `409` se o ID já existir. Permissão: `sensors:write`.
- `PUT /stations/{id}`: recebe `StationInput` e retorna a `Station`. O ID do dispositivo não muda. Permissão: `sensors:write`.
- `DELETE /stations/{id}`: responde `204`. Permissão: `sensors:write`.

### 4. Gestão de Usuários (`/users`)
- `GET /users`: `User[]`. Permissão: `users:read`.
- `GET /users/stats`: `{ total, addedThisMonth, active, admins }`. Permissão: `users:read`.
- `POST /users`: recebe `UserInput` com `password` obrigatório e retorna `201`, ou `409` se o e-mail já existir. Permissão: `users:write`.
- `PUT /users/{id}`: recebe `UserInput`; o `password` é opcional e só é enviado para trocar a senha. Permissão: `users:write`.
- `DELETE /users/{id}`: responde `204`. Permissão: `users:write`.

---

## 🔒 Segurança e Perfis de Acesso (RBAC)

O sistema usa autenticação stateless com JSON Web Tokens (JWT) e controle por perfil de acesso. A matriz abaixo é a mesma do front-end (`barto-io/src/lib/rbac.ts`):

| Permissão | ADMIN | ANALISTA_DADOS | PRODUTOR_EXPORTADOR |
|---|:-:|:-:|:-:|
| `dashboard:read`, `forecast:read`, `climate:read`, `sensors:read` | ✅ | ✅ | ✅ |
| `analytics:read`, `users:read` | ✅ | ✅ | — |
| `sensors:write`, `users:write` | ✅ | — | — |

O papel de cada perfil:
- **`PRODUTOR_EXPORTADOR`:** consulta o painel, as previsões de safra, os talhões, os sensores e os alertas.
- **`ANALISTA_DADOS`:** tem os mesmos acessos do produtor, mais análises e a consulta de usuários.
- **`ADMIN`:** gerencia usuários, estações e as configurações globais do sistema.
