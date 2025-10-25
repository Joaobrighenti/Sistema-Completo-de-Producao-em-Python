from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from dash import dash_table
from app import app
from banco_dados.banco import Banco
import pandas as pd
import os
import base64
import uuid

ASSETS_QUALI_DIR = os.path.join('assets', 'qualidade')
os.makedirs(ASSETS_QUALI_DIR, exist_ok=True)

# Helpers

def _save_uploaded(content_string, filename):
	if not content_string:
		return None
	content_type, content_string = content_string.split(',')
	ext = os.path.splitext(filename or '')[1] or '.png'
	new_name = f"laudo_{uuid.uuid4().hex}{ext}"
	path = os.path.join(ASSETS_QUALI_DIR, new_name)
	with open(path, 'wb') as f:
		f.write(base64.b64decode(content_string))
	return os.path.join('qualidade', new_name)  # relative to assets root

# Layout
layout = dbc.Card([
	dbc.CardHeader(html.H5("Cadastro de Laudos (produto_espec)")),
	dbc.CardBody([
		# Controls
		dbc.Row([
			dbc.Col(dcc.Input(id='cadlaudo-busca', type='text', placeholder='Buscar por categoria/grupo...', className='form-control'), md=8),
			dbc.Col(dbc.Button('Novo Laudo', id='cadlaudo-novo', color='primary', className='w-100'), md=4)
		], className='mb-3'),

		# Table
		dash_table.DataTable(
			id='laudos-tabela',
			columns=[
				{"name": "ID", "id": "id"},
				{"name": "Categoria", "id": "categoria"},
				{"name": "Unid.", "id": "unidade_medida"},
				{"name": "Grupo", "id": "grupo"},
				{"name": "Imagem", "id": "medidas"},
				{"name": "Editar", "id": "_edit"},
				{"name": "Excluir", "id": "_del"}
			],
			data=[], page_size=10,
			style_table={'overflowX': 'auto'},
			style_cell={'textAlign': 'left', 'fontSize': 12},
			style_data_conditional=[
				{'if': {'column_id': '_edit'}, 'color': '#0d6efd', 'textDecoration': 'underline', 'cursor': 'pointer'},
				{'if': {'column_id': '_del'}, 'color': '#dc3545', 'textDecoration': 'underline', 'cursor': 'pointer'},
			]
		),

		# Hidden store to trigger reloads
		dcc.Store(id='laudos-refresh', data=0),

		# Modal
		dbc.Modal([
			dbc.ModalHeader(dbc.ModalTitle(id='laudo-modal-title')),
			dbc.ModalBody([
				dcc.Input(id='laudo-id', type='number', style={'display': 'none'}),
				dbc.Row([
					dbc.Col([dbc.Label('Categoria'), dcc.Input(id='laudo-categoria', type='text', className='form-control')], md=6),
					dbc.Col([dbc.Label('Unidade Medida'), dcc.Input(id='laudo-unidade', type='text', className='form-control')], md=6),
				]),
				dbc.Row([
					dbc.Col([dbc.Label('Grupo'), dcc.Input(id='laudo-grupo', type='text', className='form-control')], md=6),
					dbc.Col([dbc.Label('Imagem'), dcc.Upload(id='laudo-upload', children=html.Div(['Arraste ou ', html.A('selecione um arquivo')]), multiple=False, className='border p-2 w-100'), dcc.Input(id='laudo-imagem-path', type='text', placeholder='caminho', className='form-control mt-1')], md=6),
				]),
				dbc.Row([
					dbc.Col([dbc.Label('Substrato'), dcc.Textarea(id='laudo-substrato', className='form-control')], md=6),
					dbc.Col([dbc.Label('Acabamento'), dcc.Textarea(id='laudo-acabamento', className='form-control')], md=6),
				]),
				dbc.Row([
					dbc.Col([dbc.Label('Embalagem'), dcc.Textarea(id='laudo-embalagem', className='form-control')], md=6),
					dbc.Col([dbc.Label('Especificações'), dcc.Textarea(id='laudo-especificacoes', className='form-control')], md=6),
				]),
				dbc.Row([
					dbc.Col([dbc.Label('Info Adicional'), dcc.Textarea(id='laudo-info', className='form-control')], md=12),
				])
			]),
			dbc.ModalFooter([
				dbc.Button('Salvar', id='laudo-salvar', color='success'),
				dbc.Button('Cancelar', id='laudo-cancelar', className='ms-2')
			])
		], id='laudo-modal', is_open=False, size='xl')
	])
])

# Callbacks

@app.callback(
	Output('laudos-tabela', 'data'),
	Input('laudos-refresh', 'data'),
	Input('cadlaudo-busca', 'value')
)
def _load_table(_, busca):
	banco = Banco()
	df = banco.ler_tabela('produto_espec')
	if df.empty:
		return []
	# preview URL
	def fmt_img(p):
		return f"![img](/assets/{p})" if isinstance(p, str) and p else ''
	df['_edit'] = 'Editar'
	df['_del'] = 'Excluir'
	df['medidas'] = df['medidas'].apply(fmt_img)
	if busca:
		df = df[df[['categoria','grupo']].fillna('').apply(lambda r: busca.lower() in ' '.join(map(str,r)).lower(), axis=1)]
	return df.to_dict('records')

@app.callback(
	Output('laudos-refresh', 'data', allow_duplicate=True),
	Output('laudo-modal', 'is_open'),
	Output('laudo-modal-title', 'children'),
	Output('laudo-id', 'value'),
	Output('laudo-categoria', 'value'),
	Output('laudo-unidade', 'value'),
	Output('laudo-grupo', 'value'),
	Output('laudo-imagem-path', 'value'),
	Output('laudo-substrato', 'value'),
	Output('laudo-acabamento', 'value'),
	Output('laudo-embalagem', 'value'),
	Output('laudo-especificacoes', 'value'),
	Output('laudo-info', 'value'),
	Input('cadlaudo-novo', 'n_clicks'),
	Input('laudos-tabela', 'active_cell'),
	State('laudos-tabela', 'data'),
	State('laudo-modal', 'is_open'),
	State('laudos-refresh', 'data'),
	prevent_initial_call=True
)
def _open_modal(n_novo, active_cell, table_data, is_open, refresh):
	ctx = callback_context
	if not ctx.triggered:
		return refresh, is_open, '', None, None, None, None, None, None, None, None, None, None
	trigger = ctx.triggered[0]['prop_id'].split('.')[0]
	banco = Banco()
	if trigger == 'cadlaudo-novo':
		return refresh, True, 'Novo Laudo', None, '', '', '', '', '', '', '', '', ''
	if trigger == 'laudos-tabela' and active_cell:
		row = table_data[active_cell['row']]
		col = active_cell.get('column_id')
		if col == '_edit':
			return refresh, True, f"Editar Laudo #{row.get('id')}", row.get('id'), row.get('categoria'), row.get('unidade_medida'), row.get('grupo'), str(row.get('medidas','')).replace('![img](/assets/','').replace(')',''), row.get('substrato'), row.get('acabamento'), row.get('embalagem'), row.get('especificacoes'), row.get('info_adicional')
		if col == '_del':
			try:
				banco.deletar_dado('produto_espec', row.get('id'))
				return (refresh or 0) + 1, False, '', None, None, None, None, None, None, None, None, None, None
			except Exception:
				return refresh, is_open, '', None, None, None, None, None, None, None, None, None, None
	return refresh, is_open, '', None, None, None, None, None, None, None, None, None, None

@app.callback(
	Output('laudos-refresh', 'data'),
	Output('laudo-modal', 'is_open', allow_duplicate=True),
	Input('laudo-salvar', 'n_clicks'),
	Input('laudo-cancelar', 'n_clicks'),
	State('laudo-id', 'value'),
	State('laudo-categoria', 'value'),
	State('laudo-unidade', 'value'),
	State('laudo-grupo', 'value'),
	State('laudo-imagem-path', 'value'),
	State('laudo-substrato', 'value'),
	State('laudo-acabamento', 'value'),
	State('laudo-embalagem', 'value'),
	State('laudo-especificacoes', 'value'),
	State('laudo-info', 'value'),
	State('laudos-refresh', 'data'),
	prevent_initial_call=True
)
def _save_laudo(n_save, n_cancel, _id, categoria, unidade, grupo, imagem_path, substrato, acabamento, embalagem, especificacoes, info, refresh):
	ctx = callback_context
	if not ctx.triggered:
		return refresh, False
	trigger = ctx.triggered[0]['prop_id'].split('.')[0]
	if trigger == 'laudo-cancelar':
		return refresh, False
	banco = Banco()
	data = dict(
		categoria=categoria, unidade_medida=unidade, grupo=grupo, medidas=imagem_path,
		substrato=substrato, acabamento=acabamento, embalagem=embalagem,
		especificacoes=especificacoes, info_adicional=info
	)
	if _id:
		banco.editar_dado('produto_espec', _id, **data)
	else:
		banco.inserir_dados('produto_espec', **data)
	return (refresh or 0) + 1, False

@app.callback(
	Output('laudo-imagem-path', 'value', allow_duplicate=True),
	Input('laudo-upload', 'contents'),
	State('laudo-upload', 'filename'),
	prevent_initial_call=True
)
def _handle_upload(contents, filename):
	path = _save_uploaded(contents, filename) if contents else None
	return path or ''
