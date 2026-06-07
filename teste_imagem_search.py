from ddgs import DDGS
from itertools import islice

query = "gato astronauta"
print(f"Buscando imagens: {query}")
results = list(islice(DDGS().images(query, max_results=5), 5))
print(f"Encontradas: {len(results)}")
for i, r in enumerate(results):
    print(f"{i+1}. Title: {r.get('title','')[:60]}")
    print(f"   Image URL: {r.get('image','')[:100]}")
    print(f"   Thumbnail: {r.get('thumbnail','')[:100]}")
    print("---")