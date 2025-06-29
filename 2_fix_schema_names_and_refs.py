#!/usr/bin/env python3
"""
Script para Correção de Nomes de Schemas e Referências OpenAPI (Versão Aprimorada)

Este script corrige sistematicamente nomes de componentes inválidos (com espaços)
e atualiza todas as referências '$ref' que apontam para eles.

Uso:
    python fix_schema_names_and_refs.py <caminho_para_openapi.json> [--verbose]

Exemplo:
    python fix_schema_names_and_refs.py ./openapi.json
    python fix_schema_names_and_refs.py ./openapi.json --verbose

Operação em duas fases:
    1. Renomeia schemas com espaços (ex: 'Banner V1' → 'BannerV1')
    2. Atualiza todas as referências $ref recursivamente

Melhorias implementadas:
    - Detecção de colisão de nomes
    - Logs verbosos opcionais
    - Iteração segura sobre dicionários
    - Normalização extensível
    - Uso de pathlib para manipulação de arquivos
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Set, Callable, Optional


class SchemaRenamer:
    """Classe para renomear schemas e atualizar suas referências."""

    def __init__(self, openapi_path: str, verbose: bool = False, normalizer_func: Optional[Callable[[str], str]] = None):
        """
        Inicializa o renomeador com o caminho do arquivo OpenAPI.

        Args:
            openapi_path: Caminho para o arquivo openapi.json
            verbose: Se True, mostra logs detalhados durante a execução
            normalizer_func: Função customizada para normalizar nomes (padrão: remove espaços)
        """
        self.openapi_path = Path(openapi_path)
        self.verbose = verbose
        self.normalize = normalizer_func or self._default_normalizer
        self.openapi_doc = None
        self.rename_map = {}  # nome_antigo -> nome_novo
        self.references_updated = 0

    def _default_normalizer(self, name: str) -> str:
        """
        Função padrão de normalização que remove espaços.

        Args:
            name: Nome original

        Returns:
            Nome normalizado sem espaços
        """
        return name.replace(' ', '')

    def load_document(self) -> None:
        """Carrega o documento OpenAPI."""
        if not self.openapi_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.openapi_path}")

        try:
            with open(self.openapi_path, 'r', encoding='utf-8') as file:
                self.openapi_doc = json.load(file)
                print(f"✓ Documento OpenAPI carregado: {self.openapi_path}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Erro ao decodificar JSON: {e.msg}", e.doc, e.pos)

    def generate_new_name(self, old_name: str) -> str:
        """
        Gera um novo nome usando a função de normalização.

        Args:
            old_name: Nome original

        Returns:
            Novo nome normalizado
        """
        return self.normalize(old_name)

    def _check_name_collisions(self, schemas_to_rename: list) -> None:
        """
        Verifica se há colisões de nomes antes da renomeação.

        Args:
            schemas_to_rename: Lista de tuplas (nome_antigo, nome_novo)

        Raises:
            ValueError: Se uma colisão for detectada
        """
        # Verificar colisões entre nomes novos
        new_names_seen = set()
        for old_name, new_name in schemas_to_rename:
            if new_name in new_names_seen:
                raise ValueError(
                    f"Colisão de nomes detectada! Múltiplos schemas seriam renomeados para '{new_name}'. "
                    f"Verifique os schemas de origem e resolva manualmente."
                )
            new_names_seen.add(new_name)

        # Verificar colisões com schemas existentes que não serão renomeados
        if "components" in self.openapi_doc and "schemas" in self.openapi_doc["components"]:
            existing_schemas = set(self.openapi_doc["components"]["schemas"].keys())
            schemas_being_renamed = {old_name for old_name, _ in schemas_to_rename}
            existing_untouched = existing_schemas - schemas_being_renamed

            for _, new_name in schemas_to_rename:
                if new_name in existing_untouched:
                    raise ValueError(
                        f"Colisão de nomes detectada! O nome '{new_name}' já existe no documento. "
                        f"Resolva manualmente antes de executar a renomeação."
                    )

    def rename_schemas_with_spaces(self) -> None:
        """
        Fase 1: Renomeia todos os schemas que contêm espaços.
        """
        print("\n🔄 Fase 1: Renomeando schemas com espaços...")

        # Verificar se existe components.schemas
        if "components" not in self.openapi_doc:
            print("⚠️  Nenhum objeto 'components' encontrado")
            return

        if "schemas" not in self.openapi_doc["components"]:
            print("⚠️  Nenhum objeto 'schemas' encontrado em components")
            return

        schemas = self.openapi_doc["components"]["schemas"]
        schemas_to_rename = []

        # Identificar schemas que precisam ser renomeados (iteração segura)
        for schema_name in list(schemas.keys()):
            if ' ' in schema_name:
                new_name = self.generate_new_name(schema_name)
                schemas_to_rename.append((schema_name, new_name))
                self.rename_map[schema_name] = new_name

        if not schemas_to_rename:
            print("✓ Nenhum schema com espaços encontrado")
            return

        # Verificar colisões antes de executar a renomeação
        print(f"🔍 Verificando colisões de nomes para {len(schemas_to_rename)} schemas...")
        self._check_name_collisions(schemas_to_rename)
        print("✓ Nenhuma colisão de nomes detectada")

        print(f"📋 Encontrados {len(schemas_to_rename)} schemas para renomear:")

        # Executar renomeação
        for old_name, new_name in schemas_to_rename:
            # Mover schema para novo nome
            schemas[new_name] = schemas[old_name]
            del schemas[old_name]
            print(f"  • '{old_name}' → '{new_name}'")

        print(f"✓ {len(schemas_to_rename)} schemas renomeados com sucesso")

    def update_references_recursive(self, obj: Any) -> Any:
        """
        Atualiza referências recursivamente em qualquer parte do documento.

        Args:
            obj: Objeto a ser processado

        Returns:
            Objeto com referências atualizadas
        """
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str):
                    # Verificar se é uma referência para components/schemas
                    if value.startswith("#/components/schemas/"):
                        schema_name = value.replace("#/components/schemas/", "")
                        if schema_name in self.rename_map:
                            new_ref = f"#/components/schemas/{self.rename_map[schema_name]}"
                            result[key] = new_ref
                            self.references_updated += 1
                            if self.verbose:
                                print(f"    📎 Referência atualizada: '{value}' → '{new_ref}'")
                        else:
                            result[key] = value
                    else:
                        result[key] = value
                else:
                    result[key] = self.update_references_recursive(value)
            return result
        elif isinstance(obj, list):
            return [self.update_references_recursive(item) for item in obj]
        else:
            return obj

    def update_all_references(self) -> None:
        """
        Fase 2: Atualiza todas as referências $ref no documento.
        """
        print("\n🔗 Fase 2: Atualizando referências...")

        if not self.rename_map:
            print("✓ Nenhuma referência para atualizar")
            return

        print(f"🔍 Procurando referências para {len(self.rename_map)} schemas renomeados...")
        if not self.verbose:
            print("   (use --verbose para ver detalhes de cada referência)")

        # Executar busca recursiva e atualização
        self.openapi_doc = self.update_references_recursive(self.openapi_doc)

        if self.references_updated > 0:
            print(f"✓ {self.references_updated} referências atualizadas")
        else:
            print("✓ Nenhuma referência encontrada para atualizar")

    def validate_references(self) -> None:
        """
        Valida se todas as referências ainda são válidas após as alterações.
        """
        print("\n🔍 Validando referências...")

        # Coletar todas as referências no documento
        references = set()
        self._collect_references_recursive(self.openapi_doc, references)

        # Coletar schemas disponíveis
        available_schemas = set()
        if ("components" in self.openapi_doc and
            "schemas" in self.openapi_doc["components"]):
            available_schemas = set(self.openapi_doc["components"]["schemas"].keys())

        # Verificar referências quebradas
        broken_refs = []
        for ref in references:
            if ref.startswith("#/components/schemas/"):
                schema_name = ref.replace("#/components/schemas/", "")
                if schema_name not in available_schemas:
                    broken_refs.append(ref)

        if broken_refs:
            print(f"⚠️  {len(broken_refs)} referências quebradas encontradas:")
            for ref in broken_refs:
                print(f"    • {ref}")
            raise ValueError(f"Encontradas {len(broken_refs)} referências quebradas. Verifique o documento.")
        else:
            print("✓ Todas as referências estão válidas")

    def _collect_references_recursive(self, obj: Any, references: Set[str]) -> None:
        """
        Coleta todas as referências $ref recursivamente.

        Args:
            obj: Objeto a ser processado
            references: Set para coletar as referências
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str):
                    references.add(value)
                else:
                    self._collect_references_recursive(value, references)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_references_recursive(item, references)

    def save_document(self) -> None:
        """Salva o documento OpenAPI modificado."""
        print(f"\n💾 Salvando documento modificado...")

        with open(self.openapi_path, 'w', encoding='utf-8') as file:
            json.dump(self.openapi_doc, file, indent=2, ensure_ascii=False)

        print(f"✓ Arquivo salvo: {self.openapi_path}")

    def generate_summary_report(self) -> None:
        """Gera um relatório resumo das alterações."""
        print("\n" + "=" * 60)
        print("📊 RELATÓRIO DE ALTERAÇÕES")
        print("=" * 60)

        if self.rename_map:
            print(f"🔄 Schemas renomeados: {len(self.rename_map)}")
            for old_name, new_name in self.rename_map.items():
                print(f"   • {old_name} → {new_name}")
        else:
            print("🔄 Nenhum schema foi renomeado")

        print(f"🔗 Referências atualizadas: {self.references_updated}")

        print("\n✅ Processo concluído com sucesso!")
        print("   • Todos os nomes de schemas agora são válidos (sem espaços)")
        print("   • Todas as referências foram atualizadas automaticamente")
        print("   • O documento OpenAPI está íntegro e funcional")
        print("   • Nenhuma colisão de nomes foi detectada")

    def fix_schemas_and_references(self) -> None:
        """Executa o processo completo de correção."""
        print("🚀 Iniciando correção de schemas e referências...")
        if self.verbose:
            print("   (Modo verboso ativado)")
        print("=" * 60)

        try:
            # Carregar documento
            self.load_document()

            # Fase 1: Renomear schemas
            self.rename_schemas_with_spaces()

            # Fase 2: Atualizar referências
            self.update_all_references()

            # Validar resultado
            self.validate_references()

            # Salvar documento
            self.save_document()

            # Gerar relatório
            self.generate_summary_report()

        except Exception as e:
            print(f"\n❌ Erro durante a correção: {e}")
            sys.exit(1)


def create_custom_normalizer() -> Callable[[str], str]:
    """
    Exemplo de como criar um normalizador customizado.

    Returns:
        Função que remove espaços e converte para CamelCase
    """
    def camel_case_normalizer(name: str) -> str:
        """Converte para CamelCase removendo espaços."""
        words = name.split()
        return ''.join(word.capitalize() for word in words)

    return camel_case_normalizer


def main():
    """Função principal que processa argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Corrige nomes de schemas OpenAPI e suas referências",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s openapi.json
  %(prog)s openapi.json --verbose

Este script irá:
  1. Verificar colisões de nomes
  2. Renomear schemas com espaços (ex: 'Banner V1' → 'BannerV1')
  3. Atualizar todas as referências $ref automaticamente
  4. Validar a integridade do documento final
        """
    )

    parser.add_argument(
        'openapi_path',
        help='Caminho para o arquivo openapi.json'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostra logs detalhados durante a execução'
    )

    # Argumento oculto para demonstrar extensibilidade
    parser.add_argument(
        '--camel-case',
        action='store_true',
        help='Usar normalização CamelCase (para demonstração)'
    )

    args = parser.parse_args()

    # Escolher função de normalização
    normalizer = create_custom_normalizer() if args.camel_case else None

    # Executar correção
    renamer = SchemaRenamer(
        openapi_path=args.openapi_path,
        verbose=args.verbose,
        normalizer_func=normalizer
    )
    renamer.fix_schemas_and_references()


if __name__ == "__main__":
    main()
