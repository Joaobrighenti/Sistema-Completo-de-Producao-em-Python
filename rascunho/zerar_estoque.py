#!/usr/bin/env python3
"""
Script para zerar o estoque de todos os produtos
Calcula a quantidade de saídas necessárias para zerar o estoque e insere na tabela SAIDA_NOTAS
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banco_dados.banco import Banco, engine, PCP, BAIXA, SAIDA_NOTAS, PRODUTO
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
from datetime import datetime

def calcular_estoque_atual():
    """
    Calcula o estoque atual de todos os produtos
    Estoque = Baixas - Saídas
    """
    print("🔍 Calculando estoque atual de todos os produtos...")
    
    with Session(engine) as session:
        # Obter todos os produtos
        produtos = session.query(PRODUTO.produto_id, PRODUTO.nome).all()
        
        resultados = []
        
        for produto_id, nome_produto in produtos:
            # Calcular total de baixas para o produto
            total_baixas = session.query(
                func.sum(BAIXA.qtd)
            ).join(
                PCP, BAIXA.pcp_id == PCP.pcp_id
            ).filter(
                PCP.pcp_produto_id == produto_id
            ).scalar() or 0
            
            # Calcular total de saídas para o produto
            total_saidas = session.query(
                func.sum(SAIDA_NOTAS.quantidade)
            ).filter(
                SAIDA_NOTAS.produto_id == produto_id
            ).scalar() or 0
            
            # Calcular estoque atual
            estoque_atual = total_baixas - total_saidas
            
            resultados.append({
                'produto_id': produto_id,
                'nome_produto': nome_produto,
                'total_baixas': total_baixas,
                'total_saidas': total_saidas,
                'estoque_atual': estoque_atual
            })
            
            print(f"  📦 {produto_id} - {nome_produto}: {estoque_atual:,} unidades")
        
        return resultados

def inserir_saidas_para_zerar_estoque(produtos_com_estoque):
    """
    Insere saídas na tabela SAIDA_NOTAS para zerar o estoque dos produtos
    """
    print("\n📝 Inserindo saídas para zerar estoque...")
    
    banco = Banco()
    contador = 0
    
    for produto in produtos_com_estoque:
        if produto['estoque_atual'] > 0:
            try:
                # Criar dados da saída
                dados_saida = {
                    'produto_id': produto['produto_id'],
                    'numero_nfe': f"ZERAMENTO_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{produto['produto_id']}",
                    'quantidade': produto['estoque_atual'],
                    'descricao': f"Zeramento de estoque - {produto['nome_produto']}",
                    'observacao': f"Saída automática para zerar estoque. Estoque anterior: {produto['estoque_atual']:,} unidades"
                }
                
                # Inserir na tabela SAIDA_NOTAS
                banco.inserir_dados("saida_notas", **dados_saida)
                
                contador += 1
                print(f"  ✅ {produto['produto_id']} - {produto['nome_produto']}: {produto['estoque_atual']:,} unidades zeradas")
                
            except Exception as e:
                print(f"  ❌ Erro ao zerar estoque do produto {produto['produto_id']}: {e}")
    
    return contador

def verificar_estoque_final():
    """
    Verifica se o estoque foi realmente zerado
    """
    print("\n🔍 Verificando estoque final...")
    
    with Session(engine) as session:
        # Obter todos os produtos
        produtos = session.query(PRODUTO.produto_id, PRODUTO.nome).all()
        
        produtos_com_estoque = []
        
        for produto_id, nome_produto in produtos:
            # Calcular total de baixas para o produto
            total_baixas = session.query(
                func.sum(BAIXA.qtd)
            ).join(
                PCP, BAIXA.pcp_id == PCP.pcp_id
            ).filter(
                PCP.pcp_produto_id == produto_id
            ).scalar() or 0
            
            # Calcular total de saídas para o produto
            total_saidas = session.query(
                func.sum(SAIDA_NOTAS.quantidade)
            ).filter(
                SAIDA_NOTAS.produto_id == produto_id
            ).scalar() or 0
            
            # Calcular estoque atual
            estoque_atual = total_baixas - total_saidas
            
            if estoque_atual > 0:
                produtos_com_estoque.append({
                    'produto_id': produto_id,
                    'nome_produto': nome_produto,
                    'estoque_atual': estoque_atual
                })
            
            print(f"  📦 {produto_id} - {nome_produto}: {estoque_atual:,} unidades")
        
        return produtos_com_estoque

def main():
    """
    Função principal do script
    """
    print("🚀 Iniciando processo de zeramento de estoque...")
    print("=" * 60)
    
    # Passo 1: Calcular estoque atual
    produtos_com_estoque = calcular_estoque_atual()
    
    # Filtrar apenas produtos com estoque positivo
    produtos_para_zerar = [p for p in produtos_com_estoque if p['estoque_atual'] > 0]
    
    if not produtos_para_zerar:
        print("\n✅ Nenhum produto com estoque positivo encontrado!")
        return
    
    print(f"\n📊 Total de produtos com estoque positivo: {len(produtos_para_zerar)}")
    print(f"📊 Total de unidades a zerar: {sum(p['estoque_atual'] for p in produtos_para_zerar):,}")
    
    # Perguntar confirmação
    resposta = input("\n❓ Deseja continuar com o zeramento? (s/N): ").strip().lower()
    if resposta not in ['s', 'sim', 'y', 'yes']:
        print("❌ Operação cancelada pelo usuário.")
        return
    
    # Passo 2: Inserir saídas para zerar estoque
    contador_zerados = inserir_saidas_para_zerar_estoque(produtos_para_zerar)
    
    print(f"\n✅ Processo concluído!")
    print(f"📊 Produtos zerados: {contador_zerados}")
    
    # Passo 3: Verificar estoque final
    produtos_com_estoque_final = verificar_estoque_final()
    
    if not produtos_com_estoque_final:
        print("\n🎉 Todos os estoques foram zerados com sucesso!")
    else:
        print(f"\n⚠️  Ainda existem {len(produtos_com_estoque_final)} produtos com estoque positivo:")
        for produto in produtos_com_estoque_final:
            print(f"  - {produto['produto_id']} - {produto['nome_produto']}: {produto['estoque_atual']:,} unidades")

if __name__ == "__main__":
    main()
