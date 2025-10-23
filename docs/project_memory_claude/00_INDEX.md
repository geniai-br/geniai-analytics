# 📚 Memória do Projeto - AllpFit Analytics

**Data:** 23/10/2025
**Sessão:** Continuação do desenvolvimento
**Status:** ✅ Em produção

---

## 📑 Índice da Memória

Este diretório contém a memória completa do que foi desenvolvido para referência futura do Claude.

### 📄 Arquivos de Memória:

1. **00_INDEX.md** - Este arquivo (índice)
2. **01_PROJECT_OVERVIEW.md** - Visão geral e contexto
3. **02_SESSION_HISTORY.md** - Histórico detalhado das sessões
4. **03_TECHNICAL_DECISIONS.md** - Decisões técnicas e arquitetura
5. **04_CURRENT_STATE.md** - Estado atual do sistema
6. **05_NEXT_STEPS.md** - Próximos passos sugeridos

---

## 🎯 Quick Start para Claude

### Se você foi chamado para:

#### 🐛 **Resolver um problema:**
→ Leia `04_CURRENT_STATE.md` primeiro para entender o estado atual

#### 🆕 **Adicionar funcionalidade:**
→ Leia `03_TECHNICAL_DECISIONS.md` para seguir os padrões

#### 📊 **Entender métricas:**
→ Leia `01_PROJECT_OVERVIEW.md` para contexto de negócio

#### 🔧 **Debugar ETL:**
→ Execute `./monitor_etl.sh` e veja logs

#### 📈 **Analisar dashboard:**
→ Acesse https://analytcs.geniai.online

---

## 🚀 Comandos Rápidos

```bash
# Ver status do ETL
./monitor_etl.sh

# Status rápido
./etl_status.sh

# Rodar ETL manualmente
cd /home/isaac/projects/allpfit-analytics
source venv/bin/activate
python3 src/features/etl_pipeline_v3.py --triggered-by manual

# Reiniciar dashboard
pkill -f "streamlit run"
cd /home/isaac/projects/allpfit-analytics
source venv/bin/activate
streamlit run src/app/dashboard.py --server.port 8501 --server.headless true &
```

---

## 📞 Contatos do Projeto

- **Cliente:** AllpFit Academia
- **Usuário:** Isaac
- **Bot:** WhatsApp Bot (GenIAI)
- **CRM:** EVO CRM

---

## ⚠️ Avisos Importantes

1. **NÃO commit** arquivos Excel ou relatórios (estão no `.gitignore`)
2. **Horários em SP** - Banco em UTC, sempre converter (-3h)
3. **ETL roda a cada hora** no minuto 0
4. **Dashboard em produção** - testar antes de commitar

---

## 📊 Métricas Atuais (23/10/2025)

- **Total conversas:** 495
- **Conversões rastreadas:** 7 (3.5%)
- **Visitas agendadas:** 42
- **Taxa conversão bot → CRM:** 3.5%
- **Dias rodando:** 28 dias

---

**Última atualização:** 23/10/2025 11:25
