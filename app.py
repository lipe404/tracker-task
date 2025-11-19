import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Educa Mais - Gestão de Tech",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONSTANTES E SETUP ---
NOME_PLANILHA = "Tasks Devs"
ARQUIVO_CREDENCIAIS = "credentials.json"

COLUNAS_KANBAN = ["Backlog/A Fazer",
                  "Em Desenvolvimento", "Code Review/QA", "Concluído"]
DESENVOLVEDORES = ["Eduardo", "Israel", "Pedro", "Vinícius"]
TIPOS_TAREFA = ["Feature (Nova Funcionalidade)",
                "Bugfix (Correção)", "Refatoração", "Infraestrutura"]
PRIORIDADES = ["🔴 Urgente", "🟡 Alta", "🟢 Média", "⚪ Baixa"]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


# --- FUNÇÕES DE CONEXÃO COM GOOGLE SHEETS ---
def conectar_google_sheets():
    """Estabelece conexão com o Google Sheets usando Service Account."""
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            credentials = Credentials.from_service_account_info(
                creds_dict, scopes=SCOPES)
        elif os.path.exists(ARQUIVO_CREDENCIAIS):
            credentials = Credentials.from_service_account_file(
                ARQUIVO_CREDENCIAIS, scopes=SCOPES)
        else:
            st.error(
                "Nenhuma credencial encontrada! Configure os Secrets (na nuvem) ou adicione 'credentials.json' (local).")
            st.stop()

        client = gspread.authorize(credentials)

        try:
            sheet = client.open(NOME_PLANILHA).sheet1
            return sheet
        except gspread.SpreadsheetNotFound:
            st.error(
                f"Planilha '{NOME_PLANILHA}' não encontrada! Verifique se o nome está exato e se compartilhou com o email da service account.")
            st.stop()
        except gspread.exceptions.APIError as e:
            if "Google Drive API has not been used" in str(e):
                st.error(
                    "ERRO DE API: A 'Google Drive API' não está ativada no seu projeto do Google Cloud.")
                st.markdown(
                    "[Clique aqui para ativar a Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)")
                st.stop()
            else:
                raise e

    except Exception as e:
        st.error(f"Erro ao conectar no Google Sheets: {e}")
        st.stop()


def carregar_dados():
    """Carrega os dados da Planilha do Google."""
    sheet = conectar_google_sheets()
    dados = sheet.get_all_records()

    if not dados:
        return criar_dados_iniciais(sheet)

    df = pd.DataFrame(dados)
    return df


def criar_dados_iniciais(sheet):
    """Cria dados fictícios e salva na planilha se ela estiver vazia."""
    dados = {
        "id": [1, 2, 3, 4, 5],
        "titulo": ["Landing Page Vestibular", "Correção Menu Mobile", "API de Notas", "Otimização de SEO", "Migração de Servidor"],
        "responsavel": ["Pedro", "Israel", "Vinícius", "Eduardo", "Pedro"],
        "status": ["Concluído", "Em Desenvolvimento", "Code Review/QA", "Backlog/A Fazer", "Backlog/A Fazer"],
        "tipo": ["Feature (Nova Funcionalidade)", "Bugfix (Correção)", "Feature (Nova Funcionalidade)", "Refatoração", "Infraestrutura"],
        "prioridade": ["🟢 Média", "🔴 Urgente", "🟡 Alta", "⚪ Baixa", "🟡 Alta"],
        "data_entrega": ["2025-12-01", "2025-11-25", "2025-11-30", "2025-12-15", "2026-01-10"],
        "progresso": [100, 60, 90, 0, 10],
        "data_criacao": [datetime.now().strftime("%Y-%m-%d")] * 5
    }
    df = pd.DataFrame(dados)
    salvar_dados(df)
    return df


def salvar_dados(df):
    """Salva o DataFrame na Planilha do Google (sobrescreve tudo)."""
    sheet = conectar_google_sheets()
    sheet.clear()
    dados_lista = [df.columns.values.tolist()] + df.astype(str).values.tolist()
    sheet.update(dados_lista)


# --- INICIALIZAÇÃO DO ESTADO ---
if 'df_tarefas' not in st.session_state:
    st.session_state.df_tarefas = carregar_dados()

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.title("Educa Mais")
    st.caption("Gestão de Desenvolvimento Web")
    st.success("Conectado ao Google Sheets")

    menu = st.radio(
        "Navegação",
        ["Dashboard", "Quadro Kanban", "Nova Demanda", "Configurações"]
    )

    st.divider()
    st.info(f"Equipe: {len(DESENVOLVEDORES)} Desenvolvedores")

# --- PÁGINA: DASHBOARD ---
if menu == "Dashboard":
    st.header("Dashboard de Produtividade")
    st.markdown("Visão geral do andamento dos projetos das faculdades.")

    if st.button("Atualizar Dados da Nuvem"):
        st.session_state.df_tarefas = carregar_dados()
        st.rerun()

    df = st.session_state.df_tarefas.copy()
    df['progresso'] = pd.to_numeric(df['progresso'])
    df['data_entrega'] = pd.to_datetime(df['data_entrega'])

    # Métricas (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    concluidas = len(df[df['status'] == "Concluído"])
    em_andamento = len(df[df['status'] == "Em Desenvolvimento"])
    atrasadas = len(df[(df['data_entrega'] < datetime.now())
                    & (df['status'] != 'Concluído')])

    col1.metric("Total de Demandas", total)
    col2.metric("Taxa de Conclusão",
                f"{(concluidas/total*100):.1f}%" if total > 0 else "0%")
    col3.metric("Em Andamento", em_andamento)
    col4.metric("Atrasadas", atrasadas,
                delta=f"-{atrasadas}" if atrasadas > 0 else "0", delta_color="inverse")

    st.divider()

    # Alertas e Tarefas Críticas
    col_urgentes, col_prazo = st.columns(2)

    with col_urgentes:
        st.subheader("Tarefas de Alta Prioridade")
        df_urgentes = df[df['prioridade'].isin(
            ['🔴 Urgente', '🟡 Alta']) & (df['status'] != 'Concluído')]
        if not df_urgentes.empty:
            st.dataframe(
                df_urgentes[['titulo', 'responsavel', 'prioridade',
                             'data_entrega', 'progresso']].sort_values('data_entrega'),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("Nenhuma tarefa urgente no momento!")

    with col_prazo:
        st.subheader("Próximas Entregas (15 dias)")
        hoje = datetime.now()
        df_proximas = df[
            (df['data_entrega'] >= hoje) &
            (df['data_entrega'] <= hoje + pd.Timedelta(days=15)) &
            (df['status'] != 'Concluído')
        ].sort_values('data_entrega')

        if not df_proximas.empty:
            st.dataframe(
                df_proximas[['titulo', 'responsavel',
                             'data_entrega', 'prioridade', 'progresso']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhuma entrega próxima nos próximos 15 dias.")

    st.divider()

    # Gráficos
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Demandas por Desenvolvedor")
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
        st.subheader("Distribuição por Tipo")
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
        df[['titulo', 'responsavel', 'status', 'prioridade', 'data_entrega',
            'progresso', 'tipo']].style.highlight_max(axis=0, color='lightgreen'),
        use_container_width=True,
        hide_index=True
    )

# --- PÁGINA: KANBAN ---
elif menu == "Quadro Kanban":
    st.header("Quadro Kanban")

    # Filtros
    c_filter1, c_filter2, c_filter3 = st.columns(3)
    filtro_dev = c_filter1.multiselect(
        "Filtrar por Desenvolvedor", DESENVOLVEDORES)
    filtro_tipo = c_filter2.multiselect("Filtrar por Tipo", TIPOS_TAREFA)
    filtro_prioridade = c_filter3.multiselect(
        "Filtrar por Prioridade", PRIORIDADES)

    df_view = st.session_state.df_tarefas.copy()
    df_view['progresso'] = pd.to_numeric(df_view['progresso'])
    df_view['data_entrega'] = pd.to_datetime(df_view['data_entrega'])

    if filtro_dev:
        df_view = df_view[df_view['responsavel'].isin(filtro_dev)]
    if filtro_tipo:
        df_view = df_view[df_view['tipo'].isin(filtro_tipo)]
    if filtro_prioridade:
        df_view = df_view[df_view['prioridade'].isin(filtro_prioridade)]

    # Layout das Colunas do Kanban
    cols = st.columns(len(COLUNAS_KANBAN))

    for idx, coluna_nome in enumerate(COLUNAS_KANBAN):
        with cols[idx]:
            st.subheader(coluna_nome)
            st.markdown("---")

            tarefas_coluna = df_view[df_view['status']
                                     == coluna_nome].sort_values('data_entrega')

            for i, row in tarefas_coluna.iterrows():
                # Calcular status do prazo
                dias_restantes = (row['data_entrega'] - datetime.now()).days
                emoji_prazo = "⏰" if dias_restantes <= 3 else "📅"
                cor_prazo = "red" if dias_restantes < 0 else "orange" if dias_restantes <= 3 else "green"

                # Card da Tarefa
                with st.expander(f"#{row['id']} {row['prioridade']} - {row['titulo']}", expanded=True):
                    col_info1, col_info2 = st.columns(2)
                    col_info1.caption(f"👤 **{row['responsavel']}**")
                    col_info2.caption(f"🏷️ {row['tipo'].split()[0]}")

                    # Exibir prazo com destaque visual
                    st.markdown(
                        f"**{emoji_prazo} Entrega:** :{cor_prazo}[{row['data_entrega'].strftime('%d/%m/%Y')}] ({dias_restantes} dias)")
                    st.progress(int(row['progresso']) / 100)

                    # Controles de Edição Rápida
                    novo_status = st.selectbox(
                        "Mover para:",
                        COLUNAS_KANBAN,
                        index=COLUNAS_KANBAN.index(row['status']),
                        key=f"status_{row['id']}"
                    )

                    novo_progresso = st.slider(
                        "Progresso %", 0, 100, int(row['progresso']), 10,
                        key=f"prog_{row['id']}"
                    )

                    # Lógica de Atualização
                    if novo_status != row['status'] or novo_progresso != row['progresso']:
                        st.session_state.df_tarefas.loc[st.session_state.df_tarefas['id']
                                                        == row['id'], 'status'] = novo_status
                        st.session_state.df_tarefas.loc[st.session_state.df_tarefas['id']
                                                        == row['id'], 'progresso'] = novo_progresso

                        if novo_progresso == 100 and novo_status != "Concluído":
                            st.session_state.df_tarefas.loc[st.session_state.df_tarefas['id']
                                                            == row['id'], 'status'] = "Concluído"
                            st.toast(f"Tarefa #{row['id']} concluída!")

                        with st.spinner('Salvando no Google Sheets...'):
                            salvar_dados(st.session_state.df_tarefas)
                        st.rerun()

# --- PÁGINA: NOVA DEMANDA ---
elif menu == "Nova Demanda":
    st.header("Cadastro de Nova Demanda")

    with st.form("form_nova_demanda"):
        col1, col2 = st.columns(2)
        titulo = col1.text_input(
            "Título da Demanda", placeholder="Ex: Atualização Portal do Aluno")
        responsavel = col2.selectbox(
            "Desenvolvedor Responsável", DESENVOLVEDORES)

        col3, col4 = st.columns(2)
        tipo = col3.selectbox("Tipo de Demanda", TIPOS_TAREFA)
        prioridade = col4.selectbox("Prioridade", PRIORIDADES)

        col5, col6 = st.columns(2)
        status_inicial = col5.selectbox("Status Inicial", COLUNAS_KANBAN)
        data_entrega = col6.date_input(
            "Data de Entrega",
            value=datetime.now() + pd.Timedelta(days=7),
            min_value=datetime.now()
        )

        descricao = st.text_area(
            "Descrição Detalhada", placeholder="Descreva os requisitos técnicos...")

        submitted = st.form_submit_button("Cadastrar Demanda")

        if submitted and titulo:
            ids = pd.to_numeric(st.session_state.df_tarefas['id'])
            novo_id = ids.max() + 1 if not st.session_state.df_tarefas.empty else 1

            nova_linha = {
                "id": int(novo_id),
                "titulo": titulo,
                "responsavel": responsavel,
                "status": status_inicial,
                "tipo": tipo,
                "prioridade": prioridade,
                "data_entrega": data_entrega.strftime("%Y-%m-%d"),
                "progresso": 0,
                "data_criacao": datetime.now().strftime("%Y-%m-%d")
            }

            st.session_state.df_tarefas = pd.concat(
                [st.session_state.df_tarefas, pd.DataFrame([nova_linha])], ignore_index=True)

            with st.spinner('Salvando no Google Sheets...'):
                salvar_dados(st.session_state.df_tarefas)
            st.success(f"Demanda '{titulo}' salva na nuvem com sucesso!")
            st.balloons()

# --- PÁGINA: CONFIGURAÇÕES ---
elif menu == "Configurações":
    st.header("Configurações do Sistema")

    st.subheader("Conexão Google Sheets")
    st.info(f"Conectado à planilha: **{NOME_PLANILHA}**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Recarregar Dados da Nuvem"):
            st.session_state.df_tarefas = carregar_dados()
            st.success("Dados atualizados!")
            st.rerun()

    with col2:
        st.warning("Cuidado: Isso apaga tudo.")
        if st.button("Resetar Planilha para Padrão"):
            sheet = conectar_google_sheets()
            criar_dados_iniciais(sheet)
            st.session_state.df_tarefas = carregar_dados()
            st.success("Planilha resetada!")
            st.rerun()

    st.divider()

    st.subheader("Estatísticas do Sistema")
    df = st.session_state.df_tarefas
    col_stats1, col_stats2, col_stats3 = st.columns(3)

    col_stats1.metric("Total de Tarefas Cadastradas", len(df))
    col_stats2.metric("Desenvolvedores Ativos", df['responsavel'].nunique())
    col_stats3.metric("Tipos de Demanda", df['tipo'].nunique())

# --- RODAPÉ ---
st.sidebar.markdown("---")
st.sidebar.caption("Desenvolvido por Felipe Toledo")
st.sidebar.caption("Criado com Streamlit + Google Sheets")
