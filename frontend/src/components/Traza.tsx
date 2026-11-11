import { ArrowRight, Check, ChevronRight, RotateCw, X } from "lucide-react";
import { useId, useState } from "react";
import type { HerramientaEjecutada } from "../api/tipos";
import { DESCRIPCIONES } from "../data/referencia";
import { useEjecucionDetalle } from "../hooks/useEjecucionDetalle";
import type { ResumenEjecucion } from "../tipos";

export const entero = new Intl.NumberFormat("es-PE");
export const segundos = (ms: number) => `${(ms / 1000).toLocaleString("es-PE", { maximumFractionDigits: 1 })} s`;

export function Argumentos({ paso }: { paso: HerramientaEjecutada }) {
  if (!paso.argumentos) return <p className="args args--nulo">Argumentos rechazados antes de validarse.</p>;
  return (
    <dl className="args">
      {Object.entries(paso.argumentos).map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Marcador({ ok }: { ok: boolean }) {
  return (
    <span className={ok ? "marcador marcador--ok" : "marcador marcador--err"} aria-hidden="true">
      {ok ? <Check size={11} strokeWidth={3} /> : <X size={11} strokeWidth={3} />}
    </span>
  );
}

export function CargandoDetalle() {
  return (
    <p className="traza__carga">
      <RotateCw size={13} strokeWidth={2} className="girar" aria-hidden="true" /> Cargando herramientas…
    </p>
  );
}

export function ErrorDetalle({ mensaje, onReintentar }: { mensaje: string; onReintentar: () => void }) {
  return (
    <p className="traza__error">
      {mensaje}{" "}
      <button type="button" onClick={onReintentar}>Reintentar</button>
    </p>
  );
}

type Props = {
  resumen: ResumenEjecucion;
  /** Hay panel contextual: el paso elegido se abre allí; si no, el detalle se despliega bajo el paso. */
  panelDisponible: boolean;
  seleccionada: boolean;
  onAbrirPanel: (ejecucionId: string) => void;
};

/** Traza expandible bajo cada respuesta: resumen siempre visible, pasos cargados de la API al expandir. */
export function Traza({ resumen: e, panelDisponible, seleccionada, onAbrirPanel }: Props) {
  const [abierta, setAbierta] = useState(false);
  const [enFila, setEnFila] = useState<number | null>(null);
  const id = useId();
  const carga = useEjecucionDetalle(e.id, abierta);
  const fallo = e.estado === "error";

  return (
    <section className={seleccionada ? "traza traza--activa" : "traza"} aria-label="Ejecución del agente">
      <button
        type="button"
        className="traza__resumen"
        aria-expanded={abierta}
        aria-controls={id}
        disabled={!e.id}
        onClick={() => setAbierta((a) => !a)}
      >
        <ChevronRight size={14} strokeWidth={2.25} className="traza__flecha" aria-hidden="true" />
        <span className="traza__titulo">Ejecución del agente</span>
        <span className="traza__datos">
          <span>{e.herramientasCount === 0 ? "sin herramientas" : `${e.herramientasCount} ${e.herramientasCount === 1 ? "herramienta" : "herramientas"}`}</span>
          {e.duracionMs !== null && (
            <>
              <span aria-hidden="true">·</span>
              <span>{segundos(e.duracionMs)}</span>
            </>
          )}
          <span aria-hidden="true">·</span>
          <span>{entero.format(e.tokens)} tokens</span>
        </span>
        <Marcador ok={!fallo} />
      </button>

      <div id={id} hidden={!abierta} className="traza__cuerpo">
        {!e.id ? (
          <p className="traza__vacia">Esta conversación se cargó antes de que existiera esta vista; no hay detalle disponible.</p>
        ) : carga.estado === "cargando" || carga.estado === "inactivo" ? (
          <CargandoDetalle />
        ) : carga.estado === "error" ? (
          <ErrorDetalle mensaje={carga.error.message} onReintentar={carga.reintentar} />
        ) : carga.detalle.herramientas.length > 0 ? (
          <ol className="pasos">
            {carga.detalle.herramientas.map((p: HerramientaEjecutada, i: number) => {
              const activo = panelDisponible ? false : enFila === p.orden;
              return (
                <li key={p.orden} className="paso">
                  {i > 0 && <ArrowRight size={14} strokeWidth={1.75} className="paso__union" aria-hidden="true" />}
                  <button
                    type="button"
                    className={p.ok ? "paso__chip" : "paso__chip paso__chip--err"}
                    aria-expanded={panelDisponible ? undefined : activo}
                    onClick={() => (panelDisponible ? onAbrirPanel(e.id as string) : setEnFila(activo ? null : p.orden))}
                  >
                    <span className="paso__orden">{p.orden}</span>
                    <span className="paso__nombre">{p.herramienta}</span>
                    <span className="paso__ms">{p.duracion_ms} ms</span>
                    <Marcador ok={p.ok} />
                  </button>
                  {!panelDisponible && activo && (
                    <div className="detalle">
                      {DESCRIPCIONES[p.herramienta] && <p className="detalle__desc">{DESCRIPCIONES[p.herramienta]}</p>}
                      <Argumentos paso={p} />
                      {!p.ok && p.codigo_error && <p className="detalle__error">Código: {p.codigo_error}</p>}
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="traza__vacia">
            {fallo ? `La solicitud terminó en error (${e.motivo}) antes de ejecutar herramientas.` : "Esta solicitud no necesitó herramientas."}
          </p>
        )}
      </div>
    </section>
  );
}
