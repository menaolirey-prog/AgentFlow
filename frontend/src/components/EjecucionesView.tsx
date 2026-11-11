import { ChevronRight, RotateCw } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorAPI, listarEjecucionesDeConversacion } from "../api/cliente";
import type { ConversacionResumen, EjecucionResumen } from "../api/tipos";
import { DESCRIPCIONES } from "../data/referencia";
import { useEjecucionDetalle } from "../hooks/useEjecucionDetalle";
import { tituloConversacion } from "./Sidebar";
import { Argumentos, CargandoDetalle, ErrorDetalle, Marcador, entero, segundos } from "./Traza";

function FilaEjecucion({ resumen }: { resumen: EjecucionResumen }) {
  const [abierta, setAbierta] = useState(false);
  const carga = useEjecucionDetalle(resumen.id, abierta);
  return (
    <li className="lista__item-expandible">
      <button type="button" className="lista__fila" aria-expanded={abierta} onClick={() => setAbierta((a) => !a)}>
        <ChevronRight size={14} strokeWidth={2.25} className={abierta ? "lista__flecha lista__flecha--abierta" : "lista__flecha"} aria-hidden="true" />
        <span className="lista__titulo dato">{resumen.id.slice(0, 8)}…</span>
        <span className="lista__meta">{resumen.herramientas} herramientas</span>
        <span className="lista__meta">{entero.format(resumen.tokens)} tokens</span>
        <span className="lista__meta">{resumen.duracion_ms !== null ? segundos(resumen.duracion_ms) : "—"}</span>
        <span className="lista__meta">{new Date(resumen.iniciada_en).toLocaleString("es-PE", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
        <Marcador ok={resumen.estado === "ok"} />
      </button>
      {abierta && (
        <div className="lista__detalle">
          {carga.estado === "error" && <ErrorDetalle mensaje={carga.error.message} onReintentar={carga.reintentar} />}
          {(carga.estado === "cargando" || carga.estado === "inactivo") && <CargandoDetalle />}
          {carga.estado === "listo" && (
            carga.detalle.herramientas.length === 0 ? (
              <p className="panel__vacio">Ninguna herramienta utilizada.</p>
            ) : (
              <ul className="herramientas">
                {carga.detalle.herramientas.map((p) => (
                  <li key={p.orden}>
                    <div className={p.ok ? "herramienta" : "herramienta herramienta--err"}>
                      <span className="herramienta__cab">
                        <span className="herramienta__nombre">{p.herramienta}</span>
                        <span className="herramienta__ms">{p.duracion_ms} ms</span>
                        <Marcador ok={p.ok} />
                      </span>
                      {DESCRIPCIONES[p.herramienta] && <span className="herramienta__desc">{DESCRIPCIONES[p.herramienta]}</span>}
                      <Argumentos paso={p} />
                      {!p.ok && p.codigo_error && <p className="detalle__error">Código: {p.codigo_error}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            )
          )}
        </div>
      )}
    </li>
  );
}

type Props = {
  conversaciones: ConversacionResumen[];
  cargandoConversaciones: boolean;
  /** Conversación a preseleccionar la primera vez que haya lista (p. ej. la activa en Agente). No se vuelve a aplicar. */
  conversacionIdInicial: string | null;
};

/** Pantalla «Ejecuciones»: elige una conversación y lista sus ejecuciones (la API no tiene listado global).
 * La selección es propia de esta pantalla: no comparte ni muta la conversación activa de «Agente». */
export function EjecucionesView({ conversaciones, cargandoConversaciones, conversacionIdInicial }: Props) {
  const [conversacionId, setConversacionId] = useState<string | null>(conversacionIdInicial);
  const [ejecuciones, setEjecuciones] = useState<EjecucionResumen[]>([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Preselecciona en cuanto la lista llega, solo si esta pantalla todavía no tiene nada elegido.
    if (conversacionId === null && conversaciones.length > 0) setConversacionId(conversacionIdInicial ?? conversaciones[0].id);
  }, [conversaciones, conversacionId, conversacionIdInicial]);

  useEffect(() => {
    if (!conversacionId) {
      setEjecuciones([]);
      return;
    }
    let vivo = true;
    setCargando(true);
    setError(null);
    listarEjecucionesDeConversacion(conversacionId)
      .then((r) => vivo && setEjecuciones(r))
      .catch((e: unknown) => vivo && setError(e instanceof ErrorAPI ? e.message : "No se pudieron cargar las ejecuciones."))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, [conversacionId]);

  return (
    <section className="vista">
      <div className="col">
        <header className="chat__cabecera">
          <h1 className="titulo">Ejecuciones</h1>
          <p className="meta">Por conversación: la API no ofrece un listado global.</p>
        </header>

        <label className="campo">
          <span>Conversación</span>
          <select
            value={conversacionId ?? ""}
            disabled={cargandoConversaciones || conversaciones.length === 0}
            onChange={(e) => setConversacionId(e.target.value)}
          >
            {conversaciones.length === 0 && <option value="">Sin conversaciones</option>}
            {conversaciones.map((c) => (
              <option key={c.id} value={c.id}>{tituloConversacion(c)}</option>
            ))}
          </select>
        </label>

        {cargando ? (
          <p className="carga-vista"><RotateCw size={15} strokeWidth={2} className="girar" aria-hidden="true" /> Cargando ejecuciones…</p>
        ) : error ? (
          <p className="banner banner--err" role="alert">{error}</p>
        ) : !conversacionId ? (
          <p className="vacio-discreto">Elige una conversación para ver sus ejecuciones.</p>
        ) : ejecuciones.length === 0 ? (
          <p className="vacio-discreto">Esta conversación todavía no tiene ejecuciones registradas.</p>
        ) : (
          <ul className="lista">
            {ejecuciones.map((r) => <FilaEjecucion key={r.id} resumen={r} />)}
          </ul>
        )}
      </div>
    </section>
  );
}
