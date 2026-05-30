import os
import sys
import tiktoken
from pathlib import Path

def contar_tokens_pasta(caminho_pasta, extensoes_validas=None, pastas_ignoradas=None, modelo="cl100k_base"):
    if extensoes_validas is None:
        extensoes_validas = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json",
            ".md", ".txt", ".java", ".cpp", ".c", ".h", ".rb", ".go",
            ".rs", ".php", ".swift", ".kt", ".yaml", ".yml", ".toml", ".sh", ".sql"
        }

    if pastas_ignoradas is None:
        pastas_ignoradas = {
            "node_modules", ".git", "venv", "env", ".venv", ".env",
            "__pycache__", ".vscode", ".idea", "dist", "build", "out",
            ".tox", ".mypy_cache", ".pytest_cache", "coverage", ".next",
            ".nuxt", ".svelte-kit", "target", "bin", "obj", "Model_Vault"
        }

    # Normaliza para minúsculas para ignorar independente de maiúsculas/minúsculas
    pastas_ignoradas = {p.lower() for p in pastas_ignoradas}

    print("⏳ Carregando modelo de tokenização (pode demorar na 1ª vez)...")
    try:
        encoding = tiktoken.get_encoding(modelo)
    except Exception as e:
        print(f"❌ Erro ao carregar modelo '{modelo}': {e}")
        return

    total_tokens = 0
    arquivos_processados = []
    caminho = Path(caminho_pasta).resolve()

    if not caminho.exists():
        print(f"❌ Pasta não encontrada: {caminho}")
        return

    print(f"🔍 Analisando: {caminho}")
    print(f"🚫 Ignorando pastas: {', '.join(sorted(pastas_ignoradas))}\n")

    for root, dirs, files in os.walk(caminho):
        # Remove in-place as pastas ignoradas para não descer nelas
        dirs[:] = [d for d in dirs if d.lower() not in pastas_ignoradas]

        for nome_arquivo in files:
            arquivo_path = Path(root) / nome_arquivo
            if arquivo_path.suffix.lower() in extensoes_validas:
                try:
                    conteudo = arquivo_path.read_text(encoding="utf-8", errors="ignore")
                    tokens = len(encoding.encode(conteudo))
                    total_tokens += tokens
                    arquivos_processados.append((arquivo_path.relative_to(caminho), tokens))
                except Exception as e:
                    print(f"⚠️ Falha ao ler '{arquivo_path.name}': {e}")

    # 📊 Resultados
    print("="*45)
    print("📊 RESULTADO FINAL")
    print("="*45)
    print(f"Modelo usado          : {modelo}")
    print(f"Arquivos lidos        : {len(arquivos_processados)}")
    print(f"Total de tokens       : {total_tokens:,}")
    print("="*45)

    # Top 10
    print("\n📈 Top 10 arquivos mais pesados:")
    top_10 = sorted(arquivos_processados, key=lambda x: x[1], reverse=True)[:10]
    for nome, tokens in top_10:
        print(f"  {tokens:>8,} tokens | {nome}")
    if len(arquivos_processados) > 10:
        print(f"  ... e mais {len(arquivos_processados) - 10} arquivos")

if __name__ == "__main__":
    # Usa a pasta onde o script está, ou recebe caminho via terminal
    pasta_alvo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).parent.resolve()
    contar_tokens_pasta(pasta_alvo)