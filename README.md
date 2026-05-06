# Asafe Finance — Sistema de Controle de Fluxo de Caixa
### Ministério Asafe Vocal

## Desenvolvimento local

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Copiar e ajustar variáveis de ambiente (opcional para dev)
cp .env.example .env

# 4. Executar
uvicorn app.main:app --reload
```

Acesse: http://127.0.0.1:8000

**Credenciais padrão:** `admin@sistema.com` / `admin123`

---

## Deploy no Google Cloud Run + Supabase

### Pré-requisitos

```bash
gcloud auth login
gcloud config set project SEU_PROJECT_ID
```

### 1. Configurar o banco no Supabase

1. Crie um projeto em [supabase.com](https://supabase.com)
2. Vá em **Project Settings → Database**
3. Copie a string de conexão do **Transaction Pooler** (porta 6543 — recomendado para Cloud Run)

A URL terá este formato:
```
postgresql+psycopg2://postgres.[ref]:[senha]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require
```

> Use o **Transaction Pooler** (porta 6543), não a conexão direta (porta 5432).
> O Transaction Pooler é compatível com ambientes serverless e evita esgotar as conexões.

### 2. Criar os segredos no Secret Manager

```bash
# Chave JWT — string aleatória forte
echo -n "$(python -c 'import secrets; print(secrets.token_hex(32))')" | \
  gcloud secrets create asafe-secret-key --data-file=-

# URL do Supabase (Transaction Pooler)
echo -n "postgresql+psycopg2://postgres.[ref]:[senha]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require" | \
  gcloud secrets create asafe-database-url --data-file=-
```

### 3. Criar o repositório no Artifact Registry

```bash
gcloud artifacts repositories create asafe-finance \
  --repository-format=docker \
  --location=us-central1
```

### 4. Configurar permissões do Cloud Build

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"

gcloud iam service-accounts add-iam-policy-binding \
  $PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --member="serviceAccount:$SA" --role="roles/iam.serviceAccountUser"
```

### 5. Deploy

```bash
# Via Cloud Build (recomendado)
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_REPO=asafe-finance,_SERVICE=asafe-finance

# Ou manual via Docker:
IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/asafe-finance/asafe-finance:latest"
docker build -t $IMAGE .
docker push $IMAGE

gcloud run deploy asafe-finance \
  --image=$IMAGE \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-secrets="SECRET_KEY=asafe-secret-key:latest,DATABASE_URL=asafe-database-url:latest" \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=5
```

### 6. CI/CD automático com Cloud Build Trigger

```bash
gcloud builds triggers create github \
  --repo-name=Asafe-Finance \
  --repo-owner=SEU_USUARIO_GITHUB \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_REPO=asafe-finance,_SERVICE=asafe-finance
```

### Variáveis de ambiente em produção

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| `DATABASE_URL` | URL do Supabase (Transaction Pooler) com `?sslmode=require` | Sim |
| `SECRET_KEY` | Chave JWT (32+ chars aleatórios) | Sim |
| `ADMIN_EMAIL` | E-mail do admin inicial | Não (padrão: `admin@sistema.com`) |
| `ADMIN_PASSWORD` | Senha do admin inicial | Não (padrão: `admin123`) |

> **Importante:** Troque `ADMIN_PASSWORD` imediatamente após o primeiro acesso em produção.

---

## Migrations (Alembic)

```bash
# Gerar nova migration após mudanças nos models
alembic revision --autogenerate -m "descricao_da_mudanca"

# Aplicar migrations
alembic upgrade head

# Reverter a última migration
alembic downgrade -1
```

## Estrutura

```
app/
├── main.py              # Ponto de entrada + lifespan + seed
├── config.py            # Settings via env vars (pydantic-settings)
├── database.py          # Engine SQLAlchemy (SQLite local / Supabase prod)
├── models.py            # Modelos ORM
├── schemas.py           # Validações Pydantic
├── auth.py              # JWT + bcrypt
├── templates_config.py  # Instância Jinja2 compartilhada com filtros
├── routers/             # Rotas FastAPI
├── services/            # OFX, relatórios, exportação
└── templates/           # Jinja2 + HTMX
alembic/                 # Migrations
Dockerfile
startup.sh               # Entrypoint: migrations + uvicorn
cloudbuild.yaml          # CI/CD Cloud Build
.env.example             # Template de variáveis de ambiente
```
