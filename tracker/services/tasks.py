import time
import random
import pandas as pd
from datetime import datetime
import streamlit as st
import gspread
from tracker.config import COLUNAS_OBRIGATORIAS
from tracker.services.sheets import conectar_google_sheets
from tracker.services.logs import registrar_logs

def validar_estrutura_planilha(df):
    colunas_faltantes = [col for col in COLUNAS_OBRIGATORIAS if col not in df.columns]
    return len(colunas_faltantes) == 0, colunas_faltantes

def carregar_dados():
    sheet = conectar_google_sheets()
    try:
        dados = sheet.get_all_records()
    except Exception as e:
        st.warning(f"Erro ao ler planilha: {e}. Criando estrutura inicial...")
        return criar_dados_iniciais(sheet)
    if not dados or len(dados) == 0:
        st.info("Planilha vazia detectada. Inicializando com dados padrão...")
        return criar_dados_iniciais(sheet)
    df = pd.DataFrame(dados)
    estrutura_valida, colunas_faltantes = validar_estrutura_planilha(df)
    if not estrutura_valida:
        st.error(f"Estrutura da planilha inválida! Colunas faltantes: {', '.join(colunas_faltantes)}")
        st.warning("Recriando estrutura padrão...")
        return criar_dados_iniciais(sheet)
    try:
        df['id'] = pd.to_numeric(df['id'], errors='coerce')
        df = df.dropna(subset=['id'])
        df['progresso'] = pd.to_numeric(df['progresso'], errors='coerce').fillna(0)
        df['data_entrega'] = pd.to_datetime(df['data_entrega'], errors='coerce')
        df['data_criacao'] = pd.to_datetime(df['data_criacao'], errors='coerce')
        if df.empty:
            st.warning("Dados corrompidos detectados. Reinicializando...")
            return criar_dados_iniciais(sheet)
    except Exception as e:
        st.error(f"Erro na validação de dados: {e}")
        return criar_dados_iniciais(sheet)
    return df

def criar_dados_iniciais(sheet):
    dados = {
        "id": [1, 2, 3, 4, 5],
        "titulo": ["Landing Page Vestibular", "Correção Menu Mobile", "API de Notas", "Otimização de SEO", "Migração de Servidor"],
        "descricao": ["Criar página responsiva para captação de alunos", "Ajustar menu collapse no mobile", "Desenvolver API REST para consulta de notas", "Melhorar ranqueamento no Google", "Migrar para servidor AWS"],
        "responsavel": ["Pedro", "Israel", "Vinícius", "Eduardo", "Pedro"],
        "status": ["Concluído", "Em Desenvolvimento", "Code Review/QA", "Backlog/A Fazer", "Backlog/A Fazer"],
        "tipo": ["Feature (Nova Funcionalidade)", "Bugfix (Correção)", "Feature (Nova Funcionalidade)", "Refatoração", "Infraestrutura"],
        "prioridade": ["🟢 Média", "🔴 Urgente", "🟡 Alta", "⚪ Baixa", "🟡 Alta"],
        "data_entrega": ["2025-12-01", "2025-11-25", "2025-11-30", "2025-12-15", "2026-01-10"],
        "progresso": [100, 60, 90, 0, 10],
        "data_criacao": [datetime.now().strftime("%Y-%m-%d")] * 5
    }
    df = pd.DataFrame(dados)
    salvar_dados_completo(df)
    st.success("Estrutura inicial criada com sucesso!")
    return df

def salvar_dados_completo(df):
    sheet = conectar_google_sheets()
    sheet.clear()
    dados_lista = [df.columns.values.tolist()] + df.astype(str).values.tolist()
    sheet.update(dados_lista)

def atualizar_celula_especifica(task_id, campo, novo_valor):
    try:
        sheet = conectar_google_sheets()
        cell_id = sheet.find(str(task_id))
        if not cell_id:
            st.error(f"Tarefa ID {task_id} não encontrada na planilha!")
            return False
        headers = sheet.row_values(1)
        if campo not in headers:
            st.error(f"Campo '{campo}' não existe na planilha!")
            return False
        col_index = headers.index(campo) + 1
        row_index = cell_id.row
        valor_antigo = sheet.cell(row_index, col_index).value
        sheet.update_cell(row_index, col_index, str(novo_valor))
        registrar_logs("atualizacao", task_id, {campo: (valor_antigo, novo_valor)})
        return True
    except Exception as e:
        st.error(f"Erro na atualização incremental: {e}")
        return False

def atualizar_multiplas_celulas(task_id, campos_valores):
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
        updates = []
        for campo, valor in campos_valores.items():
            if campo in headers:
                col_index = headers.index(campo) + 1
                updates.append({'range': f'{gspread.utils.rowcol_to_a1(row_index, col_index)}', 'values': [[str(valor)]]})
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
    for tentativa in range(1, max_tentativas + 1):
        try:
            sheet = conectar_google_sheets()
            coluna_ids = sheet.col_values(1)
            ids_existentes = []
            for valor in coluna_ids[1:]:
                try:
                    ids_existentes.append(int(valor))
                except (ValueError, TypeError):
                    continue
            novo_id = max(ids_existentes) + 1 if ids_existentes else 1
            if novo_id in ids_existentes:
                raise ValueError(f"ID {novo_id} já existe! Tentando novamente...")
            return novo_id
        except gspread.exceptions.APIError as e:
            if "RATE_LIMIT_EXCEEDED" in str(e):
                delay = (2 ** tentativa) + random.uniform(0, 1)
                st.warning(f"Rate limit atingido. Aguardando {delay:.1f}s (tentativa {tentativa}/{max_tentativas})...")
                time.sleep(delay)
                continue
            else:
                raise e
        except Exception as e:
            if tentativa < max_tentativas:
                delay = 0.5 * tentativa + random.uniform(0, 0.5)
                st.warning(f"Erro ao gerar ID (tentativa {tentativa}/{max_tentativas}): {e}")
                time.sleep(delay)
                continue
            else:
                st.error(f"Falha ao gerar ID após {max_tentativas} tentativas: {e}")
                raise e
    raise Exception("Falha ao gerar ID único após todas as tentativas")

def validar_id_unico(task_id):
    try:
        sheet = conectar_google_sheets()
        cells = sheet.findall(str(task_id))
        ocorrencias = [c for c in cells if c.row > 1]
        if len(ocorrencias) > 1:
            st.error(f"ID {task_id} DUPLICADO! Encontradas {len(ocorrencias)} ocorrências.")
            return False
        return True
    except Exception as e:
        st.warning(f"Não foi possível validar unicidade do ID: {e}")
        return True

def adicionar_tarefa_incremental_com_validacao(nova_tarefa_dict, validar_pos_insercao=True):
    try:
        sheet = conectar_google_sheets()
        headers = sheet.row_values(1)
        if not headers:
            st.error("Planilha sem cabeçalhos! Impossível adicionar tarefa.")
            return False
        nova_linha = []
        for coluna in headers:
            valor = nova_tarefa_dict.get(coluna, '')
            nova_linha.append(str(valor))
        sheet.append_row(nova_linha, value_input_option='USER_ENTERED')
        registrar_logs("criacao", nova_tarefa_dict.get('id'), {k: (None, nova_tarefa_dict.get(k)) for k in headers})
        if validar_pos_insercao:
            time.sleep(0.5)
            if not validar_id_unico(nova_tarefa_dict['id']):
                st.error(f"CONFLITO DETECTADO! ID {nova_tarefa_dict['id']} foi duplicado.")
                return False
        return True
    except gspread.exceptions.APIError as e:
        st.error(f"Erro da API do Google: {e}")
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar tarefa: {e}")
        return False

def adicionar_tarefa_com_fallback(nova_tarefa_dict):
    sucesso = adicionar_tarefa_incremental_com_validacao(nova_tarefa_dict, validar_pos_insercao=True)
    if sucesso:
        st.success("Tarefa adicionada com sucesso (modo rápido e seguro)!")
        return True
    st.warning("Modo rápido falhou. Tentando método completo...")
    try:
        nova_linha_df = pd.DataFrame([nova_tarefa_dict])
        st.session_state.df_tarefas = pd.concat([st.session_state.df_tarefas, nova_linha_df], ignore_index=True)
        salvar_dados_completo(st.session_state.df_tarefas)
        st.success("Tarefa adicionada com sucesso (modo completo)!")
        registrar_logs("criacao", nova_tarefa_dict.get('id'), {k: (None, nova_tarefa_dict.get(k)) for k in st.session_state.df_tarefas.columns})
        return True
    except Exception as e:
        st.error(f"Falha total ao adicionar tarefa: {e}")
        return False