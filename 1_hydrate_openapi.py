#!/usr/bin/env python3
"""
Script Mestre de Hidratação OpenAPI

Este script orquestra o enriquecimento completo de uma especificação OpenAPI
usando arquivos de configuração e dicionários como fontes da verdade.

Dependências:
    pip install PyYAML

Uso:
    python hydrate_openapi.py openapi.json config.yaml dictionary.json summaries-pt-br.json

Transformações aplicadas (em ordem):
    1. Injeção de metadados (info, servers)
    2. Injeção de segurança (securitySchemes, security)
    3. Injeção de schemas comuns
    4. Tradução recursiva de placeholders
    5. Injeção de summaries das operações
    6. Injeção de respostas de erro padrão
    7. Adição de parâmetros globais
    8. Ordenação de tags
"""

import json
import sys
import os
import re
from typing import Dict, Any, List
import yaml


class OpenAPIHydrator:
    """Classe principal para hidratação de especificações OpenAPI."""

    def __init__(self, openapi_path: str, config_path: str, dictionary_path: str, summaries_path: str):
        """
        Inicializa o hidratador com os caminhos dos arquivos.

        Args:
            openapi_path: Caminho para o arquivo openapi.json
            config_path: Caminho para o arquivo config.yaml
            dictionary_path: Caminho para o arquivo dictionary.json
            summaries_path: Caminho para o arquivo summaries-pt-br.json
        """
        self.openapi_path = openapi_path
        self.config_path = config_path
        self.dictionary_path = dictionary_path
        self.summaries_path = summaries_path

        # Dados carregados
        self.openapi_doc = None
        self.config = None
        self.dictionary = None
        self.summaries = None

    def load_files(self) -> None:
        """Carrega todos os arquivos de entrada."""
        print("📂 Carregando arquivos de entrada...")

        # Carregar OpenAPI JSON
        with open(self.openapi_path, 'r', encoding='utf-8') as f:
            self.openapi_doc = json.load(f)
        print(f"✓ OpenAPI carregado: {self.openapi_path}")

        # Carregar Config YAML
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        print(f"✓ Config carregado: {self.config_path}")

        # Carregar Dictionary JSON
        with open(self.dictionary_path, 'r', encoding='utf-8') as f:
            self.dictionary = json.load(f)
        print(f"✓ Dictionary carregado: {self.dictionary_path}")

        # Carregar Summaries JSON
        with open(self.summaries_path, 'r', encoding='utf-8') as f:
            self.summaries = json.load(f)
        print(f"✓ Summaries carregado: {self.summaries_path}")

    def inject_metadata(self) -> None:
        """Injeta metadados (info e servers) do config."""
        print("\n🏷️  Injetando metadados...")

        # Injetar info
        self.openapi_doc["info"] = self.config["metadata"]["info"]
        print("✓ Objeto 'info' injetado")

        # Injetar servers
        self.openapi_doc["servers"] = self.config["metadata"]["servers"]
        print("✓ Array 'servers' injetado")

    def inject_security(self) -> None:
        """Injeta esquemas de segurança e configuração global."""
        print("\n🔒 Injetando configurações de segurança...")

        # Garantir que existe components
        if "components" not in self.openapi_doc:
            self.openapi_doc["components"] = {}

        # Garantir que existe securitySchemes
        if "securitySchemes" not in self.openapi_doc["components"]:
            self.openapi_doc["components"]["securitySchemes"] = {}

        # Injetar security schemes do config
        for scheme_name, scheme_config in self.config["security_schemes"].items():
            self.openapi_doc["components"]["securitySchemes"][scheme_name] = scheme_config
            print(f"✓ Security scheme '{scheme_name}' injetado")

        # Injetar security global (assumindo BasicAuth como padrão)
        self.openapi_doc["security"] = [{"BasicAuth": []}]
        print("✓ Configuração de segurança global aplicada")

    def inject_common_schemas(self) -> None:
        """Injeta schemas comuns em components.schemas."""
        print("\n📋 Injetando schemas comuns...")

        # Garantir que existe components.schemas
        if "components" not in self.openapi_doc:
            self.openapi_doc["components"] = {}
        if "schemas" not in self.openapi_doc["components"]:
            self.openapi_doc["components"]["schemas"] = {}

        # Injetar schemas comuns
        for schema_name, schema_def in self.config["common_schemas"].items():
            self.openapi_doc["components"]["schemas"][schema_name] = schema_def
            print(f"✓ Schema comum '{schema_name}' injetado")

    def translate_placeholders_recursive(self, obj: Any) -> Any:
        """
        Traduz placeholders recursivamente no objeto.

        Args:
            obj: Objeto a ser processado

        Returns:
            Objeto com placeholders traduzidos
        """
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # Traduzir chave se for um placeholder
                new_key = self.dictionary.get(key, key)
                result[new_key] = self.translate_placeholders_recursive(value)
            return result
        elif isinstance(obj, list):
            return [self.translate_placeholders_recursive(item) for item in obj]
        elif isinstance(obj, str):
            # Traduzir string se for um placeholder
            return self.dictionary.get(obj, obj)
        else:
            return obj

    def translate_placeholders(self) -> None:
        """Aplica tradução recursiva de placeholders."""
        print("\n🌐 Traduzindo placeholders...")

        self.openapi_doc = self.translate_placeholders_recursive(self.openapi_doc)
        print(f"✓ {len(self.dictionary)} placeholders processados")

    def inject_summaries(self) -> None:
        """Injeta summaries nas operações usando summaries-pt-br.json."""
        print("\n📝 Injetando summaries das operações...")

        summaries_count = 0

        # Percorrer paths e operações
        if "paths" in self.openapi_doc:
            for path, path_obj in self.openapi_doc["paths"].items():
                if isinstance(path_obj, dict):
                    for method, operation in path_obj.items():
                        if method.lower() in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                            if isinstance(operation, dict) and "operationId" in operation:
                                operation_id = operation["operationId"]
                                if operation_id in self.summaries:
                                    operation["summary"] = self.summaries[operation_id]
                                    summaries_count += 1

        print(f"✓ {summaries_count} summaries injetados")

    def determine_error_response_type(self, path: str) -> str:
        """
        Determina o tipo de resposta de erro baseado no path.

        Args:
            path: Path da operação

        Returns:
            'v3' ou 'legacy'
        """
        # Lógica: v3 para paths que começam com /v3 ou /environments
        if path.startswith('/v3') or path.startswith('/environments'):
            return 'v3'
        return 'legacy'

    def inject_error_responses(self) -> None:
        """Injeta respostas de erro padrão nas operações."""
        print("\n❌ Injetando respostas de erro padrão...")

        operations_updated = 0

        # Percorrer paths e operações
        if "paths" in self.openapi_doc:
            for path, path_obj in self.openapi_doc["paths"].items():
                if isinstance(path_obj, dict):
                    # Determinar tipo de erro para este path
                    error_type = self.determine_error_response_type(path)
                    error_responses = self.config["default_error_responses"][error_type]

                    for method, operation in path_obj.items():
                        if method.lower() in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                            if isinstance(operation, dict):
                                # Garantir que existe responses
                                if "responses" not in operation:
                                    operation["responses"] = {}

                                # Adicionar respostas de erro se não existirem
                                for status_code, error_response in error_responses.items():
                                    if status_code not in operation["responses"]:
                                        operation["responses"][status_code] = error_response
                                        operations_updated += 1

        print(f"✓ Respostas de erro adicionadas a {operations_updated} operações")

    def inject_global_parameters(self) -> None:
        """Adiciona parâmetros globais a todas as operações."""
        print("\n🔧 Injetando parâmetros globais...")

        operations_updated = 0

        # Garantir que existe components.parameters
        if "components" not in self.openapi_doc:
            self.openapi_doc["components"] = {}
        if "parameters" not in self.openapi_doc["components"]:
            self.openapi_doc["components"]["parameters"] = {}

        # Adicionar parâmetros globais a components
        for param_name, param_def in self.config["global_parameters"].items():
            self.openapi_doc["components"]["parameters"][param_name] = param_def

        # Percorrer operações e adicionar referências aos parâmetros
        if "paths" in self.openapi_doc:
            for path, path_obj in self.openapi_doc["paths"].items():
                if isinstance(path_obj, dict):
                    for method, operation in path_obj.items():
                        if method.lower() in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                            if isinstance(operation, dict):
                                # Garantir que existe parameters
                                if "parameters" not in operation:
                                    operation["parameters"] = []

                                # Adicionar referências aos parâmetros globais
                                for param_name in self.config["global_parameters"].keys():
                                    param_ref = {"$ref": f"#/components/parameters/{param_name}"}
                                    if param_ref not in operation["parameters"]:
                                        operation["parameters"].append(param_ref)

                                operations_updated += 1

        print(f"✓ Parâmetros globais adicionados a {operations_updated} operações")

    def apply_tag_ordering(self) -> None:
        """Aplica ordenação de tags conforme configuração."""
        print("\n🏷️  Aplicando ordenação de tags...")

        if "ui_ordering" in self.config and "tag_order" in self.config["ui_ordering"]:
            tag_order = self.config["ui_ordering"]["tag_order"]

            # Coletar tags existentes no documento
            existing_tags = set()
            if "paths" in self.openapi_doc:
                for path_obj in self.openapi_doc["paths"].values():
                    if isinstance(path_obj, dict):
                        for operation in path_obj.values():
                            if isinstance(operation, dict) and "tags" in operation:
                                existing_tags.update(operation["tags"])

            # Criar array de tags ordenado
            ordered_tags = []
            for tag_name in tag_order:
                if tag_name in existing_tags:
                    ordered_tags.append({
                        "name": tag_name,
                        "description": f"Operações relacionadas a {tag_name.lower()}"
                    })

            # Adicionar tags que não estão na ordem configurada
            for tag_name in existing_tags:
                if tag_name not in tag_order:
                    ordered_tags.append({
                        "name": tag_name,
                        "description": f"Operações relacionadas a {tag_name.lower()}"
                    })

            # Aplicar ao documento
            self.openapi_doc["tags"] = ordered_tags
            print(f"✓ {len(ordered_tags)} tags ordenadas")
        else:
            print("⚠️  Configuração de ordenação de tags não encontrada")

    def save_document(self) -> None:
        """Salva o documento OpenAPI modificado."""
        print(f"\n💾 Salvando documento modificado...")

        with open(self.openapi_path, 'w', encoding='utf-8') as f:
            json.dump(self.openapi_doc, f, indent=2, ensure_ascii=False)

        print(f"✓ Arquivo salvo: {self.openapi_path}")

    def hydrate(self) -> None:
        """Executa o processo completo de hidratação."""
        print("🚀 Iniciando hidratação do OpenAPI...")
        print("=" * 50)

        try:
            # Carregar arquivos
            self.load_files()

            # Aplicar transformações em ordem
            self.inject_metadata()
            self.inject_security()
            self.inject_common_schemas()
            self.translate_placeholders()
            self.inject_summaries()
            self.inject_error_responses()
            self.inject_global_parameters()
            self.apply_tag_ordering()

            # Salvar resultado
            self.save_document()

            print("\n" + "=" * 50)
            print("🎉 Hidratação concluída com sucesso!")
            print("\nO arquivo OpenAPI foi enriquecido com:")
            print("  • Metadados completos (info, servers)")
            print("  • Configurações de segurança")
            print("  • Schemas de erro padronizados")
            print("  • Traduções de placeholders")
            print("  • Summaries das operações")
            print("  • Respostas de erro padrão")
            print("  • Parâmetros globais")
            print("  • Ordenação de tags")

        except Exception as e:
            print(f"\n❌ Erro durante a hidratação: {e}")
            sys.exit(1)


def validate_files(openapi_path: str, config_path: str, dictionary_path: str, summaries_path: str) -> None:
    """
    Valida se todos os arquivos de entrada existem.

    Args:
        openapi_path: Caminho para openapi.json
        config_path: Caminho para config.yaml
        dictionary_path: Caminho para dictionary.json
        summaries_path: Caminho para summaries-pt-br.json
    """
    files_to_check = [
        (openapi_path, "OpenAPI JSON"),
        (config_path, "Config YAML"),
        (dictionary_path, "Dictionary JSON"),
        (summaries_path, "Summaries JSON")
    ]

    missing_files = []
    for file_path, file_type in files_to_check:
        if not os.path.exists(file_path):
            missing_files.append(f"{file_type}: {file_path}")

    if missing_files:
        print("❌ Arquivos não encontrados:")
        for missing in missing_files:
            print(f"  • {missing}")
        sys.exit(1)


def main():
    """Função principal que processa argumentos e executa a hidratação."""
    if len(sys.argv) != 5:
        print("Uso: python hydrate_openapi.py <openapi.json> <config.yaml> <dictionary.json> <summaries-pt-br.json>")
        print("\nExemplo:")
        print("  python hydrate_openapi.py openapi.json config.yaml dictionary.json summaries-pt-br.json")
        sys.exit(1)

    openapi_path = sys.argv[1]
    config_path = sys.argv[2]
    dictionary_path = sys.argv[3]
    summaries_path = sys.argv[4]

    # Validar arquivos
    validate_files(openapi_path, config_path, dictionary_path, summaries_path)

    # Executar hidratação
    hydrator = OpenAPIHydrator(openapi_path, config_path, dictionary_path, summaries_path)
    hydrator.hydrate()


if __name__ == "__main__":
    main()
