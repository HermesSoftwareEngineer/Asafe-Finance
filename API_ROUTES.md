# 📚 Documentação — Rotas da API

## Visão Geral

O Asafe Finance oferece uma API RESTful construída com **FastAPI** para gerenciar lançamentos, transações e conciliação bancária.

---

## 🔐 Autenticação

Todas as rotas requerem autenticação via JWT em cookies `httpOnly`.

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "usuario@example.com",
  "password": "senha123"
}
```

**Resposta:** Cookie `access_token` é definido automaticamente.

---

## 💰 Lançamentos

### 1. Listar Lançamentos

```http
GET /api/lancamentos?page=1&tipo=saida&status=previsto&data_inicio=2024-01-01&data_fim=2024-12-31
```

**Parâmetros de query:**
- `page`: Número da página (padrão: 1)
- `tipo`: "entrada" ou "saida"
- `status`: "previsto", "parcial" ou "realizado"
- `categoria_id`: ID da categoria
- `centro_custo_id`: ID do centro de custo
- `data_inicio`, `data_fim`: Filtro por período (formato: YYYY-MM-DD)

**Resposta:**
```json
{
  "items": [
    {
      "id": 1,
      "descricao": "Aluguel",
      "tipo": "saida",
      "valor_total": 5000.0,
      "valor_pago": 5000.0,
      "data_competencia": "2024-05-01",
      "status": "realizado",
      "categoria_id": 2,
      "categoria_nome": "Infraestrutura",
      "centro_custo_id": 1,
      "centro_custo_nome": "Administrativo",
      "tipo_recorrencia": "fixo",
      "frequencia_recorrencia": "mensal",
      "quantidade_parcelas": null,
      "numero_parcela": null,
      "lancamento_pai_id": null
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 20
}
```

---

### 2. Criar Lançamento

```http
POST /api/lancamentos
Content-Type: application/json

{
  "descricao": "Aluguel",
  "tipo": "saida",
  "valor_total": 5000.0,
  "data_competencia": "2024-05-01",
  "categoria_id": 2,
  "centro_custo_id": 1,
  "observacao": "Aluguel do mês de maio",
  "tipo_recorrencia": "fixo",
  "frequencia_recorrencia": "mensal"
}
```

**Tipos de Recorrência:**

#### **`unico`** (padrão)
Lançamento simples, sem recorrência.

```json
{
  "descricao": "Compra de material",
  "tipo": "saida",
  "valor_total": 500.0,
  "data_competencia": "2024-05-15",
  "tipo_recorrencia": "unico"
}
```

#### **`fixo`** — Recorrência com Frequência
Lançamentos que se repetem em intervalos regulares (ex: aluguel mensal, salário).

**Frequências:**
- `diario`: Todo dia
- `semanal`: A cada 7 dias
- `quinzenal`: A cada 15 dias
- `mensal`: A cada 30 dias

```json
{
  "descricao": "Aluguel",
  "tipo": "saida",
  "valor_total": 5000.0,
  "data_competencia": "2024-05-01",
  "tipo_recorrencia": "fixo",
  "frequencia_recorrencia": "mensal"
}
```

#### **`parcelado`** — Múltiplas Parcelas
Um lançamento grande é dividido em várias parcelas (ex: 12x sem juros).

```json
{
  "descricao": "Equipamento (parcelado)",
  "tipo": "saida",
  "valor_total": 1200.0,
  "data_competencia": "2024-05-01",
  "tipo_recorrencia": "parcelado",
  "quantidade_parcelas": 12
}
```

**Resultado:** 12 lançamentos são criados automaticamente:
- Parcela 1: R$100 em 01/05/2024
- Parcela 2: R$100 em 01/06/2024
- Parcela 3: R$100 em 01/07/2024
- ... (até parcela 12)

---

### 3. Editar Lançamento

```http
PUT /api/lancamentos/{lancamento_id}
Content-Type: application/json

{
  "descricao": "Aluguel atualizado",
  "tipo": "saida",
  "valor_total": 5500.0,
  "data_competencia": "2024-05-01",
  "categoria_id": 2,
  "centro_custo_id": 1,
  "observacao": "Aluguel reajustado",
  "tipo_recorrencia": "fixo",
  "frequencia_recorrencia": "mensal"
}
```

---

### 4. Deletar Lançamento

```http
DELETE /api/lancamentos/{lancamento_id}
```

---

### 5. Listar Vínculos de um Lançamento

```http
GET /api/lancamentos/{lancamento_id}/vinculos
```

**Resposta:**
```json
[
  {
    "id": 1,
    "transacao_id": 5,
    "transacao_descricao": "Transferência Conta Corrente",
    "transacao_data": "2024-05-01",
    "transacao_conta": "Conta Corrente Principal",
    "valor_vinculado": 5000.0
  }
]
```

---

### 6. **NOVO** — Criar Transação Automaticamente para Lançamento

```http
POST /api/lancamentos/{lancamento_id}/criar-transacao
Content-Type: application/json

{
  "conta_id": 1,
  "forma_pagamento": "transferência"
}
```

**O que acontece:**
1. ✅ Uma transação é criada com o valor e data do lançamento
2. ✅ A transação é vinculada ao lançamento automaticamente
3. ✅ O lançamento muda de status para **"realizado"**
4. ✅ A transação é marcada como **"conciliado"**

**Resposta:**
```json
{
  "lancamento": {
    "id": 1,
    "descricao": "Aluguel",
    "tipo": "saida",
    "valor_total": 5000.0,
    "valor_pago": 5000.0,
    "data_competencia": "2024-05-01",
    "status": "realizado",
    "categoria_id": 2,
    "categoria_nome": "Infraestrutura",
    "tipo_recorrencia": "fixo",
    "frequencia_recorrencia": "mensal"
  },
  "transacao_id": 42,
  "mensagem": "Transação criada e vinculada ao lançamento. Status: realizado"
}
```

**Uso:** Perfeito para registros rápidos ou pagamentos que já foram efetivados.

---

### 7. Desvincular Transação

```http
DELETE /api/lancamentos/{lancamento_id}/vinculos/{vinculo_id}
```

---

## 💳 Transações

### 1. Listar Transações

```http
GET /api/transacoes?page=1&conta_id=1&status_conciliacao=pendente
```

---

### 2. Criar Transação

```http
POST /api/transacoes
Content-Type: application/json

{
  "descricao": "Transferência recebida",
  "tipo": "entrada",
  "valor": 1500.0,
  "data_pagamento": "2024-05-01",
  "conta_id": 1,
  "forma_pagamento": "transferência",
  "status_conciliacao": "pendente"
}
```

---

## 🔗 Vínculos (Lançamento ↔ Transação)

### 1. Vincular Transação a Lançamento

```http
POST /api/transacoes/{transacao_id}/vincular
Content-Type: application/json

{
  "lancamento_id": 1,
  "valor_vinculado": 5000.0
}
```

---

## 📊 Dashboard

### Dados do Dashboard

```http
GET /api/dashboard
```

**Resposta:**
```json
{
  "resumo_mes_atual": {
    "entradas": 15000.0,
    "saidas": 8500.0,
    "saldo": 6500.0
  },
  "fluxo_ultimos_12_meses": [
    {
      "mes": "Janeiro",
      "entradas": 12000.0,
      "saidas": 7000.0
    }
  ],
  "categorias_top": [
    {
      "categoria": "Infraestrutura",
      "total": 5000.0,
      "percentual": 58.8
    }
  ]
}
```

---

## 📂 Cadastros

### Categorias

#### Listar
```http
GET /api/cadastros/categorias
```

#### Criar
```http
POST /api/cadastros/categorias
Content-Type: application/json

{
  "nome": "Manutenção",
  "tipo": "saida",
  "categoria_pai_id": null,
  "cor": "#E8A838",
  "ativo": true
}
```

---

### Contas

#### Listar
```http
GET /api/cadastros/contas
```

#### Criar
```http
POST /api/cadastros/contas
Content-Type: application/json

{
  "nome": "Conta Poupança",
  "tipo": "poupanca",
  "saldo_inicial": 10000.0,
  "ativo": true
}
```

---

## 📋 Relatórios

### Relatório de Fluxo de Caixa

```http
GET /api/relatorios/fluxo-caixa?data_inicio=2024-01-01&data_fim=2024-12-31
```

---

## 📤 Exportação

### Exportar para Excel

```http
GET /api/exportar/excel?data_inicio=2024-01-01&data_fim=2024-12-31&tipo=entrada
```

---

## 🏦 Importação OFX

### Upload de Arquivo OFX

```http
POST /api/ofx/importar
Content-Type: multipart/form-data

file: <arquivo.ofx>
conta_id: 1
```

---

## ⚠️ Códigos de Erro

| Código | Significado |
|--------|-------------|
| 400 | Erro de validação (dados inválidos) |
| 401 | Não autenticado |
| 403 | Acesso negado |
| 404 | Recurso não encontrado |
| 500 | Erro interno do servidor |

---

## 🔄 Fluxo Típico

1. **Login** → Recebe cookie de autenticação
2. **Criar Lançamento** → Registro da intenção contábil
3. **Importar OFX ou Criar Transação** → Registro da movimentação real
4. **Vincular** → Conectar lançamento à transação
5. **Conciliar** → Marcar como conciliado
6. **Relatório** → Gerar PDF/Excel com dados

---

## 📝 Notas

- Todos os valores são em **Decimal(10, 2)** — até R$99.999.999,99
- Datas no formato **ISO 8601**: `YYYY-MM-DD`
- **Status do lançamento** é calculado automaticamente com base nos vínculos
- **Recorrências** (fixo/parcelado) geram lançamentos automaticamente
