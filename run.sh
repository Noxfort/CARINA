#!/bin/bash
# Navega para o diretório raiz do projeto (onde o script está localizado)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$SCRIPT_DIR"

# Ativa o ambiente virtual
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Erro: Ambiente virtual (.venv) não encontrado no diretório $SCRIPT_DIR"
    exit 1
fi

# Executa o script python repassando eventuais argumentos
python carina.py "$@"
