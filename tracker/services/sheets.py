import os
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from tracker.config import NOME_PLANILHA, ARQUIVO_CREDENCIAIS, SCOPES, NOME_ABA_LOGS

@st.cache_resource(ttl=3600)
def conectar_google_sheets():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        elif os.path.exists(ARQUIVO_CREDENCIAIS):
            credentials = Credentials.from_service_account_file(ARQUIVO_CREDENCIAIS, scopes=SCOPES)
        else:
            st.error("Nenhuma credencial encontrada! Configure os Secrets (na nuvem) ou adicione 'credentials.json' (local).")
            st.stop()
        client = gspread.authorize(credentials)
        try:
            sheet = client.open(NOME_PLANILHA).sheet1
            return sheet
        except gspread.SpreadsheetNotFound:
            st.error(f"Planilha '{NOME_PLANILHA}' não encontrada! Verifique se o nome está exato e se compartilhou com o email da service account.")
            st.stop()
        except gspread.exceptions.APIError as e:
            if "Google Drive API has not been used" in str(e):
                st.error("ERRO DE API: A 'Google Drive API' não está ativada no seu projeto do Google Cloud.")
                st.markdown("[Clique aqui para ativar a Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)")
                st.stop()
            else:
                raise e
    except Exception as e:
        st.error(f"Erro ao conectar no Google Sheets: {e}")
        st.stop()

def obter_spreadsheet():
    sheet = conectar_google_sheets()
    return sheet.spreadsheet

def obter_worksheet_logs():
    ss = obter_spreadsheet()
    try:
        ws = ss.worksheet(NOME_ABA_LOGS)
    except gspread.exceptions.WorksheetNotFound:
        ws = ss.add_worksheet(title=NOME_ABA_LOGS, rows=1, cols=7)
        ws.update([["timestamp","acao","task_id","campo","valor_antigo","valor_novo","usuario"]])
    return ws

def obter_usuario_atual():
    try:
        return st.secrets.get("usuario", os.environ.get("USERNAME") or os.environ.get("USER") or "Desconhecido")
    except Exception:
        return "Desconhecido"

def limpar_cache_conexao():
    conectar_google_sheets.clear()
    st.cache_data.clear()