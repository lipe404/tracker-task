import streamlit as st
import pandas as pd
from datetime import datetime
from tracker.config import DESENVOLVEDORES, TIPOS_TAREFA, PRIORIDADES, COLUNAS_KANBAN
from tracker.services.tasks import gerar_id_atomico_com_retry, adicionar_tarefa_com_fallback

def render():
    st.header("Cadastro de Nova Demanda")
    if 'tarefa_cadastrada' not in st.session_state:
        st.session_state.tarefa_cadastrada = None
    if st.session_state.tarefa_cadastrada is not None:
        st.success(f"Última demanda cadastrada: **#{st.session_state.tarefa_cadastrada['id']} - {st.session_state.tarefa_cadastrada['titulo']}**")
        with st.expander("Resumo da Última Tarefa", expanded=True):
            col_resumo1, col_resumo2 = st.columns(2)
            with col_resumo1:
                st.markdown(f"""
                - **ID:** #{st.session_state.tarefa_cadastrada['id']}
                - **Título:** {st.session_state.tarefa_cadastrada['titulo']}
                - **Responsável:** {st.session_state.tarefa_cadastrada['responsavel']}
                - **Status:** {st.session_state.tarefa_cadastrada['status']}
                """)
            with col_resumo2:
                st.markdown(f"""
                - **Tipo:** {st.session_state.tarefa_cadastrada['tipo'].split()[0]}
                - **Prioridade:** {st.session_state.tarefa_cadastrada['prioridade']}
                - **Entrega:** {st.session_state.tarefa_cadastrada['data_entrega']}
                - **Criada em:** {st.session_state.tarefa_cadastrada['data_criacao']}
                """)
        if st.button("Cadastrar Outra Demanda", use_container_width=True, type="primary"):
            st.session_state.tarefa_cadastrada = None
            st.rerun()
        st.divider()
    with st.form("form_nova_demanda", clear_on_submit=True):
        col1, col2 = st.columns(2)
        titulo = col1.text_input("Título da Demanda*", placeholder="Ex: Atualização Portal do Aluno")
        responsavel = col2.selectbox("Desenvolvedor Responsável*", DESENVOLVEDORES)
        col3, col4 = st.columns(2)
        tipo = col3.selectbox("Tipo de Demanda*", TIPOS_TAREFA)
        prioridade = col4.selectbox("Prioridade*", PRIORIDADES)
        col5, col6 = st.columns(2)
        status_inicial = col5.selectbox("Status Inicial*", COLUNAS_KANBAN, index=0)
        data_entrega = col6.date_input("Data de Entrega*", value=datetime.now() + pd.Timedelta(days=7), min_value=datetime.now())
        descricao = st.text_area("Descrição Detalhada (opcional)", placeholder="Descreva os requisitos técnicos, dependências, observações...", height=120)
        st.caption("*Campos obrigatórios")
        submitted = st.form_submit_button("Cadastrar Demanda", use_container_width=True, type="primary")
    if submitted:
        if not titulo or not titulo.strip():
            st.error("O título da demanda é obrigatório!")
            st.stop()
        if len(titulo) < 5:
            st.error("O título deve ter pelo menos 5 caracteres!")
            st.stop()
        try:
            with st.spinner('Gerando ID...'):
                try:
                    novo_id = gerar_id_atomico_com_retry(max_tentativas=5)
                    st.info(f"ID #{novo_id} reservado com sucesso!")
                except Exception as e:
                    st.error(f"Não foi possível gerar ID único: {e}")
                    st.stop()
            nova_tarefa = {
                "id": novo_id,
                "titulo": titulo.strip(),
                "descricao": descricao.strip() if descricao else "",
                "responsavel": responsavel,
                "status": status_inicial,
                "tipo": tipo,
                "prioridade": prioridade,
                "data_entrega": data_entrega.strftime("%Y-%m-%d"),
                "progresso": 0,
                "data_criacao": datetime.now().strftime("%Y-%m-%d")
            }
            with st.spinner('Salvando na nuvem (modo rápido)...'):
                sucesso = adicionar_tarefa_com_fallback(nova_tarefa)
            if sucesso:
                nova_linha_df = pd.DataFrame([nova_tarefa])
                st.session_state.df_tarefas = pd.concat([st.session_state.df_tarefas, nova_linha_df], ignore_index=True)
                st.session_state.tarefa_cadastrada = nova_tarefa.copy()
                st.balloons()
                st.rerun()
            else:
                st.error("Não foi possível cadastrar a demanda. Tente novamente.")
        except Exception as e:
            st.error(f"Erro inesperado ao cadastrar demanda: {e}")
            st.exception(e)
    st.divider()
    st.subheader("Estatísticas Rápidas")
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    df_stats = st.session_state.df_tarefas
    col_stat1.metric("Total de Tarefas", len(df_stats), delta="+1 ao cadastrar")
    col_stat2.metric("Tarefas Ativas", len(df_stats[df_stats['status'] != 'Concluído']), delta_color="inverse")
    col_stat3.metric("Próximo ID Disponível", int(pd.to_numeric(df_stats['id'], errors='coerce').max() + 1) if not df_stats.empty else 1)