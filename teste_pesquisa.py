import requests
import re

query = "the amazing digital circus historia"
print(f"Pesquisando: {query}")
print()

# Metodo 1: Google search com user-agent
try:
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(
        f"https://www.google.com/search?q={requests.utils.quote(query)}",
        headers=headers, timeout=10
    )
    print(f"Google status: {r.status_code}")
    if r.status_code == 200:
        links = re.findall(r'<a href="(https?://[^"]+)"', r.text)
        real = [l for l in links if "google" not in l and len(l) > 40][:5]
        for l in real:
            print(f"  - {l[:100]}")
except Exception as e:
    print(f"Google erro: {e}")

print()
print("--- Metodo 2: DuckDuckGo API JSON ---")
try:
    r2 = requests.get(
        f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json",
        timeout=10
    )
    if r2.status_code == 200:
        d = r2.json()
        print(f"Abstract: {d.get('Abstract','')[:200] or '(vazio)'}")
        print(f"RelatedTopics: {len(d.get('RelatedTopics',[]))}")
        results = d.get('Results', [])
        for i, res in enumerate(results[:3]):
            print(f"  {i+1}. {res.get('Text','')[:80]}")
    else:
        print(f"Status: {r2.status_code}")
except Exception as e:
    print(f"DuckDuckGo erro: {e}")