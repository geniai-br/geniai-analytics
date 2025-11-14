# Systemd Timer - ETL AllpFit Analytics

Configuração para execução automática do ETL a cada 1 hora usando Systemd Timer.

## 📋 Arquivos

- **etl-allpfit.service** - Define COMO o ETL será executado
- **etl-allpfit.timer** - Define QUANDO o ETL será executado (a cada 1 hora)
- **run_all_tenants.py** - Script que executa ETL para todos os tenants ativos

## 🚀 Instalação

Execute o script de setup como root:

```bash
cd /home/tester/projetos/allpfit-analytics
sudo bash scripts/etl/setup_systemd_timer.sh
```

O script irá:
1. ✅ Verificar se todos os arquivos existem
2. ✅ Copiar arquivos para `/etc/systemd/system/`
3. ✅ Recarregar systemd
4. ✅ Habilitar e iniciar o timer
5. ✅ Mostrar status e próximas execuções

## ⚙️ Configuração

### Modificar Intervalo de Execução

Edite o arquivo `etl-allpfit.timer`:

```ini
[Timer]
# Opções:
OnCalendar=hourly          # A cada 1 hora
OnCalendar=*:0/30          # A cada 30 minutos
OnCalendar=*-*-* 02:00:00  # Todo dia às 02:00
OnCalendar=Mon *-*-* 00:00:00  # Toda segunda às 00:00
```

Após modificar, recarregue:
```bash
sudo systemctl daemon-reload
sudo systemctl restart etl-allpfit.timer
```

### Modificar Timeout

Edite o arquivo `etl-allpfit.service`:

```ini
[Service]
TimeoutSec=1800  # 30 minutos (padrão)
TimeoutSec=3600  # 1 hora
TimeoutSec=600   # 10 minutos
```

## 📊 Comandos Úteis

### Ver Status do Timer
```bash
systemctl status etl-allpfit.timer
```

### Ver Logs em Tempo Real
```bash
journalctl -u etl-allpfit.service -f
```

### Ver Últimas 100 Linhas de Log
```bash
journalctl -u etl-allpfit.service -n 100
```

### Ver Logs de Hoje
```bash
journalctl -u etl-allpfit.service --since today
```

### Ver Próximas Execuções
```bash
systemctl list-timers etl-allpfit.timer
```

### Executar Manualmente (Agora)
```bash
sudo systemctl start etl-allpfit.service
```

### Parar Timer Temporariamente
```bash
sudo systemctl stop etl-allpfit.timer
```

### Iniciar Timer Novamente
```bash
sudo systemctl start etl-allpfit.timer
```

### Desabilitar Timer Permanentemente
```bash
sudo systemctl disable etl-allpfit.timer
sudo systemctl stop etl-allpfit.timer
```

### Habilitar Timer Novamente
```bash
sudo systemctl enable etl-allpfit.timer
sudo systemctl start etl-allpfit.timer
```

## 🔍 Monitoramento

### Ver se o Timer está Ativo
```bash
systemctl is-active etl-allpfit.timer
# Output: active (timer está rodando)
```

### Ver Última Execução
```bash
systemctl status etl-allpfit.service
```

### Ver Histórico de Execuções
```bash
journalctl -u etl-allpfit.service --since "1 week ago"
```

## 🐛 Troubleshooting

### Timer não está executando

1. Verifique se está habilitado:
```bash
systemctl is-enabled etl-allpfit.timer
```

2. Verifique logs de erro:
```bash
journalctl -u etl-allpfit.timer -p err
```

3. Verifique sintaxe dos arquivos:
```bash
systemd-analyze verify /etc/systemd/system/etl-allpfit.service
systemd-analyze verify /etc/systemd/system/etl-allpfit.timer
```

### ETL está falhando

1. Execute manualmente para ver o erro:
```bash
sudo -u tester /home/tester/projetos/allpfit-analytics/venv/bin/python3 \
  /home/tester/projetos/allpfit-analytics/src/multi_tenant/etl_v4/run_all_tenants.py
```

2. Verifique logs:
```bash
journalctl -u etl-allpfit.service -n 200
```

3. Verifique permissões:
```bash
ls -la /home/tester/projetos/allpfit-analytics/src/multi_tenant/etl_v4/run_all_tenants.py
```

## 📈 Performance

- **Timeout:** 30 minutos por execução
- **Restart:** Automático em caso de falha (aguarda 5 minutos)
- **Aleatoriedade:** Até 5 minutos de delay aleatório (evita sobrecarga)
- **Persistência:** Se o sistema estava desligado, executa assim que ligar

## 🔒 Segurança

- Executa como usuário `tester` (não root)
- Logs em systemd journal (rotação automática)
- Timeout configurado para evitar processos travados
- Restart controlado em caso de falha

## 📝 Logs

Os logs são armazenados no systemd journal e podem ser acessados via `journalctl`.

Para ver logs estruturados:
```bash
journalctl -u etl-allpfit.service -o json-pretty
```

Para exportar logs para arquivo:
```bash
journalctl -u etl-allpfit.service --since "1 week ago" > etl_logs.txt
```