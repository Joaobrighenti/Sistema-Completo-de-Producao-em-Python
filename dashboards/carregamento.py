from dash import html, dcc, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime, date, timedelta
from banco_dados.banco import Banco
import json
import os
import base64
from pathlib import Path
from PIL import Image
import io

# Função para converter primeira página do PDF em imagem
def pdf_para_imagem(pdf_data):
    try:
        # Tentar usar pdf2image se disponível
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(pdf_data, first_page=1, last_page=1, dpi=150)
            if images:
                # Converter para base64
                img_buffer = io.BytesIO()
                images[0].save(img_buffer, format='PNG')
                img_buffer.seek(0)
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                return f"data:image/png;base64,{img_base64}"
        except ImportError:
            pass
        
        # Fallback: tentar com PyPDF2 e PIL
        try:
            import PyPDF2
            from PIL import Image, ImageDraw, ImageFont
            
            # Criar uma imagem em branco com texto indicativo
            img = Image.new('RGB', (400, 600), color='white')
            draw = ImageDraw.Draw(img)
            
            # Adicionar texto indicativo
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            text = "PDF Preview\n(Primeira página)"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (400 - text_width) // 2
            y = (600 - text_height) // 2
            
            draw.text((x, y), text, fill='black', font=font)
            
            # Converter para base64
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"
            
        except ImportError:
            pass
        
        return None
    except Exception as e:
        print(f"Erro ao converter PDF para imagem: {e}")
        return None

# Função para gerar número único do agendamento
def gerar_numero_agendamento():
    banco = Banco()
    try:
        with banco.engine.connect() as conn:
            # Buscar o maior número de agendamento
            query = "SELECT MAX(CAST(SUBSTR(agend_numero, 5) AS INTEGER)) as max_num FROM agendamento_logistica WHERE agend_numero LIKE 'AGD-%'"
            result = pd.read_sql(query, conn)
            
            if result.empty or pd.isna(result.iloc[0]['max_num']):
                return "AGD-000001"
            else:
                proximo_numero = int(result.iloc[0]['max_num']) + 1
                return f"AGD-{proximo_numero:06d}"
    except Exception as e:
        print(f"Erro ao gerar número do agendamento: {e}")
        # Fallback: usar timestamp se houver erro
        return f"AGD-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# Função para carregar dados dos agendamentos
def carregar_agendamentos():
    banco = Banco()
    try:
        with banco.engine.connect() as conn:
            query = """
            SELECT 
                agend_id,
                agend_numero,
                agend_tipo,
                agend_data_agendada,
                agend_data_inicio,
                agend_data_fim,
                agend_status,
                agend_prioridade,
                transp_nome,
                veic_placa,
                veic_modelo,
                veic_tipo,
                mot_nome,
                agend_local,
                agend_dock,
                agend_responsavel,
                agend_observacoes
            FROM agendamento_logistica 
            ORDER BY agend_data_agendada ASC
            """
            df = pd.read_sql(query, conn)
            
            # Se não há dados, criar dados de exemplo para demonstração
            if df.empty:
                hoje = datetime.now()
                # Criar alguns agendamentos de exemplo para a semana atual
                exemplos = []
                
                # Agendamento para hoje
                exemplos.append({
                    'agend_id': 9991,
                    'agend_numero': 'AGD-EX001',
                    'agend_tipo': 'CARREGAMENTO',
                    'agend_data_agendada': hoje.replace(hour=9, minute=0, second=0, microsecond=0),
                    'agend_data_inicio': None,
                    'agend_data_fim': None,
                    'agend_status': 'AGENDADO',
                    'agend_prioridade': 'MEDIA',
                    'transp_nome': 'Transportadora Exemplo Ltda',
                    'veic_placa': 'ABC-1234',
                    'veic_modelo': 'Mercedes-Benz',
                    'veic_tipo': '6TON_TRUCK',
                    'mot_nome': 'João Silva',
                    'agend_local': 'Portão 1',
                    'agend_dock': 'Doca 01',
                    'agend_responsavel': 'Sistema',
                    'agend_observacoes': 'Agendamento de exemplo'
                })
                
                # Agendamento para amanhã
                amanha = hoje + timedelta(days=1)
                exemplos.append({
                    'agend_id': 9992,
                    'agend_numero': 'AGD-EX002',
                    'agend_tipo': 'DESCARREGAMENTO',
                    'agend_data_agendada': amanha.replace(hour=14, minute=30, second=0, microsecond=0),
                    'agend_data_inicio': None,
                    'agend_data_fim': None,
                    'agend_status': 'AGENDADO',
                    'agend_prioridade': 'ALTA',
                    'transp_nome': 'Logística Rápida S.A.',
                    'veic_placa': 'XYZ-5678',
                    'veic_modelo': 'Volvo',
                    'veic_tipo': '12TON_TRUCK',
                    'mot_nome': 'Maria Santos',
                    'agend_local': 'Portão 2',
                    'agend_dock': 'Doca 02',
                    'agend_responsavel': 'Sistema',
                    'agend_observacoes': 'Descarregamento urgente'
                })
                
                df = pd.DataFrame(exemplos)
            
            return df
    except Exception as e:
        print(f"Erro ao carregar agendamentos: {e}")
        return pd.DataFrame()

# Função para salvar agendamento
def salvar_agendamento(dados):
    banco = Banco()
    try:
        # Preparar dados para inserção/atualização
        # Preparar dados de data
        def parse_datetime(dt_str):
            if dt_str and dt_str != '' and dt_str is not None:
                try:
                    return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
                except Exception as e:
                    print(f"Erro ao converter data '{dt_str}': {e}")
                    return None
            return None
        
        # Validar data agendada obrigatória
        data_agendada = parse_datetime(dados.get('data_agendada'))
        if not data_agendada:
            return False, "Data/Hora agendada é obrigatória e deve estar no formato correto (YYYY-MM-DDTHH:MM)"
        
        dados_agendamento = {
            'agend_numero': dados.get('numero'),
            'agend_tipo': dados.get('tipo'),
            'agend_data_agendada': data_agendada,
            'agend_status': dados.get('status', 'AGENDADO'),
            'agend_prioridade': dados.get('prioridade'),
            'agend_data_inicio': parse_datetime(dados.get('data_inicio')),
            'agend_data_fim': parse_datetime(dados.get('data_fim')),
            'transp_nome': dados.get('transp_nome'),
            'transp_cnpj': dados.get('transp_cnpj'),
            'transp_telefone': dados.get('transp_telefone'),
            'transp_email': dados.get('transp_email'),
            'veic_placa': dados.get('veic_placa'),
            'veic_modelo': dados.get('veic_modelo'),
            'veic_tipo': dados.get('veic_tipo'),
            'veic_capacidade_peso': dados.get('veic_capacidade_peso'),
            'veic_capacidade_volume': dados.get('veic_capacidade_volume'),
            'mot_nome': dados.get('mot_nome'),
            'mot_cpf': dados.get('mot_cpf'),
            'mot_cnh': dados.get('mot_cnh'),
            'mot_telefone': dados.get('mot_telefone'),
            'agend_local': dados.get('agend_local'),
            'agend_dock': dados.get('agend_dock'),
            'agend_responsavel': dados.get('agend_responsavel'),
            'agend_observacoes': dados.get('agend_observacoes'),
            'agend_itens': dados.get('itens', {}),
            'agend_documentos': dados.get('documentos', {})
        }
        
        # Inserir no banco usando SQLAlchemy ORM para obter o ID
        from sqlalchemy.orm import sessionmaker
        from banco_dados.banco import AGENDAMENTO_LOGISTICA, AGENDAMENTO_HISTORICO
        
        SessionFactory = sessionmaker(bind=banco.engine)
        session = SessionFactory()
        
        try:
            # Verificar se é edição (tem agend_id) ou criação nova
            agend_id = dados.get('agend_id')
            
            if agend_id:
                # É uma edição - atualizar registro existente
                agendamento_existente = session.query(AGENDAMENTO_LOGISTICA).filter_by(agend_id=agend_id).first()
                if agendamento_existente:
                    # Atualizar campos
                    for campo, valor in dados_agendamento.items():
                        setattr(agendamento_existente, campo, valor)
                    
                    # Criar registro no histórico
                    novo_historico = AGENDAMENTO_HISTORICO(
                        hist_agend_id=agend_id,
                        hist_acao="EDITADO",
                        hist_status_anterior="AGENDADO",
                        hist_status_novo="AGENDADO",
                        hist_usuario=dados.get('agend_responsavel', 'Sistema'),
                        hist_observacoes="Agendamento editado"
                    )
                    session.add(novo_historico)
                    
                    session.commit()
                    return True, "Agendamento atualizado com sucesso!"
                else:
                    return False, "Agendamento não encontrado para edição!"
            else:
                # É uma criação nova
                novo_agendamento = AGENDAMENTO_LOGISTICA(**dados_agendamento)
                session.add(novo_agendamento)
                session.flush()  # Para obter o ID sem fazer commit
                
                agend_id = novo_agendamento.agend_id
                
                # Criar registro no histórico
                novo_historico = AGENDAMENTO_HISTORICO(
                    hist_agend_id=agend_id,
                    hist_acao="CRIADO",
                    hist_status_novo="AGENDADO",
                    hist_usuario=dados.get('agend_responsavel', 'Sistema'),
                    hist_observacoes="Agendamento criado"
                )
                session.add(novo_historico)
                
                # Fazer commit de tudo
                session.commit()
                return True, "Agendamento salvo com sucesso!"
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
        
    except Exception as e:
        print(f"Erro ao salvar agendamento: {e}")
        return False, f"Erro ao salvar: {str(e)}"

# Função para criar a visualização da agenda
def criar_agenda_semanal(df_agendamentos):
    if df_agendamentos.empty:
        return dbc.Alert("Nenhum agendamento encontrado.", color="info")
    
    # Converter data para datetime
    df_agendamentos['agend_data_agendada'] = pd.to_datetime(df_agendamentos['agend_data_agendada'])
    
    # Obter a semana atual (Domingo)
    hoje = datetime.now()
    inicio_semana = hoje - timedelta(days=hoje.weekday() + 1)  # Domingo
    
    # Filtrar agendamentos da semana atual (Domingo a Sábado)
    df_semana = df_agendamentos[
        (df_agendamentos['agend_data_agendada'].dt.date >= inicio_semana.date()) &
        (df_agendamentos['agend_data_agendada'].dt.date < (inicio_semana + timedelta(days=7)).date())
    ].copy()
    
    # Se não há agendamentos na semana atual, verificar se há na próxima semana
    if df_semana.empty:
        proxima_semana = inicio_semana + timedelta(days=7)
        df_semana = df_agendamentos[
            (df_agendamentos['agend_data_agendada'].dt.date >= proxima_semana.date()) &
            (df_agendamentos['agend_data_agendada'].dt.date < (proxima_semana + timedelta(days=7)).date())
        ].copy()
        
        # Se encontrou agendamentos na próxima semana, ajustar o início da semana
        if not df_semana.empty:
            inicio_semana = proxima_semana
    
    # Criar estrutura da agenda
    dias_semana = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']
    
    # Header da agenda
    header = html.Div([
        html.Div([
            html.Span("Hoje", className="fw-bold me-3"),
            dbc.Button("‹", size="sm", color="light", className="me-2"),
            dbc.Button("›", size="sm", color="light", className="me-2"),
            html.Span(f"{inicio_semana.strftime('%B de %Y')}", className="fw-bold"),
            html.Span("▼", className="ms-2 text-muted")
        ], className="d-flex align-items-center"),
        html.Div([
            html.Span("Você está em dia!", className="text-success me-3"),
            html.Span("🔔", className="me-2"),
            html.Span("Semana de Trabalho ▼", className="text-muted")
        ], className="d-flex align-items-center justify-content-end")
    ], className="d-flex justify-content-between align-items-center mb-4 p-3", 
       style={"backgroundColor": "#f8f9fa", "borderRadius": "8px"})
    
    # Criar faixas horárias (de 2 em 2 horas)
    faixas_horarias = []
    for hora in range(0, 24, 2):
        hora_fim = hora + 2
        faixas_horarias.append({
            'inicio': f"{hora:02d}:00",
            'fim': f"{hora_fim:02d}:00",
            'label': f"{hora:02d}:00 - {hora_fim:02d}:00"
        })
    
    # Cabeçalho da agenda com dias da semana
    cabecalho_agenda = html.Div([
        # Coluna de horas
        html.Div("Horário", className="col-2 text-center fw-bold p-2 border-bottom", 
                style={"backgroundColor": "#f8f9fa"}),
        # Dias da semana
        html.Div([
            html.Div([
                html.Div(f"{dias_semana[i]}", className="fw-bold text-center mb-1", 
                        style={"fontSize": "12px", "color": "#6c757d"}),
                html.Div(f"{(inicio_semana + timedelta(days=i)).day:02d}", 
                        className="text-center h6 mb-0 fw-bold", 
                        style={"color": "#495057"})
            ], className="col text-center p-2 border-end border-bottom", style={"backgroundColor": "#f8f9fa"})
            for i in range(7)
        ], className="col-10 row")
    ], className="row border-bottom mb-0")
    
    # Container da agenda
    agenda_container = html.Div([
        header,
        cabecalho_agenda,
        
        # Linhas de horários
        html.Div([
            # Linha de horário
            html.Div([
                # Coluna de horário
                html.Div(faixa['label'], className="col-2 text-center p-2 border-bottom", 
                        style={"backgroundColor": "#f8f9fa", "fontSize": "12px"}),
                # Colunas dos dias
                html.Div([
                    # Domingo
                    html.Div([], className="col text-center p-2 border-end border-bottom", style={"minHeight": "80px", "backgroundColor": "#ffffff"}),
                    # Segunda-feira
                    html.Div([], className="col text-center p-2 border-end border-bottom", style={"minHeight": "80px", "backgroundColor": "#ffffff"}),
                    # Terça-feira
                    html.Div([], className="col text-center p-2 border-end border-bottom", style={"minHeight": "80px", "backgroundColor": "#ffffff"}),
                    # Quarta-feira
                    html.Div([], className="col text-center p-2 border-end border-bottom", style={"minHeight": "80px", "backgroundColor": "#ffffff"}),
                    # Quinta-feira
                    html.Div([], className="col text-center p-2 border-end border-bottom", style={"minHeight": "80px", "backgroundColor": "#ffffff"}),
                    # Sexta-feira
                    html.Div([], className="col text-center p-2 border-end border-bottom", style={"minHeight": "80px", "backgroundColor": "#ffffff"}),
                    # Sábado
                    html.Div([], className="col text-center p-2 border-bottom", style={"minHeight": "80px", "backgroundColor": "#ffffff"})
                ], className="col-10 row")
            ], className="row border-bottom", id=f"linha-horario-{faixa['inicio']}")
            for faixa in faixas_horarias
        ], className="border")
    ])
    
    # Adicionar eventos aos dias e horários
    for _, evento in df_semana.iterrows():
        data_evento = evento['agend_data_agendada'].date()
        hora_evento = evento['agend_data_agendada'].hour
        
        # Calcular dia da semana (0=domingo, 1=segunda, etc.)
        dia_index = (data_evento - inicio_semana.date()).days
        
        # Calcular faixa horária
        faixa_index = hora_evento // 2
        
        if 0 <= dia_index < 7 and 0 <= faixa_index < 12:  # Domingo a Sábado, 0h a 22h
            # Encontrar a linha de horário correspondente
            linha_horario = agenda_container.children[2].children[faixa_index]
            coluna_dia = linha_horario.children[1].children[dia_index]
            
            # Definir cores baseadas no tipo (carregamento/descarregamento)
            if evento['agend_tipo'] == 'CARREGAMENTO':
                cor_tipo = '#e3f2fd'  # Azul claro
                cor_borda_tipo = '#2196f3'  # Azul
            else:  # DESCARREGAMENTO
                cor_tipo = '#e8f5e8'  # Verde claro
                cor_borda_tipo = '#4caf50'  # Verde
            
            # Definir cores baseadas no status
            cor_fundo = {
                'AGENDADO': cor_tipo,
                'EM_ANDAMENTO': '#fff3e0', 
                'CONCLUIDO': '#e8f5e8',
                'CANCELADO': '#ffebee',
                'ATRASADO': '#fce4ec'
            }.get(evento['agend_status'], '#f8f9fa')
            
            # Status badge
            status_colors = {
                'AGENDADO': 'primary',
                'EM_ANDAMENTO': 'warning',
                'CONCLUIDO': 'success',
                'CANCELADO': 'danger',
                'ATRASADO': 'danger'
            }
            status_text = {
                'AGENDADO': 'Agendado',
                'EM_ANDAMENTO': 'Em Andamento',
                'CONCLUIDO': 'Concluído',
                'CANCELADO': 'Cancelado',
                'ATRASADO': 'Atrasado'
            }
            
            evento_html = html.Div([
                html.Div([
                    html.Div([
                        html.Strong(f"{evento['agend_tipo']}", 
                                   style={"fontSize": "11px", "color": cor_borda_tipo}),
                        html.Span(f" - {evento['agend_numero']}", className="text-muted", 
                                 style={"fontSize": "10px"}),
                        html.Span([
                            dbc.Badge(status_text.get(evento['agend_status'], evento['agend_status']), 
                                     color=status_colors.get(evento['agend_status'], 'secondary'), 
                                     className="ms-1", style={"fontSize": "9px"})
                        ])
                    ]),
                    dbc.Button(
                        "🗑️", 
                        id={"type": "btn-excluir-agendamento", "index": f"excluir-{evento['agend_id']}"},
                        size="sm",
                        color="outline-danger",
                        className="ms-auto",
                        style={"fontSize": "10px", "padding": "2px 6px", "border": "none", "backgroundColor": "transparent"}
                    )
                ], className="d-flex justify-content-between align-items-center mb-1"),
                html.Div([
                    html.I(className="fa fa-truck me-1", style={"fontSize": "10px"}),
                    html.Span(evento['transp_nome'], style={"fontSize": "10px"})
                ], className="mb-1"),
                html.Div([
                    html.I(className="fa fa-car me-1", style={"fontSize": "10px"}),
                    html.Span(f"{evento['veic_modelo'] or 'N/A'} - {evento['veic_tipo'] or 'N/A'}", 
                             style={"fontSize": "10px"})
                ], className="mb-1"),
                html.Div([
                    html.I(className="fa fa-map-marker me-1", style={"fontSize": "10px"}),
                    html.Span(f"Doca: {evento['agend_dock'] or 'N/A'}", style={"fontSize": "10px"})
                ], className="mb-1"),
                html.Div([
                    html.I(className="fa fa-clock me-1", style={"fontSize": "10px"}),
                    html.Span(evento['agend_data_agendada'].strftime('%H:%M'), style={"fontSize": "10px"})
                ], className="mb-1"),
                # Observações (se houver)
                html.Div([
                    html.I(className="fa fa-comment me-1", style={"fontSize": "9px"}),
                    html.Span(evento['agend_observacoes'][:25] + "..." if evento['agend_observacoes'] and len(evento['agend_observacoes']) > 25 else (evento['agend_observacoes'] or ''), 
                             style={"fontSize": "9px", "fontStyle": "italic", "color": "#6c757d"})
                ]) if evento['agend_observacoes'] else html.Div()
            ], 
            className="border rounded p-2", 
            id={"type": "evento-agendamento", "index": f"evento-{evento['agend_id']}"},
            n_clicks=0,
            style={
                "backgroundColor": cor_fundo, 
                "borderLeft": f"4px solid {cor_borda_tipo}", 
                "fontSize": "10px",
                "cursor": "pointer",
                "minHeight": "120px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
            })
            
            coluna_dia.children.append(evento_html)
    
    return agenda_container

# Layout principal
layout = dbc.Container([
    
    
    # Página principal - Agenda
    dbc.Card([
        dbc.CardBody([
            # Botão Novo Agendamento
            dbc.Row([
                dbc.Col([
                    dbc.Button("➕ Novo Agendamento", id="btn-novo-agendamento", 
                             color="success", size="lg", className="mb-3")
                ], className="text-end")
            ]),
            
            # Área para mensagens de alerta
            html.Div(id="alert-mensagem", className="mb-3"),
            
            # Filtros da agenda
            html.H5("🔍 Filtros", className="mb-3 text-muted"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Status", style={"fontSize": "12px"}),
                    dcc.Dropdown(
                        id="filtro-status-agenda",
                        options=[
                            {"label": "Todos", "value": "TODOS"},
                            {"label": "Agendado", "value": "AGENDADO"},
                            {"label": "Em Andamento", "value": "EM_ANDAMENTO"},
                            {"label": "Concluído", "value": "CONCLUIDO"},
                            {"label": "Cancelado", "value": "CANCELADO"},
                            {"label": "Atrasado", "value": "ATRASADO"}
                        ],
                        value="TODOS",
                        style={"fontSize": "12px"}
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Tipo", style={"fontSize": "12px"}),
                    dcc.Dropdown(
                        id="filtro-tipo-agenda",
                        options=[
                            {"label": "Todos", "value": "TODOS"},
                            {"label": "Carregamento", "value": "CARREGAMENTO"},
                            {"label": "Descarregamento", "value": "DESCARREGAMENTO"}
                        ],
                        value="TODOS",
                        style={"fontSize": "12px"}
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Transportadora", style={"fontSize": "12px"}),
                    dcc.Dropdown(
                        id="filtro-transportadora",
                        options=[{"label": "Todas", "value": "TODAS"}],
                        value="TODAS",
                        style={"fontSize": "12px"}
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Modelo", style={"fontSize": "12px"}),
                    dcc.Dropdown(
                        id="filtro-modelo",
                        options=[{"label": "Todos", "value": "TODOS"}],
                        value="TODOS",
                        style={"fontSize": "12px"}
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Tipo Veículo", style={"fontSize": "12px"}),
                    dcc.Dropdown(
                        id="filtro-tipo-veiculo",
                        options=[{"label": "Todos", "value": "TODOS"}],
                        value="TODOS",
                        style={"fontSize": "12px"}
                    )
                ], md=2),
                dbc.Col([
                    dbc.Label("Doca", style={"fontSize": "12px"}),
                    dcc.Dropdown(
                        id="filtro-doca",
                        options=[{"label": "Todas", "value": "TODAS"}],
                        value="TODAS",
                        style={"fontSize": "12px"}
                    )
                ], md=2)
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Label("Semana", style={"fontSize": "12px"}),
                    dbc.Input(id="filtro-semana", type="week", style={"fontSize": "12px"})
                ], md=3),
                dbc.Col([
                    dbc.Label("Atualizar", style={"fontSize": "12px"}),
                    dbc.Button("🔄 Atualizar", id="btn-atualizar-agenda", 
                             color="primary", size="sm", className="w-100")
                ], md=3),
                dbc.Col([
                    dbc.Label("Limpar", style={"fontSize": "12px"}),
                    dbc.Button("🗑️ Limpar Filtros", id="btn-limpar-filtros", 
                             color="outline-secondary", size="sm", className="w-100")
                ], md=3),
                dbc.Col([], md=3)
            ], className="mb-4"),
            
            # Agenda semanal
            html.Div(id="agenda-semanal", children=criar_agenda_semanal(carregar_agendamentos()))
        ])
    ]),
    
    # Modal para formulário de agendamento
    dbc.Modal([
        dbc.ModalHeader("Novo Agendamento", id="modal-agendamento-header"),
        dbc.ModalBody([
            # Layout em duas colunas
            dbc.Row([
                # Coluna da esquerda - Formulário
                dbc.Col([
            # Informações básicas
            html.Div([
                html.H6("📋 Informações Básicas", className="mb-3 text-primary"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Número do Agendamento"),
                        dbc.Input(id="agend-numero", value="", 
                                 disabled=True, style={"backgroundColor": "#f8f9fa"})
                    ], md=3),
                    dbc.Col([
                        dbc.Label("Tipo *"),
                        dcc.Dropdown(
                            id="agend-tipo",
                            options=[
                                {"label": "Carregamento", "value": "CARREGAMENTO"},
                                {"label": "Descarregamento", "value": "DESCARREGAMENTO"}
                            ],
                            placeholder="Selecione o tipo"
                        )
                    ], md=3),
                    dbc.Col([
                        dbc.Label("Data/Hora Agendada *"),
                        dbc.Input(id="agend-data", type="datetime-local", required=True)
                    ], md=3),
                    dbc.Col([
                        dbc.Label("Prioridade"),
                        dcc.Dropdown(
                            id="agend-prioridade",
                            options=[
                                {"label": "Baixa", "value": "BAIXA"},
                                {"label": "Média", "value": "MEDIA"},
                                {"label": "Alta", "value": "ALTA"},
                                {"label": "Urgente", "value": "URGENTE"}
                            ],
                            value="MEDIA"
                        )
                    ], md=3)
                ], className="mb-3")
            ], className="mb-4 p-3 border rounded", style={"backgroundColor": "#f8f9fa"}),
            
            # Status do Agendamento
            html.Div([
                html.H6("📊 Status do Agendamento", className="mb-3 text-success"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Status Atual"),
                        dcc.Dropdown(
                            id="agend-status",
                            options=[
                                {"label": "Agendado", "value": "AGENDADO"},
                                {"label": "Em Andamento", "value": "EM_ANDAMENTO"},
                                {"label": "Concluído", "value": "CONCLUIDO"},
                                {"label": "Cancelado", "value": "CANCELADO"},
                                {"label": "Atrasado", "value": "ATRASADO"}
                            ],
                            placeholder="Status do agendamento"
                        )
                    ], md=3),
                    dbc.Col([
                        dbc.Label("Data/Hora Início"),
                        dbc.Input(id="agend-data-inicio", type="datetime-local")
                    ], md=3),
                    dbc.Col([
                        dbc.Label("Data/Hora Fim"),
                        dbc.Input(id="agend-data-fim", type="datetime-local")
                    ], md=3),
                    dbc.Col([
                        dbc.Label("Ações Rápidas"),
                        html.Div([
                            dbc.Button("🔄 Iniciar", id="btn-iniciar", color="success", size="sm", className="me-1 mb-1"),
                            dbc.Button("✅ Concluir", id="btn-concluir", color="primary", size="sm", className="me-1 mb-1"),
                            dbc.Button("❌ Cancelar", id="btn-cancelar", color="danger", size="sm", className="mb-1")
                        ])
                    ], md=3)
                ], className="mb-3")
            ], className="mb-4 p-3 border rounded", style={"backgroundColor": "#e8f5e8"}),
            
            # Informações da transportadora
            html.Div([
                html.H6("🚛 Transportadora", className="mb-3 text-info"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nome da Transportadora *"),
                        dbc.Input(id="transp-nome", placeholder="Nome da transportadora", required=True)
                    ], md=4),
                    dbc.Col([
                        dbc.Label("CNPJ"),
                        dbc.Input(id="transp-cnpj", placeholder="00.000.000/0000-00")
                    ], md=4),
                    dbc.Col([
                        dbc.Label("Telefone"),
                        dbc.Input(id="transp-telefone", placeholder="(00) 00000-0000")
                    ], md=4)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Email"),
                        dbc.Input(id="transp-email", placeholder="email@transportadora.com", type="email")
                    ], md=6)
                ])
            ], className="mb-4 p-3 border rounded", style={"backgroundColor": "#f0f8ff"}),
            
            # Informações do veículo
            html.Div([
                html.H6("🚚 Veículo", className="mb-3 text-warning"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Placa *"),
                        dbc.Input(id="veic-placa", placeholder="ABC-1234", required=True)
                    ], md=3),
                    dbc.Col([
                        dbc.Label("Modelo"),
                        dbc.Input(id="veic-modelo", placeholder="Ex: Mercedes-Benz")
                    ], md=3),
                    dbc.Col([
                        dbc.Label("Tipo"),
                        dcc.Dropdown(
                            id="veic-tipo",
                            options=[
                                {"label": "Saveiro 500kg", "value": "TOCO_SAVEIRO_500KG"},
                                {"label": "Van 1 Ton", "value": "VAN_1TON"},
                                {"label": "6 Ton Toco", "value": "6TON_TRUCK"},
                                {"label": "12 Ton Truck", "value": "12TON_TRUCK"},
                                {"label": "18 Ton", "value": "15TON_TRUCK"},
                                {"label": "23 Ton", "value": "23TON_TRUCK"},
                                {"label": "26 Ton", "value": "26TON_TRUCK"},
                                {"label": "33 Ton", "value": "33TON_TRUCK"},
                            ],
                            placeholder="Tipo do veículo"
                        )
                    ], md=3),
                    dbc.Col([
                        dbc.Label("Peso Estimado"),
                        dbc.Input(id="veic-capacidade-peso", type="number", step="0.1", placeholder="0.0")
                    ], md=3)
                ])
            ], className="mb-4 p-3 border rounded", style={"backgroundColor": "#fff8dc"}),
            
            # Informações do motorista
            html.Div([
                html.H6("👨‍💼 Motorista", className="mb-3 text-secondary"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nome *"),
                        dbc.Input(id="mot-nome", placeholder="Nome do motorista", required=True)
                    ], md=4),
                    dbc.Col([
                        dbc.Label("CPF"),
                        dbc.Input(id="mot-cpf", placeholder="000.000.000-00")
                    ], md=4),
                    dbc.Col([
                        dbc.Label("CNH"),
                        dbc.Input(id="mot-cnh", placeholder="Número da CNH")
                    ], md=4)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Telefone"),
                        dbc.Input(id="mot-telefone", placeholder="(00) 00000-0000")
                    ], md=6)
                ])
            ], className="mb-4 p-3 border rounded", style={"backgroundColor": "#f5f5f5"}),
            
            # Localização e observações
            html.Div([
                html.H6("📍 Localização e Observações", className="mb-3 text-dark"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Local"),
                        dbc.Input(id="agend-local", placeholder="Ex: Portão 1, Doca A")
                    ], md=4),
                    dbc.Col([
                        dbc.Label("Doca"),
                        dbc.Input(id="agend-dock", placeholder="Ex: Doca 01")
                    ], md=4),
                    dbc.Col([
                        dbc.Label("Responsável"),
                        dbc.Input(id="agend-responsavel", placeholder="Nome do responsável")
                    ], md=4)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Observações"),
                        dbc.Textarea(id="agend-observacoes", placeholder="Observações adicionais...", rows=3)
                    ])
                ])
            ], className="mb-3 p-3 border rounded", style={"backgroundColor": "#fafafa"}),
                    
                ], md=8),  # Fechar coluna da esquerda
                
                # Coluna da direita - Documentos (Clean)
                dbc.Col([
                    html.H6("📎 Documentos", className="mb-3 text-muted", style={"fontSize": "14px"}),
                    
                    # PDF dos Itens
                    html.Div([
                        html.Div([
                            html.Span("PDF Itens", className="fw-bold", style={"fontSize": "12px"}),
                            dbc.Button("Baixar", id="btn-download-pdf-itens", size="sm", 
                                     color="outline-secondary", className="ms-auto", disabled=True,
                                     style={"fontSize": "11px"})
                        ], className="d-flex justify-content-between align-items-center mb-1"),
                        html.Div(id="pdf-viewer-itens", 
                                style={"minHeight": "80px", "fontSize": "11px", "color": "#6c757d"})
                    ], className="mb-3 p-2 border rounded", style={"backgroundColor": "#fafafa"}),
                    
                    # Upload PDF Itens
                    dcc.Upload(
                        id='upload-pdf-itens',
                        children=html.Div([
                            html.I(className="fa fa-plus text-muted", style={"fontSize": "14px"}),
                            html.Span(" PDF Itens", style={"fontSize": "12px", "marginLeft": "5px"})
                        ]),
                        style={
                            'width': '100%',
                            'height': '40px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '4px',
                            'textAlign': 'center',
                            'backgroundColor': '#f8f9fa',
                            'borderColor': '#dee2e6',
                            'display': 'flex',
                            'justifyContent': 'center',
                            'alignItems': 'center',
                            'cursor': 'pointer',
                            'marginBottom': '15px'
                        },
                        multiple=False,
                        accept='.pdf'
                    ),
                    
                    # Nota Fiscal
                    html.Div([
                        html.Div([
                            html.Span("Nota Fiscal", className="fw-bold", style={"fontSize": "12px"}),
                            dbc.Button("Baixar", id="btn-download-nota", size="sm", 
                                     color="outline-secondary", className="ms-auto", disabled=True,
                                     style={"fontSize": "11px"})
                        ], className="d-flex justify-content-between align-items-center mb-1"),
                        html.Div(id="pdf-viewer-nota", 
                                style={"minHeight": "80px", "fontSize": "11px", "color": "#6c757d"})
                    ], className="mb-3 p-2 border rounded", style={"backgroundColor": "#fafafa"}),
                    
                    # Upload Nota Fiscal
                    dcc.Upload(
                        id='upload-nota-fiscal',
                        children=html.Div([
                            html.I(className="fa fa-plus text-muted", style={"fontSize": "14px"}),
                            html.Span(" Nota Fiscal", style={"fontSize": "12px", "marginLeft": "5px"})
                        ]),
                        style={
                            'width': '100%',
                            'height': '40px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '4px',
                            'textAlign': 'center',
                            'backgroundColor': '#f8f9fa',
                            'borderColor': '#dee2e6',
                            'display': 'flex',
                            'justifyContent': 'center',
                            'alignItems': 'center',
                            'cursor': 'pointer'
                        },
                        multiple=False,
                        accept='.pdf,.jpg,.jpeg,.png'
                    ),
                    
                    html.Div(id="upload-status-pdf-itens", className="mt-1"),
                    html.Div(id="upload-status-nota-fiscal", className="mt-1")
                    
                ], md=4)  # Fechar coluna da direita
            ])  # Fechar Row das colunas
        ]),  # Fechar ModalBody
        dbc.ModalFooter([
            dbc.Button("Salvar Agendamento", id="btn-salvar-agendamento", 
                     color="success", className="me-2"),
            dbc.Button("Limpar Formulário", id="btn-limpar-formulario", 
                     color="secondary", className="me-2"),
            dbc.Button("Fechar", id="btn-fechar-modal", color="danger")
        ])
    ], id="modal-agendamento", is_open=False, size="xl", backdrop="static", keyboard=False),
    
    # Modal para confirmar salvamento
    dbc.Modal([
        dbc.ModalHeader("Confirmar Salvamento"),
        dbc.ModalBody("Deseja realmente salvar este agendamento?"),
        dbc.ModalFooter([
            dbc.Button("Sim, Salvar", id="btn-confirmar-salvar", color="success", className="me-2"),
            dbc.Button("Cancelar", id="btn-cancelar-salvar", color="secondary")
        ])
    ], id="modal-confirmar-salvar", is_open=False),
    
    # Alertas
    html.Div(id="alert-mensagem"),
    
    # Store para dados temporários
    dcc.Store(id="store-dados-temporarios"),
    dcc.Store(id="store-agendamento-edicao"),
    dcc.Store(id="store-pdf-itens"),
    dcc.Store(id="store-nota-fiscal"),
    dcc.Store(id="store-pdf-itens-path"),
    dcc.Store(id="store-nota-fiscal-path"),
    
    # Componentes de download
    dcc.Download(id="download-pdf-itens"),
    dcc.Download(id="download-nota-fiscal")
], fluid=True)

# Callbacks
from app import app
import dash


# Callback para abrir modal de novo agendamento
@app.callback(
    [Output("modal-agendamento", "is_open"),
     Output("agend-numero", "value"),
     Output("modal-agendamento-header", "children"),
     Output("store-agendamento-edicao", "data")],
    [Input("btn-novo-agendamento", "n_clicks"),
     Input("btn-fechar-modal", "n_clicks")],
    prevent_initial_call=True
)
def controlar_modal_agendamento(n_clicks_novo, n_clicks_fechar):
    ctx = callback_context
    if not ctx.triggered:
        return False, dash.no_update, dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "btn-novo-agendamento":
        # Gerar novo número quando abrir modal
        novo_numero = gerar_numero_agendamento()
        return True, novo_numero, "Novo Agendamento", {}
    elif trigger_id == "btn-fechar-modal":
        return False, dash.no_update, dash.no_update, dash.no_update
    
    return False, dash.no_update, dash.no_update, dash.no_update

# Callback para validar campos obrigatórios
@app.callback(
    Output("alert-mensagem", "children", allow_duplicate=True),
    Input("btn-salvar-agendamento", "n_clicks"),
    [State("agend-tipo", "value"),
     State("agend-data", "value"),
     State("transp-nome", "value"),
     State("veic-placa", "value"),
     State("mot-nome", "value")],
    prevent_initial_call=True
)
def validar_campos_obrigatorios(n_clicks, tipo, data, transp_nome, veic_placa, mot_nome):
    if not n_clicks:
        return ""
    
    campos_obrigatorios = {
        "Tipo": tipo,
        "Data/Hora": data,
        "Nome da Transportadora": transp_nome,
        "Placa do Veículo": veic_placa,
        "Nome do Motorista": mot_nome
    }
    
    campos_faltando = [campo for campo, valor in campos_obrigatorios.items() if not valor]
    
    if campos_faltando:
        return dbc.Alert(
            f"Campos obrigatórios não preenchidos: {', '.join(campos_faltando)}",
            color="danger",
            dismissable=True
        )
    
    return ""

@app.callback(
    Output("modal-confirmar-salvar", "is_open"),
    [Input("btn-salvar-agendamento", "n_clicks"),
     Input("btn-confirmar-salvar", "n_clicks"),
     Input("btn-cancelar-salvar", "n_clicks")],
    prevent_initial_call=True
)
def controlar_modal_confirmacao(n_clicks_salvar, n_clicks_confirmar, n_clicks_cancelar):
    ctx = callback_context
    if not ctx.triggered:
        return False
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "btn-salvar-agendamento":
        return True
    elif trigger_id in ["btn-confirmar-salvar", "btn-cancelar-salvar"]:
        return False
    
    return False

@app.callback(
    [Output("alert-mensagem", "children", allow_duplicate=True),
     Output("modal-agendamento", "is_open", allow_duplicate=True),
     Output("agenda-semanal", "children", allow_duplicate=True)],
    Input("btn-confirmar-salvar", "n_clicks"),
    [State("agend-numero", "value"),
     State("agend-tipo", "value"),
     State("agend-data", "value"),
     State("agend-prioridade", "value"),
     State("agend-status", "value"),
     State("agend-data-inicio", "value"),
     State("agend-data-fim", "value"),
     State("transp-nome", "value"),
     State("transp-cnpj", "value"),
     State("transp-telefone", "value"),
     State("transp-email", "value"),
     State("veic-placa", "value"),
     State("veic-modelo", "value"),
     State("veic-tipo", "value"),
     State("veic-capacidade-peso", "value"),
     State("mot-nome", "value"),
     State("mot-cpf", "value"),
     State("mot-cnh", "value"),
     State("mot-telefone", "value"),
     State("agend-local", "value"),
     State("agend-dock", "value"),
     State("agend-responsavel", "value"),
     State("agend-observacoes", "value"),
     State("store-pdf-itens", "data"),
     State("store-nota-fiscal", "data"),
     State("store-agendamento-edicao", "data")],
    prevent_initial_call=True
)
def salvar_agendamento_callback(n_clicks, numero, tipo, data, prioridade, status, data_inicio, data_fim,
                               transp_nome, transp_cnpj, transp_telefone, transp_email, veic_placa, 
                               veic_modelo, veic_tipo, veic_capacidade_peso, mot_nome, mot_cpf, mot_cnh, 
                               mot_telefone, agend_local, agend_dock, agend_responsavel, agend_observacoes, 
                               pdf_itens_path, nota_fiscal_path, dados_edicao):
    ctx = callback_context
    if not ctx.triggered:
        return "", False, dash.no_update
    
    # Verificar se o botão de salvar foi realmente clicado
    triggered_id = ctx.triggered[0]["prop_id"].split('.')[0]
    if triggered_id != "btn-confirmar-salvar":
        return "", False, dash.no_update
    
    if not n_clicks:
        return "", False, dash.no_update
    
    # Validar campos obrigatórios
    if not data:
        return dbc.Alert("Data/Hora agendada é obrigatória!", color="danger", dismissable=True), dash.no_update, dash.no_update
    
    if not tipo:
        return dbc.Alert("Tipo do agendamento é obrigatório!", color="danger", dismissable=True), dash.no_update, dash.no_update
    
    if not transp_nome:
        return dbc.Alert("Nome da transportadora é obrigatório!", color="danger", dismissable=True), dash.no_update, dash.no_update
    
    if not veic_placa:
        return dbc.Alert("Placa do veículo é obrigatória!", color="danger", dismissable=True), dash.no_update, dash.no_update
    
    if not mot_nome:
        return dbc.Alert("Nome do motorista é obrigatório!", color="danger", dismissable=True), dash.no_update, dash.no_update
    
    # Verificar se é edição ou criação nova
    agend_id = dados_edicao.get('agend_id') if dados_edicao else None
    
    # Preparar documentos
    documentos = {}
    if pdf_itens_path:
        documentos['pdf_itens'] = pdf_itens_path
    if nota_fiscal_path:
        documentos['nota_fiscal'] = nota_fiscal_path
    
    # Para criação nova, verificar se o número já existe e gerar um novo se necessário
    if not agend_id and (numero == "AGD-000001" or numero is None or numero == ""):
        numero = gerar_numero_agendamento()
    
    dados = {
        'agend_id': agend_id,  # Passar o ID para a função de salvamento
        'numero': numero,
        'tipo': tipo,
        'data_agendada': data,
        'prioridade': prioridade,
        'status': status or 'AGENDADO',
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'transp_nome': transp_nome,
        'transp_cnpj': transp_cnpj,
        'transp_telefone': transp_telefone,
        'transp_email': transp_email,
        'veic_placa': veic_placa,
        'veic_modelo': veic_modelo,
        'veic_tipo': veic_tipo,
        'veic_capacidade_peso': veic_capacidade_peso,
        'mot_nome': mot_nome,
        'mot_cpf': mot_cpf,
        'mot_cnh': mot_cnh,
        'mot_telefone': mot_telefone,
        'agend_local': agend_local,
        'agend_dock': agend_dock,
        'agend_responsavel': agend_responsavel,
        'agend_observacoes': agend_observacoes,
        'documentos': documentos
    }
    
    sucesso, mensagem = salvar_agendamento(dados)
    
    if sucesso:
        # Recarregar agenda
        df = carregar_agendamentos()
        agenda_atualizada = criar_agenda_semanal(df)
        return dbc.Alert(mensagem, color="success", dismissable=True), False, agenda_atualizada
    else:
        return dbc.Alert(mensagem, color="danger", dismissable=True), dash.no_update, dash.no_update

@app.callback(
    Output("agenda-semanal", "children", allow_duplicate=True),
    [Input("btn-atualizar-agenda", "n_clicks"),
     Input("btn-limpar-filtros", "n_clicks"),
     Input("filtro-status-agenda", "value"),
     Input("filtro-tipo-agenda", "value"),
     Input("filtro-transportadora", "value"),
     Input("filtro-modelo", "value"),
     Input("filtro-tipo-veiculo", "value"),
     Input("filtro-doca", "value"),
     Input("filtro-semana", "value")],
    prevent_initial_call=True
)
def atualizar_agenda_semanal(n_clicks_atualizar, n_clicks_limpar, status, tipo, transportadora, modelo, tipo_veiculo, doca, semana):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update
    
    # Verificar qual input foi acionado
    triggered_id = ctx.triggered[0]["prop_id"].split('.')[0]
    
    # Se foi o botão limpar filtros
    if triggered_id == "btn-limpar-filtros":
        return dash.no_update  # Os filtros serão resetados pelos callbacks individuais
    
    # Se foi o botão de atualizar ou filtros, atualizar a agenda
    if triggered_id in ["btn-atualizar-agenda"] or triggered_id.startswith("filtro"):
        df = carregar_agendamentos()
        
        if df.empty:
            return dbc.Alert("Nenhum agendamento encontrado.", color="info")
        
        # Aplicar filtros
        if status and status != "TODOS":
            df = df[df['agend_status'] == status]
        
        if tipo and tipo != "TODOS":
            df = df[df['agend_tipo'] == tipo]
            
        if transportadora and transportadora != "TODAS":
            df = df[df['transp_nome'] == transportadora]
            
        if modelo and modelo != "TODOS":
            df = df[df['veic_modelo'] == modelo]
            
        if tipo_veiculo and tipo_veiculo != "TODOS":
            df = df[df['veic_tipo'] == tipo_veiculo]
            
        if doca and doca != "TODAS":
            df = df[df['agend_dock'] == doca]
        
        return criar_agenda_semanal(df)
    
    return dash.no_update


# Callback para popular filtros com dados dinâmicos
@app.callback(
    [Output("filtro-transportadora", "options"),
     Output("filtro-modelo", "options"),
     Output("filtro-tipo-veiculo", "options"),
     Output("filtro-doca", "options")],
    [Input("btn-atualizar-agenda", "n_clicks")],
    prevent_initial_call=True
)
def popular_filtros(n_clicks):
    df = carregar_agendamentos()
    
    if df.empty:
        return ([{"label": "Todas", "value": "TODAS"}], 
                [{"label": "Todos", "value": "TODOS"}], 
                [{"label": "Todos", "value": "TODOS"}], 
                [{"label": "Todas", "value": "TODAS"}])
    
    # Transportadoras únicas
    transportadoras = [{"label": "Todas", "value": "TODAS"}]
    for transp in df['transp_nome'].dropna().unique():
        transportadoras.append({"label": transp, "value": transp})
    
    # Modelos únicos
    modelos = [{"label": "Todos", "value": "TODOS"}]
    for modelo in df['veic_modelo'].dropna().unique():
        modelos.append({"label": modelo, "value": modelo})
    
    # Tipos de veículo únicos
    tipos_veiculo = [{"label": "Todos", "value": "TODOS"}]
    for tipo in df['veic_tipo'].dropna().unique():
        tipos_veiculo.append({"label": tipo, "value": tipo})
    
    # Docas únicas
    docas = [{"label": "Todas", "value": "TODAS"}]
    for doca in df['agend_dock'].dropna().unique():
        docas.append({"label": doca, "value": doca})
    
    return transportadoras, modelos, tipos_veiculo, docas


# Callback para limpar filtros
@app.callback(
    [Output("filtro-status-agenda", "value"),
     Output("filtro-tipo-agenda", "value"),
     Output("filtro-transportadora", "value"),
     Output("filtro-modelo", "value"),
     Output("filtro-tipo-veiculo", "value"),
     Output("filtro-doca", "value"),
     Output("filtro-semana", "value")],
    [Input("btn-limpar-filtros", "n_clicks")],
    prevent_initial_call=True
)
def limpar_filtros(n_clicks):
    if n_clicks:
        return "TODOS", "TODOS", "TODAS", "TODOS", "TODOS", "TODAS", None
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update


# Callback para excluir agendamento - TEMPORARIAMENTE DESABILITADO
# @app.callback(
#     [Output("agenda-semanal", "children", allow_duplicate=True),
#      Output("alert-mensagem", "children", allow_duplicate=True)],
#     [Input({"type": "btn-excluir-agendamento", "index": dash.dependencies.ALL}, "n_clicks")],
#     prevent_initial_call=True
# )
# def excluir_agendamento(n_clicks_list):
#     ctx = callback_context
#     if not ctx.triggered:
#         return dash.no_update, dash.no_update
#     
#     # Verificar qual botão foi clicado
#     triggered_id = ctx.triggered[0]["prop_id"]
#     print(f"DEBUG: Callback de exclusão acionado. Triggered ID: {triggered_id}")
#     
#     if "btn-excluir-agendamento" in triggered_id:
#         try:
#             # Extrair o ID do agendamento
#             agend_id = triggered_id.split('"excluir-')[1].split('"')[0]
#             agend_id = int(agend_id)
#             
#             # Excluir do banco de dados
#             banco = Banco()
#             sucesso = banco.deletar_dado("agendamento_logistica", agend_id)
#             
#             if sucesso:
#                 # Recarregar a agenda
#                 df = carregar_agendamentos()
#                 agenda_atualizada = criar_agenda_semanal(df)
#                 mensagem = f"✅ Agendamento excluído com sucesso!"
#                 return agenda_atualizada, dbc.Alert(mensagem, color="success", dismissable=True)
#             else:
#                 mensagem = f"❌ Erro ao excluir agendamento!"
#                 return dash.no_update, dbc.Alert(mensagem, color="danger", dismissable=True)
#                 
#         except Exception as e:
#             mensagem = f"❌ Erro ao excluir agendamento: {str(e)}"
#             return dash.no_update, dbc.Alert(mensagem, color="danger", dismissable=True)
#     
#     return dash.no_update, dash.no_update


# Callback para detectar cliques em eventos e abrir modal de edição
@app.callback(
    [Output("modal-agendamento", "is_open", allow_duplicate=True),
     Output("modal-agendamento-header", "children", allow_duplicate=True),
     Output("store-agendamento-edicao", "data", allow_duplicate=True),
     Output("agend-numero", "value", allow_duplicate=True)],
    [Input({"type": "evento-agendamento", "index": dash.dependencies.ALL}, "n_clicks")],
    prevent_initial_call=True
)
def abrir_edicao_agendamento(n_clicks_list):
    ctx = callback_context
    if not ctx.triggered:
        return False, "Novo Agendamento", {}, dash.no_update
    
    # Verificar se algum clique realmente aconteceu
    if not n_clicks_list or all(click is None or click == 0 for click in n_clicks_list):
        return False, "Novo Agendamento", {}, dash.no_update
    
    # Encontrar qual evento foi clicado
    triggered_id = ctx.triggered[0]["prop_id"]
    
    if not triggered_id or "n_clicks" not in triggered_id:
        return False, "Novo Agendamento", {}, dash.no_update
    
    # Verificar se o clique foi realmente acionado (maior que 0)
    triggered_value = ctx.triggered[0]["value"]
    if not triggered_value or triggered_value == 0:
        return False, "Novo Agendamento", {}, dash.no_update
    
    # Extrair ID do agendamento
    try:
        # Formato: {"type": "evento-agendamento", "index": "evento-1"}.n_clicks
        import json
        id_str = triggered_id.split('.')[0]
        id_dict = json.loads(id_str)
        evento_id = id_dict["index"]  # "evento-1"
        agend_id = int(evento_id.split('-')[1])  # 1
        
        # Carregar dados do agendamento
        banco = Banco()
        with banco.engine.connect() as conn:
            query = f"""
            SELECT * FROM agendamento_logistica WHERE agend_id = {agend_id}
            """
            df = pd.read_sql(query, conn)
            
            if not df.empty:
                agendamento = df.iloc[0]
                # Converter data para formato correto
                data_agendada = agendamento['agend_data_agendada']
                if isinstance(data_agendada, str):
                    # Se for string, converter para datetime
                    data_agendada = pd.to_datetime(data_agendada)
                
                # Converter datas de início e fim
                def format_datetime(dt):
                    if dt and pd.notna(dt):
                        if isinstance(dt, str):
                            dt = pd.to_datetime(dt)
                        return dt.strftime('%Y-%m-%dT%H:%M')
                    return ''
                
                dados_edicao = {
                    'agend_id': agendamento['agend_id'],
                    'numero': agendamento['agend_numero'],
                    'tipo': agendamento['agend_tipo'],
                    'data': data_agendada.strftime('%Y-%m-%dT%H:%M'),
                    'prioridade': agendamento['agend_prioridade'],
                    'status': agendamento['agend_status'],
                    'data_inicio': format_datetime(agendamento['agend_data_inicio']),
                    'data_fim': format_datetime(agendamento['agend_data_fim']),
                    'transp_nome': agendamento['transp_nome'],
                    'transp_cnpj': agendamento['transp_cnpj'],
                    'transp_telefone': agendamento['transp_telefone'],
                    'transp_email': agendamento['transp_email'],
                    'veic_placa': agendamento['veic_placa'],
                    'veic_modelo': agendamento['veic_modelo'],
                    'veic_tipo': agendamento['veic_tipo'],
                    'veic_capacidade_peso': agendamento['veic_capacidade_peso'],
                    'mot_nome': agendamento['mot_nome'],
                    'mot_cpf': agendamento['mot_cpf'],
                    'mot_cnh': agendamento['mot_cnh'],
                    'mot_telefone': agendamento['mot_telefone'],
                    'agend_local': agendamento['agend_local'],
                    'agend_dock': agendamento['agend_dock'],
                    'agend_responsavel': agendamento['agend_responsavel'],
                    'agend_observacoes': agendamento['agend_observacoes']
                }
                
                return True, f"Editar Agendamento - {agendamento['agend_numero']}", dados_edicao, agendamento['agend_numero']
        
    except Exception as e:
        print(f"Erro ao carregar agendamento para edição: {e}")
    
    return False, "Novo Agendamento", {}, dash.no_update

# Callback para preencher campos do formulário quando editando
@app.callback(
    [Output("agend-numero", "value", allow_duplicate=True),
     Output("agend-tipo", "value", allow_duplicate=True),
     Output("agend-data", "value", allow_duplicate=True),
     Output("agend-prioridade", "value", allow_duplicate=True),
     Output("agend-status", "value", allow_duplicate=True),
     Output("agend-data-inicio", "value", allow_duplicate=True),
     Output("agend-data-fim", "value", allow_duplicate=True),
     Output("transp-nome", "value", allow_duplicate=True),
     Output("transp-cnpj", "value", allow_duplicate=True),
     Output("transp-telefone", "value", allow_duplicate=True),
     Output("transp-email", "value", allow_duplicate=True),
     Output("veic-placa", "value", allow_duplicate=True),
     Output("veic-modelo", "value", allow_duplicate=True),
     Output("veic-tipo", "value", allow_duplicate=True),
     Output("veic-capacidade-peso", "value", allow_duplicate=True),
     Output("mot-nome", "value", allow_duplicate=True),
     Output("mot-cpf", "value", allow_duplicate=True),
     Output("mot-cnh", "value", allow_duplicate=True),
     Output("mot-telefone", "value", allow_duplicate=True),
     Output("agend-local", "value", allow_duplicate=True),
     Output("agend-dock", "value", allow_duplicate=True),
     Output("agend-responsavel", "value", allow_duplicate=True),
     Output("agend-observacoes", "value", allow_duplicate=True)],
    Input("store-agendamento-edicao", "data"),
    prevent_initial_call=True
)
def preencher_campos_edicao(dados_edicao):
    if not dados_edicao:
        return [dash.no_update] * 23
    
    # Converter datas se necessário
    def format_datetime(dt_str):
        if dt_str and dt_str != '':
            try:
                dt = pd.to_datetime(dt_str)
                return dt.strftime("%Y-%m-%dT%H:%M")
            except:
                return dt_str
        return ''
    
    return [
        dados_edicao.get('numero', ''),
        dados_edicao.get('tipo', ''),
        format_datetime(dados_edicao.get('data', '')),
        dados_edicao.get('prioridade', 'MEDIA'),
        dados_edicao.get('status', 'AGENDADO'),
        format_datetime(dados_edicao.get('data_inicio', '')),
        format_datetime(dados_edicao.get('data_fim', '')),
        dados_edicao.get('transp_nome', ''),
        dados_edicao.get('transp_cnpj', ''),
        dados_edicao.get('transp_telefone', ''),
        dados_edicao.get('transp_email', ''),
        dados_edicao.get('veic_placa', ''),
        dados_edicao.get('veic_modelo', ''),
        dados_edicao.get('veic_tipo', ''),
        dados_edicao.get('veic_capacidade_peso', ''),
        dados_edicao.get('mot_nome', ''),
        dados_edicao.get('mot_cpf', ''),
        dados_edicao.get('mot_cnh', ''),
        dados_edicao.get('mot_telefone', ''),
        dados_edicao.get('agend_local', ''),
        dados_edicao.get('agend_dock', ''),
        dados_edicao.get('agend_responsavel', ''),
        dados_edicao.get('agend_observacoes', '')
    ]

# Callback para upload do PDF dos itens
@app.callback(
    [Output("upload-status-pdf-itens", "children"),
     Output("store-pdf-itens", "data"),
     Output("pdf-viewer-itens", "children"),
     Output("btn-download-pdf-itens", "disabled"),
     Output("store-pdf-itens-path", "data")],
    Input("upload-pdf-itens", "contents"),
    prevent_initial_call=True
)
def handle_upload_pdf_itens(contents):
    if contents is None:
        return "", None, dbc.Alert("Nenhum PDF carregado", color="light"), True, None
    
    try:
        # Decodificar o conteúdo base64
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Gerar nome único para o arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pdf_itens_{timestamp}.pdf"
        
        # Criar diretório se não existir
        upload_dir = Path("assets/uploads/pdf_itens")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Salvar arquivo
        file_path = upload_dir / filename
        with open(file_path, 'wb') as f:
            f.write(decoded)
        
        # Tentar converter PDF para imagem
        pdf_preview = pdf_para_imagem(decoded)
        
        # Interface simplificada - apenas indicação e botão de download
        viewer = html.Div([
            html.Div([
                html.I(className="fa fa-file-pdf fa-2x text-success mb-2"),
                html.P("✅ PDF carregado com sucesso!", className="text-success mb-2"),
                html.P(f"Arquivo: {filename}", className="text-muted small")
            ], className="text-center p-3 border rounded", 
               style={"backgroundColor": "#f8f9fa", "minHeight": "120px", "display": "flex", 
                      "flexDirection": "column", "justifyContent": "center", "alignItems": "center"})
        ])
        
        return dbc.Alert(f"PDF salvo: {filename}", color="success", dismissable=True), str(file_path), viewer, False, str(file_path)
    
    except Exception as e:
        return dbc.Alert(f"Erro ao salvar PDF: {str(e)}", color="danger", dismissable=True), None, dbc.Alert("Erro ao carregar PDF", color="danger"), True, None

# Callback para upload da nota fiscal
@app.callback(
    [Output("upload-status-nota-fiscal", "children"),
     Output("store-nota-fiscal", "data"),
     Output("pdf-viewer-nota", "children"),
     Output("btn-download-nota", "disabled"),
     Output("store-nota-fiscal-path", "data")],
    Input("upload-nota-fiscal", "contents"),
    prevent_initial_call=True
)
def handle_upload_nota_fiscal(contents):
    if contents is None:
        return "", None, dbc.Alert("Nenhuma nota fiscal carregada", color="light"), True, None
    
    try:
        # Decodificar o conteúdo base64
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Determinar extensão do arquivo
        extension = "pdf" if content_type == "application/pdf" else "jpg"
        
        # Gerar nome único para o arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nota_fiscal_{timestamp}.{extension}"
        
        # Criar diretório se não existir
        upload_dir = Path("assets/uploads/notas_fiscais")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Salvar arquivo
        file_path = upload_dir / filename
        with open(file_path, 'wb') as f:
            f.write(decoded)
        
        # Criar visualizador
        if extension == "pdf":
            # Tentar converter PDF para imagem
            pdf_preview = pdf_para_imagem(decoded)
            
            # Interface simplificada - apenas indicação e botão de download
            viewer = html.Div([
                html.Div([
                    html.I(className="fa fa-file-pdf fa-2x text-success mb-2"),
                    html.P("✅ Nota Fiscal salva com sucesso!", className="text-success mb-2"),
                    html.P(f"Arquivo: {filename}", className="text-muted small")
                ], className="text-center p-3 border rounded", 
                   style={"backgroundColor": "#f8f9fa", "minHeight": "120px", "display": "flex", 
                          "flexDirection": "column", "justifyContent": "center", "alignItems": "center"})
            ])
        else:
            viewer = html.Img(
                src=contents,
                style={"width": "100%", "height": "400px", "objectFit": "contain"}
            )
        
        return dbc.Alert(f"Nota Fiscal salva: {filename}", color="success", dismissable=True), str(file_path), viewer, False, str(file_path)
    
    except Exception as e:
        return dbc.Alert(f"Erro ao salvar Nota Fiscal: {str(e)}", color="danger", dismissable=True), None, dbc.Alert("Erro ao carregar arquivo", color="danger"), True, None

# Callback para carregar PDFs quando editando agendamento
@app.callback(
    [Output("pdf-viewer-itens", "children", allow_duplicate=True),
     Output("pdf-viewer-nota", "children", allow_duplicate=True),
     Output("btn-download-pdf-itens", "disabled", allow_duplicate=True),
     Output("btn-download-nota", "disabled", allow_duplicate=True),
     Output("store-pdf-itens-path", "data", allow_duplicate=True),
     Output("store-nota-fiscal-path", "data", allow_duplicate=True)],
    Input("store-agendamento-edicao", "data"),
    prevent_initial_call=True
)
def carregar_pdfs_edicao(dados_edicao):
    if not dados_edicao:
        return (dbc.Alert("Nenhum PDF carregado", color="light"), 
                dbc.Alert("Nenhuma nota fiscal carregada", color="light"),
                True, True, None, None)
    
    try:
        # Carregar dados do agendamento para obter caminhos dos documentos
        agend_id = dados_edicao.get('agend_id')
        if not agend_id:
            return (dbc.Alert("Nenhum PDF carregado", color="light"), 
                    dbc.Alert("Nenhuma nota fiscal carregada", color="light"),
                    True, True, None, None)
        
        banco = Banco()
        with banco.engine.connect() as conn:
            query = f"SELECT agend_documentos FROM agendamento_logistica WHERE agend_id = {agend_id}"
            result = pd.read_sql(query, conn)
            
            if result.empty:
                return (dbc.Alert("Nenhum PDF carregado", color="light"), 
                        dbc.Alert("Nenhuma nota fiscal carregada", color="light"),
                        True, True, None, None)
            
            documentos_str = result.iloc[0]['agend_documentos']
            if not documentos_str:
                return (dbc.Alert("Nenhum PDF carregado", color="light"), 
                        dbc.Alert("Nenhuma nota fiscal carregada", color="light"),
                        True, True, None, None)
            
            # Converter string JSON para dicionário
            try:
                if isinstance(documentos_str, str):
                    documentos = json.loads(documentos_str)
                else:
                    documentos = documentos_str
            except (json.JSONDecodeError, TypeError):
                print(f"Erro ao converter documentos: {documentos_str}")
                return (dbc.Alert("Erro ao carregar documentos", color="warning"), 
                        dbc.Alert("Erro ao carregar documentos", color="warning"),
                        True, True, None, None)
            
            # Carregar PDF dos itens
            pdf_itens_path = documentos.get('pdf_itens')
            pdf_itens_viewer = dbc.Alert("Nenhum PDF carregado", color="light")
            pdf_itens_disabled = True
            if pdf_itens_path and os.path.exists(pdf_itens_path):
                try:
                    with open(pdf_itens_path, 'rb') as f:
                        pdf_data = f.read()
                        pdf_content = base64.b64encode(pdf_data).decode()
                        pdf_data_url = f"data:application/pdf;base64,{pdf_content}"
                        # Tentar converter PDF para imagem
                        pdf_preview = pdf_para_imagem(pdf_data)
                        
                        # Interface simplificada - apenas indicação e botão de download
                        pdf_itens_viewer = html.Div([
                            html.Div([
                                html.I(className="fa fa-file-pdf fa-2x text-success mb-2"),
                                html.P("✅ PDF carregado com sucesso!", className="text-success mb-2"),
                                html.P(f"Arquivo: {os.path.basename(pdf_itens_path)}", className="text-muted small")
                            ], className="text-center p-3 border rounded", 
                               style={"backgroundColor": "#f8f9fa", "minHeight": "120px", "display": "flex", 
                                      "flexDirection": "column", "justifyContent": "center", "alignItems": "center"})
                        ])
                        pdf_itens_disabled = False
                except Exception as e:
                    pdf_itens_viewer = dbc.Alert(f"Erro ao carregar PDF: {str(e)}", color="warning")
            
            # Carregar Nota Fiscal
            nota_fiscal_path = documentos.get('nota_fiscal')
            nota_fiscal_viewer = dbc.Alert("Nenhuma nota fiscal carregada", color="light")
            nota_fiscal_disabled = True
            if nota_fiscal_path and os.path.exists(nota_fiscal_path):
                try:
                    with open(nota_fiscal_path, 'rb') as f:
                        file_data = f.read()
                        file_content = base64.b64encode(file_data).decode()
                        if nota_fiscal_path.lower().endswith('.pdf'):
                            file_data_url = f"data:application/pdf;base64,{file_content}"
                            # Tentar converter PDF para imagem
                            pdf_preview = pdf_para_imagem(file_data)
                            
                            # Interface simplificada - apenas indicação e botão de download
                            nota_fiscal_viewer = html.Div([
                                html.Div([
                                    html.I(className="fa fa-file-pdf fa-2x text-success mb-2"),
                                    html.P("✅ Nota Fiscal carregada com sucesso!", className="text-success mb-2"),
                                    html.P(f"Arquivo: {os.path.basename(nota_fiscal_path)}", className="text-muted small")
                                ], className="text-center p-3 border rounded", 
                                   style={"backgroundColor": "#f8f9fa", "minHeight": "120px", "display": "flex", 
                                          "flexDirection": "column", "justifyContent": "center", "alignItems": "center"})
                            ])
                        else:
                            file_data_url = f"data:image/jpeg;base64,{file_content}"
                            nota_fiscal_viewer = html.Img(
                                src=file_data_url,
                                style={"width": "100%", "height": "400px", "objectFit": "contain"}
                            )
                        nota_fiscal_disabled = False
                except Exception as e:
                    nota_fiscal_viewer = dbc.Alert(f"Erro ao carregar nota fiscal: {str(e)}", color="warning")
            
            return (pdf_itens_viewer, nota_fiscal_viewer, pdf_itens_disabled, 
                    nota_fiscal_disabled, pdf_itens_path, nota_fiscal_path)
    
    except Exception as e:
        print(f"Erro ao carregar PDFs para edição: {e}")
        return (dbc.Alert("Erro ao carregar PDF", color="danger"), 
                dbc.Alert("Erro ao carregar nota fiscal", color="danger"),
                True, True, None, None)

# Callback para limpar visualizadores quando abrir novo agendamento
@app.callback(
    [Output("pdf-viewer-itens", "children", allow_duplicate=True),
     Output("pdf-viewer-nota", "children", allow_duplicate=True),
     Output("btn-download-pdf-itens", "disabled", allow_duplicate=True),
     Output("btn-download-nota", "disabled", allow_duplicate=True),
     Output("store-pdf-itens-path", "data", allow_duplicate=True),
     Output("store-nota-fiscal-path", "data", allow_duplicate=True)],
    Input("btn-novo-agendamento", "n_clicks"),
    prevent_initial_call=True
)
def limpar_visualizadores(n_clicks):
    if n_clicks:
        return (dbc.Alert("Nenhum PDF carregado", color="light"), 
                dbc.Alert("Nenhuma nota fiscal carregada", color="light"),
                True, True, None, None)
    return [dash.no_update] * 6

# Callbacks para mudança de status
@app.callback(
    [Output("agend-status", "value"),
     Output("agend-data-inicio", "value"),
     Output("alert-mensagem", "children", allow_duplicate=True)],
    [Input("btn-iniciar", "n_clicks"),
     Input("btn-concluir", "n_clicks"),
     Input("btn-cancelar", "n_clicks")],
    [State("agend-status", "value"),
     State("agend-numero", "value")],
    prevent_initial_call=True
)
def atualizar_status(n_iniciar, n_concluir, n_cancelar, status_atual, numero_agendamento):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update
    
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if triggered_id == "btn-iniciar" and n_iniciar:
        # Iniciar agendamento
        agora = datetime.now().strftime("%Y-%m-%dT%H:%M")
        return "EM_ANDAMENTO", agora, dbc.Alert("✅ Agendamento iniciado com sucesso!", color="success", dismissable=True)
    
    elif triggered_id == "btn-concluir" and n_concluir:
        # Concluir agendamento
        agora = datetime.now().strftime("%Y-%m-%dT%H:%M")
        return "CONCLUIDO", dash.no_update, dbc.Alert("✅ Agendamento concluído com sucesso!", color="success", dismissable=True)
    
    elif triggered_id == "btn-cancelar" and n_cancelar:
        # Cancelar agendamento
        return "CANCELADO", dash.no_update, dbc.Alert("❌ Agendamento cancelado!", color="warning", dismissable=True)
    
    return dash.no_update, dash.no_update, dash.no_update

# Callback para atualizar data fim quando status for concluído
@app.callback(
    Output("agend-data-fim", "value"),
    Input("agend-status", "value"),
    prevent_initial_call=True
)
def atualizar_data_fim(status):
    if status == "CONCLUIDO":
        return datetime.now().strftime("%Y-%m-%dT%H:%M")
    return dash.no_update

# Callback para download do PDF dos itens
@app.callback(
    Output("download-pdf-itens", "data"),
    Input("btn-download-pdf-itens", "n_clicks"),
    State("store-pdf-itens-path", "data"),
    prevent_initial_call=True
)
def download_pdf_itens(n_clicks, file_path):
    if n_clicks and file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            content = f.read()
        return dcc.send_bytes(content, os.path.basename(file_path))
    return None

# Callback para download da nota fiscal
@app.callback(
    Output("download-nota-fiscal", "data"),
    Input("btn-download-nota", "n_clicks"),
    State("store-nota-fiscal-path", "data"),
    prevent_initial_call=True
)
def download_nota_fiscal(n_clicks, file_path):
    if n_clicks and file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            content = f.read()
        return dcc.send_bytes(content, os.path.basename(file_path))
    return None