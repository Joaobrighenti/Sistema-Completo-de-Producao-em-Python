from banco_dados.banco import *
from dash import dash_table
import pandas as pd
from dash import html
import dash_bootstrap_components as dbc


def gera_cabecalho_movimentacao():
    cabecalho =  dbc.Card(
        [
            dbc.Row(
        [
            dbc.Col("", style={'font-weight': 'bold', 'text-align': 'center', 'flex': '0 0 3%'}),  # Ajustado para 5%
            dbc.Col("", style={'font-weight': 'bold', 'text-align': 'center', 'flex': '0 0 3%'}),  # Ajustado para 5%
            dbc.Col("ID PCP", style={'font-weight': 'bold', 'text-align': 'center', 'flex': '0 0 5%'}),
            dbc.Col("OP", style={'font-weight': 'bold', 'text-align': 'center', 'flex': '0 0 5%'}),
            dbc.Col("PRODUTO", style={'font-weight': 'bold', 'text-align': 'center', 'flex': '0 0 25%'}),
            dbc.Col("CLIENTE", style={'font-weight': 'bold', 'text-align': 'center', 'flex': '0 0 15%'}),  # Ajustado para 15%
            dbc.Col("QTD", style={'font-weight': 'bold', 'text-align': 'center', 'flex': '0 0 7%'}), 
            dbc.Col("OBSERVAÇÃO", style={'font-weight': 'bold', 'text-align': 'center', 'flex': '0 0 30%'}),
            dbc.Col("DATA", style={'font-weight': 'bold', 'text-align': 'center', 'flex': '0 0 7%'}),
        ],
        style={'display': 'flex', 'justify-content': 'center', 'align-items': 'center', 'margin-bottom': '0px', 'flex-wrap': 'nowrap',
                'width': '100%'},
        className="mb-2"
    )
    ],
        style={ 'background': '#284447', 'color': 'white', 'margin-bottom': '0px', 'border': '1px solid black'}  # Borda preta apenas no card
    )
    return cabecalho

def gerar_cards_movimentacao(df,  cliente, pcp, produto, ano, semana, categoria):
    df = pd.DataFrame(df)

    df['data'] = pd.to_datetime(df['data'], errors='coerce')  # Converte para datetime
    


    if cliente:
        df = df[df['nome_cliente'] == cliente]

    if pcp:
        df = df[df['pcp_pcp'].astype(str).str.contains(str(pcp), na=False)]
    
    if produto:
        df = df[df['nome_produto'].astype(str).str.contains(str(produto), na=False)]

    df = df.sort_values(by='data', ascending=False)
    df['data'] = df['data'].dt.strftime('%d/%m/%Y') 
    df = df.head(50)

    tabela_vazia = html.Div(
            dash_table.DataTable(
                id='tabela_pcp_cal',  # Aqui está o id da tabela
                columns=[],  # Sem colunas
                data=[],     # Sem dados
                style_table={'display': 'none'}  # Escondido inicialmente
            )
        )
        

    cards = []
    for _, row in df.iterrows():
        card = gerar_card_movimentacao(row)
        cards.append(card)

    cards.append(tabela_vazia)
    return cards

def gerar_card_movimentacao(df):

    df['qtd'] = f"{int(df['qtd']):,}".replace(",", ".")
    card = dbc.Card(
    [
        dbc.Row(
            [
                # Botão Editar
                dbc.Col(
                    dbc.Button(
                        [html.I(className="fa fa-pencil fa-1x")],
                        style={'color': 'black', 'padding': '0px'},
                        size='xs',
                        outline=True,
                        id={'type': 'editar_movi', 'index': df['id_movi']}
                    ),
                    style={'flex': '0 0 3%', 'height': '35px', 'text-align': 'center', 'background': 'white', 'display': 'flex', 'justify-content': 'center', 'align-items': 'center'},
                ),
                # Botão Deletar
                dbc.Col(
                    dbc.Button(
                        [html.I(className="fa fa-trash fa-1x")],
                        style={'color': 'black', 'padding': '0px'},
                        size='xs',
                        outline=True,
                        id={'type': 'deletar_movi', 'index': df['id_movi']},
                    ),
                    style={'flex': '0 0 3%', 'height': '35px', 'text-align': 'center', 'background': 'white', 'display': 'flex', 'justify-content': 'center', 'align-items': 'center'},
                ),
                # Dados do POTE em colunas separadas
                dbc.Col(f"{df['pcp_id']}", style={'flex': '0 0 5%', 'height': '35px', 'text-align': 'center', 'background': 'white', 'display': 'flex', 'justify-content': 'center', 'align-items': 'center'}),
                dbc.Col(f"{df['pcp_pcp']}", style={'flex': '0 0 5%', 'height': '35px', 'text-align': 'center', 'background': 'white', 'display': 'flex', 'justify-content': 'center', 'align-items': 'center'}),
                dbc.Col(f"{df['nome_produto']}", style={'flex': '0 0 25%', 'height': '35px', 'text-align': 'center', 'background': 'white', 'display': 'flex', 'justify-content': 'center', 'align-items': 'center','fontWeight': 'bold'}),
                dbc.Col(f"{df['nome_cliente']}", style={'flex': '0 0 15%', 'height': '35px', 'text-align': 'center', 'background': 'white', 'display': 'flex', 'justify-content': 'center', 'align-items': 'center'}),
                dbc.Col(f"{df['qtd']}", style={'flex': '0 0 7%', 'height': '35px', 'text-align': 'center', 'background': '#8B008B', 'color':'white', 'display': 'flex', 'justify-content': 'center', 'align-items': 'center','fontWeight': 'bold'}),
                dbc.Col(f"{df['Observação']}", style={'flex': '0 0 30%', 'height': '35px', 'text-align': 'center', 'background': 'white', 'display': 'flex', 'justify-content': 'center', 'align-items': 'center'}),
                dbc.Col(f"{(df['data'])}", style={'flex': '0 0 7%', 'height': '35px', 'text-align': 'center', 'background': 'white', 'display': 'flex', 'justify-content': 'center', 'align-items': 'center'})
            ],
            style={
                'display': 'flex',
                'justify-content': 'center',
                'align-items': 'center',
                'margin-bottom': '0px',
                'flex-wrap': 'nowrap',  # Para garantir que as colunas não quebrem para uma nova linha
                'width': '100%'  # Isso ajuda a ocupar toda a largura disponível
            },
        ),
        # Tabela vazia adicionada dentro do card, mas invisíve
    ],
    style={'background': 'white', 'margin-bottom': '0px', 'border': '1px solid black'}  # Borda preta apenas no card
)
    return card