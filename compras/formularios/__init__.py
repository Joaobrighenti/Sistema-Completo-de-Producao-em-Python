"""
Módulo de formulários do sistema de compras.
"""

# Importar todos os formulários
from . import form_fornecedor
from . import form_ordem_compra
from . import form_categoria_estoque
from . import form_estudo_estoque

# Exportar os formulários
__all__ = [
    'form_fornecedor',
    'form_ordem_compra',
    'form_categoria_estoque',
    'form_estudo_estoque'
]

# Este arquivo marca o diretório como um pacote Python 