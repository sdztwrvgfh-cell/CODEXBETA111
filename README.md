# SuperIA

Este repo contém o app Streamlit `meuchat.py`, um chat com geração de imagens e suporte a upload de áudio.

## Como funciona para outras pessoas testarem

### 1. Uso local
Cada testador precisa da própria chave OpenAI. A chave não deve ser colocada no código nem no GitHub.

Opções:
- Definir no terminal antes de rodar:
  ```powershell
  $env:OPENAI_API_KEY="sk-SUA_CHAVE_AQUI"
  streamlit run meuchat.py
  ```
- Ou criar um arquivo local `.streamlit/secrets.toml`:
  ```powershell
  mkdir .streamlit -Force
  @"
  OPENAI_API_KEY = "sk-SUA_CHAVE_AQUI"
  "@ > .streamlit/secrets.toml
  ```

### 2. Uso no Streamlit Cloud
Se você publicar o app no Streamlit Cloud, deve configurar `OPENAI_API_KEY` nos Secrets do app. Assim, quem abrir o link não precisa ter a chave.

### 3. O que o app usa
- Chat: OpenAI Chat API (`gpt-3.5-turbo`)
- Imagem: Pollinations (geração gratuita)
- Áudio: upload de `mp3`/`wav`

## Quais arquivos COMMITAR no GitHub
Commite apenas os arquivos de código e configuração do projeto:

- `meuchat.py`
- `requirements.txt`
- `README.md`
- `README_SECURITY.md`
- `.gitignore`
- `setup_openai_key.ps1`
- `.streamlit/secrets.toml.example`

## O que NÃO COMMITAR

- `.streamlit/secrets.toml`
- `historico_codex.json`
- `.venv/`
- `__pycache__/`
- `*.pyc`

## Deploy no Streamlit Cloud
1. Crie o repositório no GitHub e envie os arquivos acima.
2. No Streamlit Cloud, conecte o repo.
3. Em `Settings` / `Secrets`, adicione `OPENAI_API_KEY` com sua chave.
4. Rode o app.

### Observação de segurança
A chave da OpenAI é sensível. Nunca coloque isso no GitHub público. Use `.streamlit/secrets.toml` localmente ou Secrets no Streamlit Cloud.
