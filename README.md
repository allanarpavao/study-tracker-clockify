# 📚 StudyTrack — Painel de Acompanhamento de Estudos

Dashboard local para acompanhar suas horas de estudo importadas do Clockify.

---

## ⚡ Como Iniciar

### 1. Instale as dependências

```bash
pip install flask
```

> Ou use o arquivo de requirements:
> ```bash
> pip install -r requirements.txt
> ```

### 2. Rode o servidor

```bash
python app.py
```

### 3. Acesse no navegador

```
http://localhost:5000
```

---

## 📥 Como Importar Dados do Clockify

1. No Clockify, vá em **Reports → Detailed**
2. Selecione o período desejado
3. Clique em **Export → CSV**
4. No StudyTrack, clique em **"⬆ Importar CSV"**
5. Selecione ou arraste o arquivo exportado

Registros duplicados são detectados e ignorados automaticamente — pode importar com segurança sem medo de duplicar dados.

---

## 🎮 Funcionalidades

- **Metas diária / semanal / mensal** com anéis de progresso
- **Sequência de dias** (streak) — mantida quando você estuda ≥ 50% da meta diária
- **Sistema de níveis** — 1 nível a cada 50 horas totais estudadas
- **Gráfico de 30 dias** com linha de meta
- **Tendência semanal** das últimas 8 semanas
- **Breakdown por projeto** do mês atual
- **Configuração de metas** pelo botão ⚙

---

## 🗂 Estrutura

```
study-tracker/
├── app.py              # Backend Flask + SQLite
├── index.html          # Frontend (servido pelo Flask)
├── requirements.txt    # Dependências Python
├── study_tracker.db    # Banco de dados SQLite (criado automaticamente)
└── README.md
```

---

## ⚙ Metas Padrão

| Período | Padrão |
|---------|--------|
| Diária  | 3h     |
| Semanal | 20h    |
| Mensal  | 80h    |

Altere a qualquer momento clicando em **⚙ Metas** no topo do painel.
