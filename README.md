# Educa Mais - Gestão de Tech

![Logo ou Badge](https://img.shields.io/badge/Streamlit-App-blue) ![Python](https://img.shields.io/badge/Python-3.8+-green) ![Google Sheets](https://img.shields.io/badge/Google%20Sheets-Integration-yellow)

## Descrição

O **Tracker Task - Gestão de Demandas Tech** é uma aplicação web desenvolvida em Streamlit para facilitar a gestão de tarefas de desenvolvimento web/software. O sistema permite acompanhar o progresso de projetos através de um quadro Kanban interativo, integrado com o Google Sheets para armazenamento e sincronização de dados em tempo real.

Ideal para equipes de desenvolvimento pequenas que precisam de uma ferramenta simples, visual e colaborativa para organizar demandas, acompanhar status e medir produtividade.

## Funcionalidades

- **Dashboard Interativo**: Visualize métricas de produtividade, gráficos de distribuição de tarefas por desenvolvedor e tipo, e progresso detalhado.
- **Quadro Kanban**: Organize tarefas em colunas (Backlog/A Fazer, Em Desenvolvimento, Code Review/QA, Concluído) com edição rápida de status e progresso.
- **Cadastro de Novas Demandas**: Formulário intuitivo para adicionar tarefas com título, responsável, tipo e descrição.
- **Integração com Google Sheets**: Sincronização automática de dados na nuvem, permitindo acesso colaborativo.
- **Filtros e Buscas**: Filtre tarefas por desenvolvedor e tipo no quadro Kanban.
- **Configurações**: Opções para recarregar dados, resetar planilha e gerenciar conexão.
- **Responsivo**: Interface adaptável para diferentes dispositivos.

## Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Python 3.8 ou superior**
- Uma conta no **Google Cloud Platform** com as APIs ativadas:
  - Google Sheets API
  - Google Drive API
- Credenciais de **Service Account** do Google (arquivo `credentials.json`)

## Instalação

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/seu-usuario/tracker-task.git
   cd tracker-task
   ```

2. **Crie um ambiente virtual** (recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuração

### 1. Configuração do Google Cloud

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto ou selecione um existente.
3. Ative as APIs necessárias:
   - **Google Sheets API**: [Ativar aqui](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
   - **Google Drive API**: [Ativar aqui](https://console.cloud.google.com/apis/library/drive.googleapis.com)
4. Crie uma **Service Account**:
   - Vá para "IAM & Admin" > "Service Accounts".
   - Clique em "Create Service Account".
   - Dê um nome (ex: "educamais-service").
   - Gere uma chave JSON e baixe o arquivo `credentials.json`.
5. Compartilhe a planilha do Google Sheets com o email da Service Account (encontrado no arquivo JSON).

### 2. Configuração da Planilha

1. Crie uma nova planilha no Google Sheets chamada **"Tasks Devs"** (ou altere a constante `NOME_PLANILHA` no código).
2. Compartilhe a planilha com o email da Service Account (permissão de edição).

### 3. Arquivo de Credenciais

- Coloque o arquivo `credentials.json` na raiz do projeto.
- **Atenção**: Nunca faça commit deste arquivo no Git! Ele já está no `.gitignore`.

### 4. Configuração para Deploy na Nuvem (Opcional)

Para deploy no Streamlit Cloud ou similar, configure os secrets:

- No painel do Streamlit, adicione o conteúdo do `credentials.json` como um secret chamado `gcp_service_account`.

## Como Usar

1. **Execute a aplicação**:
   ```bash
   streamlit run app.py
   ```

2. **Acesse no navegador**: A aplicação será aberta em `http://localhost:8501`.

3. **Navegação**:
   - **Dashboard**: Visualize métricas e gráficos gerais.
   - **Quadro Kanban**: Gerencie tarefas arrastando entre colunas e ajustando progresso.
   - **Nova Demanda**: Cadastre novas tarefas.
   - **Configurações**: Atualize dados ou resete a planilha.

4. **Primeira Execução**: Se a planilha estiver vazia, dados fictícios serão criados automaticamente.

## Estrutura do Projeto

```
tracker-task/
├── app.py                 # Arquivo principal da aplicação Streamlit
├── requirements.txt       # Dependências Python
├── .gitignore             # Arquivos ignorados pelo Git
├── credentials.json       # Credenciais Google (não versionado)
├── dados_educamais.csv    # Dados de exemplo (opcional)
└── README.md              # Este arquivo
```

## Contribuição

Contribuições são bem-vindas! Siga estes passos:

1. Fork o projeto.
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`).
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`).
4. Push para a branch (`git push origin feature/nova-funcionalidade`).
5. Abra um Pull Request.

## Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 👨Autor

**Felipe Toledo**
- LinkedIn: [Seu LinkedIn](https://linkedin.com/in/felipetoledo-8)
- Email: toledo.felipe.ads@gmail.com

---
