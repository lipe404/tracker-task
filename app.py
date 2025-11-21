import streamlit as st
from tracker.config import DESENVOLVEDORES
from tracker.services.tasks import carregar_dados
from tracker.ui import dashboard, kanban, nova_demanda, historico, settings

st.set_page_config(page_title="Educa Mais - Gestão de Tech", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

if 'df_tarefas' not in st.session_state:
    with st.spinner('Carregando dados da nuvem...'):
        st.session_state.df_tarefas = carregar_dados()

with st.sidebar:
    st.title("Tracker Tasks")
    st.caption("Gestão de Demandas de Desenvolvimento")
    menu = st.radio("Navegação", ["Dashboard", "Quadro Kanban", "Nova Demanda", "Histórico", "Configurações"])
    st.divider()
    st.info(f"👥 Equipe: {len(DESENVOLVEDORES)} Desenvolvedores")

if menu == "Dashboard":
    dashboard.render()
elif menu == "Quadro Kanban":
    kanban.render()
elif menu == "Nova Demanda":
    nova_demanda.render()
elif menu == "Histórico":
    historico.render()
elif menu == "Configurações":
    settings.render()

st.sidebar.markdown("---")
st.sidebar.caption("Desenvolvido por Toledo")
st.sidebar.caption("Criado com Streamlit + Google Sheets")