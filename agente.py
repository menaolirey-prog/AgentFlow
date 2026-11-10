
import os
import json

import groq
from groq import Groq
from dotenv import load_dotenv

from herramientas import consultar_ventas


# Cargar claves y configuración desde .env
load_dotenv()

MODELO = "openai/gpt-oss-20b"


def iniciar_agente():
    """Ejecuta AgentFlow con Groq y PostgreSQL."""

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("ERROR: No se encontró GROQ_API_KEY en .env")
        return

    # Sin reintentos automáticos para ahorrar cuota
    client = Groq(
        api_key=api_key,
        max_retries=0,
        timeout=20.0
    )

    # Herramienta que el modelo puede solicitar
    herramientas = [
        {
            "type": "function",
            "function": {
                "name": "consultar_ventas",
                "description": (
                    "Consulta PostgreSQL y devuelve los ingresos "
                    "totales, el producto líder y las ventas "
                    "agrupadas por producto."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]

    mensajes = [
        {
            "role": "system",
            "content": (
                "Eres AgentFlow, un agente comercial. "
                "Utiliza consultar_ventas para obtener datos. "
                "Nunca inventes cifras. "
                "Responde brevemente en español."
            )
        },
        {
            "role": "user",
            "content": (
                "¿Cuánto vendimos en total y qué producto "
                "generó más ingresos?"
            )
        }
    ]

    try:
        print("\nConsultando AgentFlow con Groq...")

        # Primera solicitud: el modelo selecciona la herramienta
        respuesta = client.chat.completions.create(
            model=MODELO,
            messages=mensajes,
            tools=herramientas,
            tool_choice="required",
            parallel_tool_calls=False,
            reasoning_effort="low",
            max_completion_tokens=300
        )

        mensaje = respuesta.choices[0].message

        if not mensaje.tool_calls:
            print("El modelo no solicitó ninguna herramienta.")
            return

        llamada = mensaje.tool_calls[0]

        # Solo permitimos ejecutar herramientas autorizadas
        if llamada.function.name != "consultar_ventas":
            print("Herramienta no autorizada.")
            return

        print("[AGENTE] Groq solicitó consultar_ventas")

        # Ejecutar nuestra función local de PostgreSQL
        resultado = consultar_ventas()

        # Incorporar el resultado al historial
        mensajes.append(mensaje.model_dump(exclude_none=True))

        mensajes.append({
            "role": "tool",
            "tool_call_id": llamada.id,
            "name": "consultar_ventas",
            "content": json.dumps(resultado)
        })

        # Segunda solicitud: redactar la respuesta final
        respuesta_final = client.chat.completions.create(
            model=MODELO,
            messages=mensajes,
            tool_choice="none",
            reasoning_effort="low",
            max_completion_tokens=250
        )

        print("\nRESPUESTA DE AGENTFLOW:")
        print(
            respuesta_final.choices[0].message.content
            or "No se obtuvo una respuesta."
        )

    except groq.RateLimitError:
        print("Se alcanzó el límite gratuito de Groq.")

    except groq.APIStatusError as error:
        print(f"Error de Groq: HTTP {error.status_code}")

    except groq.APIConnectionError:
        print("No se pudo conectar con Groq.")

    except Exception as error:
        print(f"Error: {type(error).__name__}")
        print("Revisa el código o la conexión PostgreSQL.")

    finally:
        client.close()


if __name__ == "__main__":
    iniciar_agente()

