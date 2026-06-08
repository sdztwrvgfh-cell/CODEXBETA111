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
    palavras = len(texto.split())
    return int(palavras * 1.3) + 10


def transcrever_audio(audio_file):
    api_key = _obter_api_key()
    if not api_key:
        raise RuntimeError("Defina a variavel ambiente OPENAI_API_KEY antes de executar.")
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
        "Style.IA (still in test. BETA)",
        ["Realista", "Cartoon", "Anime", "Cyberpunk", "Frutiger aero style", "Pintura a oleo", "Aquarela", "Surrealista", "Pixel art"]
    )
    audio = st.sidebar.file_uploader("Envie audio para o Codex (mp3/wav)", type=["mp3", "wav"])
    if audio:
        try:
            st.sidebar.audio(audio)
        except Exception:
            pass
        if st.sidebar.button("Transcrever audio"):
            try:
                st.session_state.audio_transcricao = transcrever_audio(audio)
                st.session_state.audio_status = "Audio transcrito com sucesso. Clique em enviar para usar a transcricao."
            except Exception as e:
                st.session_state.audio_status = f"Erro ao transcrever: {e}"
        if st.session_state.audio_status:
            st.sidebar.info(st.session_state.audio_status)
        if st.session_state.audio_transcricao:
            st.sidebar.markdown("**Transcricao atual:**")
            st.sidebar.write(st.session_state.audio_transcricao)
            if st.sidebar.button("Enviar audio transcrito como mensagem"):
                st.session_state.enviar_audio_transcrito = True
    return temperatura, estilo, audio


temperatura, estilo, audio = adicionar_recursos_extras()


def _obter_api_key():
    return config.get_api_key()


def send_openai_chat(dados_chat, temperatura=0.7):
    api_key = _obter_api_key()
    if not api_key:
        raise RuntimeError("Defina a variavel ambiente OPENAI_API_KEY antes de executar.")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "gpt-3.5-turbo", "messages": dados_chat, "temperature": float(temperatura), "max_tokens": 800}
    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


ARQUIVO_SALVO = "historico_codex.json"
NOTAS_ATUALIZACAO = "v3: UI Liquid Glass iOS 26, buscas web reais, correcoes de bugs, gravacao de audio, PWA"

# --- CONFIGURACAO VISUAL ---
st.set_page_config(page_title="Codex.AI", page_icon="🧊", layout="wide")
api_key = _obter_api_key()
if not api_key:
    st.warning("Defina a variavel ambiente OPENAI_API_KEY antes de executar.")

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
    st.session_state.paleta_preset = "Padrao"
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
    with st.expander("Conta", expanded=st.session_state.usuario_logado is None):
        if st.session_state.usuario_logado is None:
            modo = st.radio("Modo", ["Login", "Criar conta"], horizontal=True, key="modo_auth")
            if modo == "Login":
                login_user = st.text_input("Usuario", key="login_user", placeholder="seu nome de usuario")
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
                reg_user = st.text_input("Usuario (min. 3 letras)", key="reg_user", placeholder="escolha um nome")
                reg_pass = st.text_input("Senha (min. 4 caracteres)", type="password", key="reg_pass", placeholder="crie uma senha")
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
            if st.button("Sair da conta", key="btn_logout"):
                st.session_state.usuario_logado = None
                st.session_state.historico_codex = []
                st.rerun()
    st.divider()
    st.image("https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg", width=60)
    st.title("Codex.AI")
    st.text_input("Mensagem da IA", value="", key="custom_message", placeholder="Escreva uma mensagem curta...")
    st.caption("Codex: IA incrivel para conversas, analise de imagens e pesquisas! Note que uma IA nao substitui diagnosticos reais.")
    with st.expander("Estimativa de custo da API"):
        st.write("OpenAI `gpt-3.5-turbo` custa cerca de US$0,002 por 1000 tokens.")
        budget_usd = st.number_input("Simular orcamento em dolares", min_value=1.0, max_value=50.0, value=DEFAULT_BILLING_DOLLARS, step=1.0)
        tokens = estimativa_tokens_por_dolar(budget_usd)
        mensagens = estimativa_mensagens(budget_usd)
        st.metric("Tokens estimados", f"{tokens:,}")
        st.metric("Mensagens estimadas", f"{mensagens:,}")
        st.info("So o chat consome a quota da OpenAI. Audio transcrito tambem consome tokens.")
    st.markdown("---")
    with st.expander("Controles", expanded=True):
        tema = st.selectbox("Tema do Site", ["Escuro", "White"], key="tema")
        modo_imagem = st.selectbox("Modo de imagem", ["Gerar com IA", "Buscar fotos reais"], key="modo_imagem")
        modo_pijama = st.checkbox("Festa do pijama", value=False, key="modo_pijama")
        estilo_divertido = st.selectbox("Modo divertido", ["Normal", "Futurista", "Anime", "Retro"], key="estilo_divertido")
        modo_neon = st.checkbox("Modo Neon (vibes 2000)", value=False, key="modo_neon")
        wallpaper_url = st.text_input("URL do papel de parede", value="https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg", key="wallpaper_url", placeholder="https://...jpg")
        paletas = {
            "Padrao": {"accent": "#7d3af2", "wall": ""},
            "Liquid Glass": {"accent": "#5ea8ff", "wall": ""},
            "Neon": {"accent": "#00f5ff", "wall": ""},
            "Cyber": {"accent": "#39ff14", "wall": ""},
            "Pastel": {"accent": "#ff78c6", "wall": ""},
            "Frutiger": {"accent": "#7ec8e3", "wall": "https://wallpapers.com/images/hd/frutiger-aero-1920-x-1080-3j7tyr5tc6y368q1.jpg"}
        }
        paleta = st.selectbox("Aplicar tema", list(paletas.keys()), index=0, key="paleta_preset")
        if st.button("Aplicar tema"):
            escolha = st.session_state.get("paleta_preset")
            dados = paletas.get(escolha, paletas["Padrao"])
            st.session_state.modo_neon = (escolha == "Neon")
            if dados.get("wall"):
                st.session_state.wallpaper_url = dados["wall"]
            st.rerun()
        st.subheader("Ficha Tecnica")
        st.markdown("* **Modelo de Texto:** GPT-3.5-turbo (OpenAI)\n* **Imagem IA:** Stable Horde\n* **Fotos reais:** DuckDuckGo Images (ddgs)")
        st.success("Sistema funcionando normalmente!")
        if modo_pijama:
            st.markdown("<div style='padding:14px;border-radius:16px;background:rgba(255,255,255,0.08);border:1px dashed rgba(168,230,207,0.20);color:#2b1532;margin-bottom:14px;'>Modo Festa do Pijama ativado! Tudo fica mais macio, divertido e com nuvens.</div>", unsafe_allow_html=True)
            if not st.session_state.get("pijama_balloons", False):
                st.balloons()
                st.session_state.pijama_balloons = True
            st.info("Esta tudo tematico: nuvens, travesseiros e emojis suaves estao liberados.")
            if st.button("Conta uma historia de dormir"):
                st.session_state.pijama_story_request = True
        if st.button("IDEIAS"):
            st.session_state.ultima_ideia = "desenhe um gato robo voando sobre uma cidade neon"
        url_audio = st.text_input("URL do audio ambiente", value=st.session_state.get("audio_url", "https://cdn.freesound.org/previews/768/768783_16425075-lq.mp3"), key="audio_url")
        if st.button("Tocar audio"):
            st.audio(url_audio, loop=True)
        if st.session_state.get("audio_autoplay", True):
            st.markdown(f'<audio autoplay loop style="display:none"><source src="{url_audio}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
        st.checkbox("Som ambiente automatico", value=st.session_state.get("audio_autoplay", True), key="audio_autoplay")
        if st.button("Recomendar prompts"):
            st.session_state.ultima_ideia = "Crie uma imagem de um cachorro astronauta explorando a lua!"
        if st.button("Resetar layout"):
            st.session_state.tema = "Escuro"
            st.session_state.modo_pijama = False
            st.session_state.estilo_divertido = "Normal"
            st.rerun()
        st.divider()
        st.markdown("**Gravar audio pelo microfone (local)**")
        dur = st.number_input("Duracao (segundos)", min_value=1, max_value=60, value=5, step=1, key="rec_duration")
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
                        st.success("Audio transcrito com sucesso.")
                        st.session_state.audio_transcricao = texto
                        st.session_state.enviar_audio_transcrito = True
                        st.info("Transcricao pronta: clique em enviar para usar como mensagem.")
                    except Exception as te:
                        st.error(f"Erro ao transcrever: {te}")
            except Exception as ie:
                st.error("Para gravar localmente instale: pip install sounddevice soundfile")
                st.write(str(ie))
        if "ultima_ideia" in st.session_state:
            st.info(f"Experimente: {st.session_state.ultima_ideia}")
        st.markdown("---")
        if st.button("Limpar Conversa Salva"):
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
    st.sidebar.metric("Mensagens salvas", total_msgs)
    st.write("DICA: peca para desenhar um gato astronauta na lua ou analisar uma foto sua!")

# --- TEMAS ---
if tema == "White":
    fundo = "linear-gradient(160deg, #f0f4ff 0%, #e8eef8 30%, #dce8ff 60%, #f5f0ff 100%)"
    texto = "#1a1a2e"
else:
    fundo = "linear-gradient(160deg, #0a0a1a 0%, #0d1035 30%, #0f1038 60%, #111840 100%)"
    texto = "#f0f4fc"

extra_css = ""
extra_html = ""
if st.session_state.get('modo_pijama', False):
    fundo = "linear-gradient(160deg, #b4a7e7 0%, #c8b6ff 40%, #f7d9ff 100%)"
    texto = "#2b1532"
    extra_css = """
    @keyframes floaty {
        0% { transform: translateY(0px) translateX(0px); opacity: 0.9; }
        50% { transform: translateY(-12px) translateX(5px); opacity: 1; }
        100% { transform: translateY(0px) translateX(0px); opacity: 0.9; }
    }
    .pijama-cloud { position: fixed; width: 130px; height: 130px; background: rgba(255,255,255,0.24); border-radius: 50%; box-shadow: 0 12px 40px rgba(255,255,255,0.3); animation: floaty 12s ease-in-out infinite; z-index: 1; pointer-events:none; }
    .pijama-cloud:nth-child(1) { top: 8%; left: 5%; }
    .pijama-cloud:nth-child(2) { top: 20%; right: 8%; width: 100px; height: 100px; animation-delay: 2s; }
    .pijama-cloud:nth-child(3) { bottom: 18%; left: 12%; width: 120px; height: 120px; animation-delay: 4s; }
    .pijama-cloud:nth-child(4) { bottom: 10%; right: 18%; width: 90px; height: 90px; animation-delay: 6s; }
    .pijama-badge { position: fixed; top: 14%; right: 14%; z-index: 2; color: #5d2b7e; font-size: 19px; font-weight: 700; }
    """
    extra_html = """
    <div class='pijama-cloud'></div><div class='pijama-cloud'></div><div class='pijama-cloud'></div><div class='pijama-cloud'></div>
    <div class='pijama-badge'>Festa do Pijama</div>
    """

accent_color = "#5ea8ff" if st.session_state.get("modo_neon", False) else "#5ea8ff"
if st.session_state.get("wallpaper_url"):
    wp = st.session_state.get("wallpaper_url").strip()
    if wp:
        fundo = f"url('{wp}') center/cover fixed"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Orbitron:wght@400;600&display=swap');
    :root {{
        --glass-bg: rgba(255,255,255,0.06);
        --glass-border: rgba(255,255,255,0.16);
        --accent: {accent_color};
        --card-radius: 24px;
    }}
    body, .stApp, .block-container {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; color: {texto}; }}
    h1, h2, h3, .stTitle {{ font-family: 'Orbitron', 'Inter', sans-serif; letter-spacing: 0.4px; font-weight: 600; }}
    .stApp {{ background: {fundo} !important; }}

    /* LIQUID GLASS iOS 26 */
    @keyframes liquidMorph {{
        0%,100% {{ background-position: 0% 50%; }}
        25% {{ background-position: 50% 100%; }}
        50% {{ background-position: 100% 50%; }}
        75% {{ background-position: 50% 0%; }}
    }}
    @keyframes gentleFloat {{
        0%,100% {{ transform: translateY(0px) scale(1); }}
        50% {{ transform: translateY(-6px) scale(1.02); }}
    }}
    @keyframes softGlow {{
        0%,100% {{ box-shadow: 0 0 40px rgba(94,168,255,0.08), 0 0 80px rgba(94,168,255,0.04); }}
        50% {{ box-shadow: 0 0 60px rgba(94,168,255,0.15), 0 0 120px rgba(94,168,255,0.08); }}
    }}
    @keyframes iridescentShift {{
        0% {{ filter: hue-rotate(0deg); }}
        100% {{ filter: hue-rotate(20deg); }}
    }}

    .block-container {{ max-width: 1100px; padding: 20px 30px !important; margin: 0 auto; }}
    div[data-testid="stSidebar"] {{
        min-width: 250px !important; max-width: 320px !important;
        background: rgba(255,255,255,0.04) !important;
        backdrop-filter: blur(40px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(40px) saturate(180%) !important;
        border-right: 0.5px solid rgba(255,255,255,0.10) !important;
    }}

    /* Cards Liquid Glass */
    div[data-testid="stSidebar"] > div, .stChatMessage, div[data-testid="stFileUploader"], .stBlock {{
        background: rgba(255,255,255,0.04) !important;
        backdrop-filter: blur(35px) saturate(200%) !important;
        -webkit-backdrop-filter: blur(35px) saturate(200%) !important;
        border: 0.5px solid rgba(255,255,255,0.15) !important;
        border-radius: var(--card-radius) !important;
        box-shadow: 0 8px 40px rgba(0,0,0,0.20), 0 2px 8px rgba(94,168,255,0.06), inset 0 1px 0 rgba(255,255,255,0.04) !important;
        transition: all 0.6s cubic-bezier(0.25, 0.1, 0.25, 1);
    }}
    .stChatMessage {{
        border-radius: 22px !important; padding: 18px !important; margin-bottom:14px !important;
        max-width: 960px;
        background: rgba(255,255,255,0.03) !important;
        border: 0.5px solid rgba(255,255,255,0.10) !important;
    }}
    .stChatMessage:hover {{
        transform: translateY(-3px);
        box-shadow: 0 20px 50px rgba(94,168,255,0.12), 0 4px 16px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.06) !important;
    }}

    /* Botoes Liquid Glass */
    .stSidebar .stButton > button, .stBlock .stButton > button {{
        background: rgba(255,255,255,0.06) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
        border: 0.5px solid rgba(255,255,255,0.16) !important;
        color: {texto} !important;
        padding: 10px 18px !important;
        border-radius: 20px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.05) !important;
        transition: all 0.5s cubic-bezier(0.25, 0.1, 0.25, 1) !important;
        font-weight: 500;
        letter-spacing: 0.2px;
    }}
    .stSidebar .stButton > button:hover, .stBlock .stButton > button:hover {{
        background: rgba(255,255,255,0.10) !important;
        transform: translateY(-1px);
        box-shadow: 0 8px 30px rgba(94,168,255,0.20), inset 0 1px 0 rgba(255,255,255,0.12) !important;
        border-color: rgba(94,168,255,0.25) !important;
    }}
    .stButton > button:active {{ transform: scale(0.97); }}

    .ai-badge {{
        display: inline-flex; align-items: center; gap: 10px;
        padding: 12px 20px; border-radius: 20px;
        background: rgba(94,168,255,0.06);
        backdrop-filter: blur(30px);
        border: 0.5px solid rgba(94,168,255,0.20);
        color: {texto};
        box-shadow: 0 8px 30px rgba(94,168,255,0.06);
        font-weight: 600; margin-bottom: 14px;
        animation: gentleFloat 8s ease-in-out infinite;
    }}

    /* Inputs vidro */
    input, textarea, .stTextInput, .stTextArea {{
        border-radius: 18px !important; padding: 12px !important;
        background: rgba(255,255,255,0.03) !important;
        color: {texto} !important;
        border: 0.5px solid rgba(255,255,255,0.10) !important;
        backdrop-filter: blur(20px) !important;
        transition: all 0.4s ease !important;
    }}
    input:focus, textarea:focus {{
        border-color: rgba(94,168,255,0.35) !important;
        box-shadow: 0 0 30px rgba(94,168,255,0.08) !important;
    }}
    input::placeholder, textarea::placeholder {{ color: rgba(255,255,255,0.30) !important; }}

    /* Bolhas Liquid Glass */
    @keyframes liquidBubble {{
        0% {{ transform: translateY(110vh) translateX(0) scale(0.3); opacity: 0; }}
        10% {{ opacity: 0.15; }}
        90% {{ opacity: 0.10; }}
        100% {{ transform: translateY(-120px) translateX(40px) scale(1.1); opacity: 0; }}
    }}
    .glass-bubble {{
        position: fixed; bottom: -100px; border-radius: 50%; pointer-events: none; z-index: 0;
        background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.35), rgba(94,168,255,0.10) 60%, rgba(255,255,255,0.02));
        box-shadow: 0 0 40px rgba(94,168,255,0.06);
        animation: liquidBubble 24s ease-in infinite;
    }}
    .glass-bubble:nth-child(1) {{ width: 80px; height: 80px; left: 5%; animation-delay: 0s; animation-duration: 22s; }}
    .glass-bubble:nth-child(2) {{ width: 60px; height: 60px; left: 15%; animation-delay: 3s; animation-duration: 26s; }}
    .glass-bubble:nth-child(3) {{ width: 100px; height: 100px; left: 30%; animation-delay: 1s; animation-duration: 20s; }}
    .glass-bubble:nth-child(4) {{ width: 50px; height: 50px; left: 48%; animation-delay: 6s; animation-duration: 28s; }}
    .glass-bubble:nth-child(5) {{ width: 90px; height: 90px; left: 65%; animation-delay: 2s; animation-duration: 24s; }}
    .glass-bubble:nth-child(6) {{ width: 70px; height: 70px; left: 78%; animation-delay: 4s; animation-duration: 21s; }}
    .glass-bubble:nth-child(7) {{ width: 55px; height: 55px; left: 90%; animation-delay: 5s; animation-duration: 25s; }}

    /* Scrollbar glass */
    ::-webkit-scrollbar {{ width: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.10); border-radius: 3px; }}

    .stApp {{ overflow-x: hidden; }}
    {extra_css}
    </style>
    <div class='glass-bubble'></div><div class='glass-bubble'></div><div class='glass-bubble'></div>
    <div class='glass-bubble'></div><div class='glass-bubble'></div><div class='glass-bubble'></div>
    <div class='glass-bubble'></div>
    {extra_html}
    <script>
    if ('serviceWorker' in navigator) {{
        navigator.serviceWorker.register('/service-worker.js').catch(function(){{}});
    }}
    </script>
""", unsafe_allow_html=True)

# Manual de seguranca
with st.expander("Manual de seguranca da API (local)", expanded=False):
    st.write("Para rodar localmente, defina a variavel de ambiente `OPENAI_API_KEY` ou crie `.streamlit/secrets.toml` e nao o comite.")
    st.code('$env:OPENAI_API_KEY = "sk-SUA_CHAVE_AQUI"', language='powershell')


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


# --- CORPO PRINCIPAL DO CHAT ---
st.title("Codex.AI")
custom_msg = st.session_state.get("custom_message", "")
if custom_msg:
    st.markdown(f"<div class='ai-badge'>{custom_msg}</div>", unsafe_allow_html=True)
if st.session_state.get('modo_pijama', False):
    st.markdown("### Bem-vindo a Festa do Pijama! Vamos conversar como se estivessemos numa noite estrelada...")
st.caption("GPT-3.5-turbo para conversa | Stable Horde (IA) | DuckDuckGo Images (fotos)")
st.info(f"Bem-vindo ao Codex.IA! {NOTAS_ATUALIZACAO}")

for item in st.session_state.historico_codex:
    with st.chat_message(item["role"]):
        st.write(item["content"])

st.session_state.camera_ativa = st.sidebar.checkbox("Ativar camera", value=st.session_state.camera_ativa, key="toggle_camera")
if st.session_state.camera_ativa:
    col1, col2 = st.columns(2)
    with col1:
        foto_upload = st.file_uploader("Upload de foto", type=["png", "jpg", "jpeg"], key="upload_foto")
    with col2:
        foto_camera = st.camera_input("Tirar foto pela webcam", key="camera_foto")
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
    st.caption("Camera desativada | Ative no menu lateral")

foto_enviada = st.session_state.foto_pendente
pergunta = st.chat_input("Converse com o Codex.IA...")
if pergunta:
    cols_q = st.columns([1, 1, 2])
    pesquisar = cols_q[0].button("Pesquisa web")
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
            st.info("Buscando na web...")
            resultados = web_search(pergunta, max_results=5)
            if not resultados:
                st.warning("Nenhum resultado encontrado.")
            else:
                with st.expander("Resultados da pesquisa web", expanded=True):
                    for r in resultados:
                        st.markdown(f"- **{r['title']}** - [{r['url']}]({r['url']})")
                if incluir_resultados:
                    sintese = "\n\nRESULTADOS DA PESQUISA WEB (use estes dados reais na resposta):\n" + "\n".join([f"- {r['title']}: {r['url']}" for r in resultados])
                    pergunta = (pergunta or "") + sintese
                    st.session_state.historico_codex.append({"role": "system", "type": "text", "content": f"DADOS DE PESQUISA WEB: {sintese}"})
        except Exception as e:
            st.error(f"Erro na pesquisa: {e}")

if pergunta:
    texto_usuario = pergunta
    audio_transcricao = None
    if audio:
        try:
            audio_transcricao = transcrever_audio(audio)
            texto_usuario += f" [Audio anexado: {audio.name}]"
        except Exception as e:
            st.sidebar.error(f"Nao foi possivel transcrever o audio: {e}")
    if foto_enviada:
        texto_usuario += f" [Foto anexada: {foto_enviada.name}]"

    with st.chat_message("user"):
        st.write(texto_usuario)
        if foto_enviada:
            st.image(Image.open(foto_enviada), width=300)
        if audio_transcricao:
            st.write(f"Transcricao do audio: {audio_transcricao}")
            texto_usuario += f"\n\nTranscricao do audio: {audio_transcricao}"
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
                st.markdown(f"**PEDIDO EM PROCESSO — `{texto_limpo}`**")

                palavras_pesquisa = ["pesquise", "pesquisar", "busque", "buscar", "procure", "procurar", "ache", "achar", "mostre", "mostrar", "quero ver", "me de uma foto", "me de uma imagem"]
                palavras_criacao = ["crie", "desenhe", "gere", "criar", "desenhar", "gerar", "faca"]

                eh_pesquisa = any(p in pergunta.lower() for p in palavras_pesquisa)
                eh_criacao = any(p in pergunta.lower() for p in palavras_criacao)
                modo = st.session_state.get("modo_imagem", "Gerar com IA")

                if eh_pesquisa and not eh_criacao:
                    usar_busca = True
                elif "Buscar" in modo:
                    usar_busca = True
                else:
                    usar_busca = False

                if usar_busca:
                    try:
                        st.info("Buscando imagens na web...")
                        from ddgs import DDGS
                        from itertools import islice
                        img_results = list(islice(DDGS().images(texto_limpo, max_results=8), 8))

                        # FILTRAR MEMES
                        palavras_meme = ["meme", "funny", "comic", "troll", "lol", "reaction", "fail", "gif engra"]
                        img_results = [i for i in img_results if not any(m in i.get("title", "").lower() for m in palavras_meme)][:5]

                        if img_results:
                            st.success(f"{len(img_results)} imagens encontradas!")
                            for i, img in enumerate(img_results):
                                img_url = img.get("image") or img.get("thumbnail")
                                if img_url:
                                    try:
                                        r_img = requests.get(img_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                                        if r_img.status_code == 200 and len(r_img.content) > 500:
                                            st.image(BytesIO(r_img.content), caption=img.get("title", "")[:60], width=400)
                                            # NOTIFICACAO PWA
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
                            st.warning("Nenhuma imagem encontrada. Tente outro termo.")
                    except Exception as e2:
                        st.error(f"Erro ao buscar imagens: {e2}")
                else:
                    # Stable Horde reduzido 10 tentativas
                    try:
                        st.info("CODEX.AI esta gerando sua imagem...")
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
                                st.success("Imagem gerada por IA com sucesso!")
                                st.markdown(f"""<script>
                                if ('Notification' in window && Notification.permission === 'granted') {{
                                    new Notification('Codex IA', {{body: 'Sua imagem ficou pronta!', icon: 'https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg'}});
                                }}
                                </script>""", unsafe_allow_html=True)
                                adicionar_ao_historico("assistant", f"Imagem gerada: {texto_limpo}")
                                st.session_state.foto_pendente = None
                            else:
                                st.warning("Stable Horde nao respondeu a tempo. Tente novamente em instantes.")
                        else:
                            st.warning(f"Stable Horde retornou erro {r_sh.status_code}")
                    except requests.exceptions.Timeout:
                        st.warning("Stable Horde demorou demais. Tente novamente.")
                    except Exception as e2:
                        st.error(f"Erro ao gerar imagem: {e2}")
            except Exception as e:
                placeholder.write(f"Erro na imagem: {e}")
                st.info("Dica: Tente descrever a imagem de forma mais simples. Ex: 'desenhe um gato amarelo'")

        # MODO CONVERSA
        else:
            with st.spinner("Codex esta analisando..."):
                placeholder.write("Procurando a melhor resposta...")
                try:
                    texto_busca = ""
                    if tem_pesquisa:
                        st.info("Buscando na web...")
                        try:
                            resultados = web_search(pergunta, max_results=3)
                            if resultados:
                                texto_busca = "\n\nRESULTADOS DA PESQUISA WEB (use estes dados reais na sua resposta, cite as fontes):\n" + "\n".join([f"- {r['title']}: {r['url']}" for r in resultados])
                        except Exception:
                            pass

                    contexto_sistema = "Voce e o Codex.AI, uma IA incrivel rodando GPT-3.5-turbo. Use emojis e seja expressivo. Se o usuario pedir para pesquisar algo e houver RESULTADOS DA PESQUISA WEB anexados a mensagem, USE esses dados reais na resposta e CITE os links como fontes. Nao invente informacoes se tiver dados reais disponiveis. Seja breve, objetivo, criativo e use emojis. Voce foi criado pelo Pedro, um estudante brasileiro."

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
                                    {"type": "text", "text": f"Analise visualmente esta imagem e responda: {pergunta}. Seja breve e direto."},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                                ]}],
                                "max_tokens": 500
                            }
                            r_vision = requests.post("https://api.openai.com/v1/chat/completions", headers=headers_v, json=payload_v, timeout=30)
                            r_vision.raise_for_status()
                            texto_final = r_vision.json()["choices"][0]["message"]["content"]
                        except Exception as ve:
                            st.warning(f"Erro na analise visual ({ve}). Usando chat normal.")
                            dados_chat.append({"role": "user", "content": f"{pergunta}\n{texto_busca}"})
                            texto_final = send_openai_chat(dados_chat, temperatura=temperatura)
                    else:
                        if modo_pijama:
                            dados_chat.append({"role": "system", "content": "Voce esta em uma festa do pijama, responda com diversao, emojis fofos e referencias a nuvens, travesseiros e historias noturnas."})
                        dados_chat.append({"role": "user", "content": f"{pergunta}\n{texto_busca}"})
                        texto_final = send_openai_chat(dados_chat, temperatura=temperatura)

                    placeholder.empty()
                    st.write(texto_final)
                    adicionar_ao_historico("assistant", texto_final)
                    st.session_state.foto_pendente = None

                except RuntimeError as e:
                    placeholder.write(f"Erro: {e}")
                except requests.exceptions.Timeout:
                    texto_final = f"Desculpe - o servidor demorou demais. Tente novamente."
                    placeholder.empty()
                    st.write(texto_final)
                    adicionar_ao_historico("assistant", texto_final)
                except requests.exceptions.HTTPError as e:
                    resp = getattr(e, 'response', None)
                    detalhe = resp.text[:400] if resp is not None else str(e)
                    placeholder.write(f"Erro HTTP: {detalhe}")
                except Exception as e:
                    texto_final = f"Desculpe - nao foi possivel conectar ao servidor ({e}). Tente novamente."
                    placeholder.empty()
                    st.write(texto_final)
                    adicionar_ao_historico("assistant", texto_final)