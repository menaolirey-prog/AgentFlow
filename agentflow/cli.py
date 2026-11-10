"""CLI interactiva: python -m agentflow [--reanudar ID]"""
import argparse
import json
import os
import shlex
import sys
from datetime import datetime

from dotenv import load_dotenv

from agentflow.agent.conversacion import ConversacionNoEncontrada
from agentflow.agent.orchestrator import Agente, Conversacion
from agentflow.agent.render import formatear_reporte
from agentflow.config import MODELO, ZONA_LIMA
from agentflow.db.repositories.ejecuciones import RegistroEjecuciones
from agentflow.db.repositories.historial import HistorialPostgres
from agentflow.db.repositories.ventas import RepositorioVentas
from agentflow.llm.groq_client import GroqLLM
from agentflow.observability.logging import configurar_archivo
from agentflow.tools.registry import RegistroHerramientas
from agentflow.tools.reportes import FILTROS_ORIGEN, construir_reporte, guardar_csv

AYUDA = ("Comandos: /herramientas (qué usé en la última respuesta), /historial (conversaciones guardadas), "
         "/ejecuciones (registro de esta conversación), /nueva (conversación nueva), /ayuda, /salir\n"
         "Reportes (sin IA, calculados en SQL): /reporte PERIODO [vs PERIODO] [--origen real|demo|todos] "
         "[--csv nombre.csv]")
USO_REPORTE = "Uso: /reporte PERIODO [vs PERIODO] [--origen real|demo|todos] [--csv nombre.csv]"


def parsear_reporte(argumentos: str) -> dict:
    """Interpreta los argumentos de /reporte. ValueError con mensaje apto para el usuario."""
    try:
        tokens = shlex.split(argumentos)
    except ValueError:
        raise ValueError(USO_REPORTE) from None
    origen, csv_nombre, posicionales, i = "todos", None, [], 0
    while i < len(tokens):
        if tokens[i] in ("--origen", "--csv"):
            if i + 1 >= len(tokens):
                raise ValueError(f"Falta el valor de {tokens[i]}. {USO_REPORTE}")
            if tokens[i] == "--origen":
                origen = tokens[i + 1]
            else:
                csv_nombre = tokens[i + 1]
            i += 2
        else:
            posicionales.append(tokens[i])
            i += 1
    if origen not in FILTROS_ORIGEN:
        raise ValueError(f"Origen inválido; use {', '.join(FILTROS_ORIGEN)}.")
    if len(posicionales) == 1:
        periodo, comparar_con = posicionales[0], None
    elif len(posicionales) == 3 and posicionales[1] == "vs":
        periodo, comparar_con = posicionales[0], posicionales[2]
    else:
        raise ValueError(USO_REPORTE)
    return {"periodo": periodo, "comparar_con": comparar_con, "origen": origen, "csv": csv_nombre}


def ejecutar_reporte(argumentos: str, repo) -> str:
    p = parsear_reporte(argumentos)
    reporte = construir_reporte(repo, p["periodo"], p["comparar_con"], p["origen"], datetime.now(ZONA_LIMA).date())
    texto = formatear_reporte(reporte)
    if p["csv"]:
        texto += f"\nCSV guardado en {guardar_csv(reporte, p['csv'])}"
    return texto


def construir_agente(api_key: str, ejecuciones: RegistroEjecuciones | None = None) -> Agente:
    return Agente(GroqLLM(api_key), RegistroHerramientas(RepositorioVentas()), ejecuciones=ejecuciones)


def formatear_ejecuciones(filas: list[dict]) -> str:
    if not filas:
        return "No hay ejecuciones registradas."
    return "\n".join(f"{f['id']}  {f['iniciada_en']:%Y-%m-%d %H:%M}  {f['estado']:<9} {f['herramientas']} herr.  "
                     f"{f['tokens']} tok  {f['duracion_ms'] if f['duracion_ms'] is not None else '-'} ms"
                     + (f"  ({f['motivo']})" if f["motivo"] else "") for f in filas)


def mostrar_herramientas(conversacion: Conversacion) -> None:
    r = conversacion.ultimo_resultado
    if r is None:
        print("Aún no hay consultas.")
    elif not r.herramientas:
        print("La última respuesta no usó herramientas.")
    for h in r.herramientas if r else []:
        estado = "ok" if h.ok else f"error ({h.codigo_error})"
        print(f"- {h.nombre} {json.dumps(h.argumentos, ensure_ascii=False)} -> {estado}, {h.duracion_ms} ms")


def formatear_historial(filas: list[dict]) -> str:
    if not filas:
        return "No hay conversaciones guardadas."
    return "\n".join(f"{f['id']}  {f['creada_en']:%Y-%m-%d %H:%M}  {f['mensajes']:>3} msgs  {f['inicio'] or '(vacía)'}"
                     for f in filas)


def conversacion_nueva(almacen: HistorialPostgres) -> Conversacion:
    try:
        c = Conversacion.nueva(almacen)
        print(f"Conversación {c.id} (se guarda en PostgreSQL).")
        return c
    except Exception:  # sin base de datos el agente sigue funcionando, solo sin historial
        print("Aviso: no se pudo crear el historial; esta conversación no se guardará.")
        return Conversacion()


def main(argv: list[str] | None = None) -> int:
    for flujo in (sys.stdout, sys.stderr):  # consola Windows: nunca fallar por un carácter
        flujo.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(prog="agentflow")
    parser.add_argument("--reanudar", metavar="ID", help="continuar una conversación guardada")
    args = parser.parse_args(argv)
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Falta GROQ_API_KEY en .env")
        return 1
    configurar_archivo("logs/agentflow.jsonl")
    almacen = HistorialPostgres()
    print(f"AgentFlow ({MODELO}). Datos ficticios de demostración. {AYUDA}")
    if args.reanudar:
        try:
            conversacion = Conversacion.reanudar(almacen, args.reanudar)
        except ValueError:
            print("El ID no es un UUID válido.")
            return 1
        except ConversacionNoEncontrada:
            print("No existe una conversación con ese ID (/historial en una sesión nueva las lista).")
            return 1
        except Exception:
            print("No se pudo leer el historial (¿migración 004 aplicada?).")
            return 1
        print(f"Conversación {conversacion.id} reanudada con {len(conversacion.mensajes)} mensajes.")
    else:
        conversacion = conversacion_nueva(almacen)
    ejecuciones, repo_ventas = RegistroEjecuciones(), RepositorioVentas()
    try:  # ejecuciones que quedaron 'en_curso' por un cierre brusco: desenlace desconocido
        huerfanas = ejecuciones.cerrar_interrumpidas()
        if huerfanas:
            print(f"Aviso: {len(huerfanas)} ejecución(es) anterior(es) quedaron interrumpidas "
                  "(marcadas como error/interrumpida; su desenlace es desconocido).")
    except Exception:
        pass  # registro no disponible: el agente funciona igual
    agente = construir_agente(api_key, ejecuciones)
    while True:
        try:
            pregunta = input("\nTú> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not pregunta:
            continue
        if pregunta == "/salir":
            return 0
        if pregunta == "/ayuda":
            print(AYUDA)
        elif pregunta == "/nueva":
            conversacion = conversacion_nueva(almacen)
        elif pregunta == "/historial":
            try:
                print(formatear_historial(almacen.listar()))
            except Exception:
                print("No se pudo leer el historial.")
        elif pregunta == "/reporte" or pregunta.startswith("/reporte "):
            try:
                print(ejecutar_reporte(pregunta[len("/reporte"):], repo_ventas))
            except (ValueError, FileExistsError) as error:  # mensajes propios y seguros
                print(f"No se pudo generar el reporte: {error}")
            except Exception:
                print("No se pudo consultar la base de datos para el reporte.")
        elif pregunta == "/ejecuciones":
            try:
                print(formatear_ejecuciones(ejecuciones.listar(conversacion.id)))
            except Exception:
                print("No se pudo leer el registro (¿migración 005 aplicada?).")
        elif pregunta == "/herramientas":
            mostrar_herramientas(conversacion)
        else:
            r = agente.responder(pregunta, conversacion)
            print(f"\n{r.respuesta}")
            print(f"[{r.estado} · {r.origen} · {len(r.herramientas)} herramientas · "
                  f"{r.tokens_entrada + r.tokens_salida} tokens · {r.duracion_ms} ms]")
            if not conversacion.persistencia_ok:
                print("Aviso: este turno no se pudo guardar en el historial.")


if __name__ == "__main__":
    sys.exit(main())
