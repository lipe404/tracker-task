from datetime import datetime
import streamlit as st
import pandas as pd
from tracker.services.sheets import obter_worksheet_logs, obter_usuario_atual

def registrar_logs(acao, task_id, alteracoes, usuario=None):
    ws = obter_worksheet_logs()
    if usuario is None:
        usuario = obter_usuario_atual()
    linhas = []
    ts = datetime.now().isoformat()
    for campo, par in alteracoes.items():
        antigo, novo = par
        linhas.append([ts, acao, str(task_id), campo, str(antigo) if antigo is not None else "", str(novo) if novo is not None else "", usuario])
    try:
        ws.append_rows(linhas, value_input_option="USER_ENTERED")
    except Exception:
        for linha in linhas:
            ws.append_row(linha, value_input_option="USER_ENTERED")

def obter_logs_df():
    ws = obter_worksheet_logs()
    registros = ws.get_all_records()
    df = pd.DataFrame(registros)
    return df