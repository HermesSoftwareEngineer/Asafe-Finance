# API Routes — Asafe Finance

Sistema de fluxo de caixa centrado em **lançamentos**. Cada lançamento tem uma única data e status explícito: `pago` ou `a pagar`.

---

## Autenticação

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/login` | Login (seta cookie httpOnly `access_token`) |
| POST | `/api/auth/logout` | Logout (remove cookie) |
| GET | `/api/auth/me` | Dados do usuário logado |
| POST | `/api/auth/alterar-senha` | Alterar senha do usuário logado |

---

## Dashboard

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/dashboard` | KPIs: saldo total, entradas/saídas do mês, vencidos, OFX pendentes, gráfico diário |

**Resposta:**
```json
{
  "saldo_total": 1500.00,
  "entradas_mes": 3000.00,
  "saidas_mes": 1500.00,
  "lancamentos_vencidos": 2,
  "ofx_pendentes": 5,
  "lancamentos_nao_conciliados": 3,
  "saldos_conta": [...],
  "chart_labels": ["01/05", "02/05"],
  "chart_entradas": [0, 500],
  "chart_saidas": [0, 200]
}
```

---

## Lançamentos

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/lancamentos` | Listar lançamentos (paginado, com filtros) |
| POST | `/api/lancamentos` | Criar lançamento (único, fixo ou parcelado) |
| PUT | `/api/lancamentos/{id}` | Editar lançamento (opções: apenas este, todos da sequência, apenas este e futuros) |
| DELETE | `/api/lancamentos/{id}` | Excluir lançamento (opções: apenas este, todos da sequência, apenas este e futuros) |
| GET | `/api/lancamentos/{id}/serie` | Listar todos os lançamentos de uma série (fixo/parcelado) |
| DELETE | `/api/lancamentos/{id}/serie` | Excluir todos os lançamentos de uma série |
| POST | `/api/lancamentos/{id}/gerar-proximo` | Gerar próxima ocorrência de um lançamento fixo |

### Escopo de edição/exclusão em lançamentos recorrentes
Os endpoints `PUT /api/lancamentos/{id}` e `DELETE /api/lancamentos/{id}` aceitam o query param `scope` com valores:
- `only` — aplica apenas ao lançamento atual
- `all` — aplica a toda a sequência (root + todas as ocorrências)
- `future` — aplica ao lançamento atual e às ocorrências futuras da sequência

Exemplos:
- `PUT /api/lancamentos/123?scope=only`
- `PUT /api/lancamentos/123?scope=all`
- `PUT /api/lancamentos/123?scope=future`
- `DELETE /api/lancamentos/123?scope=only`
- `DELETE /api/lancamentos/123?scope=all`
- `DELETE /api/lancamentos/123?scope=future`

### Filtros (GET /api/lancamentos)
- `page` — página (default: 1)
- `tipo` — `entrada` | `saida`
- `status` — `pago` | `a pagar`
- `tipo_recorrencia` — `unico` | `fixo` | `parcelado`
- `status_conciliacao` — `pendente` | `conciliado` | `ignorado`
- `categoria_id` — ID da categoria
- `centro_custo_id` — ID do centro de custo
- `conta_id` — ID da conta
- `data_inicio` — filtro por `data` >= (YYYY-MM-DD)
- `data_fim` — filtro por `data` <= (YYYY-MM-DD)

### Body (POST / PUT)
```json
{
  "descricao": "Dízimos de maio",
  "tipo": "entrada",
  "valor_total": 1500.00,
  "data": "2026-05-05",
  "status": "pago",
  "conta_id": 1,
  "categoria_id": 1,
  "centro_custo_id": null,
  "observacao": null,
  "tipo_recorrencia": "unico",
  "frequencia_recorrencia": null,
  "total_parcelas": null
}
```

**Status:**
- `a pagar` — lançamento previsto (default)
- `pago` — lançamento realizado; `status_conciliacao` é definido como `pendente` automaticamente

**Recorrência (`tipo_recorrencia`):**
- `unico` — lançamento avulso (default); os demais campos de recorrência são ignorados
- `fixo` — se repete indefinidamente na `frequencia_recorrencia`; use `POST /{id}/gerar-proximo` para criar a próxima ocorrência manualmente
- `parcelado` — dividido em `total_parcelas` parcelas de mesmo valor na `frequencia_recorrencia`; todas as parcelas são criadas de uma vez no POST

**Frequência (`frequencia_recorrencia`):** obrigatória para `fixo` e `parcelado`
- `diaria` | `semanal` | `quinzenal` | `mensal`

**Exemplo — parcelado em 3x mensais:**
```json
{
  "descricao": "Compra parcelada",
  "tipo": "saida",
  "valor_total": 300.00,
  "data": "2026-05-01",
  "status": "a pagar",
  "conta_id": 1,
  "tipo_recorrencia": "parcelado",
  "frequencia_recorrencia": "mensal",
  "total_parcelas": 3
}
```

**Exemplo — fixo mensal:**
```json
{
  "descricao": "Aluguel",
  "tipo": "saida",
  "valor_total": 1200.00,
  "data": "2026-05-05",
  "status": "a pagar",
  "conta_id": 1,
  "tipo_recorrencia": "fixo",
  "frequencia_recorrencia": "mensal"
}
```

### Resposta (lançamento único ou fixo)
```json
{
  "id": 1,
  "descricao": "Dízimos de maio",
  "tipo": "entrada",
  "valor_total": 1500.00,
  "data": "2026-05-05",
  "status": "pago",
  "tipo_recorrencia": "unico",
  "frequencia_recorrencia": null,
  "total_parcelas": null,
  "numero_parcela": null,
  "lancamento_pai_id": null,
  "status_conciliacao": "pendente",
  "ofx_transaction_id": null,
  "conta_id": 1,
  "conta_nome": "Conta Corrente Principal",
  "categoria_id": 1,
  "categoria_nome": "Dízimos",
  "categoria_icone": "🎵",
  "centro_custo_id": null,
  "centro_custo_nome": null,
  "observacao": null
}
```

### Resposta (parcelado — criação retorna todas as parcelas)
```json
{
  "total_criados": 3,
  "lancamentos": [
    { "id": 1, "descricao": "Compra parcelada (1/3)", "numero_parcela": 1, "lancamento_pai_id": null, "...": "..." },
    { "id": 2, "descricao": "Compra parcelada (2/3)", "numero_parcela": 2, "lancamento_pai_id": 1,    "...": "..." },
    { "id": 3, "descricao": "Compra parcelada (3/3)", "numero_parcela": 3, "lancamento_pai_id": 1,    "...": "..." }
  ]
}
```

### GET /{id}/serie — Listar série
```json
{
  "total": 3,
  "lancamentos": [ { "...": "..." }, "..." ]
}
```

### DELETE /{id}/serie — Excluir série
```json
{ "ok": true, "total_excluidos": 3 }
```

### POST /{id}/gerar-proximo — Gerar próxima ocorrência (apenas `fixo`)
Retorna o novo lançamento criado com a data calculada conforme a `frequencia_recorrencia`.

---

## Conciliação Bancária (OFX)

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/conciliacao/upload` | Upload de arquivo OFX (.ofx/.qfx, max 5 MB) |
| GET | `/api/conciliacao/pendentes` | Listar transações OFX pendentes com sugestões de match |
| PUT | `/api/conciliacao/vincular/{ofx_id}` | Vincular transação OFX a lançamento `pago` existente |
| PUT | `/api/conciliacao/criar-lancamento/{ofx_id}` | Criar novo lançamento `pago` a partir da transação OFX |
| PUT | `/api/conciliacao/ignorar/{ofx_id}` | Marcar transação OFX como ignorada |
| PUT | `/api/conciliacao/desvincular/{ofx_id}` | Desfazer conciliação de uma transação OFX |
| GET | `/api/conciliacao/historico` | Histórico de imports com resumo de status |
| GET | `/api/conciliacao/diferencas` | Lançamentos sem OFX e OFX sem lançamento no período |

### Upload OFX
```
POST /api/conciliacao/upload
Content-Type: multipart/form-data

conta_id: 1
file: extrato.ofx
```

### Vincular
```json
PUT /api/conciliacao/vincular/{ofx_id}
{ "lancamento_id": 15 }
```

### Criar Lançamento do OFX
```json
PUT /api/conciliacao/criar-lancamento/{ofx_id}
{
  "categoria_id": 1,
  "centro_custo_id": null,
  "observacao": null
}
```

### Filtros de pendentes
- `conta_id` — filtrar por conta
- `com_sugestoes` — `true` (default) inclui matches calculados
- `page` — paginação

### Status das transações OFX
- `pendente` — importada, aguarda conciliação
- `conciliado` — vinculada a um lançamento `pago`
- `ignorado` — descartada manualmente

### Algoritmo de Matching
Peso: valor 50% + data 40% + similaridade de descrição (`difflib`) 10%.
Score mínimo para sugestão: 0.3. Janela de busca: ±7 dias.

---

## Relatórios

Todos exigem autenticação. Suportam `formato=pdf` ou `formato=excel` para exportação.

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/relatorios/fluxo-caixa` | Fluxo de caixa por mês (lançamentos `pago`) |
| GET | `/api/relatorios/por-categoria` | Totais por categoria/subcategoria; tabela + dados para gráfico de pizza e linha; gráfico de pizza e série temporal (todas contas, `pago` e `a pagar`) |
| GET | `/api/relatorios/por-centro-custo` | Totais por centro de custo |
| GET | `/api/relatorios/previsto-realizado` | Previsto (`a pagar`) vs realizado (`pago`) por categoria |
| GET | `/api/relatorios/extrato-conta` | Extrato cronológico de uma conta (lançamentos `pago`) |

### Formato de retorno dos relatórios

#### GET `/api/relatorios/fluxo-caixa`
Retorna uma lista de períodos com totais de entradas, saídas, saldo e saldo acumulado.

```json
{
  "data_inicio": "2026-05-01",
  "data_fim": "2026-05-31",
  "conta_id": 1,
  "items": [
    {
      "periodo": "2026-05",
      "entradas": 3000.0,
      "saidas": 1500.0,
      "saldo": 1500.0,
      "saldo_acumulado": 1500.0
    }
  ]
}
```

#### GET `/api/relatorios/por-categoria`
Retorna:
- `categorias`: totais por categoria e subcategorias;
- `pie`: dados para gráfico de pizza, separados em `entrada` e `saida`;
- `series`: dados de linha ao longo do tempo, conforme `granularidade`.

```json
{
  "data_inicio": "2026-05-01",
  "data_fim": "2026-05-31",
  "granularidade": "mes",
  "filtros": {
    "categoria_ids": [1, 2]
  },
  "categorias": [
    {
      "categoria_id": 1,
      "categoria_nome": "Dízimos",
      "categoria_tipo": "entrada",
      "total": 1500.0,
      "subcategorias": [
        {
          "categoria_id": 10,
          "categoria_nome": "Dízimos Especiais",
          "total": 500.0
        }
      ]
    },
    {
      "categoria_id": 2,
      "categoria_nome": "Aluguel",
      "categoria_tipo": "saida",
      "total": 1200.0,
      "subcategorias": []
    }
  ],
  "pie": {
    "entrada": {
      "total": 1500.0,
      "items": [
        {
          "categoria_id": 1,
          "categoria_nome": "Dízimos",
          "total": 1500.0,
          "percentual": 100.0
        },
        {
          "categoria_id": 10,
          "categoria_nome": "Dízimos Especiais",
          "categoria_pai_id": 1,
          "total": 500.0,
          "percentual": 33.33
        }
      ]
    },
    "saida": {
      "total": 1200.0,
      "items": [
        {
          "categoria_id": 2,
          "categoria_nome": "Aluguel",
          "total": 1200.0,
          "percentual": 100.0
        }
      ]
    }
  },
  "series": {
    "granularidade": "mes",
    "items": [
      {
        "periodo": "2026-05",
        "entrada": 1500.0,
        "saida": 1200.0,
        "saldo": 300.0
      }
    ]
  }
}
```

#### GET `/api/relatorios/por-centro-custo`
Retorna totais agrupados por centro de custo.

```json
{
  "data_inicio": "2026-05-01",
  "data_fim": "2026-05-31",
  "items": [
    {
      "centro_id": 1,
      "centro_nome": "Marketing",
      "entradas": 500.0,
      "saidas": 1200.0,
      "saldo": -700.0
    }
  ]
}
```

#### GET `/api/relatorios/previsto-realizado`
Retorna totais previstos e realizados por categoria.

```json
{
  "data_inicio": "2026-05-01",
  "data_fim": "2026-05-31",
  "items": [
    {
      "categoria_id": 2,
      "categoria_nome": "Aluguel",
      "previsto": 1200.0,
      "realizado": 900.0,
      "diferenca": -300.0,
      "percentual": 75.0
    }
  ]
}
```

#### GET `/api/relatorios/extrato-conta`
Retorna histórico cronológico de lançamentos `pago` para uma conta.

```json
{
  "conta_id": 1,
  "conta_nome": "Conta Corrente Principal",
  "items": [
    {
      "lancamento_id": 10,
      "data": "2026-05-05",
      "descricao": "Salário",
      "valor_total": 3000.0,
      "tipo": "entrada",
      "saldo_corrente": 4500.0
    }
  ]
}
```

### Filtros comuns
- `data_inicio` (YYYY-MM-DD) — default: primeiro dia do mês
- `data_fim` (YYYY-MM-DD) — default: hoje
- `conta_id` — filtra por conta (onde aplicável)
- `categoria_ids` — lista de IDs de categoria/subcategoria para filtrar o relatório por categoria
- `granularidade` — `dia` | `semana` | `mes` — controla a série temporal no relatório por categoria
- `formato` — `pdf` | `excel` — força download

---

## Cadastros

### Contas

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/cadastros/contas` | Listar contas |
| POST | `/api/cadastros/contas` | Criar conta |
| PUT | `/api/cadastros/contas/{id}` | Editar conta |
| DELETE | `/api/cadastros/contas/{id}` | Excluir conta |

**Tipos:** `corrente`, `poupanca`, `caixa`, `outro`

### Categorias

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/cadastros/categorias` | Listar categorias (com subcategorias) |
| POST | `/api/cadastros/categorias` | Criar categoria (max 2 níveis) |
| PUT | `/api/cadastros/categorias/{id}` | Editar categoria |
| DELETE | `/api/cadastros/categorias/{id}` | Excluir categoria |

**Body:**
```json
{
  "nome": "Dízimos",
  "tipo": "entrada",
  "cor": "#4CAF7D",
  "icone": "🎵",
  "categoria_pai_id": null,
  "ativo": true
}
```
- `icone` — emoji ou nome de ícone (ex: `"🎵"`, `"music"`, `"fa-church"`)

### Centros de Custo

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/cadastros/centros-custo` | Listar centros de custo |
| POST | `/api/cadastros/centros-custo` | Criar centro de custo |
| PUT | `/api/cadastros/centros-custo/{id}` | Editar centro de custo |
| DELETE | `/api/cadastros/centros-custo/{id}` | Excluir centro de custo |

### Usuários (admin only)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/cadastros/usuarios` | Listar usuários |
| POST | `/api/cadastros/usuarios` | Criar usuário |
| PUT | `/api/cadastros/usuarios/{id}` | Editar usuário |
| DELETE | `/api/cadastros/usuarios/{id}` | Excluir usuário |
