# OpenAPI Fixer Toolkit

Kit de 3 scripts Python para automatizar processamento de documentações OpenAPI.

## Scripts Disponíveis

| Script | Função | Uso |
|--------|--------|-----|
| **1_hydrate_openapi.py** | Enriquece OpenAPI com metadados | Adiciona info, segurança, traduções |
| **2_fix_schema_names_and_refs.py** | Corrige schemas inválidos | Remove espaços dos nomes |
| **3_fix_semantic_paths.py** | Resolve erros semânticos | Configurável via YAML |

## Setup Rápido

```bash
# Clone o projeto
git clone https://github.com/rafactx/openapi-fixer-v2.git
cd openapi-fixer-v2

# Configure automaticamente
pnpm setup
```

✅ **Pronto!** Ambiente configurado automaticamente.

## Uso Rápido (PNPM Scripts)

```bash
# Processar OpenAPI completo
pnpm hydrate openapi.json config.yaml dictionary.json summaries.json

# Corrigir schemas com espaços
pnpm fix-schemas openapi.json --verbose

# Corrigir problemas semânticos
pnpm fix-semantic openapi.json --verbose

# Executar todas as correções
pnpm fix-all

# Gerar template de configuração
pnpm export-config
```

## 🛠️ Uso Direto (Python)

### 1. Hidratação OpenAPI

```bash
python3 1_hydrate_openapi.py openapi.json config.yaml dictionary.json summaries.json
```

**Faz**: Adiciona metadados, segurança, traduções, títulos PT-BR

### 2. Correção de Schemas

```bash
python3 2_fix_schema_names_and_refs.py openapi.json --verbose
```

**Faz**: `Banner V1` → `BannerV1` + atualiza todas as referências

### 3. Correções Semânticas

```bash
python3 3_fix_semantic_paths.py openapi.json --config custom.yaml
```

**Faz**: Remove requestBody de DELETE, corrige parâmetros, etc.

## 🎯 Workflow Recomendado

```bash
# Pipeline completo
pnpm hydrate openapi.json config.yaml dictionary.json summaries.json
pnpm fix-all  # Executa schemas + semânticas automaticamente
```

## ⚙️ Configuração Personalizada

Crie correções customizadas sem tocar no código:

```bash
# 1. Gere template
pnpm export-config

# 2. Edite corrections-template.yaml
- id: "custom_fix"
  action: "DELETE_KEY"
  path: "paths./users/{id}/get"
  details:
    key_to_delete: "deprecated_field"

# 3. Execute
pnpm fix-semantic openapi.json --config corrections-template.yaml
```

## 🔧 Utilitários

```bash
pnpm clean       # Limpa arquivos temporários
pnpm help        # Lista todos os comandos
python3 script.py --help  # Ajuda específica
```

## ⚡ Troubleshooting

```bash
# Erro: "No module named 'yaml'"
pip install PyYAML

# Erro: "Arquivo não encontrado"
ls -la openapi.json

# Problemas de encoding
# Certifique-se que arquivos estão em UTF-8
```

## Dicas

- **Faça backup** do `openapi.json` antes
- Use `--verbose` para debug
- Scripts são **idempotentes** (pode executar várias vezes)
- Use `--help` para ver todas as opções

---
