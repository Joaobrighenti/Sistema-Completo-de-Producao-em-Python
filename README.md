# 🏭 Sistema de Gestão Industrial - PCP

## 📋 Sobre o Sistema

Sistema integrado de gestão industrial desenvolvido em Python usando o framework Dash, focado em **Planejamento e Controle da Produção (PCP)**, compras, qualidade e gestão de estoque para a indústria de embalagens.

### 🎯 Objetivo Principal
Automatizar e otimizar os processos industriais através de um sistema web completo que integra planejamento de produção, controle de qualidade, gestão de compras e análise de eficiência operacional.

---

## 🚀 Como Iniciar

### Pré-requisitos
- Python 3.8 ou superior
- Navegador web moderno

### Instalação
1. Clone o repositório ou baixe os arquivos
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

### Execução
```bash
python index.py
```

O sistema estará disponível em: `http://localhost:8052`

---

## 🔐 Primeiro Acesso

Na primeira execução do sistema, um usuário administrador será criado automaticamente:

- **Usuário:** `admin`
- **Senha:** `admin123`
- **Acesso:** TODOS os módulos habilitados (cadastros, PCP, OEE, compras, qualidade, dashboards, export)

⚠️ **IMPORTANTE:** Altere a senha padrão após o primeiro login por questões de segurança!

---

## 🏗️ Arquitetura do Sistema

### 📊 Tecnologias Utilizadas
- **Backend:** Python 3.x
- **Frontend:** Dash Framework + Bootstrap Components
- **Banco de Dados:** SQLite
- **Análise de Dados:** Pandas, NumPy
- **Visualização:** Plotly
- **Relatórios:** ReportLab (PDF), OpenPyXL (Excel)

### 🗂️ Estrutura de Módulos

```
📁 Sistema PCP NICOPEL
├── 📁 banco_dados/          # Gerenciamento de dados
├── 📁 pcp/                  # Planejamento e Controle de Produção
├── 📁 compras/              # Sistema de Compras
├── 📁 oee/                  # Eficiência Operacional
├── 📁 qualidade/            # Controle de Qualidade
├── 📁 dashboards/           # Relatórios e Dashboards
├── 📁 login/                # Autenticação e Usuários
├── 📁 cadastros/            # Cadastros Gerais
├── 📁 modulo_pizza/         # Módulo Especializado
└── 📁 assets/               # Recursos (imagens, CSS)
```

---

## 🔧 Módulos Principais

### 1. 📋 **PCP - Planejamento e Controle de Produção**
**Funcionalidades:**
- ✅ Cadastro de ordens de produção
- ✅ Planejamento semanal por setor
- ✅ Controle de baixas de produção
- ✅ Gestão de retiradas de material
- ✅ Controle de chapas e facas
- ✅ Sistema de lembretes
- ✅ Relatórios de planejamento

**Arquivos Principais:**
- `pcp/pag_principal.py` - Interface principal
- `pcp/planejamento.py` - Planejamento semanal
- `pcp/formularios/` - Formulários de cadastro
- `pcp/sidebar.py` - Menu de navegação

### 2. 🛒 **Sistema de Compras**
**Funcionalidades:**
- ✅ Gestão de fornecedores
- ✅ Ordens de compra
- ✅ Sistema de cotações
- ✅ Controle de carregamentos
- ✅ Relatórios de compras
- ✅ Gestão de categorias
- ✅ Estudos de estoque

**Arquivos Principais:**
- `compras/pages/page_principal_compras.py` - Interface principal
- `compras/formularios/` - Formulários de cadastro
- `compras/funcoes/` - Geração de PDFs

### 3. 📊 **OEE - Eficiência Operacional**
**Funcionalidades:**
- ✅ Controle de produção por máquina
- ✅ Apontamento de paradas
- ✅ Cálculo de OEE (Overall Equipment Effectiveness)
- ✅ Gestão de setores e máquinas
- ✅ Árvore de razões de parada
- ✅ Agendamento de produção

**Arquivos Principais:**
- `oee/pagina_oee.py` - Interface principal
- `oee/formularios/` - Formulários de apontamento
- `dashboards/dashboard_oee*.py` - Dashboards OEE

### 4. 🔍 **Sistema de Qualidade**
**Funcionalidades:**
- ✅ Controle de qualidade por lote
- ✅ Inspeção de processos
- ✅ Emissão de laudos técnicos
- ✅ Controle de retrabalho
- ✅ Checklist personalizado por produto
- ✅ Relatórios de qualidade

**Arquivos Principais:**
- `qualidade/page_qualidade.py` - Controle de lotes
- `qualidade/page_inpecao_processo.py` - Inspeção de processos
- `qualidade/page_laudos.py` - Emissão de laudos

### 5. 📈 **Dashboards e Relatórios**
**Funcionalidades:**
- ✅ Dashboard PCP Geral
- ✅ Dashboard OEE por Máquina/Setor
- ✅ Dashboard de Qualidade
- ✅ Demonstrativo de Resultados (DRE)
- ✅ Relatórios de Apontamento
- ✅ Dashboard de Produtos
- ✅ Agendamento Logístico

**Arquivos Principais:**
- `dashboards/dashboard_pcp.py` - Dashboard principal
- `dashboards/dashboard_oee*.py` - Dashboards OEE
- `dashboards/dashboard_dre.py` - Demonstrativo financeiro
- `dashboards/dash_relatorio.py` - Relatórios gerais

---

## 🎛️ Funcionalidades Avançadas

### 🔐 **Sistema de Controle de Acesso**
- **Tabela:** `users` (campo `user_level` em JSON)
- **Controle:** Por módulos (cadastros, PCP, OEE, compras, qualidade, dashboards, export)
- **Níveis:** Admin (acesso total), Usuário (acesso limitado)

### 📊 **Sistema de Relatórios**
- **Formatos:** PDF, Excel
- **Tipos:** Ordens de compra, cotações, laudos técnicos, relatórios de produção
- **Exportação:** Dados em tempo real para Excel

### 🔄 **Integração de Módulos**
- **PCP ↔ Compras:** Ordens de compra vinculadas ao PCP
- **PCP ↔ Qualidade:** Controle de qualidade por lote
- **OEE ↔ PCP:** Apontamentos de produção
- **Compras ↔ Qualidade:** Controle de fornecedores

---

## 📊 Principais Dashboards

### 1. **Dashboard PCP Geral**
- Aderência à programação
- Metas mensais por categoria
- Produção vs. Meta
- Indicadores de performance

### 2. **Dashboard OEE**
- Eficiência por máquina
- Análise de paradas
- Disponibilidade, Performance, Qualidade
- Comparativo entre setores

### 3. **Dashboard de Qualidade**
- Taxa de não conformidade
- Análise por produto/setor/máquina
- Controle de retrabalho
- Indicadores de qualidade

### 4. **Demonstrativo de Resultados (DRE)**
- Projeção financeira
- Fluxo de caixa
- Análise de custos
- Indicadores econômicos

---

## 🗄️ Banco de Dados

### **Tabelas Principais:**
- `pcp` - Ordens de produção
- `clientes` - Cadastro de clientes
- `produtos` - Catálogo de produtos
- `baixa` - Baixas de produção
- `retirada` - Retiradas de material
- `ordem_compra` - Ordens de compra
- `fornecedores` - Cadastro de fornecedores
- `producao` - Controle de produção
- `apontamento_produto` - Apontamentos de produção
- `apontamento` - Apontamentos de parada
- `inspecao_processo` - Inspeções de qualidade
- `users` - Usuários do sistema

### **Relacionamentos:**
- PCP → Cliente (1:N)
- PCP → Produto (1:N)
- PCP → Baixas (1:N)
- PCP → Retiradas (1:N)
- Ordem Compra → Fornecedor (N:1)
- Produção → Setor (N:1)
- Produção → Máquina (N:1)

---

## 🛠️ Configuração e Personalização

### **Metas de Produção**
Configuração em `dashboards/dashboard_pcp.py`:
```python
METAS_MENSAIS = {
    'CAIXA 10L': 400000,
    'CAIXA 5L': 200000,
    'POTE 500ML': 3500000,
    # ... outras categorias
}
```

### **Checklist de Qualidade**
Personalização em `qualidade/formularios/form_inspecao.py`:
```python
checklist_items_por_produto = {
    "Pote e Copo": {
        "pote_copo_dimensoes": "Dimensões (Diâmetro, comprimento e altura)",
        "pote_copo_selagem": "Selagem (Fundo e Lateral)",
        # ... outros itens
    }
}
```

---

## 📱 Interface do Usuário

### **Design Responsivo**
- Interface adaptável para desktop, tablet e mobile
- Sidebar colapsível
- Cards informativos
- Tabelas interativas

### **Navegação**
- Menu lateral organizado por módulos
- Breadcrumbs para navegação
- Filtros avançados
- Busca em tempo real

### **Temas**
- Bootstrap Components
- Font Awesome icons
- Cores personalizadas da empresa

---

## 🔧 Manutenção e Suporte

### **Logs do Sistema**
- Logs de operações no banco de dados
- Rastreamento de alterações
- Auditoria de usuários

### **Backup**
- Banco SQLite incluído
- Scripts de backup automático
- Exportação de dados

### **Atualizações**
- Sistema modular para fácil manutenção
- Migrações de banco automáticas
- Versionamento de funcionalidades

---

## 📈 Métricas e KPIs

### **Produção**
- Aderência à programação
- Eficiência de máquinas (OEE)
- Produtividade por setor
- Metas vs. Realizado

### **Qualidade**
- Taxa de não conformidade
- Tempo de retrabalho
- Aprovação de lotes
- Indicadores por produto

### **Compras**
- Tempo de entrega
- Custo por categoria
- Performance de fornecedores
- Análise de estoque

---

## 🚀 Roadmap Futuro

### **Funcionalidades Planejadas**
- [ ] Integração com ERP
- [ ] App mobile nativo
- [ ] IA para previsão de demanda
- [ ] Integração com sensores IoT
- [ ] Relatórios em tempo real
- [ ] Sistema de notificações push

### **Melhorias Técnicas**
- [ ] Migração para PostgreSQL
- [ ] API REST completa
- [ ] Microserviços
- [ ] Containerização Docker
- [ ] CI/CD automatizado

---

## 📞 Suporte e Contato

### **Documentação**
- README detalhado
- Comentários no código
- Exemplos de uso
- Guias de instalação

### **Troubleshooting**
- Logs detalhados
- Validação de dados
- Tratamento de erros
- Recuperação automática

---

## 📄 Licença

Sistema proprietário desenvolvido para NICOPEL.

---

## 🏆 Créditos

**Desenvolvido por:** Equipe de Desenvolvimento NICOPEL
**Tecnologias:** Python, Dash, SQLite, Bootstrap
**Versão:** 1.1.1.10

---

*Sistema de Gestão Industrial PCP NICOPEL - Transformando dados em decisões inteligentes* 🏭📊
