import json
from datetime import date, datetime
from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment

from app.database import engine, SessionLocal
from app.models import Base, Usuario, Categoria, CentroCusto, Conta
from app.auth import hash_password
from app.routers import auth, dashboard, lancamentos, transacoes, conciliacao, relatorios, cadastros

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Asafe Finance — Ministério Asafe Vocal")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configure Jinja2 with custom filters and globals
templates = Jinja2Templates(directory="app/templates")

def _tojson(value):
    def default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    return json.dumps(value, default=default)

templates.env.filters["tojson"] = _tojson
templates.env.globals["now"] = datetime.now
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(lancamentos.router)
app.include_router(transacoes.router)
app.include_router(conciliacao.router)
app.include_router(relatorios.router)
app.include_router(cadastros.router)


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return templates.TemplateResponse("403.html", {"request": request}, status_code=403)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


def seed_database():
    db = SessionLocal()
    try:
        # Admin user
        if not db.query(Usuario).filter(Usuario.email == "admin@sistema.com").first():
            admin = Usuario(
                nome="Administrador",
                email="admin@sistema.com",
                senha_hash=hash_password("admin123"),
                ativo=True,
                is_admin=True,
            )
            db.add(admin)

        # Default conta
        if not db.query(Conta).first():
            db.add(Conta(nome="Conta Corrente Principal", tipo="corrente", saldo_inicial=0))

        # Categorias base
        if not db.query(Categoria).first():
            cats_entrada = [
                ("Dízimos", "#4CAF7D"),
                ("Ofertas", "#4CAF7D"),
                ("Doações", "#4CAF7D"),
                ("Eventos", "#4CAF7D"),
                ("Outros Ingressos", "#4CAF7D"),
            ]
            cats_saida = [
                ("Pessoal", "#E8A838"),
                ("Infraestrutura", "#E8A838"),
                ("Mídias e Marketing", "#E8A838"),
                ("Instrumentos e Equipamentos", "#E8A838"),
                ("Viagens e Eventos", "#E8A838"),
                ("Despesas Administrativas", "#E8A838"),
            ]
            pais = []
            for nome, cor in cats_entrada:
                c = Categoria(nome=nome, tipo="entrada", cor=cor, ativo=True)
                db.add(c)
                pais.append(c)
            for nome, cor in cats_saida:
                c = Categoria(nome=nome, tipo="saida", cor=cor, ativo=True)
                db.add(c)
                pais.append(c)
            db.flush()

            # Subcategorias para "Pessoal"
            pessoal = next((c for c in pais if c.nome == "Pessoal"), None)
            if pessoal:
                for sub in ["Salários", "Ajuda de Custo", "Benefícios"]:
                    db.add(Categoria(nome=sub, tipo="saida", categoria_pai_id=pessoal.id, cor="#E8A838", ativo=True))

        # Centro de custo padrão
        if not db.query(CentroCusto).first():
            for nome in ["Ministerio Geral", "Louvor e Adoração", "Eventos", "Administrativo"]:
                db.add(CentroCusto(nome=nome, ativo=True))

        db.commit()
    finally:
        db.close()


seed_database()
