# Configurações e constantes do Codex.AI
import os
import streamlit as st

# Constantes da API
API_COST_PER_1000_TOKENS = 0.002
DEFAULT_BILLING_DOLLARS = 5.0

# Arquivo de histórico
ARQUIVO_SALVO = "historico_codex.json"

# Notas de atualização
NOTAS_ATUALIZACAO = "Notas da atualização:Codex AI esta de cara nova! bugs concertados, modelo melhorado para gpt e criação de imagens amplamente melhorada com o modelo Flux-Architecture. Agora o app tem um visual mais moderno, divertido e leve, com opções de tema claro/escuro e um modo festa do pijama super fofo! 🎉✨"

# Paletas de cores
PALETAS = {
    "Padrão": {"accent": "#7d3af2", "wall": ""}, 
    "Neon":   {"accent": "#00f5ff", "wall": ""}, 
    "Cyber":  {"accent": "#39ff14", "wall": ""}, 
    "Pastel": {"accent": "#ff78c6", "wall": ""}
}

def get_api_key():
    """Obtém a chave da API OpenAI"""
    # Tenta variável de ambiente primeiro
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    # Tenta Streamlit secrets
    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return None

def aplicar_paleta(escolha):
    """Aplica a paleta escolhida corrigindo o bug da linha 249"""
    if escolha not in PALETAS:
        escolha = "Padrão"
    
    dados = PALETAS[escolha]
    
    # Corrige o bug: aplica a cor de acento corretamente
    st.session_state.accent_color = dados["accent"]
    st.session_state.modo_neon = (escolha == "Neon")
    
    # Atualiza papel de parede se definido
    if dados.get("wall"):
        st.session_state.wallpaper_url = dados["wall"]
    
    # Força recarregamento
    st.rerun()