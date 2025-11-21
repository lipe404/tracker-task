import streamlit as st
from tracker.config import NOME_PLANILHA
from tracker.services.tasks import carregar_dados, validar_estrutura_planilha
from tracker.services.sheets import limpar_cache_conexao

def render():
    st.header("Configurações do Sistema")
    st.subheader("Conexão Google Sheets")
    st.info(f"Conectado à planilha: **{NOME_PLANILHA}**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Recarregar Dados", use_container_width=True):
            with st.spinner('Carregando...'):
                st.session_state.df_tarefas = carregar_dados()
            st.success("Dados atualizados!")
            st.rerun()
    with col2:
        if st.button("Limpar Cache", use_container_width=True):
            limpar_cache_conexao()
            st.success("Cache limpo!")
            st.rerun()
    st.divider()
    st.subheader("Estatísticas do Sistema")
    df = st.session_state.df_tarefas
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    col_stats1.metric("Total de Tarefas", len(df))
    col_stats2.metric("Desenvolvedores Ativos", df['responsavel'].nunique())
    col_stats3.metric("Tipos de Demanda", df['tipo'].nunique())
    col_stats4.metric("Estrutura Validada", "OK" if validar_estrutura_planilha(df)[0] else "Erro")
    st.divider()
    st.subheader("Diagnóstico da Planilha")
    with st.expander("Ver Detalhes Técnicos"):
        st.write("**Colunas Presentes:**")
        st.code(", ".join(df.columns.tolist()))
        st.write("**Colunas Obrigatórias:**")
        from tracker.config import COLUNAS_OBRIGATORIAS
        st.code(", ".join(COLUNAS_OBRIGATORIAS))
        estrutura_ok, faltantes = validar_estrutura_planilha(df)
        if estrutura_ok:
            st.success("Estrutura da planilha está correta!")
        else:
            st.error(f"Colunas faltantes: {', '.join(faltantes)}")