# Núcleo da IA do Codex.AI com análise de imagem REAL
import requests
import base64
import streamlit as st
from io import BytesIO
from PIL import Image
from config import get_api_key

def encode_image_to_base64(image_file):
    """Converte imagem para base64 para enviar para OpenAI Vision"""
    image_file.seek(0)  # Garante que o ponteiro está no início
    image = Image.open(image_file)
    # Redimensiona se muito grande para economizar tokens
    if image.width > 1024 or image.height > 1024:
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def send_openai_chat(dados_chat, temperatura=0.7):
    """Envia dados_chat para a API OpenAI Chat e retorna o texto gerado."""
    api_key = get_api_key()
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
    return data["choices"][0]["message"]["content"]

def send_openai_vision(dados_chat, image_base64, temperatura=0.7):
    """Envia chat + imagem para OpenAI Vision API - ANÁLISE REAL DE IMAGEM"""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("Defina a variavel ambiente OPENAI_API_KEY antes de executar.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Prepara mensagem com imagem
    messages = []
    for msg in dados_chat:
        if msg["role"] == "user" and "Analise visualmente" in msg["content"]:
            # Substitui a mensagem fake por uma real com imagem
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": msg["content"]
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            })
        else:
            messages.append(msg)
    
    payload = {
        "model": "gpt-4-vision-preview",  # Modelo com visão
        "messages": messages,
        "temperature": float(temperatura),
        "max_tokens": 800
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]

def processar_conversa_com_imagem(dados_chat, foto_enviada, temperatura=0.7):
    """Processa conversa com análise REAL de imagem"""
    try:
        # Converte imagem para base64
        image_base64 = encode_image_to_base64(foto_enviada)
        
        # Usa Vision API para análise real
        return send_openai_vision(dados_chat, image_base64, temperatura)
        
    except Exception as e:
        # Fallback para chat normal se Vision falhar
        st.warning(f"Erro na análise de imagem: {e}. Usando chat normal.")
        return send_openai_chat(dados_chat, temperatura)

def gerar_imagem_openai(prompt, estilo="", api_key=None):
    """Gera imagem usando OpenAI DALL-E 3 (corrigido e melhorado)"""
    if not api_key:
        api_key = get_api_key()
    if not api_key:
        raise RuntimeError("Chave OpenAI necessária para gerar imagens")
    
    # Enriquece o prompt com o estilo selecionado pelo usuário
    prompt_completo = prompt
    if estilo and estilo != "Realista":
        prompt_completo = f"{prompt}, no estilo {estilo}"
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "dall-e-3",
        "prompt": prompt_completo,
        "size": "1024x1024",
        "quality": "hd",
        "n": 1
    }
    
    r = requests.post("https://api.openai.com/v1/images/generations", 
                     headers=headers, json=payload, timeout=90)
    r.raise_for_status()
    data = r.json()
    
    if data.get("data") and len(data["data"]) > 0:
        url = data["data"][0].get("url")
        if url:
            # Baixa a imagem e retorna os bytes para exibição
            img_resp = requests.get(url, timeout=30)
            img_resp.raise_for_status()
            return img_resp.content
    return None
