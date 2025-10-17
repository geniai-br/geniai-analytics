# 📊 AllpFit Analytics

Dashboard para análise de conversas de agente de IA do sistema Chatwoot.

## 📋 Descrição

Este projeto extrai dados de conversas de um banco PostgreSQL externo (Chatwoot), processa as informações e cria um dashboard interativo para análise de métricas e comportamento do agente de IA.

## 🏗️ Estrutura do Projeto

```
allpfit-analytics/
├── src/
│   ├── app/              # Dashboard e visualizações (Streamlit)
│   ├── features/         # Pipeline ETL e processamento de dados
│   │   └── etl_pipeline.py
│   └── shared/           # Utilitários e configurações compartilhadas
│       ├── config.py     # Configurações centralizadas
│       └── database.py   # Gerenciador de conexões DB
├── data/                 # Dados extraídos (CSV backups)
├── venv/                 # Ambiente virtual Python
├── .env                  # Variáveis de ambiente (NÃO versionado)
├── .env.example          # Template de configuração
├── requirements.txt      # Dependências do projeto
└── README.md
```

## 🚀 Setup Inicial

### 1. Clonar o repositório

```bash
git clone git@github.com:geniai-br/allpfit-analytics.git
cd allpfit-analytics
```

### 2. Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instalar dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Copie o arquivo de exemplo e configure suas credenciais:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```env
# Banco de dados externo (Chatwoot)
SOURCE_DB_HOST=seu_host
SOURCE_DB_PORT=5432
SOURCE_DB_NAME=chatwoot
SOURCE_DB_USER=seu_usuario
SOURCE_DB_PASSWORD=sua_senha
SOURCE_DB_VIEW=vw_conversas_por_lead

# Banco de dados local (onde os dados serão armazenados)
LOCAL_DB_HOST=/var/run/postgresql
LOCAL_DB_PORT=5432
LOCAL_DB_NAME=allpfit_analytics
LOCAL_DB_USER=seu_usuario_local
LOCAL_DB_TABLE=conversas_lead
```

### 5. Testar conexão

```bash
python test_connection.py
```

## 📊 Dados

### View: `vw_conversas_por_lead`

A view do banco externo contém as seguintes colunas:

- **conversation_id**: ID único da conversa
- **message_compiled**: Array JSON com todas as mensagens da conversa
- **client_sender_id**: ID do cliente/lead
- **inbox_id**: ID do canal (inbox)
- **client_phone**: Telefone do cliente
- **t_messages**: Total de mensagens na conversa

## 🔧 Uso

### Pipeline ETL

Extrai dados do banco remoto e carrega no banco local:

```bash
python -m src.features.etl_pipeline
```

### Dashboard (em desenvolvimento)

```bash
streamlit run src/app/dashboard.py
```

## 🛠️ Tecnologias

- **Python 3.11+**
- **PostgreSQL** - Banco de dados
- **Pandas** - Processamento de dados
- **SQLAlchemy** - ORM e conexões DB
- **Streamlit** - Dashboard interativo
- **Plotly** - Visualizações
- **python-dotenv** - Gerenciamento de variáveis de ambiente

## 📝 Desenvolvimento

### Estrutura de Módulos

- **src/app/**: Código do dashboard e interface
- **src/features/**: Features e pipeline de dados
- **src/shared/**: Código compartilhado (config, utils, database)

### Boas Práticas

1. Sempre ative o ambiente virtual antes de trabalhar
2. Nunca commite o arquivo `.env` (já está no .gitignore)
3. Mantenha o `requirements.txt` atualizado
4. Use o módulo `config.py` para acessar configurações

## 🔒 Segurança

- Credenciais nunca devem ser commitadas no repositório
- Use o arquivo `.env` para desenvolvimento local
- Use variáveis de ambiente para produção

## 📈 Próximos Passos

- [ ] Configurar banco de dados local
- [ ] Melhorar pipeline ETL (logging, validações)
- [ ] Criar schema do banco local
- [ ] Desenvolver dashboard Streamlit
- [ ] Adicionar análises e métricas de IA
- [ ] Implementar testes automatizados

## 👥 Equipe

Desenvolvido por GenIAI

## 📄 Licença

Projeto interno - Todos os direitos reservados
