import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def render():
    st.header("Dashboard de Produtividade")
    st.markdown("Visão geral do andamento dos projetos.")
    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        if st.button("🔄 Atualizar", use_container_width=True):
            with st.spinner('Carregando...'):
                from tracker.services.tasks import carregar_dados
                st.session_state.df_tarefas = carregar_dados()
            st.rerun()
    df = st.session_state.df_tarefas.copy()
    df['progresso'] = pd.to_numeric(df['progresso'], errors='coerce').fillna(0)
    df['data_entrega'] = pd.to_datetime(df['data_entrega'], errors='coerce')
    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    concluidas = len(df[df['status'] == "Concluído"])
    em_andamento = len(df[df['status'] == "Em Desenvolvimento"])
    atrasadas = len(df[(df['data_entrega'] < datetime.now()) & (df['status'] != 'Concluído')])
    col1.metric("Total de Demandas", total)
    col2.metric("Taxa de Conclusão", f"{(concluidas/total*100):.1f}%" if total > 0 else "0%")
    col3.metric("Em Andamento", em_andamento)
    col4.metric("⚠️ Atrasadas", atrasadas, delta=f"-{atrasadas}" if atrasadas > 0 else "0", delta_color="inverse")
    st.divider()
    col_urgentes, col_prazo = st.columns(2)
    with col_urgentes:
        st.subheader("🚨 Tarefas de Alta Prioridade")
        df_urgentes = df[df['prioridade'].isin(['🔴 Urgente', '🟡 Alta']) & (df['status'] != 'Concluído')]
        if not df_urgentes.empty:
            st.dataframe(
                df_urgentes[['titulo', 'responsavel', 'prioridade', 'data_entrega', 'progresso']].sort_values('data_entrega'),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ Nenhuma tarefa urgente no momento!")
    with col_prazo:
        st.subheader("📅 Próximas Entregas (15 dias)")
        hoje = datetime.now()
        df_proximas = df[
            (df['data_entrega'] >= hoje) &
            (df['data_entrega'] <= hoje + pd.Timedelta(days=15)) &
            (df['status'] != 'Concluído')
        ].sort_values('data_entrega')
        if not df_proximas.empty:
            st.dataframe(
                df_proximas[['titulo', 'responsavel', 'data_entrega', 'prioridade', 'progresso']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhuma entrega próxima nos próximos 15 dias.")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👨🏻‍💻 Demandas por Desenvolvedor")
        if not df.empty:
            fig_dev = px.bar(
                df,
                x="responsavel",
                color="status",
                title="Carga de Trabalho por Dev",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_dev, use_container_width=True)
    with c2:
        st.subheader("🏷️ Distribuição por Tipo")
        if not df.empty:
            fig_type = px.pie(
                df,
                names="tipo",
                title="Tipos de Demandas",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_type, use_container_width=True)
    st.subheader("Progresso Detalhado")
    st.dataframe(
        df[['titulo', 'responsavel', 'status', 'prioridade', 'data_entrega', 'progresso', 'tipo']].style.highlight_max(axis=0, color='lightgreen'),
        use_container_width=True,
        hide_index=True
    )