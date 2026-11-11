import { AlertTriangle, RotateCw, SendHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { SUGERENCIAS } from "../data/referencia";
import type { Turno } from "../tipos";
import { MarcaTile } from "./Marca";
import { Markdown } from "./Markdown";
import { Traza, entero } from "./Traza";

export const MAX_MENSAJE = 4000; // mismo límite que la API (NuevoMensaje)

function Prosa({ texto }: { texto: string }) {
  return <Markdown texto={texto} />;
}

function Respuesta({ turno, panelDisponible, seleccion, onAbrirPanel }: {
  turno: Turno;
  panelDisponible: boolean;
  seleccion: string | null;
  onAbrirPanel: (id: string) => void;
}) {
  const fallo = turno.resumen?.estado === "error";
  const degradado = turno.resumen?.estado === "degradado" || turno.resumen?.estado === "limite";
  return (
    <div className="respuesta">
      <MarcaTile size={30} />
      <div className="respuesta__cuerpo">
        {fallo || degradado ? (
          <div className={fallo ? "error" : "error error--aviso"} role="alert">
            <AlertTriangle size={18} strokeWidth={1.75} aria-hidden="true" />
            <div>
              <Prosa texto={turno.respuesta} />
              {turno.resumen?.motivo && <p className="error__motivo">Motivo: {turno.resumen.motivo}</p>}
            </div>
          </div>
        ) : (
          <Prosa texto={turno.respuesta} />
        )}
        {turno.resumen && (
          <Traza resumen={turno.resumen} panelDisponible={panelDisponible} seleccionada={seleccion === turno.resumen.id} onAbrirPanel={onAbrirPanel} />
        )}
      </div>
    </div>
  );
}

type Props = {
  titulo: string;
  turnos: Turno[];
  cargandoHistorial: boolean;
  errorHistorial: string | null;
  onReintentarHistorial: () => void;
  enviando: boolean;
  errorEnvio: string | null;
  panelDisponible: boolean;
  seleccion: string | null;
  onAbrirPanel: (id: string) => void;
  onEnviar: (contenido: string) => void;
};

export function ChatView({ titulo, turnos, cargandoHistorial, errorHistorial, onReintentarHistorial, enviando,
  errorEnvio, panelDisponible, seleccion, onAbrirPanel, onEnviar }: Props) {
  const [texto, setTexto] = useState("");
  const campo = useRef<HTMLTextAreaElement>(null);
  const finDelHilo = useRef<HTMLDivElement>(null);
  const excede = texto.length > MAX_MENSAJE;
  const vacia = !cargandoHistorial && !errorHistorial && turnos.length === 0;
  const puedeEnviar = texto.trim().length > 0 && !excede && !enviando;

  useEffect(() => {
    const el = campo.current;
    if (!el) return;
    el.style.height = "auto"; // crece con el contenido hasta el máximo del CSS
    el.style.height = `${el.scrollHeight}px`;
  }, [texto]);

  useEffect(() => {
    finDelHilo.current?.scrollIntoView({ block: "end" });
  }, [turnos.length, enviando]);

  const enviar = () => {
    const contenido = texto.trim();
    if (!contenido || contenido.length > MAX_MENSAJE || enviando) return;
    onEnviar(contenido);
    setTexto("");
  };

  return (
    <section className="chat" aria-label="Chat con el agente comercial">
      <div className="chat__hilo">
        <div className="col">
          <header className="chat__cabecera">
            <h1 className="titulo">{titulo}</h1>
          </header>

          {cargandoHistorial ? (
            <p className="carga-vista"><RotateCw size={15} strokeWidth={2} className="girar" aria-hidden="true" /> Cargando conversación…</p>
          ) : errorHistorial ? (
            <div className="banner banner--err" role="alert">
              <p>{errorHistorial}</p>
              <button type="button" className="boton boton--linea" onClick={onReintentarHistorial}>Reintentar</button>
            </div>
          ) : vacia ? (
            <div className="vacio">
              <MarcaTile size={40} />
              <h2 className="vacio__titulo">Pregunta por tus ventas</h2>
              <p>Totales por periodo, ranking de productos, comparaciones y caídas. Cada cifra sale de la base de datos y puedes ver con qué herramienta se obtuvo.</p>
              <ul className="sugerencias">
                {SUGERENCIAS.map((s) => (
                  <li key={s}>
                    <button type="button" onClick={() => { setTexto(s); campo.current?.focus(); }}>
                      {s}
                      <SendHorizontal size={14} strokeWidth={1.75} aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="hilo" role="log" aria-live="polite">
              {turnos.map((t) => (
                <article key={t.id} className="intercambio">
                  <div className="mensaje">
                    <p className="burbuja">{t.pregunta}</p>
                  </div>
                  <Respuesta turno={t} panelDisponible={panelDisponible} seleccion={seleccion} onAbrirPanel={onAbrirPanel} />
                </article>
              ))}
              {enviando && (
                <p className="carga-vista carga-vista--discreta">
                  <RotateCw size={14} strokeWidth={2} className="girar" aria-hidden="true" /> El agente está pensando…
                </p>
              )}
              <div ref={finDelHilo} />
            </div>
          )}
        </div>
      </div>

      <form
        className="compositor"
        onSubmit={(e) => {
          e.preventDefault();
          enviar();
        }}
      >
        <div className="col">
          {errorEnvio && <p className="compositor__error" role="alert">{errorEnvio}</p>}
          <div className="compositor__caja">
            <label htmlFor="mensaje" className="sr-only">Mensaje para el agente</label>
            <textarea
              ref={campo}
              id="mensaje"
              rows={1}
              value={texto}
              disabled={enviando}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  enviar();
                }
              }}
              placeholder="Pregunta sobre ventas, productos o periodos…"
              aria-describedby="ayuda-envio"
            />
            <button type="submit" className="enviar" disabled={!puedeEnviar} aria-label="Enviar">
              {enviando ? <RotateCw size={16} strokeWidth={2} className="girar" aria-hidden="true" /> : <SendHorizontal size={16} strokeWidth={2} aria-hidden="true" />}
            </button>
          </div>
          <p id="ayuda-envio" className="compositor__ayuda">
            {texto.length >= MAX_MENSAJE * 0.8 && (
              <span className={excede ? "contador contador--err" : "contador"}>{entero.format(texto.length)} / {entero.format(MAX_MENSAJE)}</span>
            )}
          </p>
        </div>
      </form>
    </section>
  );
}
