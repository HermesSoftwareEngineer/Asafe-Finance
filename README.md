# Asafe Finance — Sistema de Controle de Fluxo de Caixa
### Ministério Asafe Vocal

## Requisitos

- Python 3.11+

## Instalação

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Executar o servidor
uvicorn app.main:app --reload
```

Acesse: http://127.0.0.1:8000

## Credenciais padrão

| Campo | Valor |
|-------|-------|
| E-mail | `admin@sistema.com` |
| Senha | `admin123` |

> **Altere a senha após o primeiro acesso!**

## Funcionalidades

- **Dashboard** — saldo consolidado, fluxo do mês, alertas de vencidos
- **Lançamentos** — referência contábil (previsto/parcial/realizado)
- **Transações** — movimentações reais com vinculação a lançamentos
- **Conciliação Bancária** — importação OFX, sugestão automática de vínculos
- **Relatórios** — Fluxo de Caixa, Por Categoria, Por Centro de Custo, Previsto vs Realizado, Extrato por Conta
- **Cadastros** — Contas, Categorias (hierárquicas), Centros de Custo, Usuários (admin)

## Estrutura

```
app/
├── main.py           # Ponto de entrada + seed inicial
├── database.py       # Conexão SQLite + SQLAlchemy
├── models.py         # Modelos ORM
├── schemas.py        # Validações Pydantic
├── auth.py           # JWT + bcrypt
├── routers/          # Rotas FastAPI
├── services/         # OFX, relatórios, exportação
└── templates/        # Jinja2 + HTMX
alembic/              # Migrations de banco
```

## Migrações (Alembic)

O banco é criado automaticamente na primeira execução via `Base.metadata.create_all()`.  
Para usar migrações Alembic com controle de versão:

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```
