import streamlit as st
import pandas as pd
from datetime import datetime
from tracker.config import COLUNAS_KANBAN, DESENVOLVEDORES, TIPOS_TAREFA, PRIORIDADES
from tracker.services.tasks import atualizar_multiplas_celulas

def render():
    st.header("Quadro Kanban")
    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"] { gap: 1rem; }
        div[data-testid="column"] { position: relative; }
        div[data-testid="column"]>div { position: relative; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; min-height: 75vh; }
        div[data-testid="column"]>div::after { content: ""; position: absolute; top: 0; right: -8px; width: 2px; height: 100%; background: #d1d5db; }
        div[data-testid="column"]:last-child>div::after { display: none; }
        .kanban-header { position: sticky; top: 0; z-index: 2; display: flex; justify-content: space-between; align-items: center; background: #ffffffd9; border: 1px solid #e5e7eb; border-left: 6px solid var(--accent, #6b7280); border-radius: 10px; padding: 8px 12px; margin-bottom: 10px; backdrop-filter: blur(4px); }
        .kanban-title { font-weight: 600; }
        .kanban-count { font-size: 12px; background: #0000000a; padding: 4px 8px; border-radius: 999px; }
        .kanban-empty { border: 1px dashed #cbd5e1; background: #ffffff; color: #64748b; border-radius: 8px; padding: 10px; text-align: center; }
        .st-expander { border: 1px solid #e5e7eb; border-radius: 10px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    c_filter1, c_filter2, c_filter3 = st.columns(3)
    filtro_dev = c_filter1.multiselect("Filtrar por Desenvolvedor", DESENVOLVEDORES)
    filtro_tipo = c_filter2.multiselect("Filtrar por Tipo", TIPOS_TAREFA)
    filtro_prioridade = c_filter3.multiselect("Filtrar por Prioridade", PRIORIDADES)

    df_view = st.session_state.df_tarefas.copy()
    df_view['progresso'] = pd.to_numeric(df_view['progresso'], errors='coerce').fillna(0)
    df_view['data_entrega'] = pd.to_datetime(df_view['data_entrega'], errors='coerce')

    if filtro_dev:
        df_view = df_view[df_view['responsavel'].isin(filtro_dev)]
    if filtro_tipo:
        df_view = df_view[df_view['tipo'].isin(filtro_tipo)]
    if filtro_prioridade:
        df_view = df_view[df_view['prioridade'].isin(filtro_prioridade)]

    cols = st.columns(len(COLUNAS_KANBAN))
    cores = {
        "Backlog/A Fazer": "#EAB308",
        "Em Desenvolvimento": "#3B82F6",
        "Code Review/QA": "#EC4899",
        "Concluído": "#22C55E",
    }

    for idx, coluna_nome in enumerate(COLUNAS_KANBAN):
        with cols[idx]:
            tarefas_coluna = df_view[df_view['status'] == coluna_nome].sort_values('data_entrega')
            accent = cores.get(coluna_nome, "#6B7280")
            st.markdown(
                f"<div class='kanban-header' style='--accent:{accent}'><span class='kanban-title'>{coluna_nome}</span><span class='kanban-count'>{len(tarefas_coluna)} tarefas</span></div>",
                unsafe_allow_html=True,
            )
            if tarefas_coluna.empty:
                st.markdown("<div class='kanban-empty'>Nenhuma tarefa nesta coluna</div>", unsafe_allow_html=True)
            else:
                media_prog = int(pd.to_numeric(tarefas_coluna['progresso'], errors='coerce').fillna(0).mean())
                st.progress(media_prog / 100)

            for i, row in tarefas_coluna.iterrows():
                dias_restantes = (row['data_entrega'] - datetime.now()).days
                emoji_prazo = "⏰" if dias_restantes <= 3 else "📅"
                cor_prazo = "red" if dias_restantes < 0 else "orange" if dias_restantes <= 3 else "green"

                with st.expander(f"#{row['id']} {row['prioridade']} - {row['titulo']}", expanded=True):
                    col_info1, col_info2 = st.columns(2)
                    col_info1.caption(f"👨🏻‍💻 **{row['responsavel']}**")
                    col_info2.caption(f"🏷️ {row['tipo'].split()[0]}")
                    st.markdown(f"**{emoji_prazo} Entrega:** :{cor_prazo}[{row['data_entrega'].strftime('%d/%m/%Y')}] ({dias_restantes} dias)")
                    st.progress(int(row['progresso']) / 100)
                    novo_status = st.selectbox("Mover para:", COLUNAS_KANBAN, index=COLUNAS_KANBAN.index(row['status']), key=f"status_{row['id']}")
                    novo_progresso = st.slider("Progresso %", 0, 100, int(row['progresso']), 10, key=f"prog_{row['id']}")
                    if novo_status != row['status'] or novo_progresso != row['progresso']:
                        st.session_state.df_tarefas.loc[st.session_state.df_tarefas['id'] == row['id'], 'status'] = novo_status
                        st.session_state.df_tarefas.loc[st.session_state.df_tarefas['id'] == row['id'], 'progresso'] = novo_progresso
                        if novo_progresso == 100 and novo_status != "Concluído":
                            novo_status = "Concluído"
                            st.session_state.df_tarefas.loc[st.session_state.df_tarefas['id'] == row['id'], 'status'] = "Concluído"
                            st.toast(f"✅ Tarefa #{row['id']} concluída!")
                        with st.spinner('Salvando...'):
                            sucesso = atualizar_multiplas_celulas(row['id'], {'status': novo_status, 'progresso': novo_progresso})
                            if not sucesso:
                                from tracker.services.tasks import salvar_dados_completo
                                salvar_dados_completo(st.session_state.df_tarefas)
                        st.rerun()