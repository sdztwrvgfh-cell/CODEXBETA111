# Funções auxiliares do Codex.AI
import requests
import json
import os
import re
import streamlit as st
from config import API_COST_PER_1000_TOKENS, ARQUIVO_SALVO, get_api_key

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
    api_key = get_api_key()
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
    """Busca rápida na web usando DuckDuckGo HTML (sem necessidade de chave).
    Retorna lista de {title, url, snippet}.
    Usa BeautifulSoup se disponível, senão faz parse simples por regex.
    """
    if not query:
        return []
    try:
        resp = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        raise RuntimeError(f"Erro ao acessar DuckDuckGo: {e}")

    results = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text().strip()
            if href.startswith("/l/?kh="):
                # DuckDuckGo redirect links contain 'uddg=' param sometimes; try to extract real url
                m = re.search(r'uddg=(https?%3A%2F%2F[^&]+)', href)
                if m:
                    url = requests.utils.unquote(m.group(1))
                else:
                    continue
            else:
                url = href
            if url.startswith("http") and text:
                results.append({"title": text, "url": url, "snippet": ""})
            if len(results) >= max_results:
                break
    except Exception:
        # Fallback simples por regex
        links = re.findall(r'href="(https?://[^"]+)"', html)
        texts = re.findall(r'>([^<]{20,200})</a>', html)
        for u, t in zip(links, texts):
            results.append({"title": t.strip(), "url": u, "snippet": ""})
            if len(results) >= max_results:
                break

    # Dedupe
    seen = set()
    out = []
    for r in results:
        if r["url"] in seen:
            continue
        seen.add(r["url"]) 
        out.append(r)
    return out

def guardar_conversa():
    """Guarda apenas os textos para não dar erro no arquivo salvo"""
    mensagens_texto = [msg for msg in st.session_state.historico_codex if msg["type"] == "text"]
    with open(ARQUIVO_SALVO, "w", encoding="utf-8") as f:
        json.dump(mensagens_texto, f, ensure_ascii=False, indent=4)