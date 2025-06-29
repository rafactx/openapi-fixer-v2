#!/usr/bin/env python3
"""
Script de Pós-Refinamento e Verificação Final OpenAPI

Este script atua como uma etapa final de 'linting' e correção no pipeline,
garantindo que erros semânticos específicos e recorrentes sejam corrigidos
de forma definitiva e idempotente.

Uso:
    python3 4_final_verification.py openapi.json

Regras aplicadas:
    RULE-01: Remove requestBody de operações DELETE
    RULE-02: Remove parâmetro 'name' inválido do path brands
    RULE-03: Adiciona parâmetros environmentId ausentes
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


class OpenAPIFinalVerifier:
    """Classe para verificação final e correção de erros semânticos OpenAPI."""

    def __init__(self, openapi_path: str):
        """
        Inicializa o verificador com o caminho do arquivo OpenAPI.

        Args:
            openapi_path: Caminho para o arquivo openapi.json
        """
        self.openapi_path = Path(openapi_path)
        self.openapi_doc = None
        self.corrections_applied = 0
        self.verification_results = []

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

    def get_operation(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """
        Busca uma operação específica no documento.

        Args:
            path: Caminho da URL (ex: "/users/{id}")
            method: Método HTTP (ex: "get", "post")

        Returns:
            Dicionário da operação ou None se não encontrada
        """
        if self.openapi_doc is None:
            return None

        if "paths" not in self.openapi_doc:
            return None

        if path not in self.openapi_doc["paths"]:
            return None

        path_obj = self.openapi_doc["paths"][path]
        if not isinstance(path_obj, dict):
            return None

        return path_obj.get(method.lower())

    def rule_01_no_delete_request_body(self) -> None:
        """
        RULE-01: Garante que nenhuma operação DELETE possua requestBody.

        Itera por todos os paths e operações. Se o método for 'delete',
        verifica a existência da chave 'requestBody' e a remove se existir.
        """
        print("\n🔍 RULE-01: Verificando operações DELETE com requestBody...")

        if self.openapi_doc is None:
            print("   ⚠️  Documento OpenAPI não carregado")
            return

        if "paths" not in self.openapi_doc:
            print("   ⚠️  Nenhum objeto 'paths' encontrado")
            return

        violations_found = 0
        corrections_made = 0

        for path_template, path_obj in self.openapi_doc["paths"].items():
            if not isinstance(path_obj, dict):
                continue

            if "delete" in path_obj:
                delete_operation = path_obj["delete"]
                if isinstance(delete_operation, dict):
                    violations_found += 1
                    print(f"   🔎 Verificando DELETE {path_template}")

                    if "requestBody" in delete_operation:
                        del delete_operation["requestBody"]
                        corrections_made += 1
                        self.corrections_applied += 1
                        print(f"   ✅ Correção aplicada: requestBody removido de DELETE {path_template}")
                    else:
                        print(f"   ✓ OK: DELETE {path_template} não possui requestBody")

        if violations_found == 0:
            print("   ✓ Nenhuma operação DELETE encontrada")
        else:
            print(f"   📊 Verificadas {violations_found} operações DELETE, {corrections_made} correções aplicadas")

        self.verification_results.append({
            "rule": "RULE-01_NO_DELETE_REQUEST_BODY",
            "operations_checked": violations_found,
            "corrections_applied": corrections_made
        })

    def rule_02_no_mismatched_path_params(self) -> None:
        """
        RULE-02: Remove parâmetro 'name' inválido do path brands.

        Navega até a operação GET do path '/environments/{environmentId}/brands'
        e remove qualquer parâmetro que tenha 'name': 'name'.
        """
        print("\n🔍 RULE-02: Verificando parâmetro 'name' inválido em brands...")

        target_path = "/environments/{environmentId}/brands"
        target_method = "get"

        operation = self.get_operation(target_path, target_method)

        if operation is None:
            print(f"   ⚠️  Operação {target_method.upper()} {target_path} não encontrada")
            self.verification_results.append({
                "rule": "RULE-02_NO_MISMATCHED_PATH_PARAMS",
                "operation_found": False,
                "corrections_applied": 0
            })
            return

        print(f"   🔎 Verificando parâmetros em {target_method.upper()} {target_path}")

        if "parameters" not in operation:
            print("   ✓ OK: Nenhum parâmetro definido na operação")
            self.verification_results.append({
                "rule": "RULE-02_NO_MISMATCHED_PATH_PARAMS",
                "operation_found": True,
                "corrections_applied": 0
            })
            return

        original_count = len(operation["parameters"])

        # Filtrar parâmetros, removendo aqueles com name='name'
        operation["parameters"] = [
            param for param in operation["parameters"]
            if not (isinstance(param, dict) and param.get("name") == "name")
        ]

        removed_count = original_count - len(operation["parameters"])

        if removed_count > 0:
            self.corrections_applied += removed_count
            print(f"   ✅ Correção aplicada: {removed_count} parâmetro(s) 'name' removido(s)")
        else:
            print("   ✓ OK: Parâmetro 'name' não encontrado")

        self.verification_results.append({
            "rule": "RULE-02_NO_MISMATCHED_PATH_PARAMS",
            "operation_found": True,
            "corrections_applied": removed_count
        })

    def rule_03_ensure_path_params_defined(self) -> None:
        """
        RULE-03: Garante que parâmetros environmentId estejam definidos.

        Para cada target especificado, verifica se um parâmetro 'environmentId'
        com 'in': 'path' existe. Se não existir, adiciona o parâmetro completo.
        """
        print("\n🔍 RULE-03: Verificando parâmetros environmentId ausentes...")

        targets = [
            {
                "target_path": "/v1/{environmentId}/form/formFields/{formId}",
                "target_method": "get"
            },
            {
                "target_path": "/v1/{environmentId}/shoppingcenter/{id}",
                "target_method": "get"
            }
        ]

        parameter_payload = {
            "name": "environmentId",
            "in": "path",
            "description": "ID do Environment (ambiente). Adicionado via script de correção.",
            "required": True,
            "schema": {
                "type": "string"
            }
        }

        total_operations_checked = 0
        total_corrections_made = 0

        for target in targets:
            path = target["target_path"]
            method = target["target_method"]

            print(f"   🔎 Verificando {method.upper()} {path}")

            operation = self.get_operation(path, method)

            if operation is None:
                print(f"   ⚠️  Operação {method.upper()} {path} não encontrada")
                continue

            total_operations_checked += 1

            # Garantir que existe array de parameters
            if "parameters" not in operation:
                operation["parameters"] = []

            # Verificar se environmentId já existe
            existing_env_param = any(
                isinstance(param, dict) and
                param.get("name") == "environmentId" and
                param.get("in") == "path"
                for param in operation["parameters"]
            )

            if not existing_env_param:
                operation["parameters"].append(parameter_payload.copy())
                total_corrections_made += 1
                self.corrections_applied += 1
                print(f"   ✅ Correção aplicada: parâmetro 'environmentId' adicionado")
            else:
                print(f"   ✓ OK: parâmetro 'environmentId' já existe")

        print(f"   📊 Verificadas {total_operations_checked} operações, {total_corrections_made} correções aplicadas")

        self.verification_results.append({
            "rule": "RULE-03_ENSURE_PATH_PARAMS_DEFINED",
            "operations_checked": total_operations_checked,
            "corrections_applied": total_corrections_made
        })

    def run_semantic_validation(self) -> None:
        """
        Executa validação semântica básica para confirmar que as regras foram aplicadas.
        """
        print("\n🔍 Executando validação semântica final...")

        if self.openapi_doc is None:
            print("   ⚠️  Documento OpenAPI não carregado")
            raise ValueError("Documento OpenAPI não foi carregado para validação")

        validation_issues = []

        # Validar RULE-01: Nenhuma operação DELETE deve ter requestBody
        if "paths" in self.openapi_doc:
            for path_template, path_obj in self.openapi_doc["paths"].items():
                if isinstance(path_obj, dict) and "delete" in path_obj:
                    delete_op = path_obj["delete"]
                    if isinstance(delete_op, dict) and "requestBody" in delete_op:
                        validation_issues.append(f"DELETE {path_template} ainda possui requestBody")

        # Validar RULE-02: Path brands não deve ter parâmetro 'name'
        brands_operation = self.get_operation("/environments/{environmentId}/brands", "get")
        if brands_operation and "parameters" in brands_operation:
            for param in brands_operation["parameters"]:
                if isinstance(param, dict) and param.get("name") == "name":
                    validation_issues.append("Path brands ainda possui parâmetro 'name' inválido")

        # Validar RULE-03: Paths específicos devem ter environmentId
        required_params_paths = [
            "/v1/{environmentId}/form/formFields/{formId}",
            "/v1/{environmentId}/shoppingcenter/{id}"
        ]

        for path in required_params_paths:
            operation = self.get_operation(path, "get")
            if operation:
                has_env_param = False
                if "parameters" in operation:
                    has_env_param = any(
                        isinstance(param, dict) and
                        param.get("name") == "environmentId" and
                        param.get("in") == "path"
                        for param in operation["parameters"]
                    )

                if not has_env_param:
                    validation_issues.append(f"GET {path} não possui parâmetro environmentId definido")

        if validation_issues:
            print(f"   ⚠️  {len(validation_issues)} problemas de validação encontrados:")
            for issue in validation_issues:
                print(f"      • {issue}")
            raise ValueError(f"Validação final falhou: {len(validation_issues)} problemas encontrados")
        else:
            print("   ✅ Validação semântica final: PASSOU")

    def save_document(self) -> None:
        """Salva o documento OpenAPI modificado."""
        print(f"\n💾 Salvando documento verificado...")

        with open(self.openapi_path, 'w', encoding='utf-8') as file:
            json.dump(self.openapi_doc, file, indent=2, ensure_ascii=False)

        print(f"✓ Arquivo salvo: {self.openapi_path}")

    def generate_final_report(self) -> None:
        """Gera um relatório final das verificações e correções."""
        print("\n" + "=" * 70)
        print("📊 RELATÓRIO DE VERIFICAÇÃO FINAL")
        print("=" * 70)

        print(f"🔧 Total de correções aplicadas: {self.corrections_applied}")
        print(f"📋 Regras verificadas: {len(self.verification_results)}")

        if self.verification_results:
            print("\nDetalhes por regra:")
            for result in self.verification_results:
                rule_name = result["rule"].replace("_", " ").title()
                print(f"  ✓ {rule_name}")

                if "operations_checked" in result:
                    print(f"    • Operações verificadas: {result['operations_checked']}")
                if "operation_found" in result:
                    print(f"    • Operação encontrada: {'Sim' if result['operation_found'] else 'Não'}")

                corrections = result.get("corrections_applied", 0)
                print(f"    • Correções aplicadas: {corrections}")

        if self.corrections_applied > 0:
            print("\n✅ Verificação final concluída com correções!")
            print("   • Todas as regras semânticas foram aplicadas")
            print("   • Documento OpenAPI está em conformidade")
            print("   • Pipeline de correção finalizado com sucesso")
        else:
            print("\n✅ Verificação final concluída!")
            print("   • Nenhuma correção foi necessária")
            print("   • Documento já estava em conformidade com todas as regras")

    def run_final_verification(self) -> None:
        """Executa o processo completo de verificação final."""
        print("🚀 Iniciando verificação final e linting OpenAPI...")
        print("=" * 70)

        try:
            # Carregar documento
            self.load_document()

            # Aplicar todas as regras de verificação
            self.rule_01_no_delete_request_body()
            self.rule_02_no_mismatched_path_params()
            self.rule_03_ensure_path_params_defined()

            # Executar validação semântica final
            self.run_semantic_validation()

            # Salvar documento (apenas se houve mudanças)
            if self.corrections_applied > 0:
                self.save_document()
            else:
                print("\n💾 Nenhuma alteração necessária - arquivo não modificado")

            # Gerar relatório final
            self.generate_final_report()

        except Exception as e:
            print(f"\n❌ Erro durante a verificação final: {e}")
            sys.exit(1)


def main():
    """Função principal que processa argumentos de linha de comando."""
    if len(sys.argv) != 2:
        print("Uso: python 4_final_verification_and_linting.py <caminho_para_openapi.json>")
        print("\nExemplo:")
        print("  python 4_final_verification_and_linting.py ./openapi.json")
        print("\nEste script aplica verificação final e correção de 3 regras semânticas:")
        print("  RULE-01: Remove requestBody de operações DELETE")
        print("  RULE-02: Remove parâmetro 'name' inválido do path brands")
        print("  RULE-03: Adiciona parâmetros environmentId ausentes")
        print("\nO script é idempotente e pode ser executado múltiplas vezes.")
        sys.exit(1)

    openapi_path = sys.argv[1]

    # Executar verificação final
    verifier = OpenAPIFinalVerifier(openapi_path)
    verifier.run_final_verification()


if __name__ == "__main__":
    main()
