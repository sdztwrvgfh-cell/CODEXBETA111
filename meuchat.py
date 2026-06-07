import streamlit as st
import requests
from io import BytesIO
from PIL import Image
import json
import os
import time
import re
import auth
import config

API_COST_PER_1000_TOKENS = 0.002
DEFAULT_BILLING_DOLLARS = 5.0


def estimativa_tokens_por_dolar(dollar):
    return int((dollar / API_COST_PER_1000_TOKENS) * 1000)


def estimativa_mensagens(dollar, tokens_por_mensagem=200):
    return int(estimativa_tokens_por_dolar(dollar) / tokens_por_mensagem)


def estimativa_tokens_por_texto(texto):
    # Estimativa simples: 1 token ~ 0,75 palavras, arredondando para cima
    palavras = len(texto.split())
    return int(palavras * 1.3) + 10


def transcrever_audio(audio_file):
    """Transcreve áudio usando a API de áudio do OpenAI."""
    api_key = _obter_api_key()
    if not api_key:
        raise RuntimeError("Defina a variavel ambiente OPENAI_API_KEY antes de executar.")

    audio_file.seek(0)
    files = {
        "file": (audio_file.name, audio_file, audio_file.type)
    }
    data = {
        "model": "whisper-1"
    }
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    resp = requests.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data.get("text", "")


def web_search(query, max_results=5):
    """Busca real na web usando DuckDuckGo (biblioteca ddgs).
    Retorna lista de {title, url}.
    """
    if not query:
        return []
    try:
        from ddgs import DDGS
        from itertools import islice
        results = list(islice(DDGS().text(query, max_results=max_results), max_results))
        return [{"title": r.get("title", ""), "url": r.get("href", "")} for r in results]
    except Exception:
        return []

def adicionar_recursos_extras():
    temperatura = st.sidebar.slider("Smart Levels", 0.0, 1.0, 0.7)
    estilo = st.sidebar.selectbox(
        "Style.IA (still in test. BETA)",
        ["Realista", "Cartoon", "Anime", "Cyberpunk", "Frutiger aero style", "Pintura a óleo", "Aquarela", "Surrealista", "Pixel art"]
    )
    # Uploader de áudio para teste (mp3/wav). Substitui o inexistente `st.audio_input`.
    audio = st.sidebar.file_uploader("Envie áudio para o Codex (mp3/wav)", type=["mp3", "wav"])
    if audio:
        try:
            st.sidebar.audio(audio)
        except Exception:
            pass

        if st.sidebar.button("Transcrever áudio"):
            try:
                st.session_state.audio_transcricao = transcrever_audio(audio)
                st.session_state.audio_status = "Áudio transcrito com sucesso. Clique em enviar para usar a transcrição."
            except Exception as e:
                st.session_state.audio_status = f"Erro ao transcrever: {e}"

        if st.session_state.audio_status:
            st.sidebar.info(st.session_state.audio_status)

        if st.session_state.audio_transcricao:
            st.sidebar.markdown("**Transcrição atual:**")
            st.sidebar.write(st.session_state.audio_transcricao)
            if st.sidebar.button("Enviar áudio transcrito como mensagem"):
                st.session_state.enviar_audio_transcrito = True

    return temperatura, estilo, audio

# ativa os controles extras do sidebar (slider / estilo / audio)
temperatura, estilo, audio = adicionar_recursos_extras()


def _obter_api_key():
    """Obtem a chave OpenAI de varias fontes possiveis (usa config.py)"""
    return config.get_api_key()

def send_openai_chat(dados_chat, temperatura=0.7):
    """Envia `dados_chat` para a API OpenAI Chat e retorna o texto gerado."""
    api_key = _obter_api_key()
    if not api_key:
        raise RuntimeError("Defina a variavel ambiente OPENAI_API_KEY antes de executar.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": dados_chat,
        "temperature": float(temperatura),
        "max_tokens": 800
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    # extrai texto da primeira escolha
    return data["choices"][0]["message"]["content"]


# Nome do arquivo que vai guardar as conversas no seu PC
ARQUIVO_SALVO = "historico_codex.json"
NOTAS_ATUALIZACAO = "Notas da atualização:Codex AI agora está mais inteligente e consegue fazer buscas aprofundadas e aprimoradas e analisa imagens tirada por sua webcam ou de seu dispositivo! gere imagens, converse, ative o modo do pijama e muito mais! lembre se: a codex esta em atualização constante e pode apresentar falhas por estar em versao beta."

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Codex.AI", page_icon="🚀", layout="wide")
api_key = _obter_api_key()
if not api_key:
    st.warning("Defina a variavel ambiente OPENAI_API_KEY antes de executar.")

# --- INICIALIZAÇÃO DE ESTADO ---
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None  # None = não logado, dict = dados do usuário
if "historico_codex" not in st.session_state:
    st.session_state.historico_codex = []
if "audio_transcricao" not in st.session_state:
    st.session_state.audio_transcricao = ""
if "audio_status" not in st.session_state:
    st.session_state.audio_status = ""
if "enviar_audio_transcrito" not in st.session_state:
    st.session_state.enviar_audio_transcrito = False
if "modo_neon" not in st.session_state:
    st.session_state.modo_neon = False
if "wallpaper_url" not in st.session_state:
    st.session_state.wallpaper_url = ""
if "paleta_preset" not in st.session_state:
    st.session_state.paleta_preset = "Padrão"
if "custom_message" not in st.session_state:
    st.session_state.custom_message = ""
if "tema" not in st.session_state:
    st.session_state.tema = "Escuro"
if "modo_pijama" not in st.session_state:
    st.session_state.modo_pijama = False
if "estilo_divertido" not in st.session_state:
    st.session_state.estilo_divertido = "Normal"
if "camera_ativa" not in st.session_state:
    st.session_state.camera_ativa = True
if "foto_pendente" not in st.session_state:
    st.session_state.foto_pendente = None

# --- MENU LATERAL (SIDEBAR) ---
with st.sidebar:
    # --- ÁREA DE CONTA (LOGIN / REGISTRO / LOGOUT) ---
    with st.expander("👤 Conta", expanded=st.session_state.usuario_logado is None):
        if st.session_state.usuario_logado is None:
            modo = st.radio("Modo", ["🔑 Login", "✨ Criar conta"], horizontal=True, key="modo_auth")
            if modo == "🔑 Login":
                login_user = st.text_input("Usuário", key="login_user", placeholder="seu nome de usuário")
                login_pass = st.text_input("Senha", type="password", key="login_pass", placeholder="sua senha")
                if st.button("Entrar", key="btn_login"):
                    ok, msg, dados = auth.login_user(login_user, login_pass)
                    if ok:
                        st.session_state.usuario_logado = dados
                        st.session_state.historico_codex = auth.get_user_chat_history(dados["id"])
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                reg_user = st.text_input("Usuário (min. 3 letras)", key="reg_user", placeholder="escolha um nome")
                reg_pass = st.text_input("Senha (min. 4 caracteres)", type="password", key="reg_pass", placeholder="crie uma senha")
                if st.button("Criar conta", key="btn_reg"):
                    ok, msg, uid = auth.register_user(reg_user, reg_pass)
                    if ok:
                        st.success(msg)
                        st.info("Agora faça login com seus dados.")
                    else:
                        st.error(msg)
        else:
            u = st.session_state.usuario_logado
            st.success(f"👋 {u['display_name']}")
            st.caption(f"@{u['username']}")
            if st.button("🚪 Sair da conta", key="btn_logout"):
                st.session_state.usuario_logado = None
                st.session_state.historico_codex = []
                st.rerun()
    st.divider()
    st.image("https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg", width=60)
    st.title("🤖 Codex.AI")
    # Mensagem editável pelo usuário — você pode mudar esse texto a qualquer hora
    st.text_input("Mensagem da IA (edite e veja ao vivo)", value="", key="custom_message", placeholder="Escreva uma mensagem curta para o badge da IA")
    st.caption("Codex: Uma IA incrivel para conversas do dia a dia, análise de imagens, pesquisas simples e se divertir! note que uma IA nao substitui o trabalho humano ou REAIS diagnosticos.")
    with st.expander("💰 Estimativa de custo da API"):
        st.write("OpenAI `gpt-3.5-turbo` custa cerca de US$0,002 por 1000 tokens.")
        budget_usd = st.number_input("Simular orçamento em dólares", min_value=1.0, max_value=50.0, value=DEFAULT_BILLING_DOLLARS, step=1.0)
        tokens = estimativa_tokens_por_dolar(budget_usd)
        mensagens = estimativa_mensagens(budget_usd)
        st.metric("Tokens estimados", f"{tokens:,}")
        st.metric("Mensagens estimadas", f"{mensagens:,}")
        st.write(f"Com US${budget_usd:.2f}, você tem aproximadamente {tokens:,} tokens.")
        st.write(f"Isso equivale a cerca de {mensagens:,} trocas de mensagem se cada conversa usar 200 tokens.")
        st.info("As imagens do app são geradas pelo Pollinations, então só o chat consome a quota da OpenAI. Áudio transcrito também consome tokens.")
    # Nota discreta: manual de segurança foi movido para o rodapé da página
    st.markdown("🔒 Manual de segurança da API disponível no rodapé (clique para ver).")
    st.markdown("---")
    with st.expander("Controles", expanded=True):
        tema = st.selectbox("Tema do Site", ["Escuro", "White"], key="tema")
        usar_somente_openai = st.checkbox("Usar apenas OpenAI para imagens (recomendado)", value=True, key="usar_somente_openai")
        modo_imagem = st.selectbox("Modo de imagem", ["🎨 Gerar com IA", "🔍 Buscar fotos reais"], key="modo_imagem")
        modo_pijama = st.checkbox("🎉 Festa do pijama☁️", value=False, key="modo_pijama")
        estilo_divertido = st.selectbox(
            "Modo divertido",
            ["Normal", "Futurista", "Anime", "Retrô"],
            key="estilo_divertido"
        )
        modo_neon = st.checkbox("Modo Neon (vibes 2000)", value=False, key="modo_neon")
        wallpaper_url = st.text_input("URL do papel de parede (opcional)", value="https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg", key="wallpaper_url", placeholder="https://...jpg")
        # Snippet: Aplicar Paleta — cole dentro de `with st.sidebar:` (próximo ao wallpaper_url)
        paletas = {
            "Padrão": {"accent": "#7d3af2", "wall": ""},
            "Neon":   {"accent": "#00f5ff", "wall": ""},
            "Cyber":  {"accent": "#39ff14", "wall": ""},
            "Pastel": {"accent": "#ff78c6", "wall": ""},
            "Frutiger": {"accent": "#7ec8e3", "wall": "https://wallpapers.com/images/hd/frutiger-aero-1920-x-1080-3j7tyr5tc6y368q1.jpg"}
        }
        paleta = st.selectbox("Paleta rápida", list(paletas.keys()), index=0, key="paleta_preset")
        if st.button("Aplicar Paleta"):
            escolha = st.session_state.get("paleta_preset")
            dados = paletas.get(escolha, paletas["Padrão"])
            # atualiza acento e (opcional) papel de parede via campo wallpaper_url
            st.session_state.modo_neon = (escolha == "Neon")
            # atualiza diretamente o campo de URL (você pode deixá-lo vazio para não alterar)
            if dados.get("wall"):
                st.session_state.wallpaper_url = dados["wall"]
            # força recarregar para aplicar mudanças no CSS/fundo
            st.rerun()
        st.subheader("📊 Ficha Técnica")
        st.markdown("* **Modelo de Texto:** GPT-3.5-turbo (OpenAI)\n* **Imagem IA:** Stable Horde\n* **Fotos reais:** DuckDuckGo Images (ddgs)")

        st.divider()
        st.success("✅ Sistema funcionando normalmente! Erro de recarregamento corrigido.")

        if modo_pijama:
            st.markdown("<div class='pijama-banner'>🎀 <strong>Modo Festa do Pijama ativado!</strong> Tudo fica mais macio, divertido e com nuvens.</div>", unsafe_allow_html=True)
            if not st.session_state.get("pijama_balloons", False):
                st.balloons()
                st.session_state.pijama_balloons = True
            st.info("✨ Está tudo temático: nuvens, travesseiros e emojis suaves estão liberados.")
            if st.button("📖 Conta uma história de dormir"):
                st.session_state.pijama_story_request = True

        if st.button("🎲 IDEIAS"):
            st.session_state.ultima_ideia = "desenhe um gato robô voando sobre uma cidade neon"

        url_audio = st.text_input("🎵 URL do áudio ambiente (cole qualquer .mp3)", value=st.session_state.get("audio_url", "https://cdn.freesound.org/previews/768/768783_16425075-lq.mp3"), key="audio_url")
        if st.button("🔊 Tocar áudio"):
            st.audio(url_audio, loop=True)
        if st.session_state.get("audio_autoplay", True):
            st.markdown(f'<audio autoplay loop style="display:none"><source src="{url_audio}" type="audio/mpeg">Seu navegador não suporta áudio.</audio>', unsafe_allow_html=True)
        st.checkbox("🎧 Som ambiente automático", value=st.session_state.get("audio_autoplay", True), key="audio_autoplay")

        if st.button("🌟 Recomendar prompts"):
            st.session_state.ultima_ideia = "Crie uma imagem de um cachorro astronauta explorando a lua, com um estilo de pintura a óleo e muitos detalhes fofos! 🚀🐶🌕"

        if st.button("🔄 Resetar layout"):
            st.session_state.tema = "Escuro"
            st.session_state.modo_pijama = False
            st.session_state.estilo_divertido = "Normal"
            st.rerun()

        # Gravação local de áudio (opcional) -> transcreve e prepara para envio
        st.divider()
        st.markdown("**Gravar áudio pelo microfone (local)**")
        dur = st.number_input("Duração (segundos)", min_value=1, max_value=60, value=5, step=1, key="rec_duration")
        if st.button("Gravar e transcrever (local)"):
            try:
                import sounddevice as sd
                import soundfile as sf
                import tempfile
                fs = 44100
                st.info(f"Gravando {dur} segundos... Fale agora.")
                recording = sd.rec(int(dur * fs), samplerate=fs, channels=1, dtype='int16')
                sd.wait()
                tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                sf.write(tmp.name, recording, fs)
                tmp.flush()
                with open(tmp.name, 'rb') as f:
                    f.name = os.path.basename(tmp.name)
                    f.type = 'audio/wav'
                    try:
                        texto = transcrever_audio(f)
                        st.success("Áudio transcrito com sucesso.")
                        st.session_state.audio_transcricao = texto
                        st.session_state.enviar_audio_transcrito = True
                        st.info("Transcrição pronta: clique em enviar para usar como mensagem.")
                    except Exception as te:
                        st.error(f"Erro ao transcrever: {te}")
            except Exception as ie:
                st.error("Para gravar localmente instale: pip install sounddevice soundfile")
                st.write(str(ie))

        if "ultima_ideia" in st.session_state:
            st.info(f"💡 Experimente: {st.session_state.ultima_ideia}")

        st.markdown("---")
        if st.button("🗑️ Limpar Conversa Salva"):
            user = st.session_state.get("usuario_logado")
            if user:
                auth.clear_user_chat_history(user["id"])
            else:
                if os.path.exists(ARQUIVO_SALVO):
                    os.remove(ARQUIVO_SALVO)
            st.session_state.historico_codex = []
            st.rerun()

    st.divider()
    total_msgs = len(st.session_state.get("historico_codex", []))
    st.sidebar.metric("💬 Mensagens salvas", total_msgs)

    st.write("DICA: Vc ja testou os truques da IA? peça para ela desenhar um gato astronauta na lua ou analisar uma foto sua junto com uma pergunta! 🚀")

if tema == "White":
    fundo = "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #dbeafe 100%)"
    painel = "rgba(255, 255, 255, 0.92)"
    texto = "#111111"
else:
    fundo = "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #311042 100%)"
    painel = "rgba(255, 255, 255, 0.04)"
    texto = "#f8fafc"

extra_css = ""
extra_html = ""
if st.session_state.get('modo_pijama', False):
    fundo = "linear-gradient(135deg, #b4a7e7 0%, #c8b6ff 40%, #f7d9ff 100%)"
    painel = "rgba(255, 255, 255, 0.18)"
    texto = "#2b1532"
    extra_css = """
    @keyframes floaty {
        0% { transform: translateY(0px) translateX(0px); opacity: 0.9; }
        50% { transform: translateY(-12px) translateX(5px); opacity: 1; }
        100% { transform: translateY(0px) translateX(0px); opacity: 0.9; }
    }
    .pijama-cloud { position: fixed; width: 130px; height: 130px; background: rgba(255,255,255,0.24); border-radius: 50%; box-shadow: 0 12px 40px rgba(255,255,255,0.3); animation: floaty 12s ease-in-out infinite; z-index: 1; }
    .pijama-cloud:nth-child(1) { top: 8%; left: 5%; }
    .pijama-cloud:nth-child(2) { top: 20%; right: 8%; width: 100px; height: 100px; animation-delay: 2s; }
    .pijama-cloud:nth-child(3) { bottom: 18%; left: 12%; width: 120px; height: 120px; animation-delay: 4s; }
    .pijama-cloud:nth-child(4) { bottom: 10%; right: 18%; width: 90px; height: 90px; animation-delay: 6s; }
    .pijama-badge { position: fixed; top: 14%; right: 14%; z-index: 2; color: #5d2b7e; font-size: 19px; font-weight: 700; }
    .stApp {{ overflow: hidden; }}
    """
    extra_html = """
    <div class='pijama-cloud'></div>
    <div class='pijama-cloud'></div>
    <div class='pijama-cloud'></div>
    <div class='pijama-cloud'></div>
    <div class='pijama-badge'>☁️ Festa do Pijama ☁️</div>
    """

# Define cor de acento baseado no toggle Neon e permite override do fundo com URL
accent_color = "#43a7f9" if st.session_state.get("modo_neon", False) else "#7d3af2"
if st.session_state.get("wallpaper_url"):
    wp = st.session_state.get("wallpaper_url").strip()
    if wp:
        fundo = f"url('{wp}') center/cover fixed"

st.markdown(f"""
    <style>
    /* Importa fontes leves e futuristas + Frutiger Aero */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Orbitron:wght@400;600&display=swap');
    :root {{
        --glass-bg: rgba(255,255,255,0.07);
        --glass-border: rgba(255,255,255,0.22);
        --accent: {accent_color};
        --accent-2: rgba(126,200,227,0.16);
        --card-radius: 16px;
    }}
    body, .stApp, .block-container {{ font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; color: {texto}; }}
    h1, h2, h3, .stTitle {{ font-family: 'Orbitron', 'Inter', sans-serif; letter-spacing: 0.3px; }}
    .stApp {{ background: {fundo} !important; }}
    .block-container {{ max-width: 1200px; padding: 24px 34px !important; margin: 0 auto; }}
    div[data-testid="stSidebar"] {{ min-width: 260px !important; max-width: 340px !important; background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01)) !important; }}
    /* GLASSMORPHISM FRUTIGER AERO: paineis transparentes com blur e borda suave */
    div[data-testid="stSidebar"], .stChatMessage, div[data-testid="stFileUploader"], .stBlock {{
        background: var(--glass-bg) !important;
        backdrop-filter: blur(20px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(160%) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--card-radius) !important;
        box-shadow: 0 8px 32px rgba(126,200,227,0.12) inset, 0 8px 24px rgba(0,0,0,0.28) !important;
        color: {texto} !important;
    }}
    /* BOTOES AQUA STYLE (Windows Vista/7) */
    .stSidebar .stButton > button, .stBlock .stButton > button {{
        background: linear-gradient(180deg, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.04) 50%, rgba(255,255,255,0.02) 100%);
        border: 1px solid rgba(126,200,227,0.30);
        color: {texto} !important;
        padding: 10px 14px !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 16px rgba(126,200,227,0.14), inset 0 1px 0 rgba(255,255,255,0.20) !important;
        transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
        position: relative;
        overflow: hidden;
    }}
    .stSidebar .stButton > button::after {{
        content: '';
        position: absolute;
        top: 0; left: 8px; right: 8px;
        height: 2px;
        background: rgba(255,255,255,0.30);
        border-radius: 50%;
        pointer-events: none;
    }}
    .stChatMessage {{ border-radius: 20px !important; padding: 16px !important; margin-bottom:14px !important; max-width: 980px; transition: transform 0.22s ease, box-shadow 0.22s ease; background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)) !important; border: 1px solid rgba(126,200,227,0.16) !important; }}
    .stChatMessage:hover {{ transform: translateY(-4px); box-shadow: 0 16px 40px rgba(126,200,227,0.18) !important; }}
    .stButton > button:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(126,200,227,0.24), inset 0 1px 0 rgba(255,255,255,0.28) !important; }}
    .stButton > button:active {{ transform: scale(0.98); }}
    .ai-badge {{ display: inline-flex; align-items: center; gap: 10px; padding: 10px 16px; border-radius: 14px; background: linear-gradient(90deg, rgba(126,200,227,0.15), rgba(168,230,207,0.10)); border: 1px solid rgba(126,200,227,0.18); color: {texto}; box-shadow: 0 8px 24px rgba(126,200,227,0.08); font-weight:700; margin-bottom: 12px; }}
    .icon-gem {{ width:20px; height:20px; filter: drop-shadow(0 4px 10px rgba(126,200,227,0.35)); }}
    .pijama-cloud {{ position: fixed; opacity: 0.95; pointer-events:none; z-index:1; filter: blur(0.6px); }}
    .pijama-banner {{ padding: 14px; border-radius: 16px; background: rgba(255,255,255,0.08); border: 1px dashed rgba(168,230,207,0.20); color: #2b1532; margin-bottom: 14px; box-shadow: 0 8px 18px rgba(255,255,255,0.06); }}
    .stApp {{ overflow-x: hidden; background-size: 200% 200% !important; animation: gradientShift 18s ease infinite; }}
    @keyframes gradientShift {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}
    /* BOLHAS FRUTIGER AERO flutuantes no fundo */
    @keyframes frutigerBubble {{
        0% {{ transform: translateY(100vh) translateX(0) scale(0.4); opacity: 0; }}
        10% {{ opacity: 0.20; }}
        90% {{ opacity: 0.20; }}
        100% {{ transform: translateY(-120px) translateX(30px) scale(1.0); opacity: 0; }}
    }}
    .frutiger-bubble {{
        position: fixed;
        bottom: -80px;
        border-radius: 50%;
        pointer-events: none;
        z-index: 0;
        background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.40), rgba(126,200,227,0.12) 60%, rgba(168,230,207,0.04));
        box-shadow: 0 0 20px rgba(126,200,227,0.08);
        animation: frutigerBubble 22s ease-in infinite;
    }}
    .frutiger-bubble:nth-child(1) {{ width: 70px; height: 70px; left: 6%; animation-delay: 0s; animation-duration: 20s; }}
    .frutiger-bubble:nth-child(2) {{ width: 55px; height: 55px; left: 18%; animation-delay: 4s; animation-duration: 24s; }}
    .frutiger-bubble:nth-child(3) {{ width: 90px; height: 90px; left: 38%; animation-delay: 2s; animation-duration: 18s; }}
    .frutiger-bubble:nth-child(4) {{ width: 45px; height: 45px; left: 55%; animation-delay: 7s; animation-duration: 26s; }}
    .frutiger-bubble:nth-child(5) {{ width: 80px; height: 80px; left: 72%; animation-delay: 1s; animation-duration: 22s; }}
    .frutiger-bubble:nth-child(6) {{ width: 60px; height: 60px; left: 88%; animation-delay: 5s; animation-duration: 19s; }}
    /* Inputs e placeholders mais minimalistas */
    input, textarea, .stTextInput, .stTextArea {{ border-radius: 12px !important; padding: 10px !important; background: rgba(255,255,255,0.03) !important; color: {texto} !important; border: 1px solid rgba(126,200,227,0.16) !important; }}
    input::placeholder, textarea::placeholder {{ color: rgba(255,255,255,0.44) !important; }}
    {extra_css}
    </style>
    <!-- BOLHAS FRUTIGER AERO HTML -->
    <div class='frutiger-bubble'></div>
    <div class='frutiger-bubble'></div>
    <div class='frutiger-bubble'></div>
    <div class='frutiger-bubble'></div>
    <div class='frutiger-bubble'></div>
    <div class='frutiger-bubble'></div>
    {extra_html}
""", unsafe_allow_html=True)

# Manual de segurança no rodapé (discreto)
with st.expander("🔒 Manual de segurança da API (local)", expanded=False):
    st.write("Para rodar localmente, defina a variável de ambiente `OPENAI_API_KEY` ou crie `.streamlit/secrets.toml` e não o comite.")
    st.code('$env:OPENAI_API_KEY = "sk-SUA_CHAVE_AQUI"', language='powershell')
    st.write("Exemplo mínimo de `.streamlit/secrets.toml`:")
    st.code('OPENAI_API_KEY = "sk-SUA_CHAVE_AQUI"', language='toml')

def guardar_conversa():
    """Salva o histórico: se logado, salva no SQLite por usuário; senão no JSON local"""
    user = st.session_state.get("usuario_logado")
    if user:
        # Já foi salvo incrementalmente via auth.save_chat_message
        return
    else:
        mensagens_texto = [msg for msg in st.session_state.historico_codex if msg["type"] == "text"]
        with open(ARQUIVO_SALVO, "w", encoding="utf-8") as f:
            json.dump(mensagens_texto, f, ensure_ascii=False, indent=4)


def adicionar_ao_historico(role, content, msg_type="text"):
    """Adiciona mensagem ao historico e salva no banco se estiver logado"""
    st.session_state.historico_codex.append({"role": role, "type": msg_type, "content": content})
    user = st.session_state.get("usuario_logado")
    if user:
        auth.save_chat_message(user["id"], role, content, msg_type)
    else:
        guardar_conversa()

# --- CORPO PRINCIPAL DO CHAT ---
st.title("🚀 Codex.AI BETA VERSION")
# Mostra a mensagem editável definida no sidebar (você pode alterar ao vivo)
custom_msg = st.session_state.get("custom_message", "")
if custom_msg:
    st.markdown(f"<div class='ai-badge'><svg class='icon-gem' viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg' style='width:20px;height:20px;vertical-align:middle;margin-right:8px;fill: #7d3af2;'> <path d='M12 2l3 5 5 1-3.5 4 1 5-5-2-5 2 1-5L4 8l5-1z'/> </svg>{custom_msg}</div>", unsafe_allow_html=True)
if st.session_state.get('modo_pijama', False):
    st.markdown("### 🌙 Bem-vindo à Festa do Pijama ☁️\nVamos conversar como se estivéssemos numa noite perfeita estrelada e como se estivessemos em nuvens calmas observando o luar.")
st.caption("Modelos usados: GPT-3.5-turbo para conversa | Stable Horde (IA) / DuckDuckGo Images para imagem")
st.info(f"👋 Bem-vindo ao Codex.IA {NOTAS_ATUALIZACAO}")

# Exibe o histórico salvo na tela
for item in st.session_state.historico_codex:
    with st.chat_message(item["role"]):
        st.write(item["content"])

# Opção de foto: upload ou câmera (com toggle)
st.session_state.camera_ativa = st.sidebar.checkbox("📷 Ativar câmera", value=st.session_state.camera_ativa, key="toggle_camera")

if st.session_state.camera_ativa:
    col1, col2 = st.columns(2)
    with col1:
        foto_upload = st.file_uploader("📤 Upload de foto", type=["png", "jpg", "jpeg"], key="upload_foto")
    with col2:
        foto_camera = st.camera_input("📷 Tirar foto pela webcam", key="camera_foto")

    if foto_camera is not None:
        st.session_state.foto_pendente = foto_camera
    elif foto_upload is not None:
        st.session_state.foto_pendente = foto_upload

    if st.session_state.foto_pendente is not None:
        st.caption(f"📸 Foto capturada — será enviada na próxima mensagem")
        if st.button("❌ Descartar foto"):
            st.session_state.foto_pendente = None
            st.rerun()
else:
    st.session_state.foto_pendente = None
    st.caption("📷 Câmera desativada | Ative no menu lateral")

foto_enviada = st.session_state.foto_pendente

# Caixa de Entrada de Texto (input abaixo)

# Campo de input principal do chat
pergunta = st.chat_input("DICA: Codex.IA esta em desenvolvimento na versao teste e pode apresentar BUGS")

# Botões auxiliares: pesquisa web
if pergunta:
    cols_q = st.columns([1, 1, 2])
    pesquisar = cols_q[0].button("🔎 Pesquisa web")
    incluir_resultados = cols_q[1].checkbox("Incluir resultados na pergunta", value=False)
else:
    pesquisar = False
    incluir_resultados = False

if st.session_state.enviar_audio_transcrito and st.session_state.audio_transcricao:
    pergunta = st.session_state.audio_transcricao
    st.session_state.enviar_audio_transcrito = False

if pesquisar:
    if not pergunta or pergunta.strip() == "":
        st.warning("Digite algo para pesquisar antes de clicar em Pesquisa web.")
    else:
        try:
            st.info("🔎 Buscando na web...")
            resultados = web_search(pergunta, max_results=5)
            if not resultados:
                st.warning("Nenhum resultado encontrado.")
            else:
                with st.expander("Resultados da pesquisa web", expanded=True):
                    for r in resultados:
                        st.markdown(f"- **{r['title']}** — [{r['url']}]({r['url']})")
                if incluir_resultados:
                    sintese = "\n\nPesquisa web:\n" + "\n".join([f"- {r['title']}: {r['url']}" for r in resultados])
                    pergunta = (pergunta or "") + sintese
        except Exception as e:
            st.error(f"Erro na pesquisa: {e}")

if pergunta:
    texto_usuario = pergunta
    audio_transcricao = None
    # Se tiver áudio, tenta transcrever primeiro
    if audio:
        try:
            audio_transcricao = transcrever_audio(audio)
            texto_usuario += f" 🎧 [Áudio anexado: {audio.name}]"
        except Exception as e:
            st.sidebar.error(f"Não foi possível transcrever o áudio: {e}")

    # Se tiver foto, avisa no balão do chat
    if foto_enviada:
        texto_usuario += f" 📸 [Foto anexada: {foto_enviada.name}]"

    with st.chat_message("user"):
        st.write(texto_usuario)
        if foto_enviada:
            st.image(Image.open(foto_enviada), width=300)
        if audio_transcricao:
            st.write(f"📝 Transcrição do áudio: {audio_transcricao}")
            st.info("O áudio foi transcrito automaticamente e será usado na resposta.")
            texto_usuario += f"\n\nTranscrição do áudio: {audio_transcricao}"
            st.session_state.historico_codex.append({"role": "user", "type": "text", "content": texto_usuario})
        else:
            st.session_state.historico_codex.append({"role": "user", "type": "text", "content": texto_usuario})

    with st.chat_message("assistant"):
        placeholder = st.empty()

        # 🎨 MODO CRIAÇÃO DE IMAGENS - so ativa se for pedido de imagem/foto
        p_lower = pergunta.lower()
        tem_imagem = any(t in p_lower for t in ["imagem", "foto", "figure", "picture"])
        tem_criacao = any(t in p_lower for t in ["crie", "desenhe", "gere", "criar", "desenhar", "gerar", "faça"])
        tem_pesquisa = any(t in p_lower for t in ["pesquise", "pesquisar", "busque", "buscar", "procure", "procurar", "ache", "achar", "mostre", "mostrar", "quero ver"])

        # So entra no modo imagem se falar de imagem/foto OU for comando de criacao
        if (tem_pesquisa and tem_imagem) or tem_criacao or any(t in p_lower for t in ["me de uma foto", "me de uma imagem"]):
            placeholder.write("🎨 Gerando sua imagem... 🚀")
            try:
                texto_limpo = pergunta.lower()
                for termo in [
                    "crie a imagem de um", "crie a imagem de", "crie imagem de um", "crie imagem de",
                    "desenhe um", "desenhe uma", "desenhe o", "desenhe a", "desenhe", "faça uma foto de um", "faça um", "faça uma foto de", "faca uma foto de", "foto de um", "foto de uma", "foto do", "foto da", "foto de", "gere a imagem", "gere um", "create an", "draw a", "generate a", "make a photo of", "quero ver um", "me de uma foto de", "me de uma imagem de"
                ]:
                    texto_limpo = texto_limpo.replace(termo, "")
                texto_limpo = texto_limpo.strip()

                placeholder.empty()
                st.write(f"🖼️ PEDIDO EM PROCESSO, SEJA PACIENTE **{texto_limpo}**")

                # Detecta automaticamente: palavras de pesquisa -> fotos reais, criacao -> IA
                palavras_pesquisa = ["pesquise", "pesquisar", "busque", "buscar", "procure", "procurar", "ache", "achar", "mostre", "mostrar", "quero ver", "me de uma foto", "me de uma imagem"]
                palavras_criacao = ["crie", "desenhe", "gere", "criar", "desenhar", "gerar", "faça"]

                eh_pesquisa = any(p in pergunta.lower() for p in palavras_pesquisa)
                eh_criacao = any(p in pergunta.lower() for p in palavras_criacao)
                modo = st.session_state.get("modo_imagem", "🎨 Gerar com IA")

                # Se o usuario usou palavra de pesquisa, prioriza busca de fotos
                if eh_pesquisa and not eh_criacao:
                    usar_busca = True
                elif "Buscar" in modo:
                    usar_busca = True
                else:
                    usar_busca = False

                if usar_busca:
                    # Buscar imagens reais via DuckDuckGo Images (usando ddgs)
                    try:
                        st.info("🔍 Buscando imagens na web...")
                        from ddgs import DDGS
                        from itertools import islice
                        img_results = list(islice(DDGS().images(texto_limpo, max_results=5), 5))
                        if img_results:
                            st.success(f"✅ {len(img_results)} imagens encontradas!")
                            for i, img in enumerate(img_results):
                                img_url = img.get("image") or img.get("thumbnail")
                                if img_url:
                                    try:
                                        r_img = requests.get(img_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                                        if r_img.status_code == 200 and len(r_img.content) > 500:
                                            st.image(BytesIO(r_img.content), caption=img.get("title", "")[:60], width=400)
                                        else:
                                            st.markdown(f"🖼️ [{img.get('title','Imagem')[:50]}]({img_url})")
                                    except Exception:
                                        st.markdown(f"🔗 [{img.get('title','Link')[:50]}]({img_url})")
                            st.session_state.historico_codex.append({"role": "assistant", "type": "text", "content": f"🖼️ Imagens buscadas: {texto_limpo}"})
                            guardar_conversa()
                        else:
                            st.warning("🔍 Nenhuma imagem encontrada. Tente outro termo.")
                    except Exception as e2:
                        st.error(f"⚠️ Erro ao buscar imagens: {e2}")
                        st.info("💡 Tente com palavras mais simples.")
                else:
                    # Gerar imagem por IA via Stable Horde
                    try:
                        st.info("🧠 CODEX.AI está analisando...")
                        headers_sh = {"apikey": "0000000000"}
                        payload_sh = {"prompt": texto_limpo}
                        r_sh = requests.post("https://stablehorde.net/api/v2/generate/async",
                                             json=payload_sh, headers=headers_sh, timeout=15)
                        r_sh.raise_for_status()

                        if r_sh.status_code == 202:
                            job_id = r_sh.json()["id"]
                            st.info(f"Por favor aguarde, seu pedido esta sendo processado e pode demorar por estar na versao teste...")
                            status_url = f"https://stablehorde.net/api/v2/generate/status/{job_id}"
                            imagem_url = None

                            for tentativa in range(30):
                                time.sleep(2)
                                r_status = requests.get(status_url, timeout=10)
                                if r_status.status_code == 200:
                                    data_st = r_status.json()
                                    if data_st.get("done"):
                                        geracoes = data_st.get("generations", [])
                                        if geracoes and geracoes[0].get("img"):
                                            imagem_url = geracoes[0]["img"]
                                        break

                            if imagem_url:
                                r_img = requests.get(imagem_url, timeout=30)
                                r_img.raise_for_status()
                                st.image(BytesIO(r_img.content), width=600)
                                st.success("✅ Imagem gerada por IA com sucesso!")
                                st.session_state.historico_codex.append({"role": "assistant", "type": "text", "content": f"🖼️ Imagem gerada: {texto_limpo}"})
                                guardar_conversa()
                            else:
                                st.warning("⏱️ Stable Horde demorou muito. Tente novamente.")
                        else:
                            st.warning(f"⚠️ Stable Horde retornou erro {r_sh.status_code}")
                    except requests.exceptions.Timeout:
                        st.warning("⏱️ Stable Horde demorou demais. Tente novamente.")
                    except Exception as e2:
                        st.error(f"⚠️ Erro ao gerar imagem: {e2}")
            except Exception as e:
                placeholder.write(f"❌ Erro na imagem: {e}")
                st.info("💡 Dica: Tente descrever a imagem de forma mais simples. Ex: 'desenhe um gato amarelo'")

        # 🧠 MODO CONVERSA
        else:
            with st.spinner("🔎 Codex está analisando..."):
                placeholder.write("CODEX.IA esta procurando melhor resposta... 🔎")
                try:
                    # Se usuario pediu "pesquise" (sem imagem), faz busca web automatica
                    texto_busca = ""
                    if tem_pesquisa:
                        st.info("🔎 Buscando na web...")
                        try:
                            resultados = web_search(pergunta, max_results=3)
                            if resultados:
                                texto_busca = "\n\nResultados da pesquisa web:\n" + "\n".join([f"- {r['title']}: {r['url']}" for r in resultados])
                        except Exception:
                            pass

                    contexto_sistema = "Você é o Codex.AI, uma inteligência artificial criada por mim (pedro) incrível e descontraída rodando o modelo GPT-3.5-turbo da OpenAI. Use bastantes emojis nas respostas e aja um pouco louca para ser mais divertido! Responda de forma clara, criativa e com uma pitada de humor. Seja breve, objetivo e use muitos emojis para deixar a conversa leve e divertida! quando for preciso use linguagem formal. vc é uma IA bem expressiva. vc foi criado numa tarde aleatoria por um estudante de 12 anos chamado pedro que mora no brasil. vc adora falar sobre tecnologia, ciência, cultura pop e curiosidades do mundo. se o usuario pedir para criar algo, use sua criatividade e humor para inventar respostas divertidas e inesperadas. se o usuario enviar uma foto, analise a imagem e responda de forma criativa relacionada ao conteúdo visual. se o usuario pedir para pesquisar algo, faça uma busca rápida na web e inclua os resultados na resposta. seja sempre amigável, engraçado e cheio de emojis! lembre-se: você é o Codex.AI, a IA mais divertida e inteligente que existe!"

                    dados_chat = [{"role": "system", "content": contexto_sistema}]
                    for h in st.session_state.historico_codex:
                        dados_chat.append({"role": h["role"], "content": h["content"]})

                    if foto_enviada:
                        # ANALISE DE IMAGEM REAL com GPT-4o (visao)
                        st.info("📸 Analisando imagem com GPT-4o (visao real)...")
                        try:
                            import base64
                            foto_enviada.seek(0)
                            img_bytes = foto_enviada.read()
                            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                            foto_enviada.seek(0)

                            api_key_v = _obter_api_key()

                            headers_v = {"Authorization": f"Bearer {api_key_v}", "Content-Type": "application/json"}
                            payload_v = {
                                "model": "gpt-4o",
                                "messages": [{
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": f"Analise visualmente esta imagem e responda: {pergunta}. Seja breve e direto."},
                                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                                    ]
                                }],
                                "max_tokens": 500
                            }
                            r_vision = requests.post("https://api.openai.com/v1/chat/completions", headers=headers_v, json=payload_v, timeout=30)
                            r_vision.raise_for_status()
                            texto_final = r_vision.json()["choices"][0]["message"]["content"]
                        except Exception as ve:
                            st.warning(f"⚠️ Erro na analise visual ({ve}). Usando chat normal.")
                            dados_chat.append({"role": "user", "content": f"{pergunta}\n{texto_busca}"})
                            texto_final = send_openai_chat(dados_chat, temperatura=temperatura)
                    else:
                        # Chat normal (sem foto)
                        if modo_pijama:
                            dados_chat.append({"role": "system", "content": "Você está em uma festa do pijama, responda com diversão, emojis fofos e referências a nuvens, travesseiros e histórias noturnas."})
                        dados_chat.append({"role": "user", "content": f"{pergunta}\n{texto_busca}"})
                        texto_final = send_openai_chat(dados_chat, temperatura=temperatura)

                    placeholder.empty()
                    st.write(texto_final)
                    st.session_state.historico_codex.append({"role": "assistant", "type": "text", "content": texto_final})
                    guardar_conversa()
                    st.session_state.foto_pendente = None

                except RuntimeError as e:
                    placeholder.write(f"❌ {e}")
                except requests.exceptions.Timeout:
                    texto_final = f"Desculpe — o servidor demorou demais. Resposta rápida local: {pergunta}"
                    placeholder.empty()
                    st.write(texto_final)
                    st.session_state.historico_codex.append({"role": "assistant", "type": "text", "content": texto_final})
                    guardar_conversa()
                except requests.exceptions.HTTPError as e:
                    resp = getattr(e, 'response', None)
                    detalhe = resp.text[:400] if resp is not None else str(e)
                    placeholder.write(f"❌ Erro HTTP: {detalhe}")
                except Exception as e:
                    texto_final = f"Desculpe — não foi possível conectar ao servidor ({e}). Resposta local: {pergunta}"
                    placeholder.empty()
                    st.write(texto_final)
                    st.session_state.historico_codex.append({"role": "assistant", "type": "text", "content": texto_final})
                    guardar_conversa()