import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, dash_table, callback_context, no_update, ALL
from app import app
import requests
import json
from datetime import datetime
import pandas as pd
from banco_dados.banco import Banco, PRODUTO, engine
from sqlalchemy.orm import Session
from sqlalchemy import text

# URLs da API
PEDIDOS_API_URL = "SUA-CHAVE-AQUI"
PROGRAMACAO_FATURAMENTO_API_URL = "SUA-CHAVE-AQUI"
NFE_SAIDAS_API_URL = "SUA-CHAVE-AQUI"
NFE_SAIDAS_ITENS_API_URL = "SUA-CHAVE-AQUI"

# Layout da página de integrações
layout = dbc.Container([
    html.H3("Integrações", className="text-center mb-4"),
    
    # Botões na parte superior
    dbc.Row([
        dbc.Col([
            dbc.Button(
                "Puxar Itens Pedido",
                id="btn-puxar-itens-faturados",
                color="primary",
                size="lg",
                className="w-100 mb-3"
            )
        ], md=6),
        dbc.Col([
            dbc.Button(
                "Puxar Itens Faturados (NFE)",
                id="btn-puxar-itens-faturados-nfe",
                color="secondary",
                size="lg",
                className="w-100 mb-3"
            )
        ], md=6)
    ], className="mb-4"),
    

    
    # Store para manter dados da tabela
    dcc.Store(id="store-dados-tabela"),
    
    # Store para rastrear item sendo mapeado
    dcc.Store(id="store-item-mapeamento"),
    
    # Tabela de pedidos
    html.Div(id="tabela-pedidos-container"),
    
    # Botão para salvar no banco (inicialmente desabilitado)
    html.Div([
        dbc.Button(
            "💾 Salvar no Banco",
            id="btn-salvar-banco",
            color="success",
            size="lg",
            className="w-100 mb-3",
            disabled=True  # Inicialmente desabilitado
        ),
        html.P(
            "⚠️ Apenas itens com correspondência serão salvos no banco",
            className="text-muted small mb-2 text-center"
        )
    ], id="botao-salvar-container", className="text-center mb-3", style={'display': 'none'}),
    
    # Espaço para análise da integração
    dbc.Card([
        dbc.CardHeader([
            html.H5("Análise da Integração", className="mb-0"),
            html.Small("Resultados e logs das operações de integração", className="text-muted")
        ]),
        dbc.CardBody([
            # Área de status
            dbc.Alert(
                "Nenhuma operação realizada ainda. Clique em um dos botões acima para iniciar.",
                id="alert-status-integracao",
                color="info",
                className="mb-3"
            ),
            
            # Área de logs
            html.Div([
                html.H6("Logs de Integração:", className="mb-2"),
                html.Div(
                    id="logs-integracao",
                    style={
                        'height': '400px',
                        'overflowY': 'auto',
                        'backgroundColor': '#f8f9fa',
                        'border': '1px solid #dee2e6',
                        'borderRadius': '5px',
                        'padding': '15px',
                        'fontFamily': 'monospace',
                        'fontSize': '12px'
                    }
                )
            ]),
            
            # Área de resultados
            html.Div([
                html.H6("Resultados:", className="mb-2 mt-3"),
                html.Div(
                    id="resultados-integracao",
                    style={
                        'minHeight': '200px',
                        'backgroundColor': '#ffffff',
                        'border': '1px solid #dee2e6',
                        'borderRadius': '5px',
                        'padding': '15px'
                    }
                )
            ])
        ])
    ]),
    
    # Modal para detalhes (opcional)
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Detalhes da Integração")),
        dbc.ModalBody([
            html.Div(id="modal-content-integracao")
        ]),
        dbc.ModalFooter([
            dbc.Button("Fechar", id="fechar-modal-integracao", className="ms-auto")
        ])
    ], id="modal-integracao", size="lg", is_open=False),
    
    # Modal para seleção de produtos
    dbc.Modal([
        dbc.ModalHeader([
            dbc.ModalTitle("Selecionar Produto Correspondente"),
            dbc.Button("×", id="fechar-modal-produto", className="btn-close", n_clicks=0)
        ]),
        dbc.ModalBody([
            html.Div([
                html.H6("Descrição do Item:", id="descricao-item-modal"),
                html.Hr(),
                html.P("Selecione o produto correspondente da lista abaixo:", className="text-muted"),
                html.Div(id="lista-produtos-modal")
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button("Confirmar Seleção", id="confirmar-selecao-produto", color="success", disabled=True),
            dbc.Button("Fechar", id="fechar-modal-produto-footer", className="ms-auto")
        ])
    ], id="modal-selecao-produto", size="lg", is_open=False)
    
], fluid=True)

def buscar_dados_api(url):
    """Função para buscar dados da API"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        dados = response.json()
        
        # Debug: mostrar quantos itens foram retornados
        if isinstance(dados, list):
            print(f"🔍 API {url}: retornou {len(dados)} itens")
        elif isinstance(dados, dict) and "erro" not in dados:
            print(f"🔍 API {url}: retornou dados do tipo dict com {len(dados)} chaves")
        
        return dados
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição para {url}: {str(e)}")
        return {"erro": f"Erro na requisição: {str(e)}"}
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao decodificar JSON de {url}: {str(e)}")
        return {"erro": f"Erro ao decodificar JSON: {str(e)}"}
    except Exception as e:
        print(f"❌ Erro inesperado em {url}: {str(e)}")
        return {"erro": f"Erro inesperado: {str(e)}"}

def processar_dados_pedidos():
    """Função para processar dados de pedidos e programação de faturamento"""
    try:
        # Buscar dados das duas APIs
        pedidos = buscar_dados_api(PEDIDOS_API_URL)
        programacao_faturamento = buscar_dados_api(PROGRAMACAO_FATURAMENTO_API_URL)
        
        if "erro" in pedidos:
            return {"erro": f"Erro ao buscar pedidos: {pedidos['erro']}"}
        
        if "erro" in programacao_faturamento:
            return {"erro": f"Erro ao buscar programação de faturamento: {programacao_faturamento['erro']}"}
        
        # Criar dicionário de pedidos para lookup rápido
        pedidos_dict = {}
        for pedido in pedidos:
            pedidos_dict[pedido.get("ID_Pedido")] = pedido
        
        # Processar dados combinados
        dados_processados = []
        for item in programacao_faturamento:
            pedido_id = item.get("Pedido")
            pedido_info = pedidos_dict.get(pedido_id, {})
            
            dados_processados.append({
                "Descrição do Item": item.get("Descricao_Item_Faturamento", ""),
                "Data de Entrega": item.get("Data_Entrega", ""),
                "Data de Início": item.get("Inicio", ""),
                "Valor de Faturamento": item.get("Valor_Faturamento", "0.00"),
                "Situação": pedido_info.get("Situacao", ""),
                "Tipo de Frete": pedido_info.get("Tipo_Frete", ""),
                "ID do Pedido": pedido_id,
                "Quantidade": item.get("Quantidade", 0),
                "Código do Produto": item.get("Codigo_Produto", "")
            })
        
        return {"dados": dados_processados, "total": len(dados_processados)}
        
    except Exception as e:
        return {"erro": f"Erro ao processar dados: {str(e)}"}

def processar_dados_itens_faturados():
    """Função para processar dados de itens faturados com filtro de situação e mapeamento de produtos"""
    logs = []
    try:
        # Buscar dados das duas APIs
        pedidos = buscar_dados_api(PEDIDOS_API_URL)
        programacao_faturamento = buscar_dados_api(PROGRAMACAO_FATURAMENTO_API_URL)
        
        # Debug: mostrar quantos dados foram recebidos
        if isinstance(pedidos, list):
            log_msg = f"📊 Pedidos recebidos: {len(pedidos)}"
            print(log_msg)
            logs.append(log_msg)
        if isinstance(programacao_faturamento, list):
            log_msg = f"📊 Programação de faturamento recebida: {len(programacao_faturamento)}"
            print(log_msg)
            logs.append(log_msg)
        
        if "erro" in pedidos:
            return {"erro": f"Erro ao buscar pedidos: {pedidos['erro']}"}
        
        if "erro" in programacao_faturamento:
            return {"erro": f"Erro ao buscar programação de faturamento: {programacao_faturamento['erro']}"}
        
        # Buscar produtos do banco local
        banco = Banco()
        df_produtos = banco.ler_tabela("produtos")
        produtos_dict = {}
        for _, produto in df_produtos.iterrows():
            produtos_dict[produto['produto_id']] = produto['nome']
        
        # Situações permitidas (todas EXCETO "Faturamento solicitado")
        situacoes_permitidas = ["Pronto para faturar", "Aberto", "Fechado"]
        
        # Criar dicionário de pedidos para lookup rápido (TODOS os pedidos, sem filtro inicial)
        pedidos_dict = {}
        for pedido in pedidos:
            pedidos_dict[pedido.get("ID_Pedido")] = pedido
        
        print(f"🔍 Total de pedidos carregados no dicionário: {len(pedidos_dict)}")
        
        # Debug: mostrar alguns IDs de pedidos
        if pedidos_dict:
            ids_validos = list(pedidos_dict.keys())[:5]
            print(f"🔍 Exemplos de IDs de pedidos: {ids_validos}")
            print(f"🔍 Tipos dos IDs de pedidos: {[type(id).__name__ for id in ids_validos]}")
        
        # Processar dados combinados (apenas pedidos com situações permitidas)
        dados_processados = []
        itens_sem_correspondencia = []
        itens_sem_pedido_correspondente = 0
        itens_situacao_invalida = 0
        
        print(f"🔍 Iniciando processamento de {len(programacao_faturamento)} itens de programação de faturamento...")
        print(f"🔍 Pedidos válidos disponíveis: {len(pedidos_dict)}")
        
        # Debug: mostrar alguns IDs de programação
        ids_programacao = [item.get("Pedido") for item in programacao_faturamento[:5]]
        print(f"🔍 Exemplos de IDs de programação: {ids_programacao}")
        print(f"🔍 Tipos dos IDs de programação: {[type(id).__name__ for id in ids_programacao]}")
        
        # Verificar correspondência direta
        correspondencias_encontradas = 0
        for item in programacao_faturamento[:100]:  # Verificar apenas os primeiros 100
            pedido_id = item.get("Pedido")
            if pedido_id in pedidos_dict:
                correspondencias_encontradas += 1
        
        print(f"🔍 Correspondências encontradas nos primeiros 100 itens: {correspondencias_encontradas}")
        
        for i, item in enumerate(programacao_faturamento):
            if i % 1000 == 0:  # Log a cada 1000 itens
                print(f"🔍 Processando item {i+1} de {len(programacao_faturamento)}...")
            
            pedido_id = item.get("Pedido")
            pedido_info = pedidos_dict.get(pedido_id)
            
            # Primeiro verificar se o pedido existe
            if pedido_info:
                # Depois verificar se a situação é permitida
                situacao = pedido_info.get("Situacao", "")
                if situacao in situacoes_permitidas:
                    descricao_item = item.get("Descricao_Item_Faturamento", "")
                    if i < 5:  # Log dos primeiros 5 itens processados
                        print(f"🔍 Item {i+1}: Pedido {pedido_id} encontrado, situação: {situacao} ✅ VÁLIDO")
                else:
                    itens_situacao_invalida += 1
                    if i < 5:  # Log dos primeiros 5 itens com situação inválida
                        print(f"🔍 Item {i+1}: Pedido {pedido_id} encontrado, situação: {situacao} ❌ INVÁLIDA")
                    continue
            else:
                itens_sem_pedido_correspondente += 1
                if i < 5:  # Log dos primeiros 5 itens não encontrados
                    print(f"🔍 Item {i+1}: Pedido {pedido_id} NÃO encontrado na tabela de pedidos")
                continue
            
            # Se chegou aqui, o item tem pedido válido e situação permitida
            # Tentar encontrar correspondência automática
            produto_correspondente = None
            produto_id_correspondente = None
            
            # Buscar por correspondência exata ou similar
            for produto_id, nome_produto in produtos_dict.items():
                if (descricao_item.lower() in nome_produto.lower() or 
                    nome_produto.lower() in descricao_item.lower() or
                    descricao_item.lower() == nome_produto.lower()):
                    produto_correspondente = nome_produto
                    produto_id_correspondente = produto_id
                    break
            
            # Se não encontrou correspondência, adicionar à lista de itens sem correspondência
            if not produto_correspondente:
                itens_sem_correspondencia.append({
                    "descricao": descricao_item,
                    "pedido_id": pedido_id,
                    "item_data": item
                })
            
            dados_processados.append({
                "Descrição do Item": descricao_item,
                "Data de Entrega": item.get("Data_Entrega", ""),
                "Data de Início": item.get("Inicio", ""),
                "Valor de Faturamento": item.get("Valor_Faturamento", "0.00"),
                "Situação": pedido_info.get("Situacao", ""),
                "Tipo de Frete": pedido_info.get("Tipo_Frete", ""),
                "ID do Pedido": pedido_id,
                "Quantidade": item.get("Quantidade", 0),
                "Código do Produto": item.get("Codigo_Produto", ""),
                "Produto Correspondente": produto_correspondente or "❌ Sem correspondência",
                "Produto ID": produto_id_correspondente or "N/A",
                "Status Mapeamento": "✅ Automático" if produto_correspondente else "❌ Manual"
            })
            
            # Log a cada 100 itens processados
            if len(dados_processados) % 100 == 0:
                print(f"🔍 Processados {len(dados_processados)} itens válidos...")
        
        # Debug: mostrar quantos dados foram processados
        print(f"✅ Dados processados: {len(dados_processados)}")
        print(f"❌ Itens sem correspondência: {len(itens_sem_correspondencia)}")
        print(f"🚫 Itens sem pedido correspondente: {itens_sem_pedido_correspondente}")
        print(f"🚫 Itens com situação inválida: {itens_situacao_invalida}")
        print(f"📊 Total de itens processados: {len(dados_processados) + itens_sem_pedido_correspondente + itens_situacao_invalida}")
        
        return {
            "dados": dados_processados, 
            "total": len(dados_processados),
            "itens_sem_correspondencia": itens_sem_correspondencia,
            "produtos_disponiveis": produtos_dict
        }
        
    except Exception as e:
        return {"erro": f"Erro ao processar dados: {str(e)}"}

def processar_dados_nfe_itens_faturados():
    """Função para processar dados de NFE de itens faturados"""
    try:
        from datetime import datetime, timedelta
        
        # Buscar dados das duas APIs de NFE
        nfe_saidas = buscar_dados_api(NFE_SAIDAS_API_URL)
        nfe_saidas_itens = buscar_dados_api(NFE_SAIDAS_ITENS_API_URL)
        
        # Debug: mostrar quantos dados foram recebidos
        if isinstance(nfe_saidas, list):
            print(f"📊 NFE Saídas recebidas: {len(nfe_saidas)}")
        if isinstance(nfe_saidas_itens, list):
            print(f"📊 NFE Saídas Itens recebidos: {len(nfe_saidas_itens)}")
        
        if "erro" in nfe_saidas:
            return {"erro": f"Erro ao buscar NFE saídas: {nfe_saidas['erro']}"}
        
        if "erro" in nfe_saidas_itens:
            return {"erro": f"Erro ao buscar NFE saídas itens: {nfe_saidas_itens['erro']}"}
        
        # Buscar produtos do banco local
        banco = Banco()
        df_produtos = banco.ler_tabela("produtos")
        produtos_dict = {}
        for _, produto in df_produtos.iterrows():
            produtos_dict[produto['produto_id']] = produto['nome']
        
        # Buscar NFEs já existentes no banco para evitar duplicatas
        df_saida_notas = banco.ler_tabela("saida_notas")
        nfes_existentes = set()
        if not df_saida_notas.empty:
            nfes_existentes = set(df_saida_notas['numero_nfe'].dropna().astype(str))
            print(f"🔍 NFEs já existentes no banco: {len(nfes_existentes)}")
            if len(nfes_existentes) > 0:
                print(f"   Exemplos de NFEs existentes: {list(nfes_existentes)[:5]}")
        else:
            print(f"🔍 Nenhuma NFE existente no banco (tabela vazia)")
        
        # Calcular data limite (apenas ontem e hoje)
        hoje = datetime.now().date()
        ontem = hoje - timedelta(days=4)
        print(f"🔍 Filtro de data: apenas NFEs de {ontem} e {hoje}")
        
        # Criar dicionário de NFE saídas para lookup rápido
        nfe_saidas_dict = {}
        nfes_filtradas_por_data = 0
        
        # Log das primeiras NFEs para debug
        print(f"🔍 Exemplos das primeiras 5 NFEs:")
        for i in range(min(5, len(nfe_saidas))):
            nfe = nfe_saidas[i]
            data_emissao = nfe.get("Data_Emissao", "")
            nfe_id = nfe.get("ID_NFE_Saida")
            numero_nfe = nfe.get("Numero_NFE", "")
            print(f"   NFE {i+1}: ID={nfe_id}, Número={numero_nfe}, Data={data_emissao}")
        
        for nfe in nfe_saidas:
            data_emissao = nfe.get("Data_Emissao", "")
            if data_emissao:
                try:
                    # Converter data para verificar se é de ontem ou hoje
                    data_obj = datetime.strptime(data_emissao.split()[0], '%Y-%m-%d').date()
                    if data_obj >= ontem:
                        nfe_saidas_dict[nfe.get("ID_NFE_Saida")] = nfe
                        nfes_filtradas_por_data += 1
                        
                        # Log das primeiras NFEs válidas
                        if nfes_filtradas_por_data <= 5:
                            print(f"   ✅ NFE válida: ID={nfe.get('ID_NFE_Saida')}, Número={nfe.get('Numero_NFE')}, Data={data_emissao}")
                except:
                    continue
        
        print(f"🔍 NFEs filtradas por data (>= {ontem}): {nfes_filtradas_por_data} de {len(nfe_saidas)}")
        print(f"🔍 NFEs com data válida: {len(nfe_saidas_dict)}")
        
        # Processar dados combinados (apenas NFEs de ontem e hoje)
        dados_processados = []
        itens_sem_correspondencia = []
        itens_filtrados_duplicatas = 0
        itens_filtrados_data = 0
        
        print(f"🔍 Iniciando processamento de {len(nfe_saidas_itens)} itens de NFE...")
        
        # Log dos primeiros itens para debug
        print(f"🔍 Exemplos dos primeiros 5 itens NFE:")
        for i in range(min(5, len(nfe_saidas_itens))):
            item = nfe_saidas_itens[i]
            print(f"   Item {i+1}: NFE_ID={item.get('NFE_Saida')}, Descrição={item.get('Descricao', 'N/A')}, Qtd={item.get('Quantidade', 'N/A')}")
        
        for i, item in enumerate(nfe_saidas_itens):
            if i % 1000 == 0:  # Log a cada 1000 itens
                print(f"🔍 Processando item NFE {i+1} de {len(nfe_saidas_itens)}...")
            
            nfe_id = item.get("NFE_Saida")
            nfe_info = nfe_saidas_dict.get(nfe_id)
            
            # Só incluir se a NFE for de ontem ou hoje
            if nfe_info:
                numero_nfe = str(nfe_info.get("Numero_NFE", ""))
                
                # Verificar se a NFE já existe no banco
                if numero_nfe in nfes_existentes:
                    itens_filtrados_duplicatas += 1
                    if i < 10:  # Log dos primeiros 10 itens filtrados por duplicata
                        print(f"   Item {i+1}: NFE {numero_nfe} já existe no banco (duplicata) - PULADO")
                    continue  # Pular NFEs já existentes
                
                # Log dos primeiros itens válidos processados
                if i < 10:
                    print(f"   Item {i+1}: NFE {numero_nfe} - Processando...")
                
                descricao_item = item.get("Descricao", "")
                quantidade = item.get("Quantidade", 0)
                
                # Tentar encontrar correspondência automática
                produto_correspondente = None
                produto_id_correspondente = None
                
                # Buscar por correspondência exata ou similar
                for produto_id, nome_produto in produtos_dict.items():
                    if (descricao_item.lower() in nome_produto.lower() or 
                        nome_produto.lower() in descricao_item.lower() or
                        descricao_item.lower() == nome_produto.lower()):
                        produto_correspondente = nome_produto
                        produto_id_correspondente = produto_id
                        break
                
                # Se não encontrou correspondência, adicionar à lista de itens sem correspondência
                if not produto_correspondente:
                    itens_sem_correspondencia.append({
                        "descricao": descricao_item,
                        "numero_nfe": numero_nfe,
                        "item_data": item
                    })
                
                dados_processados.append({
                    "Descrição": descricao_item,
                    "Quantidade": quantidade,
                    "Numero_NFE": numero_nfe,
                    "Data_Emissao": nfe_info.get("Data_Emissao", ""),
                    "Cliente": nfe_info.get("Cliente", ""),
                    "Valor_Total": item.get("Valor_Total", "0.00"),
                    "Produto Correspondente": produto_correspondente or "❌ Sem correspondência",
                    "Produto ID": produto_id_correspondente or "N/A",
                    "Status Mapeamento": "✅ Automático" if produto_correspondente else "❌ Manual"
                })
                
                # Log a cada 100 itens processados
                if len(dados_processados) % 100 == 0:
                    print(f"🔍 Processados {len(dados_processados)} itens NFE válidos...")
                
                # Log dos primeiros itens processados com detalhes
                if len(dados_processados) <= 10:
                    print(f"   ✅ Item processado: NFE {numero_nfe}, Descrição: {descricao_item}, Qtd: {quantidade}, Produto: {produto_correspondente or '❌ Sem correspondência'}")
            else:
                itens_filtrados_data += 1
                if i < 10:  # Log dos primeiros 10 itens filtrados por data
                    print(f"   Item {i+1}: NFE_ID {nfe_id} não encontrado no dicionário (filtrado por data) - PULADO")
                continue
        
        # Debug: mostrar quantos dados foram processados
        print(f"✅ Dados NFE processados: {len(dados_processados)}")
        print(f"❌ Itens NFE sem correspondência: {len(itens_sem_correspondencia)}")
        print(f"🚫 Itens filtrados por data (antigas): {itens_filtrados_data}")
        print(f"🚫 Itens filtrados por duplicatas: {itens_filtrados_duplicatas}")
        print(f"📊 Total de itens NFE processados: {len(dados_processados) + itens_filtrados_data + itens_filtrados_duplicatas}")
        
        return {
            "dados": dados_processados, 
            "total": len(dados_processados),
            "itens_sem_correspondencia": itens_sem_correspondencia,
            "produtos_disponiveis": produtos_dict
        }
        
    except Exception as e:
        return {"erro": f"Erro ao processar dados NFE: {str(e)}"}

def ordenar_dados_por_mapeamento(dados):
    """Função para ordenar dados, agrupando por NFE e priorizando NFEs com itens manuais"""
    print(f"🔍 Ordenando {len(dados)} itens...")
    
    # Verificar se são dados NFE (têm Numero_NFE) ou pedidos
    if dados and "Numero_NFE" in dados[0]:
        # Dados NFE - agrupar por NFE
        print("🔍 Detectados dados NFE - agrupando por NFE...")
        
        # Separar por NFE e verificar se tem itens manuais
        nfes_com_manuais = set()
        nfes_apenas_automaticos = set()
        
        for item in dados:
            nfe = item.get("Numero_NFE", "")
            if "❌ Manual" in item.get("Status Mapeamento", ""):
                nfes_com_manuais.add(nfe)
            else:
                if nfe not in nfes_com_manuais:
                    nfes_apenas_automaticos.add(nfe)
        
        # Ordenar NFEs: primeiro as que têm itens manuais, depois as automáticas
        nfes_ordenadas = sorted(nfes_com_manuais) + sorted(nfes_apenas_automaticos)
        
        # Agrupar dados por NFE na ordem correta
        resultado = []
        for nfe in nfes_ordenadas:
            itens_nfe = [item for item in dados if item.get("Numero_NFE", "") == nfe]
            # Dentro de cada NFE, ordenar: manuais primeiro, depois automáticos
            itens_manuais = [item for item in itens_nfe if "❌ Manual" in item.get("Status Mapeamento", "")]
            itens_automaticos = [item for item in itens_nfe if "❌ Manual" not in item.get("Status Mapeamento", "")]
            resultado.extend(itens_manuais + itens_automaticos)
        
        print(f"🔍 Ordenação NFE concluída: {len(nfes_com_manuais)} NFEs com manuais + {len(nfes_apenas_automaticos)} NFEs automáticas")
        
    else:
        # Dados de pedidos - manter ordenação simples
        print("🔍 Detectados dados de pedidos - ordenação simples...")
        dados_automaticos = []
        dados_manuais = []
        
        for item in dados:
            if "❌ Manual" in item.get("Status Mapeamento", ""):
                dados_manuais.append(item)
            else:
                dados_automaticos.append(item)
        
        resultado = dados_manuais + dados_automaticos
        print(f"🔍 Ordenação pedidos concluída: {len(dados_manuais)} manuais + {len(dados_automaticos)} automáticos")
    
    return resultado

def salvar_pedidos_em_aberto_no_banco(dados_processados):
    """Função para salvar pedidos em aberto no banco de dados"""
    try:
        # Usar SQLAlchemy diretamente para limpar a tabela
        with Session(engine) as session:
            # Limpar tabela existente
            session.execute(text("DELETE FROM pedidos_em_aberto"))
            session.commit()
        
        banco = Banco()
        
        # Contador de itens salvos
        itens_salvos = 0
        
        # Salvar apenas itens com correspondência
        for item in dados_processados:
            # Verificar se o item tem correspondência (não é "❌ Sem correspondência")
            if item.get("Produto Correspondente") != "❌ Sem correspondência" and item.get("Produto ID") != "N/A":
                try:
                    # Preparar dados para inserção
                    dados_insercao = {
                        'descricao_item': item.get("Descrição do Item", ""),
                        'produto_id': item.get("Produto ID"),
                        'data_entrega': item.get("Data de Entrega", ""),
                        'data_inicio': item.get("Data de Início", ""),
                        'valor_faturamento': item.get("Valor de Faturamento", ""),
                        'situacao': item.get("Situação", ""),
                        'tipo_frete': item.get("Tipo de Frete", ""),
                        'id_pedido': item.get("ID do Pedido", ""),
                        'quantidade': item.get("Quantidade", 0),
                        'codigo_produto': item.get("Código do Produto", ""),
                        'status_mapeamento': item.get("Status Mapeamento", "")
                    }
                    
                    # Inserir no banco
                    banco.inserir_dados('pedidos_em_aberto', **dados_insercao)
                    itens_salvos += 1
                    
                except Exception as e:
                    print(f"Erro ao salvar item {item.get('Descrição do Item', '')}: {e}")
                    continue
        
        return {
            "sucesso": True,
            "itens_salvos": itens_salvos,
            "total_processados": len(dados_processados)
        }
        
    except Exception as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "itens_salvos": 0,
            "total_processados": 0
        }

def salvar_nfe_itens_faturados_no_banco(dados_processados):
    """Função para salvar NFE de itens faturados no banco de dados"""
    try:
        print(f"🔍 DEBUG - Iniciando salvamento de {len(dados_processados)} itens NFE")
        banco = Banco()
        
        # Contador de itens salvos
        itens_salvos = 0
        
        # Salvar apenas itens com correspondência
        for i, item in enumerate(dados_processados):
            print(f"🔍 DEBUG - Processando item {i+1}: {item.get('Descrição', '')[:50]}...")
            print(f"🔍 DEBUG - Produto Correspondente: {item.get('Produto Correspondente', '')}")
            print(f"🔍 DEBUG - Produto ID: {item.get('Produto ID', '')}")
            # Verificar se o item tem correspondência (não é "❌ Sem correspondência")
            if item.get("Produto Correspondente") != "❌ Sem correspondência" and item.get("Produto ID") != "N/A":
                print(f"✅ DEBUG - Item tem correspondência, salvando...")
                try:
                    # Preparar dados para inserção
                    dados_insercao = {
                        'produto_id': item.get("Produto ID"),
                        'descricao': item.get("Descrição", ""),
                        'quantidade': item.get("Quantidade", 0),
                        'numero_nfe': item.get("Numero_NFE", ""),
                        'observacao': f"Data Emissão: {item.get('Data_Emissao', '')} | Cliente: {item.get('Cliente', '')} | Valor: {item.get('Valor_Total', '')}"
                    }
                    
                    print(f"🔍 DEBUG - Dados para inserção: {dados_insercao}")
                    
                    # Inserir no banco
                    banco.inserir_dados('saida_notas', **dados_insercao)
                    itens_salvos += 1
                    print(f"✅ DEBUG - Item salvo com sucesso! Total: {itens_salvos}")
                    
                except Exception as e:
                    print(f"❌ DEBUG - Erro ao salvar item NFE {item.get('Descrição', '')}: {e}")
                    continue
            else:
                print(f"❌ DEBUG - Item sem correspondência, pulando...")
        
        return {
            "sucesso": True,
            "itens_salvos": itens_salvos,
            "total_processados": len(dados_processados)
        }
        
    except Exception as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "itens_salvos": 0,
            "total_processados": 0
        }

# Callback para buscar itens faturados
@app.callback(
    [Output('tabela-pedidos-container', 'children'),
     Output('alert-status-integracao', 'children'),
     Output('alert-status-integracao', 'color'),
     Output('logs-integracao', 'children'),
     Output('btn-salvar-banco', 'disabled'),
     Output('botao-salvar-container', 'style'),
     Output('store-dados-tabela', 'data')],
    Input('btn-puxar-itens-faturados', 'n_clicks'),
    prevent_initial_call=True
)
def buscar_itens_faturados(n_clicks):
    if not n_clicks:
        return [], "Nenhuma operação realizada ainda.", "info", [], True, {'display': 'none'}, None
    
    # Log de início
    log_inicio = f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando busca de itens faturados (pedidos)..."
    logs = [html.P(log_inicio)]
    
    try:
        # Testar APIs primeiro
        logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] Testando APIs..."))
        
        # Testar API de pedidos
        try:
            response_pedidos = requests.get(PEDIDOS_API_URL, timeout=10)
            if response_pedidos.status_code == 200:
                dados_pedidos = response_pedidos.json()
                if isinstance(dados_pedidos, list):
                    logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ API Pedidos OK: {len(dados_pedidos)} itens", style={'color': 'green'}))
                else:
                    logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ API Pedidos retornou: {type(dados_pedidos)}", style={'color': 'orange'}))
            else:
                logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ API Pedidos erro: {response_pedidos.status_code}", style={'color': 'red'}))
        except Exception as e:
            logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ API Pedidos falhou: {str(e)}", style={'color': 'red'}))
        
        # Testar API de programação
        try:
            response_prog = requests.get(PROGRAMACAO_FATURAMENTO_API_URL, timeout=10)
            if response_prog.status_code == 200:
                dados_prog = response_prog.json()
                if isinstance(dados_prog, list):
                    logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ API Programação OK: {len(dados_prog)} itens", style={'color': 'green'}))
                else:
                    logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ API Programação retornou: {type(dados_prog)}", style={'color': 'orange'}))
            else:
                logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ API Programação erro: {response_prog.status_code}", style={'color': 'red'}))
        except Exception as e:
            logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ API Programação falhou: {str(e)}", style={'color': 'red'}))
        
        # Processar dados de pedidos
        logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] Processando dados..."))
        
        # Testar processamento passo a passo
        try:
            # Testar API de pedidos
            response_pedidos = requests.get(PEDIDOS_API_URL, timeout=10)
            dados_pedidos = response_pedidos.json()
            
            # Verificar situações dos pedidos
            situacoes = {}
            for pedido in dados_pedidos:
                situacao = pedido.get("Situacao", "")
                situacoes[situacao] = situacoes.get(situacao, 0) + 1
            
            logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Situações encontradas: {dict(list(situacoes.items())[:10])}", style={'color': 'blue'}))
            
            # Verificar quantos pedidos têm situações permitidas
            situacoes_permitidas = ["Pronto para faturar", "Aberto", "Fechado"]
            pedidos_validos = sum(situacoes.get(sit, 0) for sit in situacoes_permitidas)
            logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Pedidos com situações permitidas: {pedidos_validos} de {len(dados_pedidos)}", style={'color': 'blue'}))
            
        except Exception as e:
            logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erro ao analisar pedidos: {str(e)}", style={'color': 'red'}))
        
        # Testar correspondência entre programação e pedidos
        try:
            response_prog = requests.get(PROGRAMACAO_FATURAMENTO_API_URL, timeout=10)
            dados_prog = response_prog.json()
            
            # Verificar quantos itens de programação têm pedidos correspondentes
            pedidos_ids = set(pedido.get("ID_Pedido") for pedido in dados_pedidos)
            itens_com_pedido = 0
            itens_sem_pedido = 0
            
            for item in dados_prog:
                pedido_id = item.get("Pedido")
                if pedido_id in pedidos_ids:
                    itens_com_pedido += 1
                else:
                    itens_sem_pedido += 1
            
            logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Itens com pedido correspondente: {itens_com_pedido} de {len(dados_prog)}", style={'color': 'blue'}))
            logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Itens sem pedido correspondente: {itens_sem_pedido}", style={'color': 'blue'}))
            
            # Verificar quantos itens têm pedidos com situações permitidas
            pedidos_validos_ids = set()
            for pedido in dados_pedidos:
                situacao = pedido.get("Situacao", "")
                if situacao in situacoes_permitidas:
                    pedidos_validos_ids.add(pedido.get("ID_Pedido"))
            
            itens_com_pedido_valido = 0
            for item in dados_prog:
                pedido_id = item.get("Pedido")
                if pedido_id in pedidos_validos_ids:
                    itens_com_pedido_valido += 1
            
            logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Itens com pedido válido (situação permitida): {itens_com_pedido_valido} de {len(dados_prog)}", style={'color': 'blue'}))
            
        except Exception as e:
            logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erro ao analisar correspondência: {str(e)}", style={'color': 'red'}))
        
        resultado = processar_dados_itens_faturados()
        
        if "erro" in resultado:
            log_erro = f"[{datetime.now().strftime('%H:%M:%S')}] ERRO: {resultado['erro']}"
            logs.append(html.P(log_erro, style={'color': 'red'}))
            return [], f"Erro ao buscar itens faturados: {resultado['erro']}", "danger", logs, True, {'display': 'none'}
        
        dados = resultado["dados"]
        total = resultado["total"]
        
        print(f"🔍 Dados recebidos do processamento: {len(dados)}")
        print(f"🔍 Total informado: {total}")
        
        # Ordenar dados: primeiro os manuais, depois os automáticos
        dados_ordenados = ordenar_dados_por_mapeamento(dados)
        
        print(f"🔍 Dados ordenados: {len(dados_ordenados)}")
        
        # Criar tabela
        if dados_ordenados:
            # Criar colunas da tabela
            colunas = [
                {"name": "Descrição do Item", "id": "Descrição do Item"},
                {"name": "Data de Entrega", "id": "Data de Entrega"},
                {"name": "Data de Início", "id": "Data de Início"},
                {"name": "Valor de Faturamento", "id": "Valor de Faturamento"},
                {"name": "Situação", "id": "Situação"},
                {"name": "Tipo de Frete", "id": "Tipo de Frete"},
                {"name": "ID do Pedido", "id": "ID do Pedido"},
                {"name": "Quantidade", "id": "Quantidade"},
                {"name": "Código do Produto", "id": "Código do Produto"},
                {"name": "Produto Correspondente", "id": "Produto Correspondente"},
                {"name": "Status Mapeamento", "id": "Status Mapeamento"}
            ]
            
            # Adicionar coluna de ações para mapeamento manual
            colunas.append({"name": "Ações", "id": "acoes"})
            
            # Adicionar indicadores de ação para itens que precisam de mapeamento manual
            for item in dados_ordenados:
                if "❌ Manual" in item.get("Status Mapeamento", ""):
                    item["acoes"] = f"🔗 Clique na linha para mapear (ID: {item.get('ID do Pedido', 'N/A')})"
                else:
                    item["acoes"] = "✅ Mapeado"
            
            # Formatar valores monetários
            for item in dados_ordenados:
                if item["Valor de Faturamento"]:
                    try:
                        valor = float(item["Valor de Faturamento"])
                        item["Valor de Faturamento"] = f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                    except:
                        pass
            
            # Verificar se há itens sem correspondência
            itens_sem_correspondencia = resultado.get("itens_sem_correspondencia", [])
            alerta_correspondencia = ""
            if itens_sem_correspondencia:
                alerta_correspondencia = dbc.Alert(
                    f"⚠️ {len(itens_sem_correspondencia)} itens sem correspondência automática encontrados. "
                    "Clique em uma linha da tabela para mapear manualmente. "
                    f"📋 Itens manuais aparecem primeiro na tabela.",
                    color="warning",
                    className="mb-3"
                )
            
            tabela = dbc.Card([
                dbc.CardHeader([
                    html.H5(f"Pedidos em Aberto Encontrados: {total}", className="mb-0"),
                    html.Small("Filtrado por: Situação = Pronto para faturar, Aberto, Fechado (exceto Faturamento solicitado) | Ordenado: Manuais primeiro", className="text-muted")
                ]),
                dbc.CardBody([
                    alerta_correspondencia,
                    dash_table.DataTable(
                        id='tabela-itens-faturados',
                        columns=colunas,
                        data=dados_ordenados,
                        style_table={'height': '600px', 'overflowY': 'auto'},
                        page_size=50,
                        sort_action="native",
                        sort_mode="multi",
                        style_header={
                            'backgroundColor': '#28a745', 
                            'fontWeight': 'bold', 
                            'textAlign': 'center', 
                            'padding': '8px',
                            'color': 'white',
                            'fontSize': '12px'
                        },
                        style_cell={
                            'textAlign': 'left', 
                            'padding': '6px', 
                            'fontSize': '11px', 
                            'border': '1px solid #ddd',
                            'whiteSpace': 'normal',
                            'height': 'auto',
                            'cursor': 'pointer'
                        },
                        style_data_conditional=[
                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                            {'if': {'filter_query': '{Status Mapeamento} contains "❌ Manual"'}, 'backgroundColor': 'rgba(220, 53, 69, 0.2)'},
                            {'if': {'filter_query': '{Status Mapeamento} contains "✅ Automático"'}, 'backgroundColor': 'rgba(40, 167, 69, 0.2)'},
                            {'if': {'filter_query': '{acoes} contains "🔗 Clique na linha para mapear"'}, 'backgroundColor': 'rgba(255, 193, 7, 0.3)', 'fontWeight': 'bold'}
                        ]
                    )
                ])
            ])
            
            log_sucesso = f"[{datetime.now().strftime('%H:%M:%S')}] Sucesso: {total} pedidos em aberto carregados (ordenados: manuais primeiro)"
            logs.append(html.P(log_sucesso, style={'color': 'green'}))
            
            # Armazenar dados processados para uso posterior (salvamento no banco)
            # Os dados ficam disponíveis na tabela para o callback de salvamento
            
            return tabela, f"✅ {total} pedidos em aberto carregados com sucesso!", "success", logs, False, {'display': 'block'}, dados_ordenados
        else:
            logs.append(html.P(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Nenhum dado encontrado.", style={'color': 'orange'}))
            return [], "Nenhum pedido em aberto encontrado com os critérios especificados.", "warning", logs, True, {'display': 'none'}, None
            
    except Exception as e:
        log_erro = f"[{datetime.now().strftime('%H:%M:%S')}] ERRO: {str(e)}"
        logs.append(html.P(log_erro, style={'color': 'red'}))
        return [], f"Erro inesperado: {str(e)}", "danger", logs, True, {'display': 'none'}, None

# Callback para abrir modal de seleção de produtos
@app.callback(
    [Output('modal-selecao-produto', 'is_open'),
     Output('descricao-item-modal', 'children'),
     Output('lista-produtos-modal', 'children')],
    [Input('fechar-modal-produto', 'n_clicks'),
     Input('fechar-modal-produto-footer', 'n_clicks')],
    [State('modal-selecao-produto', 'is_open')],
    prevent_initial_call=True
)
def abrir_modal_selecao_produto(n_clicks_fechar, n_clicks_fechar_footer, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return is_open, "", []
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id in ['fechar-modal-produto', 'fechar-modal-produto-footer']:
        return False, no_update, no_update
    
    return is_open, no_update, no_update

# Callback para abrir modal de mapeamento via cliques nas linhas das tabelas
@app.callback(
    [Output('modal-selecao-produto', 'is_open', allow_duplicate=True),
     Output('descricao-item-modal', 'children', allow_duplicate=True),
     Output('lista-produtos-modal', 'children', allow_duplicate=True)],
    [Input('fechar-modal-produto', 'n_clicks'),
     Input('fechar-modal-produto-footer', 'n_clicks')],
    [State('modal-selecao-produto', 'is_open')],
    prevent_initial_call=True
)
def abrir_modal_mapeamento_clique_tabela(n_clicks_fechar, n_clicks_fechar_footer, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return is_open, no_update, no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id in ['fechar-modal-produto', 'fechar-modal-produto-footer']:
        return False, no_update, no_update
    
    return is_open, no_update, no_update

# Callback unificado para mapeamento via cliques em qualquer tabela
@app.callback(
    [Output('modal-selecao-produto', 'is_open', allow_duplicate=True),
     Output('descricao-item-modal', 'children', allow_duplicate=True),
     Output('lista-produtos-modal', 'children', allow_duplicate=True),
     Output('store-item-mapeamento', 'data')],
    [Input('tabela-itens-faturados', 'selected_cells')],
    [State('tabela-itens-faturados', 'data'),
     State('tabela-itens-faturados', 'page_current')],
    prevent_initial_call=True
)
def abrir_modal_mapeamento_unificado(selected_cells_pedidos, data_pedidos, page_current):
    ctx = callback_context
    if not ctx.triggered:
        return False, "", [], None
    
    try:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'tabela-itens-faturados' and selected_cells_pedidos and data_pedidos:
            # selected_cells é uma lista, pegamos o primeiro item
            if len(selected_cells_pedidos) > 0:
                selected_cell = selected_cells_pedidos[0]
                row_index = selected_cell['row']
            else:
                return False, no_update, no_update, None
            
            # Calcular o índice global considerando a paginação (igual ao seu código)
            page_size = 50  # Mesmo page_size da tabela
            if page_current is None:
                page_current = 0
            row_index_global = page_current * page_size + row_index
            
            # Verificar se o índice global está dentro do range dos dados
            if row_index_global < len(data_pedidos):
                row_data = data_pedidos[row_index_global]
                print(f"🔍 DEBUG - Modal: Página {page_current}, linha {row_index}, índice global {row_index_global}")
                print(f"🔍 DEBUG - Modal: Status Mapeamento: {row_data.get('Status Mapeamento', '')}")
                
                # Verificar se o item precisa de mapeamento manual
                if "❌ Manual" in row_data.get("Status Mapeamento", ""):
                    # Determinar a chave correta para descrição baseado no tipo de dados
                    if "Descrição" in row_data:
                        descricao_item = row_data.get("Descrição", "")
                        id_identificador = row_data.get("Numero_NFE", "")
                    else:
                        descricao_item = row_data.get("Descrição do Item", "")
                        id_identificador = row_data.get("ID do Pedido", "")
                    
                    # Salvar informações do item sendo mapeado
                    item_info = {
                        'row_index': row_index_global,  # Usar índice global
                        'descricao': descricao_item,
                        'id_pedido': id_identificador,
                        'row_data': row_data
                    }
                    print(f"✅ DEBUG - Modal: Abrindo modal para item: {descricao_item[:50]}...")
                    return True, descricao_item, criar_lista_produtos_modal(), item_info
            else:
                print(f"❌ DEBUG - Modal: Índice global {row_index_global} fora do range dos dados ({len(data_pedidos)})")
                return False, no_update, no_update, None
        
        return False, no_update, no_update, None
        
    except Exception as e:
        print(f"Erro ao abrir modal de mapeamento unificado: {e}")
        return False, no_update, no_update, None



def criar_lista_produtos_modal():
    """Função auxiliar para criar a lista de produtos no modal"""
    try:
        # Buscar produtos disponíveis
        banco = Banco()
        df_produtos = banco.ler_tabela("produtos")
        
        # Criar lista de produtos para seleção
        opcoes_produtos = []
        for _, produto in df_produtos.iterrows():
            opcoes_produtos.append({
                'label': f"{produto['produto_id']} - {produto['nome']}",
                'value': produto['produto_id']
            })
        
        # Criar dropdown de seleção
        dropdown_produtos = dcc.Dropdown(
            id='dropdown-selecao-produto',
            options=opcoes_produtos,
            placeholder="Selecione o produto correspondente...",
            className="mb-3"
        )
        
        # Criar lista de produtos
        lista_produtos = html.Div([
            html.P("Selecione o produto correspondente:", className="mb-2"),
            dropdown_produtos,
            html.Div(id="produto-selecionado-info", className="mt-3")
        ])
        
        return lista_produtos
        
    except Exception as e:
        return html.P(f"Erro ao carregar produtos: {str(e)}", className="text-danger")

# Callback para mostrar informações do produto selecionado
@app.callback(
    Output('produto-selecionado-info', 'children'),
    Output('confirmar-selecao-produto', 'disabled'),
    Input('dropdown-selecao-produto', 'value'),
    prevent_initial_call=True
)
def mostrar_info_produto_selecionado(produto_id):
    if not produto_id:
        return "", True
    
    try:
        banco = Banco()
        df_produtos = banco.ler_tabela("produtos")
        produto = df_produtos[df_produtos['produto_id'] == produto_id].iloc[0]
        
        info_produto = html.Div([
            html.H6("Produto Selecionado:", className="text-success"),
            html.P(f"ID: {produto['produto_id']}", className="mb-1"),
            html.P(f"Nome: {produto['nome']}", className="mb-1"),
            html.P(f"Tipo de Trabalho: {produto.get('tipo_trabalho', 'N/A')}", className="mb-1"),
            html.P(f"Fluxo de Produção: {produto.get('fluxo_producao', 'N/A')}", className="mb-0")
        ])
        
        return info_produto, False
        
    except Exception as e:
        return html.P(f"Erro ao carregar informações do produto: {str(e)}", className="text-danger"), True

# Callback para confirmar seleção e atualizar tabela
@app.callback(
    [Output('modal-selecao-produto', 'is_open', allow_duplicate=True),
     Output('tabela-pedidos-container', 'children', allow_duplicate=True),
     Output('btn-salvar-banco', 'disabled', allow_duplicate=True),
     Output('botao-salvar-container', 'style', allow_duplicate=True),
     Output('store-dados-tabela', 'data', allow_duplicate=True)],
    Input('confirmar-selecao-produto', 'n_clicks'),
    [State('dropdown-selecao-produto', 'value'),
     State('store-dados-tabela', 'data'),
     State('store-item-mapeamento', 'data')],
    prevent_initial_call=True
)
def confirmar_selecao_produto(n_clicks, produto_id, table_data_pedidos, item_mapeamento):
    print(f"🔍 DEBUG - confirmar_selecao_produto chamado:")
    print(f"   n_clicks: {n_clicks}")
    print(f"   produto_id: {produto_id}")
    print(f"   table_data_pedidos: {len(table_data_pedidos) if table_data_pedidos else 'None'}")
    print(f"   item_mapeamento: {item_mapeamento}")
    
    if not n_clicks or not produto_id or not item_mapeamento:
        print("❌ DEBUG - Condição de saída ativada")
        return False, no_update, True, {'display': 'none'}, no_update
    
    try:
        print("✅ DEBUG - Iniciando processamento...")
        # Buscar nome do produto selecionado
        banco = Banco()
        df_produtos = banco.ler_tabela("produtos")
        produto = df_produtos[df_produtos['produto_id'] == produto_id].iloc[0]
        nome_produto = produto['nome']
        
        # Atualizar tabela de pedidos
        if table_data_pedidos and len(table_data_pedidos) > 0:
            print(f"✅ DEBUG - Dados da tabela encontrados: {len(table_data_pedidos)} itens")
            
            # Usar informações do item sendo mapeado para encontrar o item correto
            row_index = item_mapeamento.get('row_index', -1)
            id_pedido = item_mapeamento.get('id_pedido', '')
            
            print(f"🔍 DEBUG - Procurando item:")
            print(f"   row_index: {row_index}")
            print(f"   id_pedido: {id_pedido}")
            
            # Encontrar o item específico usando o índice ou ID do pedido
            item_atualizado = False
            for i, item in enumerate(table_data_pedidos):
                print(f"🔍 DEBUG - Verificando item {i}: {item.get('Descrição do Item', '')[:50]}...")
                print(f"🔍 DEBUG - Comparando: i={i} vs row_index={row_index}, ID={item.get('ID do Pedido', '')} vs id_pedido={id_pedido}")
                
                # Verificar se é o item correto usando índice OU ID do pedido
                if i == row_index:
                    print(f"✅ DEBUG - Item encontrado por índice! Atualizando...")
                    item['Produto Correspondente'] = nome_produto
                    item['Produto ID'] = produto_id
                    item['Status Mapeamento'] = "✅ Manual"
                    item_atualizado = True
                    print(f"✅ Item atualizado: {item.get('Descrição do Item', '')} -> {nome_produto}")
                    break
                elif str(item.get("ID do Pedido", "")) == str(id_pedido):
                    print(f"✅ DEBUG - Item encontrado por ID do pedido! Atualizando...")
                    item['Produto Correspondente'] = nome_produto
                    item['Produto ID'] = produto_id
                    item['Status Mapeamento'] = "✅ Manual"
                    item_atualizado = True
                    print(f"✅ Item atualizado: {item.get('Descrição do Item', '')} -> {nome_produto}")
                    break
            
            if not item_atualizado:
                print("❌ DEBUG - Nenhum item foi atualizado!")
            
            # Recriar tabela com dados atualizados
            if table_data_pedidos and len(table_data_pedidos) > 0:
                print(f"✅ DEBUG - Recriando tabela com {len(table_data_pedidos)} itens")
                
                # Determinar colunas baseado no tipo de dados
                # Verificar se são dados NFE ou pedidos baseado nas chaves
                primeiro_item = table_data_pedidos[0]
                if "Numero_NFE" in primeiro_item:
                    # Dados NFE
                    colunas = [
                        {"name": "Descrição", "id": "Descrição"},
                        {"name": "Quantidade", "id": "Quantidade"},
                        {"name": "Numero_NFE", "id": "Numero_NFE"},
                        {"name": "Data_Emissao", "id": "Data_Emissao"},
                        {"name": "Cliente", "id": "Cliente"},
                        {"name": "Valor_Total", "id": "Valor_Total"},
                        {"name": "Produto Correspondente", "id": "Produto Correspondente"},
                        {"name": "Status Mapeamento", "id": "Status Mapeamento"},
                        {"name": "Ações", "id": "acoes"}
                    ]
                    titulo = f"Itens Faturados NFE Encontrados: {len(table_data_pedidos)}"
                    subtitulo = "Filtrado por: NFEs de ontem e hoje | Evita duplicatas | Ordenado: NFEs com manuais primeiro, agrupadas por NFE"
                else:
                    # Dados de pedidos
                    colunas = [
                        {"name": "Descrição do Item", "id": "Descrição do Item"},
                        {"name": "Data de Entrega", "id": "Data de Entrega"},
                        {"name": "Data de Início", "id": "Data de Início"},
                        {"name": "Valor de Faturamento", "id": "Valor de Faturamento"},
                        {"name": "Situação", "id": "Situação"},
                        {"name": "Tipo de Frete", "id": "Tipo de Frete"},
                        {"name": "ID do Pedido", "id": "ID do Pedido"},
                        {"name": "Quantidade", "id": "Quantidade"},
                        {"name": "Código do Produto", "id": "Código do Produto"},
                        {"name": "Produto Correspondente", "id": "Produto Correspondente"},
                        {"name": "Status Mapeamento", "id": "Status Mapeamento"},
                        {"name": "Ações", "id": "acoes"}
                    ]
                    titulo = f"Pedidos em Aberto Encontrados: {len(table_data_pedidos)}"
                    subtitulo = "Filtrado por: Situação = Pronto para faturar, Aberto, Fechado (exceto Faturamento solicitado) | Ordenado: Manuais primeiro"
            
            # Atualizar ações
            for item in table_data_pedidos:
                if "❌ Manual" in item.get("Status Mapeamento", ""):
                    if "Numero_NFE" in item:
                        # Dados NFE
                        item["acoes"] = f"🔗 Clique na linha para mapear (NFE: {item.get('Numero_NFE', 'N/A')})"
                    else:
                        # Dados de pedidos
                        item["acoes"] = f"🔗 Clique na linha para mapear (ID: {item.get('ID do Pedido', 'N/A')})"
                else:
                    item["acoes"] = "✅ Mapeado"
            
            print(f"✅ DEBUG - Recriando tabela com {len(table_data_pedidos)} itens")
            print(f"✅ DEBUG - Colunas: {[col['name'] for col in colunas]}")
            
            tabela_atualizada = dbc.Card([
                dbc.CardHeader([
                    html.H5(titulo, className="mb-0"),
                    html.Small(subtitulo, className="text-muted")
                ]),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='tabela-itens-faturados',
                        columns=colunas,
                        data=table_data_pedidos,
                        style_table={'height': '600px', 'overflowY': 'auto'},
                        page_size=50,
                        sort_action="native",
                        sort_mode="multi",
                        style_header={
                            'backgroundColor': '#28a745', 
                            'fontWeight': 'bold', 
                            'textAlign': 'center', 
                            'padding': '8px',
                            'color': 'white',
                            'fontSize': '12px'
                        },
                        style_cell={
                            'textAlign': 'left', 
                            'padding': '6px', 
                            'fontSize': '11px', 
                            'border': '1px solid #ddd',
                            'whiteSpace': 'normal',
                            'height': 'auto',
                            'cursor': 'pointer'
                        },
                        style_data_conditional=[
                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                            {'if': {'filter_query': '{Status Mapeamento} contains "❌ Manual"'}, 'backgroundColor': 'rgba(220, 53, 69, 0.2)'},
                            {'if': {'filter_query': '{Status Mapeamento} contains "✅ Automático"'}, 'backgroundColor': 'rgba(40, 167, 69, 0.2)'},
                            {'if': {'filter_query': '{acoes} contains "🔗 Clique na linha para mapear"'}, 'backgroundColor': 'rgba(255, 193, 7, 0.3)', 'fontWeight': 'bold'}
                        ]
                    )
                ])
            ])
            
            return False, tabela_atualizada, False, {'display': 'block'}, table_data_pedidos  # Habilitar botão salvar e mostrar
        
        return False, no_update, True, {'display': 'none'}, no_update  # Manter botão desabilitado e ocultar
        
    except Exception as e:
        return False, no_update, True, {'display': 'none'}, no_update  # Manter botão desabilitado e ocultar

# Callback para salvar dados no banco
@app.callback(
    [Output('alert-status-integracao', 'children', allow_duplicate=True),
     Output('alert-status-integracao', 'color', allow_duplicate=True),
     Output('logs-integracao', 'children', allow_duplicate=True),
     Output('tabela-pedidos-container', 'children', allow_duplicate=True),
     Output('btn-salvar-banco', 'disabled', allow_duplicate=True),
     Output('botao-salvar-container', 'style', allow_duplicate=True),
     Output('store-dados-tabela', 'data', allow_duplicate=True),
     Output('store-item-mapeamento', 'data', allow_duplicate=True),
     Output('modal-selecao-produto', 'is_open', allow_duplicate=True)],
    Input('btn-salvar-banco', 'n_clicks'),
    [State('store-dados-tabela', 'data')],
    prevent_initial_call=True
)
def salvar_dados_no_banco(n_clicks, table_data_pedidos):
    if not n_clicks:
        return ("Nenhuma operação realizada.", "info", [], 
                [], True, {'display': 'none'}, None, None, False)
    
    # Log de início
    log_inicio = f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando salvamento no banco..."
    
    try:
        # Verificar se há dados para salvar
        if table_data_pedidos and len(table_data_pedidos) > 0:
            # Determinar tipo de dados baseado nas chaves do primeiro item
            primeiro_item = table_data_pedidos[0]
            if "Numero_NFE" in primeiro_item:
                # Dados NFE - salvar na tabela saida_notas
                print(f"🔍 DEBUG - Salvando dados NFE na tabela saida_notas")
                resultado = salvar_nfe_itens_faturados_no_banco(table_data_pedidos)
                tipo_dados = "itens faturados NFE"
            else:
                # Dados de pedidos - salvar na tabela pedidos_em_aberto
                print(f"🔍 DEBUG - Salvando dados de pedidos na tabela pedidos_em_aberto")
                resultado = salvar_pedidos_em_aberto_no_banco(table_data_pedidos)
                tipo_dados = "pedidos em aberto"
        else:
            return ("⚠️ Nenhum dado disponível para salvar", "warning", [],
                    [], True, {'display': 'none'}, None, None, False)
        
        if resultado["sucesso"]:
            itens_salvos = resultado["itens_salvos"]
            total_processados = resultado["total_processados"]
            
            log_sucesso = f"[{datetime.now().strftime('%H:%M:%S')}] Sucesso: {itens_salvos} {tipo_dados} salvos no banco de {total_processados} processados"
            
            mensagem = f"✅ {itens_salvos} {tipo_dados} salvos com sucesso no banco! (de {total_processados} processados)"
            cor = "success"
            
            # Limpar tudo após salvamento bem-sucedido
            return (mensagem, cor, [html.P(log_inicio), html.P(log_sucesso, style={'color': 'green'})],
                    [], True, {'display': 'none'}, None, None, False)
        else:
            log_erro = f"[{datetime.now().strftime('%H:%M:%S')}] ERRO: {resultado['erro']}"
            return (f"❌ Erro ao salvar no banco: {resultado['erro']}", "danger", 
                    [html.P(log_inicio), html.P(log_erro, style={'color': 'red'})],
                    [], True, {'display': 'none'}, None, None, False)
            
    except Exception as e:
        log_erro = f"[{datetime.now().strftime('%H:%M:%S')}] ERRO: {str(e)}"
        return (f"❌ Erro inesperado: {str(e)}", "danger", 
                [html.P(log_inicio), html.P(log_erro, style={'color': 'red'})],
                [], True, {'display': 'none'}, None, None, False)

# Callback para o botão NFE
@app.callback(
    [Output('tabela-pedidos-container', 'children', allow_duplicate=True),
     Output('alert-status-integracao', 'children', allow_duplicate=True),
     Output('alert-status-integracao', 'color', allow_duplicate=True),
     Output('logs-integracao', 'children', allow_duplicate=True),
     Output('btn-salvar-banco', 'disabled', allow_duplicate=True),
     Output('botao-salvar-container', 'style', allow_duplicate=True),
     Output('store-dados-tabela', 'data', allow_duplicate=True)],
    Input('btn-puxar-itens-faturados-nfe', 'n_clicks'),
    prevent_initial_call=True
)
def buscar_itens_faturados_nfe(n_clicks):
    if not n_clicks:
        return [], "Nenhuma operação realizada ainda.", "info", [], True, {'display': 'none'}, None
    
    # Log de início
    log_inicio = f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando busca de itens faturados NFE..."
    
    try:
        # Processar dados de NFE
        resultado = processar_dados_nfe_itens_faturados()
        
        if "erro" in resultado:
            log_erro = f"[{datetime.now().strftime('%H:%M:%S')}] ERRO: {resultado['erro']}"
            return [], f"Erro ao buscar itens faturados NFE: {resultado['erro']}", "danger", [html.P(log_inicio), html.P(log_erro, style={'color': 'red'})], True, {'display': 'none'}
        
        # Criar tabela com dados de NFE
        if resultado["dados"]:
            print(f"🔍 Dados NFE recebidos do processamento: {len(resultado['dados'])}")
            print(f"🔍 Total NFE informado: {resultado['total']}")
            
            # Ordenar dados: primeiro os manuais, depois os automáticos
            dados_ordenados = ordenar_dados_por_mapeamento(resultado["dados"])
            
            print(f"🔍 Dados NFE ordenados: {len(dados_ordenados)}")
            
            # Criar tabela
            colunas = [
                {"name": "Descrição", "id": "Descrição"},
                {"name": "Quantidade", "id": "Quantidade"},
                {"name": "Numero_NFE", "id": "Numero_NFE"},
                {"name": "Data_Emissao", "id": "Data_Emissao"},
                {"name": "Cliente", "id": "Cliente"},
                {"name": "Valor_Total", "id": "Valor_Total"},
                {"name": "Produto Correspondente", "id": "Produto Correspondente"},
                {"name": "Status Mapeamento", "id": "Status Mapeamento"}
            ]
            
            # Adicionar coluna de ações para mapeamento manual
            colunas.append({"name": "Ações", "id": "acoes"})
            
            # Adicionar indicadores de ação para itens que precisam de mapeamento manual
            for item in dados_ordenados:
                if "❌ Manual" in item.get("Status Mapeamento", ""):
                    item["acoes"] = f"🔗 Clique na linha para mapear (NFE: {item.get('Numero_NFE', 'N/A')})"
                else:
                    item["acoes"] = "✅ Mapeado"
            
            # Formatar valores monetários
            for item in dados_ordenados:
                if item["Valor_Total"]:
                    try:
                        valor = float(item["Valor_Total"])
                        item["Valor_Total"] = f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                    except:
                        pass
            
            # Verificar se há itens sem correspondência
            itens_sem_correspondencia = resultado.get("itens_sem_correspondencia", [])
            alerta_correspondencia = ""
            if itens_sem_correspondencia:
                alerta_correspondencia = dbc.Alert(
                    f"⚠️ {len(itens_sem_correspondencia)} itens sem correspondência automática encontrados. "
                    "Clique em uma linha da tabela para mapear manualmente. "
                    f"📋 Itens manuais aparecem primeiro na tabela.",
                    color="warning",
                    className="mb-3"
                )
            
            tabela = dbc.Card([
                dbc.CardHeader([
                    html.H5(f"Itens Faturados NFE Encontrados: {resultado['total']}", className="mb-0"),
                                         html.Small("Filtrado por: NFEs de ontem e hoje | Evita duplicatas | Ordenado: NFEs com manuais primeiro, agrupadas por NFE", className="text-muted")
                ]),
                dbc.CardBody([
                    alerta_correspondencia,
                    dash_table.DataTable(
                        id='tabela-itens-faturados',
                        columns=colunas,
                        data=dados_ordenados,
                        style_table={'height': '600px', 'overflowY': 'auto'},
                        page_size=50,
                        sort_action="native",
                        sort_mode="multi",
                        style_header={
                            'backgroundColor': '#28a745', 
                            'fontWeight': 'bold', 
                            'textAlign': 'center', 
                            'padding': '8px',
                            'color': 'white',
                            'fontSize': '12px'
                        },
                        style_cell={
                            'textAlign': 'left', 
                            'padding': '6px', 
                            'fontSize': '11px', 
                            'border': '1px solid #ddd',
                            'whiteSpace': 'normal',
                            'height': 'auto',
                            'cursor': 'pointer'
                        },
                        style_data_conditional=[
                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                            {'if': {'filter_query': '{Status Mapeamento} contains "❌ Manual"'}, 'backgroundColor': 'rgba(220, 53, 69, 0.2)'},
                            {'if': {'filter_query': '{Status Mapeamento} contains "✅ Automático"'}, 'backgroundColor': 'rgba(40, 167, 69, 0.2)'},
                            {'if': {'filter_query': '{acoes} contains "🔗 Clique na linha para mapear"'}, 'backgroundColor': 'rgba(255, 193, 7, 0.3)', 'fontWeight': 'bold'}
                        ]
                    )
                ])
            ])
            
            log_sucesso = f"[{datetime.now().strftime('%H:%M:%S')}] Sucesso: {resultado['total']} itens NFE carregados (ordenados: manuais primeiro)"
            
            # Mostrar botão de salvar
            return (
                tabela,
                f"✅ {resultado['total']} itens faturados NFE carregados com sucesso!",
                "success",
                [html.P(log_inicio), html.P(log_sucesso, style={'color': 'green'})],
                False,  # Habilitar botão
                {'display': 'block'},
                dados_ordenados  # Salvar dados no Store
            )
        else:
            return (
                [],
                "⚠️ Nenhum dado NFE encontrado.",
                "warning",
                [html.P(log_inicio), html.P("Nenhum dado encontrado.", style={'color': 'orange'})],
                True,
                {'display': 'none'},
                None
            )
            
    except Exception as e:
        log_erro = f"[{datetime.now().strftime('%H:%M:%S')}] ERRO: {str(e)}"
        return (
            [],
            f"❌ Erro ao buscar dados NFE: {str(e)}",
            "danger",
            [html.P(log_inicio), html.P(log_erro, style={'color': 'red'})],
            True,
            {'display': 'none'},
            None
        )
