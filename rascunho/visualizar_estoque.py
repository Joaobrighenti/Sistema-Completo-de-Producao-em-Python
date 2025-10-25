#!/usr/bin/env python3
"""
Script para visualizar o estoque atual de todos os produtos
Apenas mostra o estoque sem fazer alterações
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banco_dados.banco import engine, PCP, BAIXA, SAIDA_NOTAS, PRODUTO
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd

def visualizar_estoque_atual():
    """
    Visualiza o estoque atual de todos os produtos
    Estoque = Baixas - Saídas
    """
    print("🔍 Visualizando estoque atual de todos os produtos...")
    print("=" * 80)
    
    with Session(engine) as session:
        # Obter todos os produtos
        produtos = session.query(PRODUTO.produto_id, PRODUTO.nome).all()
        
        produtos_com_estoque = []
        produtos_sem_estoque = []
        total_estoque = 0
        
        print(f"{'ID':<5} {'Nome do Produto':<50} {'Baixas':<10} {'Saídas':<10} {'Estoque':<10}")
        print("-" * 80)
        
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
            
            # Formatar nome do produto (truncar se muito longo)
            nome_formatado = nome_produto[:47] + "..." if len(nome_produto) > 50 else nome_produto
            
            print(f"{produto_id:<5} {nome_formatado:<50} {total_baixas:<10,} {total_saidas:<10,} {estoque_atual:<10,}")
            
            if estoque_atual > 0:
                produtos_com_estoque.append({
                    'produto_id': produto_id,
                    'nome_produto': nome_produto,
                    'total_baixas': total_baixas,
                    'total_saidas': total_saidas,
                    'estoque_atual': estoque_atual
                })
                total_estoque += estoque_atual
            else:
                produtos_sem_estoque.append({
                    'produto_id': produto_id,
                    'nome_produto': nome_produto,
                    'estoque_atual': estoque_atual
                })
        
        print("-" * 80)
        print(f"\n📊 RESUMO:")
        print(f"   Total de produtos: {len(produtos)}")
        print(f"   Produtos com estoque positivo: {len(produtos_com_estoque)}")
        print(f"   Produtos sem estoque: {len(produtos_sem_estoque)}")
        print(f"   Total de unidades em estoque: {total_estoque:,}")
        
        if produtos_com_estoque:
            print(f"\n📦 PRODUTOS COM ESTOQUE POSITIVO:")
            print("-" * 60)
            for produto in sorted(produtos_com_estoque, key=lambda x: x['estoque_atual'], reverse=True):
                print(f"   {produto['produto_id']} - {produto['nome_produto']}: {produto['estoque_atual']:,} unidades")
        
        return produtos_com_estoque, total_estoque

def main():
    """
    Função principal do script
    """
    print("🚀 Visualizando estoque atual...")
    print()
    
    produtos_com_estoque, total_estoque = visualizar_estoque_atual()
    
    if produtos_com_estoque:
        print(f"\n💡 Para zerar o estoque, execute o script 'zerar_estoque.py'")
    else:
        print(f"\n✅ Todos os produtos já estão com estoque zero!")

if __name__ == "__main__":
    main()
