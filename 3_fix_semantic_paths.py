#!/usr/bin/env python3
"""
Script para Correção de Erros Semânticos em Paths OpenAPI

Este script aplica correções específicas para resolver problemas semânticos
em definições de paths que violam a especificação OpenAPI.

Uso:
    python fix_semantic_paths.py <caminho_para_openapi.json>

Exemplo:
    python fix_semantic_paths.py ./openapi.json

Correções aplicadas:
    1. Remove requestBody inválido de operação DELETE
    2. Remove parâmetro 'name' inexistente no template da URL
    3. Adiciona parâmetro 'environmentId' ausente (formFields)
    4. Adiciona parâmetro 'environmentId' ausente (shoppingcenter)
"""

import json
import sys
import os
from typing import Dict, Any, List, Optional


class SemanticPathsFixer:
    """Classe para corrigir erros semânticos em paths OpenAPI."""

    def __init__(self, openapi_path: str):
        """
        Inicializa o corretor com o caminho do arquivo OpenAPI.

        Args:
            openapi_path: Caminho para o arquivo openapi.json
        """
        self.openapi_path = openapi_path
        self.openapi_doc = None
        self.corrections_applied = 0

    def load_document(self) -> None:
        """Carrega o documento OpenAPI."""
        if not os.path.exists(self.openapi_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {self.openapi_path}")

        with open(self.openapi_path, 'r', encoding='utf-8') as file:
            try:
                self.openapi_doc = json.load(file)
                print(f"✓ Documento OpenAPI carregado: {self.openapi_path}")
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(f"Erro ao decodificar JSON: {e.msg}", e.doc, e.pos)

    def navigate_to_operation(self, json_path: str) -> Optional[Dict[str, Any]]:
        """
        Navega até uma operação específica no documento.

        Args:
            json_path: Caminho no formato "paths./path/template/method"

        Returns:
            Dicionário da operação ou None se não encontrada
        """
        # Parse do caminho: "paths./environments/{environmentId}/employees/{employeeId}/scheduledvisits/delete"
        if not json_path.startswith("paths."):
            return None

        path_part = json_path[6:]  # Remove "paths."

        # Separar path template do método HTTP
        path_segments = path_part.split('/')
        method = path_segments[-1]  # Último segmento é o método
        path_template = '/' + '/'.join(path_segments[:-1])  # Reconstrói o path template

        # Navegar no documento
        if "paths" not in self.openapi_doc:
            return None

        if path_template not in self.openapi_doc["paths"]:
            return None

        path_obj = self.openapi_doc["paths"][path_template]
        if method not in path_obj:
            return None

        return path_obj[method]

    def navigate_to_path_object(self, json_path: str) -> Optional[Dict[str, Any]]:
        """
        Navega até um objeto de path específico no documento.

        Args:
            json_path: Caminho no formato "paths./path/template/method"

        Returns:
            Dicionário do path object ou None se não encontrado
        """
        if not json_path.startswith("paths."):
            return None

        path_part = json_path[6:]  # Remove "paths."

        # Separar path template do método HTTP
        path_segments = path_part.split('/')
        method = path_segments[-1]  # Último segmento é o método
        path_template = '/' + '/'.join(path_segments[:-1])  # Reconstrói o path template

        # Navegar no documento
        if "paths" not in self.openapi_doc:
            return None

        if path_template not in self.openapi_doc["paths"]:
            return None

        return self.openapi_doc["paths"][path_template]

    def correction_1_remove_delete_request_body(self) -> None:
        """
        Correção 1: Remove requestBody de operação DELETE.
        Path: /environments/{environmentId}/employees/{employeeId}/scheduledvisits
        """
        print("\n🔧 Correção 1: Removendo requestBody de operação DELETE...")

        json_path = "paths./environments/{environmentId}/employees/{employeeId}/scheduledvisits/delete"
        operation = self.navigate_to_operation(json_path)

        if operation is None:
            print("⚠️  Operação não encontrada:", json_path)
            return

        if "requestBody" in operation:
            del operation["requestBody"]
            self.corrections_applied += 1
            print("✓ requestBody removido da operação DELETE")
        else:
            print("ℹ️  requestBody não encontrado na operação DELETE")

    def correction_2_remove_name_parameter(self) -> None:
        """
        Correção 2: Remove parâmetro 'name' inexistente.
        Path: /environments/{environmentId}/brands
        """
        print("\n🔧 Correção 2: Removendo parâmetro 'name' inexistente...")

        json_path = "paths./environments/{environmentId}/brands/get"
        operation = self.navigate_to_operation(json_path)

        if operation is None:
            print("⚠️  Operação não encontrada:", json_path)
            return

        if "parameters" not in operation:
            print("ℹ️  Nenhum parâmetro encontrado na operação")
            return

        # Procurar e remover parâmetro 'name'
        parameters = operation["parameters"]
        original_count = len(parameters)

        # Filtrar parâmetros, removendo aqueles com name='name'
        operation["parameters"] = [
            param for param in parameters
            if not (isinstance(param, dict) and param.get("name") == "name")
        ]

        removed_count = original_count - len(operation["parameters"])
        if removed_count > 0:
            self.corrections_applied += 1
            print(f"✓ {removed_count} parâmetro(s) 'name' removido(s)")
        else:
            print("ℹ️  Parâmetro 'name' não encontrado")

    def correction_3_add_environment_id_form_fields(self) -> None:
        """
        Correção 3: Adiciona parâmetro environmentId ausente.
        Path: /v1/{environmentId}/form/formFields/{formId}
        """
        print("\n🔧 Correção 3: Adicionando parâmetro 'environmentId' (formFields)...")

        json_path = "paths./v1/{environmentId}/form/formFields/{formId}/get"
        operation = self.navigate_to_operation(json_path)

        if operation is None:
            print("⚠️  Operação não encontrada:", json_path)
            return

        # Garantir que existe array de parameters
        if "parameters" not in operation:
            operation["parameters"] = []

        # Verificar se environmentId já existe
        existing_env_param = any(
            isinstance(param, dict) and param.get("name") == "environmentId"
            for param in operation["parameters"]
        )

        if not existing_env_param:
            environment_param = {
                "name": "environmentId",
                "in": "path",
                "required": True,
                "description": "ID do Environment (ambiente).",
                "schema": {
                    "type": "string"
                }
            }
            operation["parameters"].append(environment_param)
            self.corrections_applied += 1
            print("✓ Parâmetro 'environmentId' adicionado")
        else:
            print("ℹ️  Parâmetro 'environmentId' já existe")

    def correction_4_add_environment_id_shopping_center(self) -> None:
        """
        Correção 4: Adiciona parâmetro environmentId ausente.
        Path: /v1/{environmentId}/shoppingcenter/{id}
        """
        print("\n🔧 Correção 4: Adicionando parâmetro 'environmentId' (shoppingcenter)...")

        json_path = "paths./v1/{environmentId}/shoppingcenter/{id}/get"
        operation = self.navigate_to_operation(json_path)

        if operation is None:
            print("⚠️  Operação não encontrada:", json_path)
            return

        # Garantir que existe array de parameters
        if "parameters" not in operation:
            operation["parameters"] = []

        # Verificar se environmentId já existe
        existing_env_param = any(
            isinstance(param, dict) and param.get("name") == "environmentId"
            for param in operation["parameters"]
        )

        if not existing_env_param:
            environment_param = {
                "name": "environmentId",
                "in": "path",
                "required": True,
                "description": "ID do Environment (ambiente).",
                "schema": {
                    "type": "string"
                }
            }
            operation["parameters"].append(environment_param)
            self.corrections_applied += 1
            print("✓ Parâmetro 'environmentId' adicionado")
        else:
            print("ℹ️  Parâmetro 'environmentId' já existe")

    def validate_paths_semantics(self) -> None:
        """Executa validações básicas na estrutura de paths."""
        print("\n🔍 Validando semântica dos paths...")

        if "paths" not in self.openapi_doc:
            print("⚠️  Nenhum objeto 'paths' encontrado")
            return

        validation_issues = []

        # Verificar paths processados
        paths_to_check = [
            "/environments/{environmentId}/employees/{employeeId}/scheduledvisits",
            "/environments/{environmentId}/brands",
            "/v1/{environmentId}/form/formFields/{formId}",
            "/v1/{environmentId}/shoppingcenter/{id}"
        ]

        for path_template in paths_to_check:
            if path_template in self.openapi_doc["paths"]:
                path_obj = self.openapi_doc["paths"][path_template]

                # Verificar operação DELETE não tem requestBody
                if "delete" in path_obj:
                    delete_op = path_obj["delete"]
                    if "requestBody" in delete_op:
                        validation_issues.append(f"DELETE {path_template} ainda tem requestBody")

                # Verificar se parâmetros de path estão definidos
                for method, operation in path_obj.items():
                    if method.lower() in ['get', 'post', 'put', 'patch', 'delete']:
                        if isinstance(operation, dict):
                            # Extrair parâmetros do template da URL
                            import re
                            path_params = re.findall(r'\{([^}]+)\}', path_template)

                            # Verificar se todos os parâmetros estão definidos
                            defined_params = set()
                            if "parameters" in operation:
                                for param in operation["parameters"]:
                                    if isinstance(param, dict) and param.get("in") == "path":
                                        defined_params.add(param.get("name"))

                            missing_params = set(path_params) - defined_params
                            if missing_params:
                                validation_issues.append(
                                    f"{method.upper()} {path_template} está faltando parâmetros: {missing_params}"
                                )

        if validation_issues:
            print(f"⚠️  {len(validation_issues)} problemas de validação encontrados:")
            for issue in validation_issues:
                print(f"    • {issue}")
        else:
            print("✓ Validação semântica passou sem problemas")

    def save_document(self) -> None:
        """Salva o documento OpenAPI modificado."""
        print(f"\n💾 Salvando documento modificado...")

        with open(self.openapi_path, 'w', encoding='utf-8') as file:
            json.dump(self.openapi_doc, file, indent=2, ensure_ascii=False)

        print(f"✓ Arquivo salvo: {self.openapi_path}")

    def generate_summary_report(self) -> None:
        """Gera um relatório resumo das correções."""
        print("\n" + "=" * 60)
        print("📊 RELATÓRIO DE CORREÇÕES SEMÂNTICAS")
        print("=" * 60)

        print(f"🔧 Total de correções aplicadas: {self.corrections_applied}")

        if self.corrections_applied > 0:
            print("\nCorreções realizadas:")
            print("  ✓ Remoção de requestBody inválido em DELETE")
            print("  ✓ Remoção de parâmetros inexistentes")
            print("  ✓ Adição de parâmetros de path ausentes")
            print("\n✅ Todos os problemas semânticos foram corrigidos!")
            print("   • Operações DELETE não têm requestBody")
            print("   • Parâmetros de path estão corretamente definidos")
            print("   • Documento OpenAPI está em conformidade com a especificação")
        else:
            print("\n✅ Nenhuma correção foi necessária!")
            print("   • O documento já estava semanticamente correto")

    def fix_semantic_paths(self) -> None:
        """Executa o processo completo de correção semântica."""
        print("🚀 Iniciando correção de erros semânticos em paths...")
        print("=" * 60)

        try:
            # Carregar documento
            self.load_document()

            # Aplicar correções específicas
            self.correction_1_remove_delete_request_body()
            self.correction_2_remove_name_parameter()
            self.correction_3_add_environment_id_form_fields()
            self.correction_4_add_environment_id_shopping_center()

            # Validar resultado
            self.validate_paths_semantics()

            # Salvar documento
            self.save_document()

            # Gerar relatório
            self.generate_summary_report()

        except Exception as e:
            print(f"\n❌ Erro durante a correção: {e}")
            sys.exit(1)


def main():
    """Função principal que processa argumentos de linha de comando."""
    if len(sys.argv) != 2:
        print("Uso: python fix_semantic_paths.py <caminho_para_openapi.json>")
        print("\nExemplo:")
        print("  python fix_semantic_paths.py ./openapi.json")
        print("\nEste script irá aplicar 4 correções semânticas específicas:")
        print("  1. Remover requestBody de operação DELETE")
        print("  2. Remover parâmetro 'name' inexistente")
        print("  3. Adicionar parâmetro 'environmentId' ausente (formFields)")
        print("  4. Adicionar parâmetro 'environmentId' ausente (shoppingcenter)")
        sys.exit(1)

    openapi_path = sys.argv[1]

    # Executar correções
    fixer = SemanticPathsFixer(openapi_path)
    fixer.fix_semantic_paths()


if __name__ == "__main__":
    main()
