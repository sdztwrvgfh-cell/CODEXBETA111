 import requests
import os
import sys

# Carrega a chave do secrets.toml ou da variavel de ambiente
api_key = os.environ.get("OPENAI_API_KEY")

# Tenta ler do secrets.toml do Streamlit
if not api_key:
    try:
        with open(".streamlit/secrets.toml", "r", encoding="utf-8") as f:
            content = f.read()
            for line in content.split("\n"):
                line = line.strip()
                if "=" in line and "OPENAI_API_KEY" in line:
                    # Extrai o valor apos o =
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        val = parts[1].strip().strip('"').strip("'")
                        if val:
                            api_key = val
                            break
    except Exception as e:
        print(f"Nao foi possivel ler .streamlit/secrets.toml: {e}")

if not api_key:
    print("❌ Nenhuma chave API encontrada!")
    sys.exit(1)

print("=" * 50)
print("🔑 TESTE DA CHAVE OPENAI COM DALL-E 3")
print("=" * 50)
print(f"Chave encontrada: {api_key[:15]}...{api_key[-10:]}")
print()
print("1️⃣ Testando chat GPT-3.5...")

# Teste 1: Chat
try:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Diga so: OK"}],
        "max_tokens": 5
    }
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=15)
    if r.status_code == 200:
        print("   ✅ Chat GPT-3.5: FUNCIONANDO")
    else:
        print(f"   ❌ Chat GPT-3.5: ERRO {r.status_code}")
        data = r.json()
        print(f"   Detalhes: {data.get('error', {}).get('message', r.text[:200])}")
except Exception as e:
    print(f"   ❌ Chat GPT-3.5: EXCECAO - {e}")

# Teste 2: DALL-E 3
print()
print("2️⃣ Testando DALL-E 3...")
try:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "dall-e-2",
        "prompt": "a simple red circle on white background",
        "size": "1024x1024",
        "n": 1
    }
    r = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload, timeout=90)
    
    if r.status_code == 200:
        data = r.json()
        url = data.get("data", [{}])[0].get("url", "sem URL")
        print(f"   ✅ DALL-E 3: FUNCIONANDO")
        print(f"   URL da imagem gerada: {url}")
    else:
        data = r.json()
        error_msg = data.get('error', {}).get('message', 'sem mensagem')
        error_code = data.get('error', {}).get('code', 'sem codigo')
        print(f"   ❌ DALL-E 3: ERRO {r.status_code}")
        print(f"   Codigo: {error_code}")
        print(f"   Mensagem: {error_msg}")
        
        if r.status_code == 401:
            print()
            print("   ⚠️ CHAVE INVALIDA OU EXPIRADA")
            print("   Va em: https://platform.openai.com/api-keys")
            print("   Gere uma nova chave e atualize o arquivo .streamlit/secrets.toml")
        elif r.status_code == 429:
            print()
            print("   ⚠️ SEM CREDITOS ou LIMITE ATINGIDO")
            print("   Verifique se voce tem creditos em: https://platform.openai.com/usage")
            print("   DALL-E 3 requer creditos PAGOS (nao funciona com trial gratuito)")
            print("   Custo aproximado: $0.04 por imagem 1024x1024")
        
except Exception as e:
    print(f"   ❌ DALL-E 3: EXCECAO - {e}")

print()
print("=" * 50)
print("RESULTADO FINAL:")
print("  Se o chat funcionou e DALL-E 3 falhou com 401:")
print("    -> Gere uma NOVA chave API na OpenAI (a atual pode ser so para chat)")
print("  Se o chat funcionou e DALL-E 3 falhou com 429:")
print("    -> Voce precisa ADICIONAR CREDITOS na conta OpenAI")
print("  Se AMBOS funcionaram:")
print("    -> O problema esta no codigo do meuchat.py")
print("=" * 50)