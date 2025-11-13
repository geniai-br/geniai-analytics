"""
Utilitários para cálculo de próxima execução do ETL
"""

from datetime import datetime, timedelta


def get_next_etl_time(last_sync: datetime = None) -> dict:
    """
    Calcula quando será a próxima execução do ETL baseado no schedule fixo do systemd
    (a cada 30 minutos: XX:00 e XX:30 de cada hora)

    Args:
        last_sync: Timestamp da última sincronização (UTC). Não usado, mas mantido para compatibilidade

    Returns:
        dict com:
            - next_etl: datetime da próxima execução (UTC)
            - next_etl_sp: datetime da próxima execução (SP - UTC-3)
            - time_until: timedelta até a próxima execução
            - hours_left: horas restantes (int)
            - minutes_left: minutos restantes (int)
            - formatted_time: string formatada "HH:MM"
            - is_overdue: bool se já passou da hora
    """
    ETL_INTERVAL_MINUTES = 30

    now_utc = datetime.utcnow()

    # Calcular próxima execução baseado no schedule fixo (a cada 30 minutos)
    # Horários: XX:00, XX:30 (de cada hora)
    current_hour = now_utc.hour
    current_minute = now_utc.minute

    # Determinar próximo horário (00 ou 30)
    if current_minute < 30:
        # Próximo é XX:30
        next_etl_utc = now_utc.replace(hour=current_hour, minute=30, second=0, microsecond=0)
    else:
        # Próximo é (XX+1):00
        if current_hour == 23:
            # Próximo dia, 00:00
            next_etl_utc = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            next_etl_utc = now_utc.replace(hour=current_hour + 1, minute=0, second=0, microsecond=0)

    # Calcular tempo restante
    time_until = next_etl_utc - now_utc
    is_overdue = time_until.total_seconds() < 0

    if is_overdue:
        hours_left = 0
        minutes_left = 0
    else:
        hours_left = int(time_until.total_seconds() // 3600)
        minutes_left = int((time_until.total_seconds() % 3600) // 60)

    # Converter para SP (UTC-3)
    next_etl_sp = next_etl_utc - timedelta(hours=3)

    return {
        'next_etl': next_etl_utc,
        'next_etl_sp': next_etl_sp,
        'time_until': time_until,
        'hours_left': hours_left,
        'minutes_left': minutes_left,
        'formatted_time': next_etl_sp.strftime('%H:%M'),
        'formatted_datetime': next_etl_sp.strftime('%d/%m/%Y %H:%M'),
        'is_overdue': is_overdue
    }


def format_etl_countdown(next_info: dict) -> str:
    """
    Formata mensagem de countdown para próxima execução

    Args:
        next_info: Dict retornado por get_next_etl_time()

    Returns:
        String formatada para exibir
    """
    if next_info['is_overdue']:
        return "🔄 Atualização em andamento ou atrasada"

    hours = next_info['hours_left']
    minutes = next_info['minutes_left']
    time_str = next_info['formatted_time']

    if hours > 0:
        return f"⏰ Próxima atualização: **{time_str}** (em {hours}h {minutes}min)"
    else:
        return f"⏰ Próxima atualização: **{time_str}** (em {minutes}min)"
