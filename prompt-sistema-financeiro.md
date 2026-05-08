# Prompt — Sistema de Controle de Fluxo de Caixa (Unificado em Lançamentos)

## Contexto

Refatore o sistema web de controle de fluxo de caixa para unificar tudo em **lançamentos**, removendo completamente a distinção entre lançamentos (referência contábil) e transações (movimentação real). Agora, um lançamento representa tanto a previsão quanto a realização financeira. Remova todas as tabelas, endpoints, páginas e funcionalidades relacionadas a transações, conciliação bancária via OFX e vinculações N:N. Simplifique o modelo para focar exclusivamente em lançamentos, que agora incorporam campos de realização (como data de pagamento, forma de pagamento e status de conciliação). A conciliação OFX, se mantida, deve importar lançamentos diretamente como realizados.

Essa é uma alteração total e crítica: o sistema passa a ser centrado em lançamentos únicos, eliminando a complexidade de transações separadas.

---

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy (ORM), Alembic (migrations)
- **Frontend:** Jinja2 templates, HTMX, TailwindCSS via CDN, Chart.js via CDN
- **Banco:** SQLite
- **Auth:** JWT com cookies httpOnly, bcrypt para senhas
- **Exportação:** `reportlab` para PDF, `openpyxl` para Excel
- **(Removido):** OFX parsing e biblioteca `ofxparse` — se conciliação for mantida, simplificar para importação direta de lançamentos via CSV ou similar, sem OFX.

---

## Identidade Visual — Ministério Asafe Vocal

Mantenha rigorosamente a paleta de cores, tipografia e elementos visuais descritos no prompt original. Ajuste apenas os status visuais se necessário (ex: status único baseado em realização).

---

## Modelo de dados

### Tabela `usuarios`
- id, nome, email (único), senha_hash, ativo (bool), is_admin (bool), created_at

### Tabela `contas`
- id, nome, tipo (enum: corrente, poupanca, caixa, outro), saldo_inicial (decimal), ativo (bool)

### Tabela `categorias`
- id, nome, tipo (enum: entrada, saida), categoria_pai_id (FK self, nullable — para subcategorias), cor (hex), ativo (bool)
- Regra: máximo 2 níveis (categoria → subcategoria). Subcategoria não pode ter filhos.

### Tabela `centros_custo`
- id, nome, ativo (bool)

### Tabela `lancamentos` (unificado — incorpora campos de realização)
- id, descricao, tipo (enum: entrada, saida), valor_total (decimal 10,2), data_competencia (date)
- status (enum: previsto, realizado) — previsto se data_pagamento é null; realizado se data_pagamento está preenchida
- data_pagamento (date, nullable) — quando preenchida, o lançamento é considerado realizado
- forma_pagamento (enum: pix, boleto, ted, doc, debito, credito, dinheiro, outro, nullable)
- categoria_id (FK), centro_custo_id (FK, nullable), conta_id (FK), usuario_id (FK), observacao (text), created_at, updated_at
- (Removido: recorrência, parcelas, vinculações — simplificar para lançamentos únicos ou recorrentes manuais)

### (Removidas:)
- Tabela `transacoes`
- Tabela `lancamento_transacao`
- Tabela `ofx_imports`

---

## Páginas e funcionalidades

### 🔐 Autenticação
- Mantenha como no prompt original.

### 📊 Dashboard (`/`)
- Cards: saldo total consolidado (baseado em lançamentos realizados), saldo por conta, total entradas do mês, total saídas do mês
- Gráfico de linha: fluxo do mês atual (entradas vs saídas por dia, baseado em data_competencia ou data_pagamento)
- Tabela: lançamentos previstos vencidos (data_competencia < hoje e status = previsto)
- (Removido: alertas de transações pendentes)

### 📋 Lançamentos (`/lancamentos`) — agora central
- Lista paginada com filtros: período (data_competencia ou data_pagamento), tipo, status, categoria, centro de custo, conta
- Formulário de criação/edição via modal HTMX: incluir campos de realização (data_pagamento, forma_pagamento) — ao preencher data_pagamento, status muda para realizado automaticamente
- Exclusão com confirmação
- Status calculado: previsto (data_pagamento null), realizado (data_pagamento preenchida)

### (Removidas:)
- 📋 Transações (`/transacoes`)
- 🔄 Conciliação Bancária (`/conciliacao`)

### 📈 Relatórios (`/relatorios`)

Todos os relatórios têm:
- Filtros: período (data_competencia ou data_pagamento), conta, categoria, centro de custo
- Botões de exportação: PDF e Excel

**1. Fluxo de Caixa**
- Gráfico de barras agrupadas: entradas vs saídas por mês/semana/dia
- Gráfico de linha: saldo acumulado no tempo (baseado em lançamentos realizados)
- Tabela resumo: período, entradas, saídas, saldo do período, saldo acumulado

**2. Por Categoria**
- Gráfico de pizza: distribuição de saídas/entradas por categoria
- Tabela hierárquica: categoria > subcategorias com totais e percentuais

**3. Por Centro de Custo**
- Gráfico de barras horizontais comparando centros de custo
- Tabela: centro de custo, total entradas, total saídas, saldo

**4. Previsto vs Realizado**
- Tabela: categoria, valor previsto (status previsto), valor realizado (status realizado), diferença
- Gráfico de barras: previsto vs realizado por categoria

**5. Extrato por Conta**
- Selecionar conta e período
- Tabela cronológica de lançamentos realizados com saldo running

### ⚙️ Cadastros

Mantenha como no prompt original: Contas, Categorias, Centros de Custo, Usuários.

---

## Comportamentos importantes

1. **Status do lançamento** é calculado dinamicamente: previsto se data_pagamento é null; realizado se preenchida. Não há mais "parcial".

2. **Saldo das contas** é calculado pela soma dos lançamentos realizados (tipo entrada + valor, saida - valor), somado ao saldo_inicial.

3. **(Removido: Conciliação OFX)** — se necessário, adicionar importação simples via CSV para criar lançamentos realizados diretamente.

4. **Subcategorias:** mantenha como no original.

5. **HTMX:** mantenha como no original.

6. **Autenticação e controle de acesso:** mantenha como no original.

---

## Estrutura de arquivos sugerida

```
app/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── auth.py
├── routers/
│   ├── auth.py
│   ├── dashboard.py
│   ├── lancamentos.py
│   ├── relatorios.py
│   └── cadastros.py
├── services/
│   ├── relatorio_service.py
│   └── export_service.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── lancamentos/
│   ├── relatorios/
│   └── cadastros/
└── static/
    └── css/

alembic/
requirements.txt
README.md
```

---

## Instruções finais para o Claude Code

- Refatore o projeto completo para essa nova arquitetura, removendo todo código relacionado a transações, conciliação e OFX.
- Atualize migrations Alembic para remover tabelas e ajustar lancamentos.
- Ajuste todos os templates, routers e services conforme as mudanças.
- Seed inicial: mantenha usuário admin e categorias básicas.
- Valide formulários e tratamentos de erro em português.
- README atualizado com as mudanças.