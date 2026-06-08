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

# ============================================================
# 🍎 POP-UP DE BOAS-VINDAS — EDITE AQUI O TEXTO QUE APARECE!
# ============================================================
POPUP_TITULO = "Codex.AI"
POPUP_SUBTITULO = "Liquid Glass Edition"
POPUP_TEXTO = "Sua IA inteligente com visual inspirado no iOS 26. Converse, crie imagens com IA, pesquise fotos reais na web, grave aúdio e muito mais!"
POPUP_BOTAO = "Continuar"
POPUP_NOVIDADES = "✨ Novidades: visual Liquid Glass, buscas web reais com fontes citadas, gravação de áudio local, filtro anti-memes, Stable Horde otimizado, PWA instalável"
# ============================================================

API_COST_PER_1000_TOKENS = 0.002
DEFAULT_BILLING_DOLLARS = 5.0


def estimativa_tokens_por_dolar(dollar):
    return int((dollar / API_COST_PER_1000_TOKENS) * 1000)


def estimativa_mensagens(dollar, tokens_por_mensagem=200):
    return int(estimativa_tokens_por_dolar(dollar) / tokens_por_mensagem)


def estimativa_tokens_por_texto(texto):
    palavras = len(texto.split())
    return int(palavras * 1.3) + 10


def transcrever_audio(audio_file):
    api_key = _obter_api_key()
    if not api_key:
        raise RuntimeError("Defina OPENAI_API_KEY antes de executar.")
    audio_file.seek(0)
    files = {"file": (audio_file.name, audio_file, audio_file.type)}
    data = {"model": "whisper-1"}
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=60)
    resp.raise_for_status()
    return resp.json().get("text", "")


def web_search(query, max_results=5):
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
        "Style.IA",
        ["Realista", "Cartoon", "Anime", "Cyberpunk", "Frutiger aero style", "Pintura a oleo", "Aquarela", "Surrealista", "Pixel art"]
    )
    audio = st.sidebar.file_uploader("Audio (mp3/wav)", type=["mp3", "wav"])
    if audio:
        try:
            st.sidebar.audio(audio)
        except Exception:
            pass
        if st.sidebar.button("Transcrever audio"):
            try:
                st.session_state.audio_transcricao = transcrever_audio(audio)
                st.session_state.audio_status = "Audio transcrito! Clique em enviar para usar."
            except Exception as e:
                st.session_state.audio_status = f"Erro: {e}"
        if st.session_state.audio_status:
            st.sidebar.info(st.session_state.audio_status)
        if st.session_state.audio_transcricao:
            st.sidebar.markdown("**Transcricao:**")
            st.sidebar.write(st.session_state.audio_transcricao)
            if st.sidebar.button("Enviar transcricao"):
                st.session_state.enviar_audio_transcrito = True
    return temperatura, estilo, audio


temperatura, estilo, audio = adicionar_recursos_extras()


def _obter_api_key():
    return config.get_api_key()


def send_openai_chat(dados_chat, temperatura=0.7):
    api_key = _obter_api_key()
    if not api_key:
        raise RuntimeError("Defina OPENAI_API_KEY antes de executar.")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "gpt-3.5-turbo", "messages": dados_chat, "temperature": float(temperatura), "max_tokens": 800}
    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


ARQUIVO_SALVO = "historico_codex.json"
NOTAS_ATUALIZACAO = "v3.1: Liquid Glass iOS 26 — buscas reais, audio local, PWA, notificacoes"

# --- CONFIGURACAO VISUAL ---
st.set_page_config(page_title="Codex.AI", page_icon="🧊", layout="wide")
api_key = _obter_api_key()
if not api_key:
    st.warning("Defina OPENAI_API_KEY antes de executar.")

# --- INICIALIZACAO DE ESTADO ---
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
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
    st.session_state.paleta_preset = "Liquid Glass"
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
if "popup_fechado" not in st.session_state:
    st.session_state.popup_fechado = False

# Fecha pop-up via query param
if st.query_params.get("close"):
    st.session_state.popup_fechado = True
    if st.query_params.get("notif"):
        st.markdown("""<script>
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
        </script>""", unsafe_allow_html=True)
    st.query_params.clear()
    st.rerun()

# ============================================================
# 🍎 POP-UP LIQUID GLASS
# ============================================================
if not st.session_state.popup_fechado:
    st.markdown(f"""
    <style>
    @keyframes glassPopIn {{
        0% {{ transform: translate(-50%, -50%) scale(0.85); opacity: 0; }}
        60% {{ transform: translate(-50%, -50%) scale(1.03); opacity: 1; }}
        100% {{ transform: translate(-50%, -50%) scale(1); opacity: 1; }}
    }}
    @keyframes fadeOverlay {{
        0% {{ opacity: 0; }}
        100% {{ opacity: 1; }}
    }}
    .popup-overlay {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(0,0,0,0.55);
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        z-index: 99999; display: flex; align-items: center; justify-content: center;
        animation: fadeOverlay 0.4s ease;
    }}
    .popup-glass {{
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        width: 440px; max-width: 92vw; padding: 40px 32px 32px; z-index: 100000;
        background: rgba(255,255,255,0.07);
        backdrop-filter: blur(60px) saturate(200%);
        -webkit-backdrop-filter: blur(60px) saturate(200%);
        border: 0.4px solid rgba(255,255,255,0.22);
        border-radius: 28px;
        box-shadow: 0 30px 80px rgba(0,0,0,0.50), 0 0 60px rgba(94,168,255,0.12),
                    0 0 120px rgba(94,168,255,0.06), inset 0 1px 0 rgba(255,255,255,0.06);
        animation: glassPopIn 0.55s cubic-bezier(0.25, 0.1, 0.25, 1.4);
        text-align: center;
        color: #f0f4fc;
        font-family: 'Inter', system-ui, sans-serif;
    }}
    .popup-glass::before {{
        content: '';
        position: absolute; top: -1px; left: 20px; right: 20px; height: 0.5px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.20), rgba(94,168,255,0.12), rgba(255,255,255,0.20), transparent);
    }}
    .popup-glass::after {{
        content: '';
        position: absolute; bottom: -1px; left: 20px; right: 20px; height: 0.5px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
    }}
    .popup-title {{
        font-family: 'Orbitron', 'Inter', sans-serif;
        font-size: 28px; font-weight: 700; letter-spacing: 0.5px;
        background: linear-gradient(135deg, #a0d2ff, #5ea8ff, #c4b5fd);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 2px;
    }}
    .popup-subtitle {{
        font-size: 13px; font-weight: 500; letter-spacing: 2px; text-transform: uppercase;
        color: rgba(255,255,255,0.55); margin-bottom: 20px;
    }}
    .popup-text {{
        font-size: 15px; line-height: 1.6; color: rgba(255,255,255,0.75); margin-bottom: 10px;
    }}
    .popup-novidades {{
        font-size: 12px; line-height: 1.5; color: rgba(255,255,255,0.50);
        background: rgba(94,168,255,0.06); border-radius: 14px; padding: 12px 16px;
        margin-bottom: 24px; border: 0.5px solid rgba(94,168,255,0.12);
    }}
    .popup-btn {{
        display: inline-block;
        background: rgba(255,255,255,0.08);
        backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        border: 0.5px solid rgba(94,168,255,0.25);
        border-radius: 20px; padding: 12px 42px;
        color: #a0d2ff; font-size: 16px; font-weight: 600;
        cursor: pointer; transition: all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1);
        box-shadow: 0 4px 20px rgba(94,168,255,0.10), inset 0 1px 0 rgba(255,255,255,0.05);
        text-decoration: none;
    }}
    .popup-btn:hover {{
        background: rgba(94,168,255,0.14);
        border-color: rgba(94,168,255,0.45);
        box-shadow: 0 8px 32px rgba(94,168,255,0.22), inset 0 1px 0 rgba(255,255,255,0.10);
        transform: translateY(-1px);
    }}
    </style>
    <div class="popup-overlay" id="popup-overlay">
        <div class="popup-glass">
            <div class="popup-title">{POPUP_TITULO}</div>
            <div class="popup-subtitle">{POPUP_SUBTITULO}</div>
            <div class="popup-text">{POPUP_TEXTO}</div>
            <div class="popup-novidades">{POPUP_NOVIDADES}</div>
            <div style="display:flex;gap:12px;justify-content:center;">
                <a href="?close=1" class="popup-btn" style="padding:12px 20px;">✕</a>
                <a href="?close=1&notif=1" class="popup-btn" style="flex:1;">{POPUP_BOTAO}</a>
            </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- MENU LATERAL ---
with st.sidebar:
    with st.expander("Conta", expanded=st.session_state.usuario_logado is None):
        if st.session_state.usuario_logado is None:
            modo = st.radio("Modo", ["Login", "Criar conta"], horizontal=True, key="modo_auth")
            if modo == "Login":
                login_user = st.text_input("Usuario", key="login_user", placeholder="nome de usuario")
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
                reg_user = st.text_input("Usuario (min. 3 letras)", key="reg_user")
                reg_pass = st.text_input("Senha (min. 4 caracteres)", type="password", key="reg_pass")
                if st.button("Criar conta", key="btn_reg"):
                    ok, msg, uid = auth.register_user(reg_user, reg_pass)
                    if ok:
                        st.success(msg)
                        st.info("Agora faca login com seus dados.")
                    else:
                        st.error(msg)
        else:
            u = st.session_state.usuario_logado
            st.success(f"Ola {u['display_name']}")
            st.caption(f"@{u['username']}")
            if st.button("Sair", key="btn_logout"):
                st.session_state.usuario_logado = None
                st.session_state.historico_codex = []
                st.rerun()
    st.divider()
    st.image("https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg", width=60)
    st.title("Codex.AI")
    st.text_input("Mensagem da IA", value="", key="custom_message", placeholder="Escreva uma mensagem...")
    st.caption("IA para conversas, analise de imagens e pesquisas reais.")
    with st.expander("Estimativa de custo"):
        budget_usd = st.number_input("Orcamento (USD)", min_value=1.0, max_value=50.0, value=DEFAULT_BILLING_DOLLARS, step=1.0)
        tokens = estimativa_tokens_por_dolar(budget_usd)
        mensagens = estimativa_mensagens(budget_usd)
        st.metric("Tokens", f"{tokens:,}")
        st.metric("Mensagens", f"{mensagens:,}")
    st.markdown("---")
    with st.expander("Controles", expanded=True):
        tema = st.selectbox("Tema", ["Escuro", "White"], key="tema")
        modo_imagem = st.selectbox("Modo de imagem", ["Gerar com IA", "Buscar fotos reais"], key="modo_imagem")
        modo_pijama = st.checkbox("Festa do pijama", value=False, key="modo_pijama")
        modo_neon = st.checkbox("Modo Neon", value=False, key="modo_neon")
        wallpaper_url = st.text_input("URL do papel de parede", value=st.session_state.wallpaper_url or "https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg", key="wallpaper_url")
        paletas = {
            "Liquid Glass": {"accent": "#5ea8ff", "wall": ""},
            "Padrao": {"accent": "#7d3af2", "wall": ""},
            "Neon": {"accent": "#00f5ff", "wall": ""},
            "Cyber": {"accent": "#39ff14", "wall": ""},
            "Pastel": {"accent": "#ff78c6", "wall": ""},
            "Frutiger": {"accent": "#7ec8e3", "wall": "https://wallpapers.com/images/hd/frutiger-aero-1920-x-1080-3j7tyr5tc6y368q1.jpg"}
        }
        paleta = st.selectbox("Aplicar tema", list(paletas.keys()), index=0, key="paleta_preset")
        if st.button("Aplicar tema"):
            escolha = st.session_state.get("paleta_preset")
            dados = paletas.get(escolha, paletas["Liquid Glass"])
            st.session_state.modo_neon = (escolha == "Neon")
            if dados.get("wall"):
                st.session_state.wallpaper_url = dados["wall"]
            st.rerun()
        st.subheader("Ficha Tecnica")
        st.markdown("* **Texto:** GPT-3.5-turbo\n* **Imagem IA:** Stable Horde\n* **Fotos:** DuckDuckGo Images")
        st.success("Sistema operando!")
        if modo_pijama:
            st.markdown("<div style='padding:14px;border-radius:16px;background:rgba(255,255,255,0.08);border:1px dashed rgba(168,230,207,0.20);color:#2b1532;margin-bottom:14px;'>Festa do Pijama ativada!</div>", unsafe_allow_html=True)
            if not st.session_state.get("pijama_balloons", False):
                st.balloons()
                st.session_state.pijama_balloons = True
        if st.button("IDEIAS"):
            st.session_state.ultima_ideia = "desenhe um gato robo voando sobre uma cidade neon"
        url_audio = st.text_input("URL do audio ambiente", value=st.session_state.get("audio_url", "https://cdn.freesound.org/previews/768/768783_16425075-lq.mp3"), key="audio_url")
        if st.button("Tocar audio"):
            st.audio(url_audio, loop=True)
        if st.session_state.get("audio_autoplay", True):
            st.markdown(f'<audio autoplay loop style="display:none"><source src="{url_audio}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
        st.checkbox("Som ambiente", value=st.session_state.get("audio_autoplay", True), key="audio_autoplay")
        if st.button("Resetar layout"):
            st.session_state.tema = "Escuro"
            st.session_state.modo_pijama = False
            st.rerun()
        st.divider()
        st.markdown("**Gravar audio local**")
        dur = st.number_input("Duracao (seg)", min_value=1, max_value=60, value=5, step=1, key="rec_duration")
        if st.button("Gravar e transcrever"):
            try:
                import sounddevice as sd
                import soundfile as sf
                import tempfile
                fs = 44100
                st.info(f"Gravando {dur}s...")
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
                        st.success("Audio transcrito!")
                        st.session_state.audio_transcricao = texto
                        st.session_state.enviar_audio_transcrito = True
                    except Exception as te:
                        st.error(f"Erro: {te}")
            except Exception as ie:
                st.error("Instale: pip install sounddevice soundfile")
        if st.button("Limpar Conversa"):
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
    st.sidebar.metric("Mensagens", total_msgs)

# --- TEMAS ---
if tema == "White":
    fundo = "linear-gradient(160deg, #f0f4ff 0%, #e8eef8 30%, #dce8ff 60%, #f5f0ff 100%)"
    texto = "#1a1a2e"
else:
    fundo = "linear-gradient(160deg, #050510 0%, #080c28 30%, #0a0e30 60%, #0c1035 100%)"
    texto = "#f0f4fc"

extra_css = ""
extra_html = ""
if st.session_state.get('modo_pijama', False):
    fundo = "linear-gradient(160deg, #b4a7e7 0%, #c8b6ff 40%, #f7d9ff 100%)"
    texto = "#2b1532"
    extra_css = """
    @keyframes floaty {
        0% { transform: translateY(0px); opacity: 0.9; }
        50% { transform: translateY(-14px); opacity: 1; }
        100% { transform: translateY(0px); opacity: 0.9; }
    }
    .pijama-cloud { position: fixed; width: 130px; height: 130px; background: rgba(255,255,255,0.24); border-radius: 50%; box-shadow: 0 12px 40px rgba(255,255,255,0.3); animation: floaty 12s ease-in-out infinite; z-index: 1; pointer-events:none; }
    .pijama-cloud:nth-child(1) { top: 8%; left: 5%; }
    .pijama-cloud:nth-child(2) { top: 20%; right: 8%; width: 100px; height: 100px; animation-delay: 2s; }
    .pijama-cloud:nth-child(3) { bottom: 18%; left: 12%; width: 120px; height: 120px; animation-delay: 4s; }
    .pijama-cloud:nth-child(4) { bottom: 10%; right: 18%; width: 90px; height: 90px; animation-delay: 6s; }
    """
    extra_html = """
    <div class='pijama-cloud'></div><div class='pijama-cloud'></div><div class='pijama-cloud'></div><div class='pijama-cloud'></div>
    """

accent_color = "#5ea8ff"
if st.session_state.get("wallpaper_url"):
    wp = st.session_state.get("wallpaper_url").strip()
    if wp:
        fundo = f"url('{wp}') center/cover fixed"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Orbitron:wght@400;600;700&display=swap');
    :root {{
        --glass-bg: rgba(255,255,255,0.05);
        --glass-border: rgba(255,255,255,0.14);
        --accent: {accent_color};
        --card-radius: 26px;
    }}
    body, .stApp, .block-container {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; color: {texto}; }}
    h1, h2, h3, .stTitle {{ font-family: 'Orbitron', 'Inter', sans-serif; letter-spacing: 0.5px; font-weight: 700; }}
    .stApp {{ background: {fundo} !important; }}

    /* LIQUID GLASS iOS 26 TURBINADO */
    @keyframes liquidMorph {{
        0%,100% {{ background-position: 0% 50%; }}
        25% {{ background-position: 50% 100%; }}
        50% {{ background-position: 100% 50%; }}
        75% {{ background-position: 50% 0%; }}
    }}
    @keyframes gentleFloat {{
        0%,100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-8px); }}
    }}
    @keyframes iridescentGlow {{
        0%,100% {{ box-shadow: 0 0 60px rgba(94,168,255,0.08), 0 0 120px rgba(94,168,255,0.04), inset 0 1px 0 rgba(255,255,255,0.04); }}
        50% {{ box-shadow: 0 0 80px rgba(94,168,255,0.16), 0 0 160px rgba(94,168,255,0.08), inset 0 1px 0 rgba(255,255,255,0.08); }}
    }}
    @keyframes borderShift {{
        0%,100% {{ border-color: rgba(94,168,255,0.14); }}
        50% {{ border-color: rgba(168,130,255,0.20); }}
    }}

    .block-container {{ max-width: 1100px; padding: 20px 30px !important; margin: 0 auto; }}
    div[data-testid="stSidebar"] {{
        min-width: 250px !important; max-width: 320px !important;
        background: rgba(255,255,255,0.03) !important;
        backdrop-filter: blur(50px) saturate(200%) !important;
        -webkit-backdrop-filter: blur(50px) saturate(200%) !important;
        border-right: 0.5px solid rgba(255,255,255,0.08) !important;
    }}

    /* CARDS LIQUID GLASS */
    div[data-testid="stSidebar"] > div, .stChatMessage, div[data-testid="stFileUploader"], .stBlock {{
        background: rgba(255,255,255,0.04) !important;
        backdrop-filter: blur(50px) saturate(220%) !important;
        -webkit-backdrop-filter: blur(50px) saturate(220%) !important;
        border: 0.5px solid rgba(255,255,255,0.14) !important;
        border-radius: var(--card-radius) !important;
        box-shadow: 0 8px 40px rgba(0,0,0,0.25), 0 0 60px rgba(94,168,255,0.06), inset 0 1px 0 rgba(255,255,255,0.04) !important;
        transition: all 0.7s cubic-bezier(0.25, 0.1, 0.25, 1);
        animation: iridescentGlow 10s ease-in-out infinite;
    }}
    .stChatMessage {{
        border-radius: 22px !important; padding: 18px !important; margin-bottom:14px !important;
        max-width: 960px;
        background: rgba(255,255,255,0.03) !important;
        border: 0.5px solid rgba(255,255,255,0.10) !important;
        animation: borderShift 12s ease-in-out infinite;
    }}
    .stChatMessage:hover {{
        transform: translateY(-3px);
        box-shadow: 0 24px 60px rgba(94,168,255,0.16), 0 4px 20px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.06) !important;
    }}

    /* BOTOES LIQUID GLASS */
    .stSidebar .stButton > button, .stBlock .stButton > button {{
        background: rgba(255,255,255,0.05) !important;
        backdrop-filter: blur(30px) saturate(200%) !important;
        -webkit-backdrop-filter: blur(30px) saturate(200%) !important;
        border: 0.5px solid rgba(255,255,255,0.16) !important;
        color: {texto} !important;
        padding: 10px 18px !important;
        border-radius: 22px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.05) !important;
        transition: all 0.5s cubic-bezier(0.25, 0.1, 0.25, 1) !important;
        font-weight: 500; letter-spacing: 0.3px;
    }}
    .stSidebar .stButton > button:hover, .stBlock .stButton > button:hover {{
        background: rgba(255,255,255,0.10) !important;
        transform: translateY(-2px);
        border-radius: 26px !important;
        box-shadow: 0 10px 36px rgba(94,168,255,0.24), inset 0 1px 0 rgba(255,255,255,0.14) !important;
        border-color: rgba(94,168,255,0.30) !important;
    }}
    .stButton > button:active {{ transform: scale(0.96); border-radius: 20px !important; }}

    .ai-badge {{
        display: inline-flex; align-items: center; gap: 10px;
        padding: 14px 22px; border-radius: 24px;
        background: rgba(94,168,255,0.06);
        backdrop-filter: blur(40px); -webkit-backdrop-filter: blur(40px);
        border: 0.4px solid rgba(94,168,255,0.20);
        color: {texto}; box-shadow: 0 10px 40px rgba(94,168,255,0.08);
        font-weight: 600; margin-bottom: 16px;
        animation: gentleFloat 7s ease-in-out infinite;
    }}

    /* INPUTS VIDRO */
    input, textarea, .stTextInput, .stTextArea {{
        border-radius: 20px !important; padding: 12px 16px !important;
        background: rgba(255,255,255,0.03) !important;
        color: {texto} !important;
        border: 0.5px solid rgba(255,255,255,0.10) !important;
        backdrop-filter: blur(30px) !important; -webkit-backdrop-filter: blur(30px) !important;
        transition: all 0.5s cubic-bezier(0.25, 0.1, 0.25, 1) !important;
    }}
    input:focus, textarea:focus {{
        border-color: rgba(94,168,255,0.40) !important;
        box-shadow: 0 0 40px rgba(94,168,255,0.12), 0 0 80px rgba(94,168,255,0.06) !important;
        transform: scale(1.01);
    }}
    input::placeholder, textarea::placeholder {{ color: rgba(255,255,255,0.25) !important; }}

    /* 12 BOLHAS LIQUID GLASS */
    @keyframes liquidBubble {{
        0% {{ transform: translateY(115vh) translateX(0) scale(0.2); opacity: 0; }}
        8% {{ opacity: 0.18; }}
        92% {{ opacity: 0.10; }}
        100% {{ transform: translateY(-120px) translateX(50px) scale(1.2); opacity: 0; }}
    }}
    .glass-bubble {{
        position: fixed; bottom: -100px; border-radius: 50%; pointer-events: none; z-index: 0;
        background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.40), rgba(94,168,255,0.12) 55%, rgba(168,130,255,0.04) 80%, transparent);
        box-shadow: 0 0 50px rgba(94,168,255,0.08);
        animation: liquidBubble 26s ease-in infinite;
        filter: blur(0.3px);
    }}
    .glass-bubble:nth-child(1) {{ width: 90px; height: 90px; left: 3%; animation-delay: 0s; animation-duration: 23s; }}
    .glass-bubble:nth-child(2) {{ width: 65px; height: 65px; left: 10%; animation-delay: 2s; animation-duration: 27s; }}
    .glass-bubble:nth-child(3) {{ width: 110px; height: 110px; left: 22%; animation-delay: 4s; animation-duration: 21s; }}
    .glass-bubble:nth-child(4) {{ width: 55px; height: 55px; left: 32%; animation-delay: 1s; animation-duration: 29s; }}
    .glass-bubble:nth-child(5) {{ width: 85px; height: 85px; left: 42%; animation-delay: 6s; animation-duration: 25s; }}
    .glass-bubble:nth-child(6) {{ width: 70px; height: 70px; left: 52%; animation-delay: 3s; animation-duration: 22s; }}
    .glass-bubble:nth-child(7) {{ width: 100px; height: 100px; left: 62%; animation-delay: 5s; animation-duration: 28s; }}
    .glass-bubble:nth-child(8) {{ width: 50px; height: 50px; left: 72%; animation-delay: 0.5s; animation-duration: 24s; }}
    .glass-bubble:nth-child(9) {{ width: 80px; height: 80px; left: 80%; animation-delay: 3.5s; animation-duration: 26s; }}
    .glass-bubble:nth-child(10) {{ width: 95px; height: 95px; left: 88%; animation-delay: 1.5s; animation-duration: 20s; }}
    .glass-bubble:nth-child(11) {{ width: 60px; height: 60px; left: 94%; animation-delay: 4.5s; animation-duration: 30s; }}
    .glass-bubble:nth-child(12) {{ width: 75px; height: 75px; left: 48%; animation-delay: 7s; animation-duration: 23s; }}

    /* SCROLLBAR MACOS */
    ::-webkit-scrollbar {{ width: 5px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.08); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.16); }}

    /* ANIMACOES DE ENTRADA CHAT */
    @keyframes slideUpFade {{
        0% {{ transform: translateY(24px); opacity: 0; }}
        100% {{ transform: translateY(0); opacity: 1; }}
    }}
    .stChatMessage {{ animation: slideUpFade 0.5s cubic-bezier(0.25, 0.1, 0.25, 1) !important; }}

    .stApp {{ overflow-x: hidden; }}
    {extra_css}
    </style>
    <div class='glass-bubble'></div><div class='glass-bubble'></div><div class='glass-bubble'></div>
    <div class='glass-bubble'></div><div class='glass-bubble'></div><div class='glass-bubble'></div>
    <div class='glass-bubble'></div><div class='glass-bubble'></div><div class='glass-bubble'></div>
    <div class='glass-bubble'></div><div class='glass-bubble'></div><div class='glass-bubble'></div>
    {extra_html}
    <script>
    if ('serviceWorker' in navigator) {{
        navigator.serviceWorker.register('/service-worker.js').catch(function(){{}});
    }}
    </script>
""", unsafe_allow_html=True)


def guardar_conversa():
    user = st.session_state.get("usuario_logado")
    if user:
        return
    else:
        mensagens_texto = [msg for msg in st.session_state.historico_codex if msg["type"] == "text"]
        with open(ARQUIVO_SALVO, "w", encoding="utf-8") as f:
            json.dump(mensagens_texto, f, ensure_ascii=False, indent=4)


def adicionar_ao_historico(role, content, msg_type="text"):
    st.session_state.historico_codex.append({"role": role, "type": msg_type, "content": content})
    user = st.session_state.get("usuario_logado")
    if user:
        auth.save_chat_message(user["id"], role, content, msg_type)
    else:
        guardar_conversa()


# --- CORPO PRINCIPAL ---
st.title("Codex.AI")
custom_msg = st.session_state.get("custom_message", "")
if custom_msg:
    st.markdown(f"<div class='ai-badge'>🧊 {custom_msg}</div>", unsafe_allow_html=True)
if st.session_state.get('modo_pijama', False):
    st.markdown("### Festa do Pijama! Vamos conversar numa noite estrelada...")
st.caption("GPT-3.5-turbo | Stable Horde (IA) | DuckDuckGo Images")
st.info(f"Bem-vindo ao Codex.IA! {NOTAS_ATUALIZACAO}")

for item in st.session_state.historico_codex:
    with st.chat_message(item["role"]):
        st.write(item["content"])

st.session_state.camera_ativa = st.sidebar.checkbox("Ativar camera", value=st.session_state.camera_ativa, key="toggle_camera")
if st.session_state.camera_ativa:
    col1, col2 = st.columns(2)
    with col1:
        foto_upload = st.file_uploader("Upload foto", type=["png", "jpg", "jpeg"], key="upload_foto")
    with col2:
        foto_camera = st.camera_input("Tirar foto", key="camera_foto")
    if foto_camera is not None:
        st.session_state.foto_pendente = foto_camera
    elif foto_upload is not None:
        st.session_state.foto_pendente = foto_upload
    if st.session_state.foto_pendente is not None:
        st.caption("Foto capturada - sera enviada na proxima mensagem")
        if st.button("Descartar foto"):
            st.session_state.foto_pendente = None
            st.rerun()
else:
    st.session_state.foto_pendente = None
    st.caption("Camera desativada | Ative no menu")

foto_enviada = st.session_state.foto_pendente
pergunta = st.chat_input("Converse com o Codex.IA...")
if pergunta:
    cols_q = st.columns([1, 1, 2])
    pesquisar = cols_q[0].button("Pesquisa web")
    incluir_resultados = cols_q[1].checkbox("Incluir na pergunta", value=False)
else:
    pesquisar = False
    incluir_resultados = False

if st.session_state.enviar_audio_transcrito and st.session_state.audio_transcricao:
    pergunta = st.session_state.audio_transcricao
    st.session_state.enviar_audio_transcrito = False

if pesquisar:
    if not pergunta or pergunta.strip() == "":
        st.warning("Digite algo para pesquisar.")
    else:
        try:
            st.info("Buscando na web...")
            resultados = web_search(pergunta, max_results=5)
            if not resultados:
                st.warning("Nenhum resultado encontrado.")
            else:
                with st.expander("Resultados da pesquisa web", expanded=True):
                    for r in resultados:
                        st.markdown(f"- **{r['title']}** - [{r['url']}]({r['url']})")
                if incluir_resultados:
                    sintese = "\n\nRESULTADOS DA PESQUISA WEB (use estes dados reais, cite as fontes):\n" + "\n".join([f"- {r['title']}: {r['url']}" for r in resultados])
                    pergunta = (pergunta or "") + sintese
        except Exception as e:
            st.error(f"Erro: {e}")

if pergunta:
    texto_usuario = pergunta
    audio_transcricao = None
    if audio:
        try:
            audio_transcricao = transcrever_audio(audio)
            texto_usuario += f" [Audio: {audio.name}]"
        except Exception as e:
            st.sidebar.error(f"Erro audio: {e}")
    if foto_enviada:
        texto_usuario += f" [Foto: {foto_enviada.name}]"

    with st.chat_message("user"):
        st.write(texto_usuario)
        if foto_enviada:
            st.image(Image.open(foto_enviada), width=300)
        if audio_transcricao:
            st.write(f"Transcricao: {audio_transcricao}")
            texto_usuario += f"\n\nAudio: {audio_transcricao}"
            st.session_state.historico_codex.append({"role": "user", "type": "text", "content": texto_usuario})
        else:
            st.session_state.historico_codex.append({"role": "user", "type": "text", "content": texto_usuario})

    with st.chat_message("assistant"):
        placeholder = st.empty()
        p_lower = pergunta.lower()
        tem_imagem = any(t in p_lower for t in ["imagem", "foto", "figure", "picture"])
        tem_criacao = any(t in p_lower for t in ["crie", "desenhe", "gere", "criar", "desenhar", "gerar", "faca"])
        tem_pesquisa = any(t in p_lower for t in ["pesquise", "pesquisar", "busque", "buscar", "procure", "procurar", "ache", "achar", "mostre", "mostrar", "quero ver"])

        if (tem_pesquisa and tem_imagem) or tem_criacao or any(t in p_lower for t in ["me de uma foto", "me de uma imagem"]):
            placeholder.write("Gerando sua imagem...")
            try:
                texto_limpo = pergunta.lower()
                for termo in [
                    "crie a imagem de um", "crie a imagem de", "crie imagem de um", "crie imagem de",
                    "desenhe um", "desenhe uma", "desenhe o", "desenhe a", "desenhe",
                    "faca uma foto de um", "faca um", "faca uma foto de", "foto de um",
                    "foto de uma", "foto do", "foto da", "foto de",
                    "gere a imagem", "gere um", "create an", "draw a", "generate a",
                    "make a photo of", "quero ver um", "me de uma foto de", "me de uma imagem de"
                ]:
                    texto_limpo = texto_limpo.replace(termo, "")
                texto_limpo = texto_limpo.strip()

                placeholder.empty()
                st.markdown(f"**Gerando: `{texto_limpo}`**")

                palavras_pesquisa = ["pesquise", "pesquisar", "busque", "buscar", "procure", "procurar", "ache", "achar", "mostre", "mostrar", "quero ver", "me de uma foto", "me de uma imagem"]
                palavras_criacao = ["crie", "desenhe", "gere", "criar", "desenhar", "gerar", "faca"]
                eh_pesquisa = any(p in pergunta.lower() for p in palavras_pesquisa)
                eh_criacao = any(p in pergunta.lower() for p in palavras_criacao)
                modo = st.session_state.get("modo_imagem", "Gerar com IA")
                usar_busca = ((eh_pesquisa and not eh_criacao) or "Buscar" in modo)

                if usar_busca:
                    try:
                        st.info("Buscando imagens na web...")
                        from ddgs import DDGS
                        from itertools import islice
                        img_results = list(islice(DDGS().images(texto_limpo, max_results=12), 12))
                        palavras_meme = ["meme", "funny", "comic", "troll", "lol", "reaction", "fail", "gif engra"]
                        img_results = [i for i in img_results if not any(m in i.get("title", "").lower() for m in palavras_meme)][:6]
                        if img_results:
                            st.success(f"{len(img_results)} imagens encontradas!")
                            for img in img_results:
                                img_url = img.get("image") or img.get("thumbnail")
                                if img_url:
                                    try:
                                        r_img = requests.get(img_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                                        if r_img.status_code == 200 and len(r_img.content) > 500:
                                            st.image(BytesIO(r_img.content), caption=img.get("title", "")[:60], width=400)
                                            st.markdown(f"""<script>
                                            if ('Notification' in window && Notification.permission === 'granted') {{
                                                new Notification('Codex IA', {{body: 'Imagem carregada: {img.get("title","")[:50]}', icon: 'https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg'}});
                                            }}
                                            </script>""", unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"[{img.get('title','Imagem')[:50]}]({img_url})")
                                    except Exception:
                                        st.markdown(f"[{img.get('title','Link')[:50]}]({img_url})")
                            adicionar_ao_historico("assistant", f"Imagens buscadas: {texto_limpo}")
                            st.session_state.foto_pendente = None
                        else:
                            st.warning("Nenhuma imagem encontrada.")
                    except Exception as e2:
                        st.error(f"Erro: {e2}")
                else:
                    try:
                        st.info("CODEX.AI esta gerando...")
                        headers_sh = {"apikey": "0000000000"}
                        payload_sh = {"prompt": texto_limpo}
                        r_sh = requests.post("https://stablehorde.net/api/v2/generate/async", json=payload_sh, headers=headers_sh, timeout=15)
                        r_sh.raise_for_status()
                        if r_sh.status_code == 202:
                            job_id = r_sh.json()["id"]
                            status_url = f"https://stablehorde.net/api/v2/generate/status/{job_id}"
                            imagem_url = None
                            for tentativa in range(10):
                                time.sleep(1.5)
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
                                st.success("Imagem gerada por IA!")
                                st.markdown(f"""<script>
                                if ('Notification' in window && Notification.permission === 'granted') {{
                                    new Notification('Codex IA', {{body: 'Sua imagem ficou pronta!', icon: 'https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg'}});
                                }}
                                </script>""", unsafe_allow_html=True)
                                adicionar_ao_historico("assistant", f"Imagem gerada: {texto_limpo}")
                                st.session_state.foto_pendente = None
                            else:
                                st.warning("Stable Horde nao respondeu. Tente novamente.")
                        else:
                            st.warning(f"Erro {r_sh.status_code}")
                    except requests.exceptions.Timeout:
                        st.warning("Tempo esgotado. Tente novamente.")
                    except Exception as e2:
                        st.error(f"Erro: {e2}")
            except Exception as e:
                placeholder.write(f"Erro: {e}")
                st.info("Dica: descreva de forma simples. Ex: 'desenhe um gato'")
        else:
            with st.spinner("Analisando..."):
                placeholder.write("Procurando melhor resposta...")
                try:
                    texto_busca = ""
                    if tem_pesquisa:
                        st.info("Buscando na web...")
                        try:
                            resultados = web_search(pergunta, max_results=3)
                            if resultados:
                                texto_busca = "\n\nRESULTADOS DA PESQUISA WEB (use estes dados reais, cite as fontes):\n" + "\n".join([f"- {r['title']}: {r['url']}" for r in resultados])
                        except Exception:
                            pass

                    contexto_sistema = "Voce e o Codex.AI rodando GPT-3.5-turbo. Use emojis e seja expressivo. Se houver RESULTADOS DA PESQUISA WEB anexados, USE esses dados reais e CITE os links como fontes. Nao invente se tiver dados reais. Seja breve, criativo e use emojis."
                    dados_chat = [{"role": "system", "content": contexto_sistema}]
                    for h in st.session_state.historico_codex:
                        dados_chat.append({"role": h["role"], "content": h["content"]})

                    if foto_enviada:
                        st.info("Analisando imagem com GPT-4o...")
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
                                "messages": [{"role": "user", "content": [
                                    {"type": "text", "text": f"Analise esta imagem e responda: {pergunta}"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                                ]}],
                                "max_tokens": 500
                            }
                            r_vision = requests.post("https://api.openai.com/v1/chat/completions", headers=headers_v, json=payload_v, timeout=30)
                            r_vision.raise_for_status()
                            texto_final = r_vision.json()["choices"][0]["message"]["content"]
                        except Exception as ve:
                            st.warning(f"Erro visao ({ve}). Usando chat normal.")
                            dados_chat.append({"role": "user", "content": f"{pergunta}\n{texto_busca}"})
                            texto_final = send_openai_chat(dados_chat, temperatura=temperatura)
                    else:
                        if modo_pijama:
                            dados_chat.append({"role": "system", "content": "Festa do pijama! Use emojis fofos, nuvens, travesseiros."})
                        dados_chat.append({"role": "user", "content": f"{pergunta}\n{texto_busca}"})
                        texto_final = send_openai_chat(dados_chat, temperatura=temperatura)

                    placeholder.empty()
                    st.write(texto_final)
                    adicionar_ao_historico("assistant", texto_final)
                    st.session_state.foto_pendente = None

                except RuntimeError as e:
                    placeholder.write(f"Erro: {e}")
                except requests.exceptions.Timeout:
                    placeholder.empty()
                    st.write("Servidor demorou. Tente novamente.")
                    adicionar_ao_historico("assistant", "Erro de timeout.")
                except Exception as e:
                    placeholder.empty()
                    st.write(f"Erro: {e}. Tente novamente.")
                    adicionar_ao_historico("assistant", f"Erro: {e}")