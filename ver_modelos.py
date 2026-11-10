
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("No se encontró GEMINI_API_KEY")
    raise SystemExit(1)

client = genai.Client(api_key=api_key)

try:
    print("Modelos Gemini disponibles:\n")

    for modelo in client.models.list():
        nombre = modelo.name

        if "gemini" in nombre.lower():
            print(nombre)

except Exception as error:
    print(f"Error: {type(error).__name__}")
    print("No se pudo consultar la lista de modelos.")

finally:
    client.close()
