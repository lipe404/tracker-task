import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Educa Mais - Gestão de Tech",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONSTANTES E SETUP ---
ARQUIVO_DADOS = "dados_educamais.csv"
COLUNAS_KANBAN = ["Backlog/A Fazer",
                  "Em Desenvolvimento", "Code Review/QA", "Concluído"]
DESENVOLVEDORES = ["Pedro", "Israel", "Vinícius", "Eduardo"]
TIPOS_TAREFA = ["Feature (Nova Funcionalidade)",
                "Bugfix (Correção)", "Refatoração", "Infraestrutura"]

# --- FUNÇÕES DE PERSISTÊNCIA DE DADOS ---


def carregar_dados():
    """Carrega os dados do CSV ou cria um DataFrame inicial se não existir."""
    if os.path.exists(ARQUIVO_DADOS):
        try:
            return pd.read_csv(ARQUIVO_DADOS)
        except:
            return criar_dados_iniciais()
    else:
        return criar_dados_iniciais()


def criar_dados_iniciais():
    """Cria dados fictícios para demonstração inicial."""
    dados = {
        "id": [1, 2, 3, 4, 5],
        "titulo": ["Landing Page Vestibular", "Correção Menu Mobile", "API de Notas", "Otimização de SEO", "Migração de Servidor"],
        "responsavel": ["Ana", "Carlos", "João", "Beatriz", "Carlos"],
        "status": ["Concluído", "Em Desenvolvimento", "Code Review/QA", "Backlog/A Fazer", "Backlog/A Fazer"],
        "tipo": ["Feature (Nova Funcionalidade)", "Bugfix (Correção)", "Feature (Nova Funcionalidade)", "Refatoração", "Infraestrutura"],
        "progresso": [100, 60, 90, 0, 10],
        "data_criacao": [datetime.now().strftime("%Y-%m-%d")] * 5
    }
    df = pd.DataFrame(dados)
    salvar_dados(df)
    return df


def salvar_dados(df):
    """Salva o DataFrame no arquivo CSV."""
    df.to_csv(ARQUIVO_DADOS, index=False)


# --- INICIALIZAÇÃO DO ESTADO ---
if 'df_tarefas' not in st.session_state:
    st.session_state.df_tarefas = carregar_dados()

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.title("🎓 Educa Mais")
    st.caption("Gestão de Desenvolvimento Web")

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

    df = st.session_state.df_tarefas

    # Métricas (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    concluidas = len(df[df['status'] == "Concluído"])
    em_andamento = len(df[df['status'] == "Em Desenvolvimento"])

    col1.metric("Total de Demandas", total)
    col2.metric("Taxa de Conclusão",
                f"{(concluidas/total*100):.1f}%" if total > 0 else "0%")
    col3.metric("Em Andamento", em_andamento)
    col4.metric("Aguardando Review", len(df[df['status'] == "Code Review/QA"]))

    st.divider()

    # Gráficos
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Demandas por Desenvolvedor")
        if not df.empty:
            fig_dev = px.bar(df, x="responsavel", color="status", title="Carga de Trabalho por Dev",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_dev, use_container_width=True)

    with c2:
        st.subheader("Distribuição por Tipo")
        if not df.empty:
            fig_type = px.pie(df, names="tipo", title="Tipos de Demandas", hole=0.4,
                              color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig_type, use_container_width=True)

    st.subheader("Progresso Detalhado")
    st.dataframe(
        df[['titulo', 'responsavel', 'status', 'progresso', 'tipo']
           ].style.highlight_max(axis=0, color='lightgreen'),
        use_container_width=True
    )

# --- PÁGINA: KANBAN ---
elif menu == "Quadro Kanban":
    st.header("Quadro Kanban")

    # Filtros
    c_filter1, c_filter2 = st.columns(2)
    filtro_dev = c_filter1.multiselect(
        "Filtrar por Desenvolvedor", DESENVOLVEDORES)
    filtro_tipo = c_filter2.multiselect("Filtrar por Tipo", TIPOS_TAREFA)

    df_view = st.session_state.df_tarefas.copy()

    if filtro_dev:
        df_view = df_view[df_view['responsavel'].isin(filtro_dev)]
    if filtro_tipo:
        df_view = df_view[df_view['tipo'].isin(filtro_tipo)]

    # Layout das Colunas do Kanban
    cols = st.columns(len(COLUNAS_KANBAN))

    for idx, coluna_nome in enumerate(COLUNAS_KANBAN):
        with cols[idx]:
            st.subheader(coluna_nome)
            # Estilização visual da coluna (apenas separador)
            st.markdown("---")

            # Filtrar tarefas desta coluna
            tarefas_coluna = df_view[df_view['status'] == coluna_nome]

            for i, row in tarefas_coluna.iterrows():
                # Card da Tarefa
                with st.expander(f"{row['id']} - {row['titulo']} ({row['progresso']}%)", expanded=True):
                    st.caption(
                        f"👤 **{row['responsavel']}** | 🏷️ {row['tipo'].split()[0]}")
                    st.progress(row['progresso'] / 100)

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

                        # Regra de negócio simples: Se 100%, move para Concluído
                        if novo_progresso == 100 and novo_status != "Concluído":
                            st.session_state.df_tarefas.loc[st.session_state.df_tarefas['id']
                                                            == row['id'], 'status'] = "Concluído"
                            st.toast(f"Tarefa {row['id']} concluída!")

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
        status_inicial = col4.selectbox("Status Inicial", COLUNAS_KANBAN)

        descricao = st.text_area(
            "Descrição Detalhada", placeholder="Descreva os requisitos técnicos...")

        submitted = st.form_submit_button("Cadastrar Demanda")

        if submitted and titulo:
            novo_id = st.session_state.df_tarefas['id'].max(
            ) + 1 if not st.session_state.df_tarefas.empty else 1
            nova_linha = {
                "id": novo_id,
                "titulo": titulo,
                "responsavel": responsavel,
                "status": status_inicial,
                "tipo": tipo,
                "progresso": 0,
                "data_criacao": datetime.now().strftime("%Y-%m-%d")
            }

            # Adiciona ao DataFrame usando pd.concat
            st.session_state.df_tarefas = pd.concat(
                [st.session_state.df_tarefas, pd.DataFrame([nova_linha])], ignore_index=True)
            salvar_dados(st.session_state.df_tarefas)
            st.success(f"Demanda '{titulo}' cadastrada com sucesso!")

# --- PÁGINA: CONFIGURAÇÕES ---
elif menu == "Configurações":
    st.header("Configurações do Sistema")

    st.subheader("Gerenciamento de Dados")
    st.write("Os dados são salvos automaticamente em 'dados_educamais.csv'.")

    col1, col2 = st.columns(2)
    with col1:
        csv = st.session_state.df_tarefas.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Baixar Backup (CSV)",
            data=csv,
            file_name='backup_tarefas.csv',
            mime='text/csv',
        )

    with col2:
        if st.button("Limpar/Resetar Banco de Dados"):
            st.session_state.df_tarefas = criar_dados_iniciais()
            st.rerun()

# --- RODAPÉ ---
st.sidebar.markdown("---")
st.sidebar.caption("Desenvolvido por Felipe Toledo")
st.sidebar.caption("v1.0 - ADS Project")
