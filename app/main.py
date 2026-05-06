from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, SessionLocal
from app.models import Base, Categoria, CentroCusto, Conta, Usuario
from app.auth import hash_password
from app.templates_config import templates
from app.routers import auth, dashboard, lancamentos, transacoes, conciliacao, relatorios, cadastros


def _seed_database():
    db = SessionLocal()
    try:
        if not db.query(Usuario).filter(Usuario.email == settings.admin_email).first():
            db.add(Usuario(
                nome="Administrador",
                email=settings.admin_email,
                senha_hash=hash_password(settings.admin_password),
                ativo=True,
                is_admin=True,
            ))

        if not db.query(Conta).first():
            db.add(Conta(nome="Conta Corrente Principal", tipo="corrente", saldo_inicial=0))

        if not db.query(Categoria).first():
            cats_entrada = [
                ("Dízimos", "#4CAF7D"), ("Ofertas", "#4CAF7D"), ("Doações", "#4CAF7D"),
                ("Eventos", "#4CAF7D"), ("Outros Ingressos", "#4CAF7D"),
            ]
            cats_saida = [
                ("Pessoal", "#E8A838"), ("Infraestrutura", "#E8A838"),
                ("Mídias e Marketing", "#E8A838"), ("Instrumentos e Equipamentos", "#E8A838"),
                ("Viagens e Eventos", "#E8A838"), ("Despesas Administrativas", "#E8A838"),
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
            pessoal = next((c for c in pais if c.nome == "Pessoal"), None)
            if pessoal:
                for sub in ["Salários", "Ajuda de Custo", "Benefícios"]:
                    db.add(Categoria(nome=sub, tipo="saida", categoria_pai_id=pessoal.id, cor="#E8A838", ativo=True))

        if not db.query(CentroCusto).first():
            for nome in ["Ministerio Geral", "Louvor e Adoração", "Eventos", "Administrativo"]:
                db.add(CentroCusto(nome=nome, ativo=True))

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_database()
    yield


app = FastAPI(title="Asafe Finance — Ministério Asafe Vocal", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
