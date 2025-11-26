import time
import random
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
    initial_sidebar_state="expanded",
)

# --- CONSTANTES E SETUP ---
NOME_PLANILHA = "Tasks Devs"
ARQUIVO_CREDENCIAIS = "credentials.json"
NOME_ABA_LOGS = "Logs"

COLUNAS_KANBAN = [
    "Backlog/A Fazer",
    "Em Desenvolvimento",
    "Code Review/QA",
    "Concluído",
]
DESENVOLVEDORES = ["Eduardo", "Israel", "Pedro", "Vinícius"]
TIPOS_TAREFA = [
    "Feature (Nova Funcionalidade)",
    "Bugfix (Correção)",
    "Refatoração",
    "Infraestrutura",
]
PRIORIDADES = ["🔴 Urgente", "🟡 Alta", "🟢 Média", "⚪ Baixa"]

COLUNAS_OBRIGATORIAS = [
    "id",
    "titulo",
    "descricao",
    "responsavel",
    "status",
    "tipo",
    "prioridade",
    "data_entrega",
    "progresso",
    "data_criacao",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def obter_spreadsheet():
    sheet = conectar_google_sheets()
    return sheet.spreadsheet


def obter_worksheet_logs():
    ss = obter_spreadsheet()
    try:
        ws = ss.worksheet(NOME_ABA_LOGS)
    except gspread.exceptions.WorksheetNotFound:
        ws = ss.add_worksheet(title=NOME_ABA_LOGS, rows=1, cols=7)
        ws.update(
            [
                [
                    "timestamp",
                    "acao",
                    "task_id",
                    "campo",
                    "valor_antigo",
                    "valor_novo",
                    "usuario",
                ]
            ]
        )
    return ws


def obter_usuario_atual():
    try:
        return st.secrets.get(
            "usuario",
            os.environ.get("USERNAME") or os.environ.get("USER") or "Desconhecido",
        )
    except Exception:
        return "Desconhecido"


def registrar_logs(acao, task_id, alteracoes, usuario=None):
    ws = obter_worksheet_logs()
    if usuario is None:
        usuario = obter_usuario_atual()
    linhas = []
    ts = datetime.now().isoformat()
    for campo, par in alteracoes.items():
        antigo, novo = par
        linhas.append(
            [
                ts,
                acao,
                str(task_id),
                campo,
                str(antigo) if antigo is not None else "",
                str(novo) if novo is not None else "",
                usuario,
            ]
        )
    try:
        ws.append_rows(linhas, value_input_option="USER_ENTERED")
    except Exception:
        for linha in linhas:
            ws.append_row(linha, value_input_option="USER_ENTERED")


# --- CACHE DE CONEXÃO ---
@st.cache_resource(ttl=3600)  # Cache por 1 hora
def conectar_google_sheets():
    """
    Estabelece conexão com o Google Sheets usando Service Account.
    """
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            credentials = Credentials.from_service_account_info(
                creds_dict, scopes=SCOPES
            )
        elif os.path.exists(ARQUIVO_CREDENCIAIS):
            credentials = Credentials.from_service_account_file(
                ARQUIVO_CREDENCIAIS, scopes=SCOPES
            )
        else:
            st.error(
                "Nenhuma credencial encontrada! Configure os Secrets (na nuvem) ou adicione 'credentials.json' (local)."
            )
            st.stop()

        client = gspread.authorize(credentials)

        try:
            sheet = client.open(NOME_PLANILHA).sheet1
            return sheet
        except gspread.SpreadsheetNotFound:
            st.error(
                f"Planilha '{NOME_PLANILHA}' não encontrada! Verifique se o nome está exato e se compartilhou com o email da service account."
            )
            st.stop()
        except gspread.exceptions.APIError as e:
            if "Google Drive API has not been used" in str(e):
                st.error(
                    "ERRO DE API: A 'Google Drive API' não está ativada no seu projeto do Google Cloud."
                )
                st.markdown(
                    "[Clique aqui para ativar a Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)"
                )
                st.stop()
            else:
                raise e

    except Exception as e:
        st.error(f"Erro ao conectar no Google Sheets: {e}")
        st.stop()


# --- TRATAMENTO DE DADOS VAZIOS E VALIDAÇÃO ---
def validar_estrutura_planilha(df):
    """
    Valida se o DataFrame possui todas as colunas obrigatórias.
    Retorna (bool, lista_colunas_faltantes)
    """
    colunas_faltantes = [col for col in COLUNAS_OBRIGATORIAS if col not in df.columns]
    return len(colunas_faltantes) == 0, colunas_faltantes


def carregar_dados():
    """
    Carrega os dados da Planilha do Google com validação robusta.
    Detecta dados vazios, colunas faltantes e estrutura corrompida.
    """
    sheet = conectar_google_sheets()

    try:
        dados = sheet.get_all_records()
    except Exception as e:
        st.warning(f"Erro ao ler planilha: {e}. Criando estrutura inicial...")
        return criar_dados_iniciais(sheet)

    # Caso 1: Planilha completamente vazia
    if not dados or len(dados) == 0:
        st.info("Planilha vazia detectada. Inicializando com dados padrão...")
        return criar_dados_iniciais(sheet)

    df = pd.DataFrame(dados)

    # Caso 2: Planilha tem dados mas está com estrutura incorreta
    estrutura_valida, colunas_faltantes = validar_estrutura_planilha(df)

    if not estrutura_valida:
        st.error(
            f"Estrutura da planilha inválida! Colunas faltantes: {', '.join(colunas_faltantes)}"
        )
        st.warning("Recriando estrutura padrão...")
        return criar_dados_iniciais(sheet)

    # Caso 3: Validação de tipos de dados críticos
    try:
        # Garante que ID seja numérico
        df["id"] = pd.to_numeric(df["id"], errors="coerce")
        df = df.dropna(subset=["id"])  # Remove linhas com ID inválido

        # Garante que progresso seja numérico
        df["progresso"] = pd.to_numeric(df["progresso"], errors="coerce").fillna(0)

        # Garante que datas sejam válidas
        df["data_entrega"] = pd.to_datetime(df["data_entrega"], errors="coerce")
        df["data_criacao"] = pd.to_datetime(df["data_criacao"], errors="coerce")

        # Remove linhas completamente inválidas
        if df.empty:
            st.warning("Dados corrompidos detectados. Reinicializando...")
            return criar_dados_iniciais(sheet)

    except Exception as e:
        st.error(f"Erro na validação de dados: {e}")
        return criar_dados_iniciais(sheet)

    return df


def criar_dados_iniciais(sheet):
    """
    Cria dados fictícios e salva na planilha se ela estiver vazia ou corrompida.
    """
    dados = {
        "id": [1, 2, 3, 4, 5],
        "titulo": [
            "Landing Page Vestibular",
            "Correção Menu Mobile",
            "API de Notas",
            "Otimização de SEO",
            "Migração de Servidor",
        ],
        "descricao": [
            "Criar página responsiva para captação de alunos",
            "Ajustar menu collapse no mobile",
            "Desenvolver API REST para consulta de notas",
            "Melhorar ranqueamento no Google",
            "Migrar para servidor AWS",
        ],
        "responsavel": ["Pedro", "Israel", "Vinícius", "Eduardo", "Pedro"],
        "status": [
            "Concluído",
            "Em Desenvolvimento",
            "Code Review/QA",
            "Backlog/A Fazer",
            "Backlog/A Fazer",
        ],
        "tipo": [
            "Feature (Nova Funcionalidade)",
            "Bugfix (Correção)",
            "Feature (Nova Funcionalidade)",
            "Refatoração",
            "Infraestrutura",
        ],
        "prioridade": ["🟢 Média", "🔴 Urgente", "🟡 Alta", "⚪ Baixa", "🟡 Alta"],
        "data_entrega": [
            "2025-12-01",
            "2025-11-25",
            "2025-11-30",
            "2025-12-15",
            "2026-01-10",
        ],
        "progresso": [100, 60, 90, 0, 10],
        "data_criacao": [datetime.now().strftime("%Y-%m-%d")] * 5,
    }
    df = pd.DataFrame(dados)
    salvar_dados_completo(df)
    st.success("Estrutura inicial criada com sucesso!")
    return df


# --- SINCRONIZAÇÃO INCREMENTAL ---
def atualizar_celula_especifica(task_id, campo, novo_valor):
    """
    Args:
        task_id: ID da tarefa a ser atualizada
        campo: Nome da coluna a ser modificada
        novo_valor: Novo valor a ser inserido
    """
    try:
        sheet = conectar_google_sheets()

        # Busca a linha correspondente ao ID
        cell_id = sheet.find(str(task_id))

        if not cell_id:
            st.error(f"Tarefa ID {task_id} não encontrada na planilha!")
            return False

        # Descobre qual coluna modificar
        headers = sheet.row_values(1)  # Primeira linha = cabeçalhos

        if campo not in headers:
            st.error(f"Campo '{campo}' não existe na planilha!")
            return False

        col_index = headers.index(campo) + 1  # gspread usa índice 1-based
        row_index = cell_id.row

        valor_antigo = sheet.cell(row_index, col_index).value
        sheet.update_cell(row_index, col_index, str(novo_valor))
        registrar_logs("atualizacao", task_id, {campo: (valor_antigo, novo_valor)})
        return True

    except Exception as e:
        st.error(f"Erro na atualização incremental: {e}")
        return False


def atualizar_multiplas_celulas(task_id, campos_valores):
    """
    Atualiza múltiplas células de uma mesma linha de forma eficiente.

    Args:
        task_id: ID da tarefa
        campos_valores: Dicionário {campo: novo_valor}
    """
    try:
        sheet = conectar_google_sheets()
        cell_id = sheet.find(str(task_id))

        if not cell_id:
            return False

        headers = sheet.row_values(1)
        row_index = cell_id.row
        linha_atual = sheet.row_values(row_index)
        mapa_antigo = {}
        for i, h in enumerate(headers):
            v = linha_atual[i] if i < len(linha_atual) else ""
            mapa_antigo[h] = v

        # Prepara lista de atualizações em lote
        updates = []
        for campo, valor in campos_valores.items():
            if campo in headers:
                col_index = headers.index(campo) + 1
                updates.append(
                    {
                        "range": f"{gspread.utils.rowcol_to_a1(row_index, col_index)}",
                        "values": [[str(valor)]],
                    }
                )

        # Executa todas as atualizações de uma vez (batch update)
        if updates:
            sheet.batch_update(updates)
        alteracoes = {}
        for campo, valor in campos_valores.items():
            if campo in headers:
                alteracoes[campo] = (mapa_antigo.get(campo), valor)
        if alteracoes:
            registrar_logs("atualizacao", task_id, alteracoes)
        return True

    except Exception as e:
        st.error(f"Erro na atualização em lote: {e}")
        return False


def gerar_id_atomico_com_retry(max_tentativas=5):
    """
    Gera ID único consultando DIRETAMENTE a planilha (não o cache local).
    Implementa retry com backoff exponencial para evitar race conditions.

    Returns:
        int: ID único e seguro

    Raises:
        Exception: Se falhar após todas as tentativas
    """
    for tentativa in range(1, max_tentativas + 1):
        try:
            # CRÍTICO: Lê diretamente da planilha (não usa session_state)
            sheet = conectar_google_sheets()

            # Pega TODOS os IDs da coluna 'id' (coluna A)
            # row_values(1) = cabeçalhos
            # col_values(1) = todos os valores da coluna A
            coluna_ids = sheet.col_values(1)  # ['id', '1', '2', '3', ...]

            # Remove o cabeçalho e converte para int
            ids_existentes = []
            for valor in coluna_ids[1:]:  # Pula o cabeçalho
                try:
                    ids_existentes.append(int(valor))
                except (ValueError, TypeError):
                    continue  # Ignora valores inválidos

            # Gera o próximo ID
            if ids_existentes:
                novo_id = max(ids_existentes) + 1
            else:
                novo_id = 1

            # Valida se o ID é único (dupla verificação)
            if novo_id in ids_existentes:
                raise ValueError(f"ID {novo_id} já existe! Tentando novamente...")

            return novo_id

        except gspread.exceptions.APIError as e:
            if "RATE_LIMIT_EXCEEDED" in str(e):
                # Backoff exponencial com jitter
                delay = (2**tentativa) + random.uniform(0, 1)
                st.warning(
                    f"Rate limit atingido. Aguardando {delay:.1f}s (tentativa {tentativa}/{max_tentativas})..."
                )
                time.sleep(delay)
                continue
            else:
                raise e

        except Exception as e:
            if tentativa < max_tentativas:
                delay = 0.5 * tentativa + random.uniform(0, 0.5)
                st.warning(
                    f"Erro ao gerar ID (tentativa {tentativa}/{max_tentativas}): {e}"
                )
                time.sleep(delay)
                continue
            else:
                st.error(f"Falha ao gerar ID após {max_tentativas} tentativas: {e}")
                raise e

    raise Exception("Falha ao gerar ID único após todas as tentativas")


def validar_id_unico(task_id):
    """
    Valida se o ID inserido é único na planilha.

    Args:
        task_id: ID a ser validado

    Returns:
        bool: True se único, False se duplicado
    """
    try:
        sheet = conectar_google_sheets()

        # Busca todas as ocorrências do ID
        cells = sheet.findall(str(task_id))

        # Remove o cabeçalho da contagem
        ocorrencias = [c for c in cells if c.row > 1]

        if len(ocorrencias) > 1:
            st.error(
                f"ID {task_id} DUPLICADO! Encontradas {len(ocorrencias)} ocorrências."
            )
            return False

        return True

    except Exception as e:
        st.warning(f"Não foi possível validar unicidade do ID: {e}")
        return True  # Assume válido em caso de erro na validação


def adicionar_tarefa_incremental_com_validacao(
    nova_tarefa_dict, validar_pos_insercao=True
):
    """
    Adiciona uma nova tarefa COM VALIDAÇÃO de ID único.

    Args:
        nova_tarefa_dict: Dicionário com os dados da nova tarefa
        validar_pos_insercao: Se True, valida se ID é único após inserção

    Returns:
        bool: True se sucesso, False se falhou
    """
    try:
        sheet = conectar_google_sheets()

        # Obtém os cabeçalhos da planilha (primeira linha)
        headers = sheet.row_values(1)

        if not headers:
            st.error("Planilha sem cabeçalhos! Impossível adicionar tarefa.")
            return False

        # Cria a linha na MESMA ORDEM dos cabeçalhos da planilha
        nova_linha = []
        for coluna in headers:
            valor = nova_tarefa_dict.get(coluna, "")
            nova_linha.append(str(valor))

        # Adiciona a linha no final da planilha
        sheet.append_row(nova_linha, value_input_option="USER_ENTERED")
        registrar_logs(
            "criacao",
            nova_tarefa_dict.get("id"),
            {k: (None, nova_tarefa_dict.get(k)) for k in headers},
        )

        # VALIDAÇÃO PÓS-INSERÇÃO (Opcional mas recomendado)
        if validar_pos_insercao:
            time.sleep(0.5)  # Aguarda propagação da API

            if not validar_id_unico(nova_tarefa_dict["id"]):
                st.error(
                    f"CONFLITO DETECTADO! ID {nova_tarefa_dict['id']} foi duplicado."
                )
                # Aqui você pode implementar lógica de rollback se necessário
                return False

        return True

    except gspread.exceptions.APIError as e:
        st.error(f"Erro da API do Google: {e}")
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar tarefa: {e}")
        return False


def adicionar_tarefa_com_fallback(nova_tarefa_dict):
    """
    Tenta adicionar tarefa incrementalmente com validação.
    Se falhar, usa o método completo como fallback.

    Args:
        nova_tarefa_dict: Dicionário com os dados da nova tarefa

    Returns:
        bool: True se sucesso (qualquer método), False se ambos falharam
    """
    # Tentativa 1: Método rápido com validação
    sucesso = adicionar_tarefa_incremental_com_validacao(
        nova_tarefa_dict, validar_pos_insercao=True
    )

    if sucesso:
        st.success("Tarefa adicionada com sucesso (modo rápido e seguro)!")
        return True

    # Tentativa 2: Fallback para método completo
    st.warning("Modo rápido falhou. Tentando método completo...")

    try:
        # Adiciona ao DataFrame local
        nova_linha_df = pd.DataFrame([nova_tarefa_dict])
        st.session_state.df_tarefas = pd.concat(
            [st.session_state.df_tarefas, nova_linha_df], ignore_index=True
        )

        # Salva tudo (método lento mas confiável)
        salvar_dados_completo(st.session_state.df_tarefas)

        st.success("Tarefa adicionada com sucesso (modo completo)!")
        registrar_logs(
            "criacao",
            nova_tarefa_dict.get("id"),
            {
                k: (None, nova_tarefa_dict.get(k))
                for k in st.session_state.df_tarefas.columns
            },
        )
        return True

    except Exception as e:
        st.error(f"Falha total ao adicionar tarefa: {e}")
        return False


def salvar_dados_completo(df):
    """
    Salva o DataFrame COMPLETO na Planilha (operação pesada).
    Use apenas quando necessário (criar planilha, reset, etc).
    """
    sheet = conectar_google_sheets()
    sheet.clear()
    dados_lista = [df.columns.values.tolist()] + df.astype(str).values.tolist()
    sheet.update(dados_lista)


# --- FUNÇÃO AUXILIAR PARA FORÇAR LIMPEZA DE CACHE ---
def limpar_cache_conexao():
    """Força recarregamento da conexão (útil após erros ou updates)"""
    conectar_google_sheets.clear()
    st.cache_data.clear()


# --- INICIALIZAÇÃO DO ESTADO ---
if "df_tarefas" not in st.session_state:
    with st.spinner("Carregando dados da nuvem..."):
        st.session_state.df_tarefas = carregar_dados()

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.title("Tracker Tasks")
    st.caption("Gestão de Demandas de Desenvolvimento")

    menu = st.radio(
        "Navegação",
        ["Dashboard", "Quadro Kanban", "Nova Demanda", "Histórico", "Configurações"],
    )

    st.divider()
    st.info(f"👥 Equipe: {len(DESENVOLVEDORES)} Desenvolvedores")

# --- PÁGINA: DASHBOARD ---
if menu == "Dashboard":
    st.header("Dashboard de Produtividade")
    st.markdown("Visão geral do andamento dos projetos.")

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        if st.button("🔄 Atualizar", use_container_width=True):
            with st.spinner("Carregando..."):
                st.session_state.df_tarefas = carregar_dados()
            st.rerun()

    df = st.session_state.df_tarefas.copy()
    df["progresso"] = pd.to_numeric(df["progresso"], errors="coerce").fillna(0)
    df["data_entrega"] = pd.to_datetime(df["data_entrega"], errors="coerce")

    # Métricas (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    concluidas = len(df[df["status"] == "Concluído"])
    em_andamento = len(df[df["status"] == "Em Desenvolvimento"])
    atrasadas = len(
        df[(df["data_entrega"] < datetime.now()) & (df["status"] != "Concluído")]
    )

    col1.metric("Total de Demandas", total)
    col2.metric(
        "Taxa de Conclusão", f"{(concluidas/total*100):.1f}%" if total > 0 else "0%"
    )
    col3.metric("Em Andamento", em_andamento)
    col4.metric(
        "⚠️ Atrasadas",
        atrasadas,
        delta=f"-{atrasadas}" if atrasadas > 0 else "0",
        delta_color="inverse",
    )

    st.divider()

    # Alertas e Tarefas Críticas
    col_urgentes, col_prazo = st.columns(2)

    with col_urgentes:
        st.subheader("🚨 Tarefas de Alta Prioridade")
        df_urgentes = df[
            df["prioridade"].isin(["🔴 Urgente", "🟡 Alta"])
            & (df["status"] != "Concluído")
        ]
        if not df_urgentes.empty:
            st.dataframe(
                df_urgentes[
                    ["titulo", "responsavel", "prioridade", "data_entrega", "progresso"]
                ].sort_values("data_entrega"),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("✅ Nenhuma tarefa urgente no momento!")

    with col_prazo:
        st.subheader("📅 Próximas Entregas (15 dias)")
        hoje = datetime.now()
        df_proximas = df[
            (df["data_entrega"] >= hoje)
            & (df["data_entrega"] <= hoje + pd.Timedelta(days=15))
            & (df["status"] != "Concluído")
        ].sort_values("data_entrega")

        if not df_proximas.empty:
            st.dataframe(
                df_proximas[
                    ["titulo", "responsavel", "data_entrega", "prioridade", "progresso"]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nenhuma entrega próxima nos próximos 15 dias.")

    st.divider()

    # Gráficos
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("👨🏻‍💻 Demandas por Desenvolvedor")
        if not df.empty:
            # Agrupa dados para contagem
            df_grouped = (
                df.groupby(["responsavel", "status"])
                .size()
                .reset_index(name="quantidade")
            )

            fig_dev = px.bar(
                df_grouped,
                x="responsavel",
                y="quantidade",
                color="status",
                text="quantidade",  # Mostra o número na barra
                title="Carga de Trabalho por Dev",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            # Ajusta posição do texto para ficar dentro da barra
            fig_dev.update_traces(textposition="auto")
            st.plotly_chart(fig_dev, use_container_width=True)

    with c2:
        st.subheader("🏷️ Distribuição por Tipo")
        if not df.empty:
            fig_type = px.pie(
                df,
                names="tipo",
                title="Tipos de Demandas",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            st.plotly_chart(fig_type, use_container_width=True)

    st.subheader("Progresso Detalhado")
    st.dataframe(
        df[
            [
                "titulo",
                "responsavel",
                "status",
                "prioridade",
                "data_entrega",
                "progresso",
                "tipo",
            ]
        ].style.highlight_max(axis=0, color="lightgreen"),
        use_container_width=True,
        hide_index=True,
    )

# --- PÁGINA: KANBAN ---
elif menu == "Quadro Kanban":
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

    # Filtros
    c_filter1, c_filter2, c_filter3 = st.columns(3)
    filtro_dev = c_filter1.multiselect("Filtrar por Desenvolvedor", DESENVOLVEDORES)
    filtro_tipo = c_filter2.multiselect("Filtrar por Tipo", TIPOS_TAREFA)
    filtro_prioridade = c_filter3.multiselect("Filtrar por Prioridade", PRIORIDADES)

    df_view = st.session_state.df_tarefas.copy()
    df_view["progresso"] = pd.to_numeric(df_view["progresso"], errors="coerce").fillna(
        0
    )
    df_view["data_entrega"] = pd.to_datetime(df_view["data_entrega"], errors="coerce")

    if filtro_dev:
        df_view = df_view[df_view["responsavel"].isin(filtro_dev)]
    if filtro_tipo:
        df_view = df_view[df_view["tipo"].isin(filtro_tipo)]
    if filtro_prioridade:
        df_view = df_view[df_view["prioridade"].isin(filtro_prioridade)]

    # Layout das Colunas do Kanban
    cols = st.columns(len(COLUNAS_KANBAN))
    cores = {
        "Backlog/A Fazer": "#EAB308",
        "Em Desenvolvimento": "#3B82F6",
        "Code Review/QA": "#EC4899",
        "Concluído": "#22C55E",
    }

    for idx, coluna_nome in enumerate(COLUNAS_KANBAN):
        with cols[idx]:
            tarefas_coluna = df_view[df_view["status"] == coluna_nome].sort_values(
                "data_entrega"
            )
            accent = cores.get(coluna_nome, "#6B7280")
            st.markdown(
                f"<div class='kanban-header' style='--accent:{accent}'><span class='kanban-title'>{coluna_nome}</span><span class='kanban-count'>{len(tarefas_coluna)} tarefas</span></div>",
                unsafe_allow_html=True,
            )
            if tarefas_coluna.empty:
                st.markdown(
                    "<div class='kanban-empty'>Nenhuma tarefa nesta coluna</div>",
                    unsafe_allow_html=True,
                )
            else:
                media_prog = int(
                    pd.to_numeric(tarefas_coluna["progresso"], errors="coerce")
                    .fillna(0)
                    .mean()
                )
                st.progress(media_prog / 100)

            for i, row in tarefas_coluna.iterrows():
                # Calcular status do prazo
                dias_restantes = (row["data_entrega"] - datetime.now()).days
                emoji_prazo = "⏰" if dias_restantes <= 3 else "📅"
                cor_prazo = (
                    "red"
                    if dias_restantes < 0
                    else "orange" if dias_restantes <= 3 else "green"
                )

                # Card da Tarefa
                with st.expander(
                    f"#{row['id']} {row['prioridade']} - {row['titulo']}", expanded=True
                ):
                    col_info1, col_info2 = st.columns(2)
                    col_info1.caption(f"👨🏻‍💻 **{row['responsavel']}**")
                    col_info2.caption(f"🏷️ {row['tipo'].split()[0]}")

                    # Exibir prazo com destaque visual
                    st.markdown(
                        f"**{emoji_prazo} Entrega:** :{cor_prazo}[{row['data_entrega'].strftime('%d/%m/%Y')}] ({dias_restantes} dias)"
                    )
                    st.progress(int(row["progresso"]) / 100)

                    # Controles de Edição Rápida
                    novo_status = st.selectbox(
                        "Mover para:",
                        COLUNAS_KANBAN,
                        index=COLUNAS_KANBAN.index(row["status"]),
                        key=f"status_{row['id']}",
                    )

                    novo_progresso = st.slider(
                        "Progresso %",
                        0,
                        100,
                        int(row["progresso"]),
                        10,
                        key=f"prog_{row['id']}",
                    )

                    # Atualização Incremental
                    if (
                        novo_status != row["status"]
                        or novo_progresso != row["progresso"]
                    ):
                        # Atualiza no Session State
                        st.session_state.df_tarefas.loc[
                            st.session_state.df_tarefas["id"] == row["id"], "status"
                        ] = novo_status
                        st.session_state.df_tarefas.loc[
                            st.session_state.df_tarefas["id"] == row["id"], "progresso"
                        ] = novo_progresso

                        # Auto-completar se progresso = 100%
                        if novo_progresso == 100 and novo_status != "Concluído":
                            novo_status = "Concluído"
                            st.session_state.df_tarefas.loc[
                                st.session_state.df_tarefas["id"] == row["id"], "status"
                            ] = "Concluído"
                            st.toast(f"✅ Tarefa #{row['id']} concluída!")

                        # Atualização incremental (rápida)
                        with st.spinner("Salvando..."):
                            sucesso = atualizar_multiplas_celulas(
                                row["id"],
                                {"status": novo_status, "progresso": novo_progresso},
                            )

                            if not sucesso:
                                st.warning(
                                    "Falha na atualização rápida. Tentando salvar tudo..."
                                )
                                salvar_dados_completo(st.session_state.df_tarefas)

                        st.rerun()

# --- PÁGINA: NOVA DEMANDA ---
elif menu == "Nova Demanda":
    st.header("Cadastro de Nova Demanda")

    # Controle de estado para exibir resumo
    if "tarefa_cadastrada" not in st.session_state:
        st.session_state.tarefa_cadastrada = None

    # Botão "Cadastrar Outra" FORA do form
    if st.session_state.tarefa_cadastrada is not None:
        st.success(
            f"Última demanda cadastrada: **#{st.session_state.tarefa_cadastrada['id']} - {st.session_state.tarefa_cadastrada['titulo']}**"
        )

        # Mostra resumo
        with st.expander("Resumo da Última Tarefa", expanded=True):
            col_resumo1, col_resumo2 = st.columns(2)

            with col_resumo1:
                st.markdown(
                    f"""
                - **ID:** #{st.session_state.tarefa_cadastrada['id']}
                - **Título:** {st.session_state.tarefa_cadastrada['titulo']}
                - **Responsável:** {st.session_state.tarefa_cadastrada['responsavel']}
                - **Status:** {st.session_state.tarefa_cadastrada['status']}
                """
                )

            with col_resumo2:
                st.markdown(
                    f"""
                - **Tipo:** {st.session_state.tarefa_cadastrada['tipo'].split()[0]}
                - **Prioridade:** {st.session_state.tarefa_cadastrada['prioridade']}
                - **Entrega:** {st.session_state.tarefa_cadastrada['data_entrega']}
                - **Criada em:** {st.session_state.tarefa_cadastrada['data_criacao']}
                """
                )

        # Botão FORA do form
        if st.button(
            "Cadastrar Outra Demanda", use_container_width=True, type="primary"
        ):
            st.session_state.tarefa_cadastrada = None
            st.rerun()

        st.divider()

    # FORMULÁRIO
    with st.form("form_nova_demanda", clear_on_submit=True):
        col1, col2 = st.columns(2)
        titulo = col1.text_input(
            "Título da Demanda*", placeholder="Ex: Atualização Portal do Aluno"
        )
        responsavel = col2.selectbox("Desenvolvedor Responsável*", DESENVOLVEDORES)

        col3, col4 = st.columns(2)
        tipo = col3.selectbox("Tipo de Demanda*", TIPOS_TAREFA)
        prioridade = col4.selectbox("Prioridade*", PRIORIDADES)

        col5, col6 = st.columns(2)
        status_inicial = col5.selectbox("Status Inicial*", COLUNAS_KANBAN, index=0)
        data_entrega = col6.date_input(
            "Data de Entrega*",
            value=datetime.now() + pd.Timedelta(days=7),
            min_value=datetime.now(),
        )

        descricao = st.text_area(
            "Descrição Detalhada (opcional)",
            placeholder="Descreva os requisitos técnicos, dependências, observações...",
            height=120,
        )

        st.caption("*Campos obrigatórios")

        # APENAS form_submit_button é permitido dentro do form
        submitted = st.form_submit_button(
            "Cadastrar Demanda", use_container_width=True, type="primary"
        )

    # PROCESSAMENTO FORA DO FORM
    if submitted:
        # Validação básica
        if not titulo or not titulo.strip():
            st.error("O título da demanda é obrigatório!")
            st.stop()

        if len(titulo) < 5:
            st.error("O título deve ter pelo menos 5 caracteres!")
            st.stop()

        try:
            # Calcula o próximo ID
            with st.spinner("Gerando ID..."):
                try:
                    novo_id = gerar_id_atomico_com_retry(max_tentativas=5)
                    st.info(f"ID #{novo_id} reservado com sucesso!")
                except Exception as e:
                    st.error(f"Não foi possível gerar ID único: {e}")
                    st.stop()

            # Cria o dicionário da nova tarefa
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
                "data_criacao": datetime.now().strftime("%Y-%m-%d"),
            }

            # Adiciona apenas a nova linha
            with st.spinner("Salvando na nuvem (modo rápido)..."):
                sucesso = adicionar_tarefa_com_fallback(nova_tarefa)

            if sucesso:
                # Atualiza o DataFrame local APENAS com a nova linha
                nova_linha_df = pd.DataFrame([nova_tarefa])
                st.session_state.df_tarefas = pd.concat(
                    [st.session_state.df_tarefas, nova_linha_df], ignore_index=True
                )

                # Salva no estado para exibir resumo
                st.session_state.tarefa_cadastrada = nova_tarefa.copy()

                st.balloons()
                st.rerun()

            else:
                st.error("Não foi possível cadastrar a demanda. Tente novamente.")

        except Exception as e:
            st.error(f"Erro inesperado ao cadastrar demanda: {e}")
            st.exception(e)

    # Seção de Estatísticas Rápidas
    st.divider()
    st.subheader("Estatísticas Rápidas")

    col_stat1, col_stat2, col_stat3 = st.columns(3)

    df_stats = st.session_state.df_tarefas

    col_stat1.metric("Total de Tarefas", len(df_stats), delta="+1 ao cadastrar")

    col_stat2.metric(
        "Tarefas Ativas",
        len(df_stats[df_stats["status"] != "Concluído"]),
        delta_color="inverse",
    )

    col_stat3.metric(
        "Próximo ID Disponível",
        (
            int(pd.to_numeric(df_stats["id"], errors="coerce").max() + 1)
            if not df_stats.empty
            else 1
        ),
    )

elif menu == "Histórico":
    st.header("Histórico de Alterações")
    try:
        ws = obter_worksheet_logs()
        registros = ws.get_all_records()
    except Exception as e:
        st.error(f"Erro ao carregar logs: {e}")
        registros = []
    if not registros:
        st.info("Nenhum log registrado.")
    else:
        df_logs = pd.DataFrame(registros)
        if "timestamp" in df_logs.columns:
            try:
                df_logs["timestamp"] = pd.to_datetime(
                    df_logs["timestamp"], errors="coerce"
                )
            except Exception:
                pass
        colf1, colf2, colf3, colf4 = st.columns(4)
        filtro_id = colf1.text_input("Filtrar por ID", "")
        filtro_acao = colf2.multiselect(
            "Ações", sorted(df_logs["acao"].dropna().unique().tolist())
        )
        filtro_usuario = colf3.multiselect(
            "Usuário", sorted(df_logs["usuario"].dropna().unique().tolist())
        )
        filtro_campo = colf4.multiselect(
            "Campo", sorted(df_logs["campo"].dropna().unique().tolist())
        )
        if filtro_id.strip():
            df_logs = df_logs[df_logs["task_id"].astype(str) == filtro_id.strip()]
        if filtro_acao:
            df_logs = df_logs[df_logs["acao"].isin(filtro_acao)]
        if filtro_usuario:
            df_logs = df_logs[df_logs["usuario"].isin(filtro_usuario)]
        if filtro_campo:
            df_logs = df_logs[df_logs["campo"].isin(filtro_campo)]
        if "timestamp" in df_logs.columns:
            df_logs = df_logs.sort_values("timestamp", ascending=False)
        st.dataframe(
            df_logs[
                [
                    c
                    for c in [
                        "timestamp",
                        "acao",
                        "task_id",
                        "campo",
                        "valor_antigo",
                        "valor_novo",
                        "usuario",
                    ]
                    if c in df_logs.columns
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

# --- PÁGINA: CONFIGURAÇÕES ---
elif menu == "Configurações":
    st.header("Configurações do Sistema")

    st.subheader("Conexão Google Sheets")
    st.info(f"Conectado à planilha: **{NOME_PLANILHA}**")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Recarregar Dados", use_container_width=True):
            with st.spinner("Carregando..."):
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
    col_stats2.metric("Desenvolvedores Ativos", df["responsavel"].nunique())
    col_stats3.metric("Tipos de Demanda", df["tipo"].nunique())
    col_stats4.metric(
        "Estrutura Validada", "OK" if validar_estrutura_planilha(df)[0] else "Erro"
    )

    st.divider()

    # Diagnóstico da planilha
    st.subheader("Diagnóstico da Planilha")

    with st.expander("Ver Detalhes Técnicos"):
        st.write("**Colunas Presentes:**")
        st.code(", ".join(df.columns.tolist()))

        st.write("**Colunas Obrigatórias:**")
        st.code(", ".join(COLUNAS_OBRIGATORIAS))

        estrutura_ok, faltantes = validar_estrutura_planilha(df)
        if estrutura_ok:
            st.success("Estrutura da planilha está correta!")
        else:
            st.error(f"Colunas faltantes: {', '.join(faltantes)}")

# --- RODAPÉ ---
st.sidebar.markdown("---")
st.sidebar.caption("Desenvolvido por Toledo")
st.sidebar.caption("Criado com Streamlit + Google Sheets")
