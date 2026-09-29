# Dashboard de Monitoramento Climático e Logístico — Agronegócio (Vale do São Francisco)

Solução em nuvem para ingestão, processamento e análise preditiva de dados climáticos (IoT) e de mercado, voltada à otimização da janela de colheita e exportação de frutas na região de Petrolina/Juazeiro.

Projeto Integrador desenvolvido para o 4º módulo de Análise e Desenvolvimento de Sistemas (ADS).

---

## 🛠️ Tecnologias e Ferramentas

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| Framework web | FastAPI (Uvicorn) |
| Banco de dados | PostgreSQL 15 (Docker) |
| ORM | SQLAlchemy |
| IoT / Ingestão | ThingSpeak REST API / ESP32 |
| Execução | Docker e Docker Compose |

---

## 📋 Arquitetura e Fluxo de Dados

1. **Camada IoT:** o microcontrolador ESP32 coleta temperatura e umidade em intervalos regulares e publica no canal do ThingSpeak via HTTP/MQTT.
2. **Camada de ingestão (back-end):** a API em FastAPI consome periodicamente os *channel feeds* do ThingSpeak, respeitando os limites da API REST pública.
3. **Persistência:** os dados de telemetria climática e as cotações de mercado são higienizados e gravados no banco de dados relacional.
4. **Camada analítica e de apresentação:** módulos de previsão geram alertas sobre a janela ideal de safra, disponíveis no dashboard operacional.

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

Crie um arquivo `.env` na raiz do projeto com o modelo abaixo:

```env
DATABASE_URL=postgresql://admin:adminpassword@localhost:5432/agrotech_db
THINGSPEAK_CHANNEL_ID=seu_channel_id_aqui
THINGSPEAK_READ_KEY=sua_read_api_key_aqui
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

## 📖 Documentação da API

Com a aplicação em execução, a documentação interativa gerada automaticamente pelo OpenAPI pode ser acessada em:

- **Swagger UI:** <http://localhost:8000/docs>
- **ReDoc:** <http://localhost:8000/redoc>

---

## 🔒 Segurança e Boas Práticas

- Credenciais sensíveis e chaves de acesso a serviços externos (como o ThingSpeak) **não** são versionadas; o arquivo `.env` deve permanecer no `.gitignore`.
- A validação estrutural dos dados de entrada e as comunicações com o banco de dados seguem modelos Pydantic rigorosos.
