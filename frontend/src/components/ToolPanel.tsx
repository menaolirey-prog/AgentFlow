import { Clock, Coins, Layers, X } from "lucide-react";
import { useState } from "react";
import type { Estado, HerramientaEjecutada, Origen } from "../api/tipos";
import { DESCRIPCIONES } from "../data/referencia";
import { useEjecucionDetalle } from "../hooks/useEjecucionDetalle";
import { Argumentos, CargandoDetalle, ErrorDetalle, Marcador, entero, segundos } from "./Traza";

const ESTADOS: Record<Estado, string> = { ok: "Completada", degradado: "Degradada", limite: "Cortada por límite", error: "Con error" };
const ORIGENES: Record<Origen, string> = { modelo: "Modelo", plantilla: "Plantilla determinista", mensaje_error: "Mensaje de error" };

type Props = { ejecucionId: string; onCerrar: () => void };

/** Panel contextual: la ejecución elegida y sus herramientas, cargadas de la API al abrirse. */
export function ToolPanel({ ejecucionId, onCerrar }: Props) {
  const [pasoAbierto, setPasoAbierto] = useState<number | null>(null);
  const carga = useEjecucionDetalle(ejecucionId, true);

  return (
    <aside className="panel" aria-label="Detalle de ejecución">
      <header className="panel__cabecera">
        <h2 className="panel__titulo">Detalle de ejecución</h2>
        <button type="button" className="icono-boton" onClick={onCerrar} aria-label="Cerrar panel">
          <X size={17} strokeWidth={1.75} aria-hidden="true" />
        </button>
      </header>

      <div className="panel__cuerpo">
        {carga.estado === "error" && <ErrorDetalle mensaje={carga.error.message} onReintentar={carga.reintentar} />}
        {(carga.estado === "cargando" || carga.estado === "inactivo") && <CargandoDetalle />}
        {carga.estado === "listo" && (() => {
          const e = carga.detalle;
          const fallo = e.estado === "error";
          return (
            <>
              <div className={fallo ? "estado-card estado-card--err" : "estado-card"}>
                <p className="estado-card__titulo">
                  <Marcador ok={!fallo} />
                  {ESTADOS[e.estado]}
                  {e.motivo && <span className="estado-card__motivo">{e.motivo}</span>}
                </p>
                <dl className="trio">
                  <div>
                    <dt><Clock size={13} strokeWidth={1.75} aria-hidden="true" /> Duración</dt>
                    <dd>{e.duracion_ms !== null ? segundos(e.duracion_ms) : "—"}</dd>
                  </div>
                  <div>
                    <dt><Layers size={13} strokeWidth={1.75} aria-hidden="true" /> Herramientas</dt>
                    <dd>{e.herramientas.length}</dd>
                  </div>
                  <div>
                    <dt><Coins size={13} strokeWidth={1.75} aria-hidden="true" /> Tokens</dt>
                    <dd>{entero.format(e.tokens_entrada + e.tokens_salida)}</dd>
                  </div>
                </dl>
              </div>

              <h3 className="panel__sub">Herramientas utilizadas</h3>
              {e.herramientas.length === 0 ? (
                <p className="panel__vacio">Ninguna: la respuesta no llegó a consultar la base de datos.</p>
              ) : (
                <ul className="herramientas">
                  {e.herramientas.map((p: HerramientaEjecutada) => {
                    const activo = pasoAbierto === p.orden;
                    return (
                      <li key={p.orden}>
                        <button
                          type="button"
                          className={p.ok ? "herramienta" : "herramienta herramienta--err"}
                          aria-expanded={activo}
                          onClick={() => setPasoAbierto(activo ? null : p.orden)}
                        >
                          <span className="herramienta__cab">
                            <span className="herramienta__nombre">{p.herramienta}</span>
                            <span className="herramienta__ms">{p.duracion_ms} ms</span>
                            <Marcador ok={p.ok} />
                          </span>
                          {DESCRIPCIONES[p.herramienta] && <span className="herramienta__desc">{DESCRIPCIONES[p.herramienta]}</span>}
                        </button>
                        {activo && (
                          <div className="herramienta__detalle">
                            <Argumentos paso={p} />
                            {!p.ok && p.codigo_error && <p className="detalle__error">Código: {p.codigo_error}</p>}
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}

              <h3 className="panel__sub">Registro</h3>
              <dl className="resumen">
                <div><dt>Origen de la respuesta</dt><dd>{e.origen ? ORIGENES[e.origen] : "—"}</dd></div>
                <div><dt>Llamadas al modelo</dt><dd className="dato">{e.llamadas_llm}</dd></div>
                <div><dt>Tokens entrada → salida</dt><dd className="dato">{entero.format(e.tokens_entrada)} → {entero.format(e.tokens_salida)}</dd></div>
                <div><dt>ID de ejecución</dt><dd className="dato" title={e.id}>{e.id.slice(0, 8)}…</dd></div>
              </dl>
              <p className="panel__nota">
                La separación real/demo de los datos consultados no la expone este endpoint; consulta Reportes para esa vista.
              </p>
            </>
          );
        })()}
      </div>
    </aside>
  );
}
