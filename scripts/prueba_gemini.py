
import os
from google import genai

if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("Falta configurar GEMINI_API_KEY")

client = genai.Client()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Responde únicamente: AgentFlow conectado correctamente."
)

print(response.text)
