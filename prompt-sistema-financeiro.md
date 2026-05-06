  # Prompt — Sistema de Controle de Fluxo de Caixa

## Contexto

Crie um sistema web de controle de fluxo de caixa completo usando **FastAPI + HTMX + Jinja2 + SQLite**. O sistema deve ser multi-usuário com autenticação, e distinguir claramente entre **lançamentos** (referência contábil) e **transações** (movimentação monetária real), permitindo conciliação bancária via arquivo OFX.

---

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy (ORM), Alembic (migrations)
- **Frontend:** Jinja2 templates, HTMX, TailwindCSS via CDN, Chart.js via CDN
- **Banco:** SQLite
- **Auth:** JWT com cookies httpOnly, bcrypt para senhas
- **OFX:** biblioteca `ofxparse` para leitura de extratos
- **Exportação:** `reportlab` para PDF, `openpyxl` para Excel

---

## Identidade Visual — Ministério Asafe Vocal

O sistema deve seguir rigorosamente a paleta de cores e tipografia do Ministério Asafe Vocal.

### Paleta de cores (variáveis CSS globais)
```css
:root {
  --azul-profundo:   #0A2540;  /* fundo principal de páginas */
  --azul-escuro:     #061826;  /* sidebar, navbar, cabeçalhos */
  --dourado:         #D4AF37;  /* botões primários, destaques, bordas ativas */
  --dourado-claro:   #F5E6A7;  /* textos dourados secundários, ícones */
  --dourado-escuro:  #B8860B;  /* hover de botões, gradiente inicial */
  --branco-suave:    #F8F8F8;  /* textos principais sobre fundo escuro */
  --gradiente-ouro:  linear-gradient(90deg, #B8860B, #D4AF37, #F5E6A7);
}
```

### Aplicação das cores
- **Fundo geral:** `--azul-profundo`
- **Sidebar / Navbar:** `--azul-escuro`
- **Botões primários (Salvar, Confirmar):** fundo `--dourado`, texto `--azul-escuro`, hover `--dourado-escuro`
- **Botões secundários:** borda `--dourado`, texto `--dourado-claro`, fundo transparente
- **Links e itens ativos no menu:** `--dourado-claro`
- **Cards do dashboard:** fundo `--azul-escuro`, borda sutil `--dourado` com baixa opacidade
- **Tabelas:** cabeçalho `--azul-escuro`, linhas alternadas com leve variação de `--azul-profundo`
- **Inputs e selects:** fundo `--azul-escuro`, borda `--dourado` ao focar, texto `--branco-suave`
- **Separadores e divisores:** `--gradiente-ouro` como linha decorativa fina
- **Status "realizado":** verde suave `#4CAF7D`; **"previsto":** `--dourado-claro`; **"parcial":** laranja `#E8A838`

### Tipografia (via Google Fonts)
```html
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Montserrat:wght@300;400;500;600&family=Great+Vibes&display=swap" rel="stylesheet">
```
- **Títulos de página e seções:** `Cinzel`, weight 600 — ex: "LANÇAMENTOS", "RELATÓRIOS"
- **Interface geral (labels, textos, tabelas):** `Montserrat`, weight 400/500
- **Nome do sistema / branding no topo da sidebar:** `Great Vibes` — "Ministério Asafe Vocal"

### Elementos visuais
- Sidebar com logo do ministério no topo (usar texto estilizado se não houver arquivo de imagem)
- Linha decorativa dourada (`--gradiente-ouro`) abaixo do header e separando seções
- Ícones em `--dourado-claro` (usar Heroicons ou Feather Icons via CDN)
- Gráficos Chart.js: cores de entrada em `#D4AF37`, saídas em `#4A7FBF`, saldo em `#F5E6A7`
- Modais com fundo `--azul-escuro`, borda `--dourado`, overlay escuro semitransparente

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

### Tabela `lancamentos`
- id, descricao, tipo (enum: entrada, saida), valor_total (decimal 10,2), data_competencia (date)
- status (enum: previsto, parcial, realizado) — calculado automaticamente com base nas transações vinculadas
- categoria_id (FK), centro_custo_id (FK, nullable), usuario_id (FK), observacao (text), created_at, updated_at

### Tabela `transacoes`
- id, descricao, tipo (enum: entrada, saida), valor (decimal 10,2), data_pagamento (date)
- conta_id (FK), forma_pagamento (enum: pix, boleto, ted, doc, debito, credito, dinheiro, outro)
- status_conciliacao (enum: pendente, conciliado, ignorado)
- ofx_transaction_id (varchar, nullable — ID único do OFX para evitar duplicatas)
- usuario_id (FK), created_at

### Tabela `lancamento_transacao` (junção N:N)
- id, lancamento_id (FK), transacao_id (FK), valor_vinculado (decimal 10,2)
- Um lançamento pode ser pago por N transações; uma transação pode cobrir N lançamentos

### Tabela `ofx_imports`
- id, conta_id (FK), arquivo_nome, data_inicio, data_fim, total_registros, importado_em, usuario_id (FK)

---

## Páginas e funcionalidades

### 🔐 Autenticação
- GET/POST `/login` — formulário de login com JWT em cookie httpOnly
- POST `/logout`
- GET/POST `/alterar-senha`

### 📊 Dashboard (`/`)
- Cards: saldo total consolidado, saldo por conta, total entradas do mês, total saídas do mês
- Gráfico de linha: fluxo do mês atual (entradas vs saídas por dia)
- Tabela: lançamentos vencidos não realizados (data_competencia < hoje e status != realizado)
- Alerta: quantidade de transações pendentes de conciliação

### 📋 Lançamentos (`/lancamentos`)
- Lista paginada com filtros: período (data_competencia), tipo, status, categoria, centro de custo
- Formulário de criação/edição via modal HTMX (sem reload de página)
- Ao editar, exibir transações já vinculadas e valor já coberto vs valor total
- Exclusão com confirmação
- Status calculado automaticamente: previsto (sem transações), parcial (soma vinculada < valor_total), realizado (soma vinculada >= valor_total)

### 💸 Transações (`/transacoes`)
- Lista paginada com filtros: conta, período, forma de pagamento, status de conciliação
- Criação/edição manual via modal HTMX
- Botão "Vincular a lançamento" — abre busca de lançamentos compatíveis (mesmo tipo, período próximo)

### 🔄 Conciliação Bancária (`/conciliacao`)
- Upload de arquivo OFX vinculado a uma conta
- Sistema parseia o OFX e importa transações com status `pendente`, ignorando duplicatas (via ofx_transaction_id)
- Tela de conciliação: lista de transações pendentes lado a lado com sugestões de lançamentos compatíveis (por valor e data)
- Ações por transação: Vincular a lançamento existente | Criar novo lançamento | Ignorar
- Histórico de importações OFX

### 📈 Relatórios (`/relatorios`)

Todos os relatórios têm:
- Filtros: período (data início/fim), conta, categoria, centro de custo
- Botões de exportação: PDF e Excel

**1. Fluxo de Caixa**
- Gráfico de barras agrupadas: entradas vs saídas por mês/semana/dia (conforme período)
- Gráfico de linha: saldo acumulado no tempo
- Tabela resumo: período, entradas, saídas, saldo do período, saldo acumulado

**2. Por Categoria**
- Gráfico de pizza: distribuição de saídas por categoria
- Gráfico de pizza: distribuição de entradas por categoria
- Tabela hierárquica: categoria > subcategorias com totais e percentuais

**3. Por Centro de Custo**
- Gráfico de barras horizontais comparando centros de custo
- Tabela: centro de custo, total entradas, total saídas, saldo

**4. Previsto vs Realizado**
- Tabela: categoria, valor previsto, valor realizado, diferença, percentual executado
- Gráfico de barras: previsto (cinza) vs realizado (cor) por categoria

**5. Extrato por Conta**
- Selecionar conta e período
- Tabela cronológica de todas as transações com saldo running (saldo corrente após cada transação)

### ⚙️ Cadastros

**Contas** (`/cadastros/contas`) — CRUD completo
**Categorias** (`/cadastros/categorias`) — CRUD com hierarquia pai/filho, exibição em árvore
**Centros de Custo** (`/cadastros/centros-custo`) — CRUD completo
**Usuários** (`/cadastros/usuarios`) — **exclusivo para administradores (`is_admin = true`)**. CRUD completo com ativação/desativação. Usuários não-admin não enxergam este menu e recebem erro 403 se tentarem acessar a URL diretamente. Somente admins podem criar novos usuários, editar perfis alheios, redefinir senhas e alterar o nível de acesso.

---

## Comportamentos importantes

1. **Status do lançamento** é sempre calculado dinamicamente pela soma dos `valor_vinculado` na tabela `lancamento_transacao`, nunca salvo manualmente.

2. **Saldo das contas** é sempre calculado pela soma das transações (não pelo saldo_inicial isolado). saldo_inicial é o ponto de partida.

3. **Conciliação OFX:** ao importar, verificar `ofx_transaction_id` para evitar duplicatas. Transações importadas ficam com `status_conciliacao = pendente` até o usuário agir.

4. **Subcategorias:** ao exibir selects de categoria nos formulários, mostrar agrupado (optgroup por categoria pai) e permitir selecionar apenas subcategorias (folhas), nunca a categoria pai diretamente em lançamentos.

5. **HTMX:** usar `hx-boost`, `hx-target`, `hx-swap` para todas as interações de formulário e listagem. Modais via `hx-get` + fragment de template. Evitar reloads completos de página.

6. **Autenticação:** todas as rotas protegidas por middleware que valida o JWT do cookie. Rota `/login` é pública.

7. **Controle de acesso admin:** criar decorator `require_admin` aplicado a todas as rotas de `/cadastros/usuarios`. Verificar `is_admin` no token JWT. Menu lateral deve ocultar o item "Usuários" para não-admins via condicional no template Jinja2 (`{% if current_user.is_admin %}`). Retornar 403 com página de erro amigável se não-admin tentar acessar via URL direta.

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
│   ├── transacoes.py
│   ├── conciliacao.py
│   ├── relatorios.py
│   └── cadastros.py
├── services/
│   ├── ofx_service.py
│   ├── relatorio_service.py
│   └── export_service.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── lancamentos/
│   ├── transacoes/
│   ├── conciliacao/
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

- Criar o projeto completo e funcional, não apenas esqueleto
- Começar pelo modelo de dados e migrations (Alembic)
- Implementar autenticação antes de qualquer outra rota
- Usar `async` no FastAPI onde possível
- Seed inicial: criar usuário admin padrão (admin@sistema.com / admin123) e categorias básicas de exemplo
- Validar todos os formulários no backend (Pydantic schemas)
- Tratar erros com mensagens amigáveis em português
- README com instruções de instalação e execução
