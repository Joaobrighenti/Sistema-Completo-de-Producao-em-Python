from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, Table, Text, MetaData, DateTime, Time, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column,relationship ,sessionmaker, Session
from pathlib import Path
from sqlalchemy import create_engine, func, text
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from datetime import datetime
import json

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(50), nullable=False)
    # Agora em JSON; valores antigos em string serão migrados para JSON válido (ex.: "admin" -> '"admin"')
    user_level = Column(JSON, nullable=True, default="user")
    
class PCP(Base):
    __tablename__ = 'pcp'

    pcp_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # ID único
    pcp_oc: Mapped[str] = mapped_column(String(15), nullable=True)  # Ordem de Compra
    pcp_pcp: Mapped[int] = mapped_column(Integer, nullable=True)  # Planejamento e Controle de Produção
    pcp_categoria: Mapped[str] = mapped_column(String(20), nullable=False)  # Categoria do produto
    pcp_cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.cliente_id"), nullable=False)  # Relacionamento com cliente
    pcp_produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.produto_id"), nullable=False)  # Referência ao ID do produto
    pcp_qtd: Mapped[int] = mapped_column(Integer, nullable=False)  # Quantidade planejada
    pcp_entrega: Mapped[Date] = mapped_column(Date, nullable=True)  # Data de entrega
    pcp_odc: Mapped[str] = mapped_column(String(50), nullable=True)  # Ordem de Carregamento
    pcp_observacao: Mapped[str] = mapped_column(String(255), nullable=True)  # Observações
    pcp_primiera_entrega: Mapped[Date] = mapped_column(Date, nullable=False)  # Primeira data de entrega
    pcp_emissao: Mapped[Date] = mapped_column(Date, nullable=False)  # Data de emissão
    pcp_cod_prod: Mapped[str] = mapped_column(String(50), nullable=True)  # Material
    pcp_imp: Mapped[str] = mapped_column(String(50), nullable=True)  # Impressão
    pcp_aca: Mapped[str] = mapped_column(String(50), nullable=True)  # Acabamento
    pcp_correncia: Mapped[int] = mapped_column(Integer, nullable=True)  # Nova coluna para ocorrência
    pcp_bopp: Mapped[int] = mapped_column(Integer, nullable=True)  # BOPP
    pcp_terceirizacao: Mapped[int] = mapped_column(Integer, nullable=True)  # Terceirização
    pcp_retrabalho: Mapped[int] = mapped_column(Integer, nullable=True)
    pcp_perdida_retrabalho: Mapped[int] = mapped_column(Integer, nullable=True)
    
    pcp_chapa_id: Mapped[str] = mapped_column(ForeignKey("chapa.ch_codigo"), nullable=True)  # Relacionamento com chapa
    pcp_faca_id: Mapped[int] = mapped_column(ForeignKey("faca.fac_id"), nullable=True) # Relacionamento com faca
    
    cliente: Mapped["CLIENTE"] = relationship("CLIENTE", back_populates="pcps")
    produto: Mapped["PRODUTO"] = relationship("PRODUTO", back_populates="pcps")
    chapa: Mapped["CHAPA"] = relationship("CHAPA", back_populates="pcps")  # Novo relacionamento com CHAPA
    faca: Mapped["FACA"] = relationship("FACA", back_populates="pcps") # Relacionamento com FACA
    baixas: Mapped[list["BAIXA"]] = relationship("BAIXA", back_populates="pcp")
    retiradas: Mapped[list["RETIRADA"]] = relationship("RETIRADA", back_populates="pcp")
    ordens_compra: Mapped[list["ORDEM_COMPRA"]] = relationship("ORDEM_COMPRA", back_populates="pcp")  # Relacionamento com ordens de compra
    apontamentos_produto: Mapped[list["APONTAMENTO_PRODUTO"]] = relationship("APONTAMENTO_PRODUTO", back_populates="pcp")
    apontamentos_retrabalho: Mapped[list["APONTAMENTO_RETRABALHO"]] = relationship("APONTAMENTO_RETRABALHO", back_populates="pcp")
    laudos: Mapped[list["LAUDOS"]]= relationship(
        "LAUDOS",
        back_populates="pcp",
        cascade="all, delete-orphan"
    )
class APONTAMENTO_RETRABALHO(Base):
    __tablename__ = 'apontamento_retrabalho'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pcp_id: Mapped[int] = mapped_column(ForeignKey("pcp.pcp_id"), nullable=False)
    quantidade_verificada: Mapped[int] = mapped_column(Integer, nullable=True)
    quantidade_nao_conforme: Mapped[int] = mapped_column(Integer, nullable=True)
    observacao: Mapped[str] = mapped_column(String(255), nullable=True)
    data_hora: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=True)

    pcp: Mapped["PCP"] = relationship("PCP", back_populates="apontamentos_retrabalho")

class INSPECAO_PROCESSO(Base):
    __tablename__ = 'inspecao_processo'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    setor_id: Mapped[int] = mapped_column(ForeignKey('setor.setor_id'), nullable=False)
    data: Mapped[Date] = mapped_column(Date, nullable=False)
    maquina_id: Mapped[int] = mapped_column(ForeignKey('maquina.maquina_id'), nullable=False)
    pcp_id: Mapped[int] = mapped_column(ForeignKey('pcp.pcp_id'), nullable=False)
    qtd_inspecionada: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_produto: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., Pote/Copo
    checklist: Mapped[dict] = mapped_column(JSON, nullable=True) # JSON column for checklist
    observacao: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    setor: Mapped["SETOR"] = relationship("SETOR")
    maquina: Mapped["MAQUINA"] = relationship("MAQUINA")
    pcp: Mapped["PCP"] = relationship("PCP")

class LEMBRETE(Base):
    __tablename__ = 'lembretes'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lembrete: Mapped[str] = mapped_column(String(255), nullable=False)  # Texto do lembrete
    data: Mapped[Date] = mapped_column(Date, nullable=False)  # Data do lembrete
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendente")  # Status: pendente, feito, cancelado

class PRODUTO(Base):
    __tablename__ = 'produtos'

    produto_id: Mapped[int] = mapped_column(primary_key=True)  # ID único
    nome: Mapped[str] = mapped_column(String(100), nullable=False)  # Nome do produto
    pedido_mensal: Mapped[int] = mapped_column(nullable=True, default=0)  # Quantidade pedida mensalmente
    tipo_trabalho: Mapped[str] = mapped_column(String(50), nullable=True)  # Tipo de trabalho
    fluxo_producao: Mapped[str] = mapped_column(String(10), nullable=True)  # "Puxado" ou "Empurrado"
    dia_entrega: Mapped[int] = mapped_column(Integer, nullable=True)  # Dia de entrega
    observacao: Mapped[str] = mapped_column(Text, nullable=True)  # Observações opcionais
    pap_id: Mapped[int] = mapped_column(ForeignKey("partes_produto.pap_id"), nullable=True)

    pcps: Mapped[list["PCP"]] = relationship("PCP", back_populates="produto")
    retiradas_exp: Mapped[list["RETIRADA_EXP"]] = relationship("RETIRADA_EXP", back_populates="produto")
    valores_produto: Mapped[list["VALOR_PRODUTO"]] = relationship("VALOR_PRODUTO", back_populates="produto")
    partes_produto: Mapped["PARTES_PRODUTO"] = relationship("PARTES_PRODUTO", back_populates="produtos")
    pedidos_em_aberto: Mapped[list["PEDIDOS_EM_ABERTO"]] = relationship("PEDIDOS_EM_ABERTO", back_populates="produto")
    saida_notas: Mapped[list["SAIDA_NOTAS"]] = relationship("SAIDA_NOTAS", back_populates="produto")

class PEDIDOS_EM_ABERTO(Base):
    __tablename__ = 'pedidos_em_aberto'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    descricao_item: Mapped[str] = mapped_column(String(500), nullable=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.produto_id"), nullable=False)  # Obrigatório
    data_entrega: Mapped[str] = mapped_column(String(50), nullable=True)
    data_inicio: Mapped[str] = mapped_column(String(50), nullable=True)
    valor_faturamento: Mapped[str] = mapped_column(String(50), nullable=True)
    situacao: Mapped[str] = mapped_column(String(100), nullable=True)
    tipo_frete: Mapped[str] = mapped_column(String(100), nullable=True)
    id_pedido: Mapped[str] = mapped_column(String(50), nullable=True)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=True)
    codigo_produto: Mapped[str] = mapped_column(String(100), nullable=True)
    status_mapeamento: Mapped[str] = mapped_column(String(50), nullable=True)
    
    # Relacionamento com PRODUTO
    produto: Mapped["PRODUTO"] = relationship("PRODUTO", back_populates="pedidos_em_aberto")

class SAIDA_NOTAS(Base):
    __tablename__ = 'saida_notas'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.produto_id"), nullable=False)  # Obrigatório
    descricao: Mapped[str] = mapped_column(String(500), nullable=True)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=True)
    numero_nfe: Mapped[str] = mapped_column(String(50), nullable=True)
    observacao: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Relacionamento com PRODUTO
    produto: Mapped["PRODUTO"] = relationship("PRODUTO", back_populates="saida_notas")

class CLIENTE (Base):
    __tablename__ = 'clientes'

    cliente_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # ID único
    nome: Mapped[str] = mapped_column(String(100), nullable=False)  # Nome do cliente
    cli_prazo: Mapped[str] = mapped_column(String(100), nullable=True)
    cli_forma_pagamento: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Relacionamento com a tabela PCP (1 cliente -> vários registros de PCP)
    pcps: Mapped[list["PCP"]] = relationship("PCP", back_populates="cliente")

class CHAPA(Base):
    __tablename__ = 'chapa'

    ch_codigo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ch_semana: Mapped[int] = mapped_column(Integer, nullable=True)       # Semana de referência
    ch_tamanho: Mapped[str] = mapped_column(String(50), nullable=True)   # Tamanho do produto
    ch_folhas: Mapped[int] = mapped_column(Integer, nullable=True)       # Quantidade de folhas
    ch_obs: Mapped[str] = mapped_column(String(255), nullable=True)
    ch_st_op: Mapped[str] = mapped_column(String(22), nullable=True)         # Observações
    ch_st_ar: Mapped[str] = mapped_column(String(22), nullable=True) 
    ch_imagem: Mapped[str] = mapped_column(String(255), nullable=True)    # Caminho para a imagem da chapa
    pcps: Mapped[list["PCP"]] = relationship("PCP", back_populates="chapa")  # Relacionamento com PCP

class BAIXA(Base):
    __tablename__ = 'baixa'

    baixa_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # ID único
    pcp_id: Mapped[int] = mapped_column(ForeignKey("pcp.pcp_id"), nullable=False)  # Relacionamento com PCP
    qtd: Mapped[int] = mapped_column(Integer, nullable=False)  # Quantidade baixada
    pallets: Mapped[int] = mapped_column(Integer, nullable=True)  # Pallets
    turno: Mapped[str] = mapped_column(String(50), nullable=True)  # Turno
    maquina: Mapped[str] = mapped_column(String(50), nullable=True)  # Máquina
    observacao: Mapped[str] = mapped_column(String(255), nullable=True)  # Observações
    data: Mapped[Date] = mapped_column(Date, nullable=False)  # Data da baixa
    categoria_qualidade: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=True)
    notafiscal: Mapped[str] = mapped_column(String(50), nullable=True)

    # Relacionamento com PCP
    pcp: Mapped["PCP"] = relationship("PCP", back_populates="baixas")     

class RETIRADA(Base):
    __tablename__ = 'retirada'

    ret_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # ID único
    ret_id_pcp: Mapped[int] = mapped_column(ForeignKey("pcp.pcp_id"), nullable=False)  # Relacionamento com PCP
    ret_qtd: Mapped[int] = mapped_column(Integer, nullable=False)  # Quantidade retirada
    ret_data: Mapped[Date] = mapped_column(Date, nullable=False)  # Data da retirada
    ret_obs: Mapped[str] = mapped_column(String(255), nullable=True)  # Observações

    # Relacionamento com PCP
    pcp: Mapped["PCP"] = relationship("PCP", back_populates="retiradas")

class RETIRADA_EXP(Base):
    __tablename__ = 'retirada_exp'

    ret_exp_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ret_exp_produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.produto_id"), nullable=False)
    ret_exp_qtd: Mapped[int] = mapped_column(Integer, nullable=False)
    ret_exp_data: Mapped[Date] = mapped_column(Date, nullable=False)
    ret_exp_usuario: Mapped[str] = mapped_column(String(100), nullable=True)
    ret_exp_ajuste: Mapped[str] = mapped_column(String(255), nullable=True)

    # Relacionamento com PRODUTO
    produto: Mapped["PRODUTO"] = relationship("PRODUTO", back_populates="retiradas_exp")

class PLANEJAMENTO(Base):
    __tablename__ = 'planejamento'

    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_pcp: Mapped[int] = mapped_column(ForeignKey("pcp.pcp_id"), nullable=False) # Foreign Key to PCP table
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    data_programacao: Mapped[Date] = mapped_column(Date, nullable=False)
    observacao: Mapped[str] = mapped_column(String(255), nullable=True)
    etiqueta: Mapped[str] = mapped_column(String(50), nullable=True) # Label/Tag field
    plano_setor: Mapped[dict] = mapped_column(JSON, nullable=True)
    planejamento_partes: Mapped[int] = mapped_column(Integer, nullable=True)

class FORNECEDORES(Base):
    __tablename__ = 'fornecedores'
    
    for_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    for_nome: Mapped[str] = mapped_column(String(100), nullable=False)
    for_prazo: Mapped[int] = mapped_column(Integer, nullable=True)  # Prazo em dias
    for_observacao: Mapped[str] = mapped_column(String(255), nullable=True)
    for_forma_pagamento: Mapped[str] = mapped_column(String(100), nullable=True)  # Nova coluna para forma de pagamento
    cotacoes: Mapped[list["COTACAO"]] = relationship("COTACAO", back_populates="fornecedor")

class PRODUTO_ESPEC(Base):
    __tablename__ = 'produto_espec'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria: Mapped[str] = mapped_column(String(100), nullable=True)  # Texto pequeno
    unidade_medida: Mapped[str] = mapped_column(String(50), nullable=True)  # Texto pequeno
    grupo: Mapped[str] = mapped_column(String(100), nullable=True)  # Texto pequeno
    medidas: Mapped[str] = mapped_column(String(255), nullable=True)  # Caminho para foto (upload)
    substrato: Mapped[str] = mapped_column(Text, nullable=True)  # Texto longo
    acabamento: Mapped[str] = mapped_column(Text, nullable=True)  # Texto longo
    embalagem: Mapped[str] = mapped_column(Text, nullable=True)  # Texto longo
    especificacoes: Mapped[str] = mapped_column(Text, nullable=True)  # Texto longo
    info_adicional: Mapped[str] = mapped_column(Text, nullable=True)  # Texto longo

    laudos: Mapped[list["LAUDOS"]] = relationship(
        "LAUDOS",
        back_populates="produto_espec",
        cascade="all, delete-orphan"  # opcional; use se quiser apagar laudos quando excluir o produto_espec
    )

class LAUDOS(Base):
    __tablename__ = 'laudos'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_pcp: Mapped[int] = mapped_column(ForeignKey("pcp.pcp_id"), nullable=False)
    nota_fiscal: Mapped[int] = mapped_column(Integer, nullable=True)
    qtd_por_plano: Mapped[dict] = mapped_column(JSON, nullable=True)
    produto_espec_id: Mapped[int] = mapped_column(ForeignKey("produto_espec.id"), nullable=True)

    # Relacionamento com PCP
    pcp: Mapped["PCP"] = relationship("PCP", back_populates="laudos")
    # Relacionamento com PRODUTO_ESPEC
    produto_espec: Mapped["PRODUTO_ESPEC"] = relationship("PRODUTO_ESPEC", back_populates="laudos")
        
class PRODUTO_COMPRAS(Base):
    __tablename__ = 'produto_compras'
    
    prod_comp_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Relacionamento com ORDEM_COMPRA
    ordens_compra: Mapped[list["ORDEM_COMPRA"]] = relationship("ORDEM_COMPRA", back_populates="produto")

class ORDEM_COMPRA(Base):
    __tablename__ = 'ordem_compra'
    
    oc_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    oc_nome_solicitacao: Mapped[str] = mapped_column(String(100), nullable=True)
    oc_solicitacao: Mapped[int] = mapped_column(Integer, nullable=True)
    oc_qtd_solicitada: Mapped[float] = mapped_column(Float, nullable=True)
    oc_unid_compra: Mapped[str] = mapped_column(String(50), nullable=True)
    oc_solicitante: Mapped[str] = mapped_column(String(100), nullable=True)
    oc_setor: Mapped[str] = mapped_column(String(100), nullable=True)
    oc_data_necessaria: Mapped[Date] = mapped_column(Date, nullable=True)
    oc_data_emissao: Mapped[Date] = mapped_column(Date, nullable=True)
    oc_data_entrega: Mapped[Date] = mapped_column(Date, nullable=True)
    oc_produto_id: Mapped[int] = mapped_column(ForeignKey("produto_compras.prod_comp_id"), nullable=True)
    oc_fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.for_id"), nullable=True)
    oc_categoria_id: Mapped[int] = mapped_column(ForeignKey("categoria_compras.id_categoria"), nullable=True)
    oc_qtd_recebida: Mapped[float] = mapped_column(Float, nullable=True)
    oc_sku: Mapped[str] = mapped_column(String(50), nullable=True)
    oc_conversao: Mapped[float] = mapped_column(Float, nullable=True)
    oc_unidade_conversao: Mapped[str] = mapped_column(String(50), nullable=True)
    oc_numero: Mapped[str] = mapped_column(String(50), nullable=True)
    oc_observacao: Mapped[str] = mapped_column(String(255), nullable=True)
    oc_ipi: Mapped[float] = mapped_column(Float, nullable=True)
    oc_icms: Mapped[float] = mapped_column(Float, nullable=True)
    oc_frete: Mapped[float] = mapped_column(Float, nullable=True)
    oc_status: Mapped[str] = mapped_column(String(50), nullable=True)
    oc_valor_unit: Mapped[float] = mapped_column(Float, nullable=True)  # Valor unitário
    oc_pcp_id: Mapped[int] = mapped_column(ForeignKey("pcp.pcp_id"), nullable=True)  # Novo campo linkado com o PCP
    oc_nota: Mapped[str] = mapped_column(String(50), nullable=True)  # Número da nota fiscal
    oc_cotacao: Mapped[str] = mapped_column(String(255), nullable=True) # Cotação
    
    # Relacionamentos
    produto: Mapped["PRODUTO_COMPRAS"] = relationship("PRODUTO_COMPRAS", back_populates="ordens_compra")
    fornecedor: Mapped["FORNECEDORES"] = relationship("FORNECEDORES")
    pcp: Mapped["PCP"] = relationship("PCP", back_populates="ordens_compra")  # Atualizado para back_populates
    carregamentos: Mapped[list["CARREGAMENTO"]] = relationship("CARREGAMENTO", back_populates="ordem_compra")  # Relacionamento com carregamentos
    categoria_compra: Mapped["CATEGORIA_COMPRAS"] = relationship("CATEGORIA_COMPRAS", back_populates="ordens_compra")
    cotacoes: Mapped[list["COTACAO"]] = relationship("COTACAO", back_populates="ordem_compra")

class COTACAO(Base):
    __tablename__ = 'cotacao'
    
    cot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    oc_id: Mapped[int] = mapped_column(ForeignKey("ordem_compra.oc_id"), nullable=False)
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.for_id"), nullable=True)
    valor_unit: Mapped[float] = mapped_column(Float, nullable=True)
    ipi: Mapped[float] = mapped_column(Float, nullable=True)
    icms: Mapped[float] = mapped_column(Float, nullable=True)
    valor_entrada: Mapped[float] = mapped_column(Float, nullable=True)
    condicao_pagamento: Mapped[str] = mapped_column(String(100), nullable=True)
    forma_pagamento: Mapped[str] = mapped_column(String(100), nullable=True)
    observacao: Mapped[str] = mapped_column(String(255), nullable=True)
    imagem: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Relationship
    ordem_compra: Mapped["ORDEM_COMPRA"] = relationship("ORDEM_COMPRA", back_populates="cotacoes")
    fornecedor: Mapped["FORNECEDORES"] = relationship("FORNECEDORES", back_populates="cotacoes")

class CARREGAMENTO(Base):
    __tablename__ = 'carregamento'
    
    car_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    car_oc_id: Mapped[int] = mapped_column(ForeignKey("ordem_compra.oc_id"), nullable=False)  # Linkado com ordem de compra
    car_qtd: Mapped[float] = mapped_column(Float, nullable=False)  # Quantidade carregada
    car_data: Mapped[Date] = mapped_column(Date, nullable=False)  # Data do carregamento
    
    # Relacionamento
    ordem_compra: Mapped["ORDEM_COMPRA"] = relationship("ORDEM_COMPRA", back_populates="carregamentos")

class FACA(Base):
    __tablename__ = 'faca'
    
    fac_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fac_cod: Mapped[str] = mapped_column(String(50), nullable=False)  # Código alfanumérico
    fac_descricao: Mapped[str] = mapped_column(Text, nullable=True)  # Descrição da faca
    fac_medida: Mapped[str] = mapped_column(String(50), nullable=True)  # Medidas (ex: 500x800)
    fac_maquina: Mapped[str] = mapped_column(String(100), nullable=True)  # Máquina onde a faca é utilizada
    fac_status: Mapped[str] = mapped_column(String(50), nullable=True)  # Status da faca
    fac_localizacao: Mapped[str] = mapped_column(String(100), nullable=True)  # Localização física da faca
    fac_tipo_papel: Mapped[str] = mapped_column(String(100), nullable=True)  # Tipo de papel compatível
    fac_imagem: Mapped[str] = mapped_column(String(100), nullable=True) # Caminho para a imagem da faca
    pcps: Mapped[list["PCP"]] = relationship("PCP", back_populates="faca")

class CATEGORIA_ESTOQUE(Base):
    __tablename__ = 'categoria_estoque'
    
    cae_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cae_linha: Mapped[str] = mapped_column(String(100), nullable=False)
    cae_consumo_mensal: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Relacionamento com ESTUDO_ESTOQUE
    estudos: Mapped[list["ESTUDO_ESTOQUE"]] = relationship("ESTUDO_ESTOQUE", back_populates="categoria")

class ESTUDO_ESTOQUE(Base):
    __tablename__ = 'estudo_estoque'
    
    ese_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ese_cae_id: Mapped[int] = mapped_column(ForeignKey("categoria_estoque.cae_id"), nullable=False)
    ese_subtipo: Mapped[str] = mapped_column(String(100), nullable=False)
    ese_peso_medio: Mapped[float] = mapped_column(Float, nullable=True)  # Nova coluna para peso médio
    
    # Relacionamento com CATEGORIA_ESTOQUE
    categoria: Mapped["CATEGORIA_ESTOQUE"] = relationship("CATEGORIA_ESTOQUE", back_populates="estudos")

class PRODUCAO(Base):
    __tablename__ = 'producao'

    pr_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pr_setor_id: Mapped[int] = mapped_column(ForeignKey('setor.setor_id'), nullable=False)
    pr_data: Mapped[Date] = mapped_column(Date, nullable=False)
    pr_inicio: Mapped[Time] = mapped_column(Time, nullable=False)
    pr_termino: Mapped[Time] = mapped_column(Time, nullable=False)
    pr_maquina_id: Mapped[int] = mapped_column(ForeignKey('maquina.maquina_id'), nullable=False)
    pr_categoria_produto_id: Mapped[int] = mapped_column(ForeignKey('categoria_produto.cp_id'), nullable=True)
    pr_fechado: Mapped[int] = mapped_column(Integer, nullable=True)

    # Relacionamentos
    setor: Mapped["SETOR"] = relationship("SETOR", back_populates="producoes")
    maquina: Mapped["MAQUINA"] = relationship("MAQUINA", back_populates="producoes")
    categoria_produto: Mapped["CATEGORIA_PRODUTO"] = relationship("CATEGORIA_PRODUTO", back_populates="producoes")
    apontamentos: Mapped[list["APONTAMENTO"]] = relationship("APONTAMENTO", back_populates="producao")
    apontamentos_produto: Mapped[list["APONTAMENTO_PRODUTO"]] = relationship("APONTAMENTO_PRODUTO", back_populates="producao")

class APONTAMENTO(Base):
    __tablename__ = 'apontamento'

    ap_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ap_tempo: Mapped[int] = mapped_column(Integer, nullable=False)
    ap_pr: Mapped[int] = mapped_column(ForeignKey('producao.pr_id'), nullable=False)
    ap_lv1: Mapped[int] = mapped_column(Integer, nullable=False)
    ap_lv2: Mapped[int] = mapped_column(Integer, nullable=True)
    ap_lv3: Mapped[int] = mapped_column(Integer, nullable=True)
    ap_lv4: Mapped[int] = mapped_column(Integer, nullable=True)
    ap_lv5: Mapped[int] = mapped_column(Integer, nullable=True)
    ap_lv6: Mapped[int] = mapped_column(Integer, nullable=True)

    # Relacionamento com PRODUCAO
    producao: Mapped["PRODUCAO"] = relationship("PRODUCAO", back_populates="apontamentos")

class CATEGORIA_PRODUTO(Base):
    __tablename__ = 'categoria_produto'

    cp_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cp_nome: Mapped[str] = mapped_column(String(30), nullable=False)
    cp_meta: Mapped[int] = mapped_column(Integer, nullable=False)
    c_maq_id: Mapped[int] = mapped_column(ForeignKey('maquina.maquina_id'), nullable=False)

    # Relacionamento com MAQUINA
    maquina: Mapped["MAQUINA"] = relationship("MAQUINA", back_populates="categorias_produto")
    producoes: Mapped[list["PRODUCAO"]] = relationship("PRODUCAO", back_populates="categoria_produto")

class SETOR(Base):
    __tablename__ = 'setor'

    setor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    setor_nome: Mapped[str] = mapped_column(String(30), nullable=False)
    tipo_plano: Mapped[int] = mapped_column(Integer, nullable=True)
    set_padrao: Mapped[int] = mapped_column(Integer, nullable=True)

    # Relacionamentos
    maquinas: Mapped[list["MAQUINA"]] = relationship("MAQUINA", back_populates="setor")
    razoens: Mapped[list["RAZAO"]] = relationship("RAZAO", back_populates="setor")
    producoes: Mapped[list["PRODUCAO"]] = relationship("PRODUCAO", back_populates="setor")
    
class RAZAO(Base):
    __tablename__ = 'razao'

    ra_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ra_razao: Mapped[str] = mapped_column(String(30), nullable=False)
    ra_level: Mapped[str] = mapped_column(String(30), nullable=False)
    ra_sub: Mapped[str] = mapped_column(String(30), nullable=False)
    ra_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    setor_id: Mapped[int] = mapped_column(ForeignKey('setor.setor_id'), nullable=False)

    # Relacionamento
    setor: Mapped["SETOR"] = relationship("SETOR", back_populates="razoens")

class MAQUINA(Base):
    __tablename__ = 'maquina'

    maquina_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    maquina_nome: Mapped[str] = mapped_column(String(30), nullable=False)
    maquina_custo: Mapped[float] = mapped_column(Float, nullable=True)
    setor_id: Mapped[int] = mapped_column(ForeignKey('setor.setor_id'), nullable=False)

    # Relacionamentos
    setor: Mapped["SETOR"] = relationship("SETOR", back_populates="maquinas")
    producoes: Mapped[list["PRODUCAO"]] = relationship("PRODUCAO", back_populates="maquina")
    categorias_produto: Mapped[list["CATEGORIA_PRODUTO"]] = relationship("CATEGORIA_PRODUTO", back_populates="maquina")

class APONTAMENTO_PRODUTO(Base):
    __tablename__ = 'apontamento_produto'

    atp_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    atp_producao: Mapped[int] = mapped_column(ForeignKey('producao.pr_id'), nullable=False)
    atp_pcp: Mapped[int] = mapped_column(ForeignKey('pcp.pcp_id'), nullable=False)
    atp_qtd: Mapped[int] = mapped_column(Integer, nullable=False)
    atp_data: Mapped[Date] = mapped_column(Date, nullable=False)
    atp_refugos: Mapped[int] = mapped_column(Integer, nullable=True)
    atp_obs: Mapped[str] = mapped_column(String(255), nullable=True)
    atp_custo: Mapped[float] = mapped_column(Float, nullable=True)
    atp_plano: Mapped[int] = mapped_column(Integer, nullable=True)
    atp_repeticoes: Mapped[int] = mapped_column(Integer, nullable=True)

    # Relacionamentos
    producao: Mapped["PRODUCAO"] = relationship("PRODUCAO", back_populates="apontamentos_produto")
    pcp: Mapped["PCP"] = relationship("PCP", back_populates="apontamentos_produto")

class GRUPO_CATEGORIA(Base):
    __tablename__ = 'grupo_categoria'
    
    id_grupo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_grupo: Mapped[str] = mapped_column(String(100), nullable=False)
    unidade: Mapped[str] = mapped_column(String(50), nullable=True)
    
    # Relacionamento com CATEGORIA_COMPRAS
    categorias: Mapped[list["CATEGORIA_COMPRAS"]] = relationship("CATEGORIA_COMPRAS", back_populates="grupo")

class CATEGORIA_COMPRAS(Base):
    __tablename__ = 'categoria_compras'
    
    id_categoria: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria_nome: Mapped[str] = mapped_column(String(100), nullable=False)
    conversao: Mapped[float] = mapped_column(Float, nullable=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupo_categoria.id_grupo"), nullable=True)
    
    # Relacionamentos
    grupo: Mapped["GRUPO_CATEGORIA"] = relationship("GRUPO_CATEGORIA", back_populates="categorias")
    valores_alvo: Mapped[list["VALOR_ALVO"]] = relationship("VALOR_ALVO", back_populates="categoria")
    ordens_compra: Mapped[list["ORDEM_COMPRA"]] = relationship("ORDEM_COMPRA", back_populates="categoria_compra")

class VALOR_ALVO(Base):
    __tablename__ = 'valor_alvo'
    
    id_valor_alvo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    preco: Mapped[float] = mapped_column(Float, nullable=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categoria_compras.id_categoria"), nullable=False)
    data: Mapped[Date] = mapped_column(Date, nullable=False)
    custo: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Relacionamento
    categoria: Mapped["CATEGORIA_COMPRAS"] = relationship("CATEGORIA_COMPRAS", back_populates="valores_alvo")

class VALOR_PRODUTO(Base):
    __tablename__ = 'valor_produto'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.produto_id"), nullable=False)
    valor: Mapped[float] = mapped_column(Float, nullable=False)
    orcamento: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[Date] = mapped_column(Date, nullable=False)
    
    # Relacionamento
    produto: Mapped["PRODUTO"] = relationship("PRODUTO", back_populates="valores_produto")
    
class PARTES_PRODUTO(Base):
    __tablename__ = 'partes_produto'

    pap_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pap_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    pap_parte: Mapped[dict] = mapped_column(JSON, nullable=True)
    produtos: Mapped[list["PRODUTO"]] = relationship("PRODUTO", back_populates="partes_produto")

class AGENDAMENTO_LOGISTICA(Base):
    __tablename__ = 'agendamento_logistica'
    
    agend_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agend_numero: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)  # Número único do agendamento
    agend_tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # CARREGAMENTO ou DESCARREGAMENTO
    agend_data_agendada: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    agend_data_inicio: Mapped[DateTime] = mapped_column(DateTime, nullable=True)  # Quando realmente começou
    agend_data_fim: Mapped[DateTime] = mapped_column(DateTime, nullable=True)  # Quando realmente terminou
    agend_status: Mapped[str] = mapped_column(String(30), nullable=False, default="AGENDADO")  # AGENDADO, EM_ANDAMENTO, CONCLUIDO, CANCELADO, ATRASADO
    agend_prioridade: Mapped[str] = mapped_column(String(20), nullable=True)  # BAIXA, MEDIA, ALTA, URGENTE
    
    # Informações da transportadora
    transp_nome: Mapped[str] = mapped_column(String(100), nullable=False)
    transp_cnpj: Mapped[str] = mapped_column(String(18), nullable=True)
    transp_telefone: Mapped[str] = mapped_column(String(20), nullable=True)
    transp_email: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Informações do veículo
    veic_placa: Mapped[str] = mapped_column(String(8), nullable=False)
    veic_modelo: Mapped[str] = mapped_column(String(100), nullable=True)
    veic_tipo: Mapped[str] = mapped_column(String(50), nullable=True)  # Caminhão, Van, Carreta, etc.
    veic_capacidade_peso: Mapped[float] = mapped_column(Float, nullable=True)  # Em toneladas
    veic_capacidade_volume: Mapped[float] = mapped_column(Float, nullable=True)  # Em m³
    
    # Informações do motorista
    mot_nome: Mapped[str] = mapped_column(String(100), nullable=False)
    mot_cpf: Mapped[str] = mapped_column(String(14), nullable=True)
    mot_cnh: Mapped[str] = mapped_column(String(20), nullable=True)
    mot_telefone: Mapped[str] = mapped_column(String(20), nullable=True)
    
    # Informações do agendamento
    agend_local: Mapped[str] = mapped_column(String(100), nullable=True)  # Local do carregamento/descarregamento
    agend_dock: Mapped[str] = mapped_column(String(20), nullable=True)  # Doca específica
    agend_responsavel: Mapped[str] = mapped_column(String(100), nullable=True)  # Quem agendou
    agend_observacoes: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Itens do agendamento (JSON para armazenar múltiplos itens)
    agend_itens: Mapped[dict] = mapped_column(JSON, nullable=True)  # Lista de itens com produto, quantidade, etc.
    
    # Documentos (JSON para armazenar caminhos dos arquivos)
    agend_documentos: Mapped[dict] = mapped_column(JSON, nullable=True)  # PDFs, notas fiscais, etc.
    
    # Relacionamento com histórico
    historico: Mapped[list["AGENDAMENTO_HISTORICO"]] = relationship("AGENDAMENTO_HISTORICO", back_populates="agendamento", cascade="all, delete-orphan")

class AGENDAMENTO_HISTORICO(Base):
    __tablename__ = 'agendamento_historico'
    
    hist_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hist_agend_id: Mapped[int] = mapped_column(ForeignKey("agendamento_logistica.agend_id"), nullable=False)
    hist_acao: Mapped[str] = mapped_column(String(100), nullable=False)  # CRIADO, AGENDADO, INICIADO, CONCLUIDO, CANCELADO, etc.
    hist_status_anterior: Mapped[str] = mapped_column(String(30), nullable=True)
    hist_status_novo: Mapped[str] = mapped_column(String(30), nullable=True)
    hist_data_acao: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)
    hist_usuario: Mapped[str] = mapped_column(String(100), nullable=True)
    hist_observacoes: Mapped[str] = mapped_column(Text, nullable=True)
    hist_dados_extras: Mapped[dict] = mapped_column(JSON, nullable=True)  # Dados adicionais em JSON
    
    # Relacionamentos
    agendamento: Mapped["AGENDAMENTO_LOGISTICA"] = relationship("AGENDAMENTO_LOGISTICA", back_populates="historico")
    
# Criar o banco de dados SQLite ========================
pasta_atual = Path(__file__).parent
PATH_TO_BD = pasta_atual / 'bd_pcp.sqlite'

engine = create_engine(
    f'sqlite:///{PATH_TO_BD}',
    connect_args={"check_same_thread": False},  # Permitir múltiplos threads
    pool_size=10,  # Definindo o tamanho do pool (conexões simultâneas)
    max_overflow=20  # Número máximo de conexões extras permitidas
)



Base.metadata.create_all(bind=engine)
# Limpar o cache de metadados
Base.metadata.clear()

# Recarregar o esquema atualizado (sem a tabela pcp_old)
Base.metadata.reflect(bind=engine)

engine.dispose()  # Desconecta a engine do banco
Base.metadata.clear()  # Limpa os metadados
Base.metadata.reflect(bind=engine)  # Recarrega as tabelas
#======================================================

def listar_pcp():
    try:
        # Conexão ao banco de dados
        with engine.connect() as conn:
            # Query para juntar PCP com CLIENTE e PRODUTO
            query = """
            SELECT 
                pcp.*, 
                clientes.nome AS cliente_nome,
                produtos.nome AS produto_nome
            FROM 
                pcp
            LEFT JOIN 
                clientes 
            ON 
                pcp.pcp_cliente_id = clientes.cliente_id
            LEFT JOIN 
                produtos
            ON 
                pcp.pcp_produto_id = produtos.produto_id
            """
            # Ler o resultado como DataFrame
            df = pd.read_sql(query, conn)
            
            if df.empty:
                print("Nenhum registro encontrado na tabela PCP.")
            else:
                pass
                #print(f"{len(df)} registros encontrados.")
    except SQLAlchemyError as e:
        #print(f'ERRO AO BAIXAR BANCO DE DADOS: {e}')
        df = pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro

    return df

df_pcp = listar_pcp()

def listar_dados(nome_tabela):
    pasta_atual = Path(__file__).parent
    PATH_TO_BD = pasta_atual / 'bd_pcp.sqlite'

    engine = create_engine(f'sqlite:///{PATH_TO_BD}')
    Base.metadata.create_all(bind=engine)
    try:
        # Conexão ao banco de dados
        with engine.connect() as conn:
            # Ler a tabela diretamente como um DataFrame
            df = pd.read_sql(f"SELECT * FROM {nome_tabela}", conn)
            if df.empty:
                pass
            else:
                pass
    except SQLAlchemyError as e:
        print(f'ERRO AO LER TABELA {nome_tabela.upper()}: {e}')
    return df

df_produtos = listar_dados('produtos')
df_clientes = listar_dados('clientes')
df_chapas = listar_dados('chapa')
df_baixas = listar_dados('baixa')

def juncao_ret_pcp():
    # Criação da sessão
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()

    try:
        # Consulta que junta as tabelas RETIRADA, PCP, CLIENTE e PRODUTO
        query = session.query(
            RETIRADA.ret_id.label("id_retirada"),
            PCP.pcp_id.label("pcp_id"),
            PCP.pcp_pcp.label("pcp_pcp"),
            PCP.pcp_produto_id.label("produto"),
            PRODUTO.nome.label("nome_produto"),  # Nome do produto
            CLIENTE.nome.label("nome_cliente"),  # Nome do cliente
            RETIRADA.ret_qtd.label("qtd_retirada"),  # Quantidade retirada
            RETIRADA.ret_data.label("data_retirada"),  # Data da retirada
            RETIRADA.ret_obs.label("observacao")  # Observação da retirada
        ).join(CLIENTE, PCP.pcp_cliente_id == CLIENTE.cliente_id) \
         .join(RETIRADA, PCP.pcp_id == RETIRADA.ret_id_pcp) \
         .join(PRODUTO, PCP.pcp_produto_id == PRODUTO.produto_id)

        # Converter os resultados em uma lista de dicionários
        results = query.all()
        data = [row._asdict() for row in results]

        # Criar um DataFrame do pandas
        df = pd.DataFrame(data)
        return df
    
    except SQLAlchemyError as e:
        print(f'Erro na consulta: {e}')
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro
    
    finally:
        # Garantir o fechamento da sessão
        session.close()

def juncao():
    # Criação da sessão
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()

    try:
        # Consulta que junta as tabelas PCP, CLIENTE, BAIXA e PRODUTO
        query = session.query(
            BAIXA.baixa_id.label("id_movi"),
            PCP.pcp_id.label("pcp_id"), 
            PCP.pcp_pcp.label("pcp_pcp"), 
            PCP.pcp_produto_id.label("produto"), 
            PRODUTO.nome.label("nome_produto"),  # Puxando o nome do produto
            CLIENTE.nome.label("nome_cliente"),
            BAIXA.qtd.label("qtd"),  # Incluindo a quantidade baixada da tabela BAIXA
            BAIXA.data.label("data"),
            BAIXA.observacao.label("Observação")
        ).join(CLIENTE, PCP.pcp_cliente_id == CLIENTE.cliente_id) \
         .join(BAIXA, PCP.pcp_id == BAIXA.pcp_id)  \
         .join(PRODUTO, PCP.pcp_produto_id == PRODUTO.produto_id)  # Novo join com a tabela PRODUTO

        # Converter os resultados em uma lista de dicionários
        results = query.all()
        data = [row._asdict() for row in results]

        # Criar um DataFrame do pandas
        df = pd.DataFrame(data)
        return df
    
    except SQLAlchemyError as e:
        print(f'Erro na consulta: {e}')
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro
    
    finally:
        # Garantir o fechamento da sessão
        session.close()

class Banco:
    def __init__(self):
        # Correção para usar um caminho absoluto para o banco de dados
        pasta_bd = Path(__file__).parent
        db_path = pasta_bd / 'bd_pcp.sqlite'
        database_url = f"sqlite:///{db_path.resolve()}"

        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            pool_size=10,
            max_overflow=20
        )
        self.Session = sessionmaker(bind=self.engine)
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)

        # Criação da tabela de logs caso não exista
        #self.criar_tabela_logs()

    def criar_tabela_logs(self):
        # Define a tabela de logs
        if 'logs' not in self.metadata.tables:
            logs = Table('logs', self.metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('tipo_movimentacao', String(50)),  # Inserção, Edição, Deleção
                Column('nome_tabela', String(100)),
                Column('dados_antigos', Text, nullable=True),  # Dados antigos como JSON ou String
                Column('dados_novos', Text, nullable=True),  # Dados novos como JSON ou String
                Column('timestamp', DateTime, default=datetime.utcnow)
            )
            self.metadata.create_all(self.engine)

    def registrar_log(self, tipo, nome_tabela, dados_antigos=None, dados_novos=None):
        """
        Função para registrar movimentação na tabela de logs.
        """
        session = self.Session()
        try:
            dados_antigos = str(dados_antigos) if dados_antigos else None
            dados_novos = str(dados_novos) if dados_novos else None

            log = {
                'tipo_movimentacao': tipo,
                'nome_tabela': nome_tabela,
                'dados_antigos': dados_antigos,
                'dados_novos': dados_novos,
                'timestamp': datetime.utcnow()
            }

            tabela_logs = Table('logs', self.metadata, autoload_with=self.engine)
            session.execute(tabela_logs.insert().values(log))
            session.commit()
        finally:
            session.close()

    def ler_tabela(self, nome_tabela, **kwargs):  # READ
        if nome_tabela not in self.metadata.tables:
            raise ValueError(f"A tabela '{nome_tabela}' não existe no banco de dados.")
        
        tabela = Table(nome_tabela, self.metadata, autoload_with=self.engine)
        session = self.Session()
        
        try:
            query = session.query(tabela)
            if kwargs:
                query = query.filter_by(**kwargs)

            consulta = query.all()
            dados = [dict(row._mapping) for row in consulta]  # Converte os resultados para dicionário
            return pd.DataFrame(dados)  # Retorna um DataFrame
        finally:
            session.close()

    def inserir_dados(self, nome_tabela, **campos):  # POST 
        if nome_tabela not in self.metadata.tables:
            raise ValueError(f"A tabela '{nome_tabela}' não existe no banco de dados.")
        
        tabela = Table(nome_tabela, self.metadata, autoload_with=self.engine)
        session = self.Session()
        
        try:
            colunas = [col.name for col in tabela.columns if not col.primary_key]
            dados_filtrados = {k: v for k, v in campos.items() if k in colunas}

            if not dados_filtrados:
                raise ValueError("Nenhum campo válido foi fornecido para inserção.")

            # A serialização de dicionários para JSON é tratada pelo tipo JSON do SQLAlchemy.
            # O código a seguir foi removido para evitar dupla serialização.
            # for key, value in dados_filtrados.items():
            #     if isinstance(value, dict):
            #         dados_filtrados[key] = json.dumps(value, ensure_ascii=False)

            inserir = tabela.insert().values(**dados_filtrados)
            session.execute(inserir)
            session.commit()

            # Registra o log
            self.registrar_log("insercao", nome_tabela, dados_novos=dados_filtrados)
        finally:
            session.close()

    def deletar_dado(self, nome_tabela, id):  # DELETE
        if nome_tabela not in self.metadata.tables:
            raise ValueError(f"A tabela '{nome_tabela}' não existe no banco de dados.")
        
        tabela = Table(nome_tabela, self.metadata, autoload_with=self.engine)
        
        # Obtém o nome da chave primária automaticamente
        chave_primaria = [col.name for col in tabela.columns if col.primary_key]
        
        if not chave_primaria:
            raise ValueError(f"A tabela '{nome_tabela}' não possui uma chave primária definida.")
        
        nome_id = chave_primaria[0]  # Pega o nome correto da chave primária (ex: fo_id)
        
        session = self.Session()
        
        try:
            # Obtém os dados antes da exclusão para registrar
            dados_antigos = session.query(tabela).filter(tabela.c[nome_id] == id).first()
            if not dados_antigos:
                raise ValueError(f"O dado com ID '{id}' não foi encontrado.")

            dados_antigos = dict(dados_antigos._mapping)  # Converte os dados antigos para dicionário
            deletar = tabela.delete().where(tabela.c[nome_id] == id)
            resultado = session.execute(deletar)
            session.commit()

            # Registra o log
            self.registrar_log("delecao", nome_tabela, dados_antigos=dados_antigos)
            return resultado.rowcount > 0
        finally:
            session.close()

    def editar_dado(self, nome_tabela, id, **campos):  # UPLOAD
        if nome_tabela not in self.metadata.tables:
            raise ValueError(f"A tabela '{nome_tabela}' não existe no banco de dados.")
        
        tabela = Table(nome_tabela, self.metadata, autoload_with=self.engine)

        # Obtém o nome da chave primária automaticamente
        chave_primaria = [col.name for col in tabela.columns if col.primary_key]
        
        if not chave_primaria:
            raise ValueError(f"A tabela '{nome_tabela}' não possui uma chave primária definida.")
        
        nome_id = chave_primaria[0]  # Pega o nome correto da chave primária (ex: fo_id)

        session = self.Session()
        
        try:
            # Obtém os dados antigos antes da atualização
            dados_antigos = session.query(tabela).filter(tabela.c[nome_id] == id).first()
            if not dados_antigos:
                raise ValueError(f"O dado com ID '{id}' não foi encontrado.")
                
            dados_antigos = dict(dados_antigos._mapping)  # Converte os dados antigos para dicionário

            colunas = [col.name for col in tabela.columns if col.name != nome_id]
            dados_filtrados = {k: v for k, v in campos.items() if k in colunas}

            if not dados_filtrados:
                raise ValueError("Nenhum campo válido foi fornecido para atualização.")

            # A serialização de dicionários para JSON é tratada pelo tipo JSON do SQLAlchemy.
            # O código a seguir foi removido para evitar dupla serialização.
            # for key, value in dados_filtrados.items():
            #     if isinstance(value, dict):
            #         dados_filtrados[key] = json.dumps(value, ensure_ascii=False)

            atualizar = tabela.update().where(tabela.c[nome_id] == id).values(**dados_filtrados)
            resultado = session.execute(atualizar)
            session.commit()

            # Registra o log
            self.registrar_log("edicao", nome_tabela, dados_antigos=dados_antigos, dados_novos=dados_filtrados)
            return resultado.rowcount > 0
        except Exception as e:
            print(f"--- [ERROR] EDITAR_DADO FAILED ---")
            print(e)
            print("---------------------------------")
            session.rollback()
        finally:
            session.close()

# Função para adicionar usuários
def add_user(username, password, user_level="user"):
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    if session.query(User).filter_by(username=username).first():
        print(f"Usuário '{username}' já existe.")
        return
    new_user = User(username=username, password=password, user_level=user_level)
    session.add(new_user)
    session.commit()
    print(f"Usuário '{username}' com nível '{user_level}' adicionado com sucesso.")

# Função para editar senha
def edit_password(username, new_password):
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    user = session.query(User).filter_by(username=username).first()
    if not user:
        print(f"Usuário '{username}' não encontrado.")
        return
    user.password = new_password
    session.commit()
    print(f"Senha do usuário '{username}' atualizada com sucesso.")

# Função para editar nível de usuário
def edit_user_level(username, new_user_level):
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    user = session.query(User).filter_by(username=username).first()
    if not user:
        print(f"Usuário '{username}' não encontrado.")
        return
    user.user_level = new_user_level
    session.commit()
    print(f"Nível do usuário '{username}' atualizado para '{new_user_level}'.")

# Função para excluir usuários
def delete_user(username):
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    user = session.query(User).filter_by(username=username).first()
    if not user:
        print(f"Usuário '{username}' não encontrado.")
        return
    session.delete(user)
    session.commit()
    print(f"Usuário '{username}' excluído com sucesso.")

# Função de autenticação personalizada com banco de dados
def authenticate_user(username, password):
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    try:
        user = session.query(User).filter_by(username=username).first()
        if user and user.password == password:
            return user.user_level  # Pode ser JSON (dict) ou string, conforme armazenado
        return None
    finally:
        session.close()

def listar_lembretes(status=None):
    try:
        # Database connection
        with engine.connect() as conn:
            if status:
                query = f"SELECT * FROM lembretes WHERE status = '{status}' ORDER BY data ASC"
            else:
                query = "SELECT * FROM lembretes ORDER BY data ASC"
                
            # Read the result as DataFrame
            df = pd.read_sql(query, conn)
            
            if df.empty:
                pass
            else:
                pass
    except SQLAlchemyError as e:
        print(f'ERRO AO CONSULTAR LEMBRETES: {e}')
        df = pd.DataFrame()  # Return empty DataFrame in case of error

    return df

def criar_usuario_admin_inicial():
    """
    Cria um usuário admin inicial se não existir nenhum usuário no sistema.
    Esta função deve ser chamada na inicialização do sistema.
    """
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    
    try:
        # Verifica se já existe algum usuário no sistema
        total_usuarios = session.query(User).count()
        
        if total_usuarios == 0:
            # Permissões completas para o admin inicial
            permissoes_admin = {
                "collapses": {
                    "cadastros": True,
                    "pcp": True,
                    "oee": True,
                    "compras": True,
                    "qualidade": True,
                    "dashboards": True,
                    "export": True
                }
            }
            
            # Se não há usuários, cria o admin inicial
            admin_user = User(
                username="admin",
                password="admin123",
                user_level=permissoes_admin
            )
            session.add(admin_user)
            session.commit()
            print("=" * 60)
            print("🔐 USUÁRIO ADMIN CRIADO COM SUCESSO!")
            print("=" * 60)
            print("👤 Usuário: admin")
            print("🔑 Senha: admin123")
            print("🔓 Acesso: TODOS os módulos habilitados")
            print("⚠️  IMPORTANTE: Altere a senha após o primeiro login!")
            print("=" * 60)
        else:
            print(f"✅ Sistema já possui {total_usuarios} usuário(s) cadastrado(s).")
            
    except Exception as e:
        print(f"❌ Erro ao criar usuário admin: {e}")
        session.rollback()
    finally:
        session.close()

# Chama a função para criar o admin inicial quando o módulo é importado
criar_usuario_admin_inicial()