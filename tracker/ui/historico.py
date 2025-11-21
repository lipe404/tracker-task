import streamlit as st
import pandas as pd
from tracker.services.logs import obter_logs_df

def render():
    st.header("Histórico de Alterações")
    try:
        df_logs = obter_logs_df()
    except Exception as e:
        st.error(f"Erro ao carregar logs: {e}")
        df_logs = pd.DataFrame()
    if df_logs.empty:
        st.info("Nenhum log registrado.")
        return
    if 'timestamp' in df_logs.columns:
        try:
            df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'], errors='coerce')
        except Exception:
            pass
    colf1, colf2, colf3, colf4 = st.columns(4)
    filtro_id = colf1.text_input("Filtrar por ID", "")
    filtro_acao = colf2.multiselect("Ações", sorted(df_logs['acao'].dropna().unique().tolist()))
    filtro_usuario = colf3.multiselect("Usuário", sorted(df_logs['usuario'].dropna().unique().tolist()))
    filtro_campo = colf4.multiselect("Campo", sorted(df_logs['campo'].dropna().unique().tolist()))
    if filtro_id.strip():
        df_logs = df_logs[df_logs['task_id'].astype(str) == filtro_id.strip()]
    if filtro_acao:
        df_logs = df_logs[df_logs['acao'].isin(filtro_acao)]
    if filtro_usuario:
        df_logs = df_logs[df_logs['usuario'].isin(filtro_usuario)]
    if filtro_campo:
        df_logs = df_logs[df_logs['campo'].isin(filtro_campo)]
    if 'timestamp' in df_logs.columns:
        df_logs = df_logs.sort_values('timestamp', ascending=False)
    st.dataframe(
        df_logs[[c for c in ['timestamp','acao','task_id','campo','valor_antigo','valor_novo','usuario'] if c in df_logs.columns]],
        use_container_width=True,
        hide_index=True
    )