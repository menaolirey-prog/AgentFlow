import { ArrowDown, ArrowUp, Download, RotateCw } from "lucide-react";
import { useState } from "react";
import { ErrorAPI, descargarReporteCsv, reporteVentas } from "../api/cliente";
import type { ParametrosReporte, ProductoFila, ReporteVentas } from "../api/tipos";
import { PRESETS_PERIODO } from "../data/referencia";

const ETIQUETAS_PRESET: Record<string, string> = {
  este_mes: "Este mes", mes_anterior: "Mes anterior", ultimos_7_dias: "Últimos 7 días",
  ultimos_30_dias: "Últimos 30 días", este_anio: "Este año",
};

function Variacion({ pct }: { pct: number | null | undefined }) {
  if (pct === undefined || pct === null) return null;
  const baja = pct < 0;
  return (
    <span className={baja ? "chip chip--baja" : "chip chip--sube"}>
      {baja ? <ArrowDown size={12} strokeWidth={2.25} aria-hidden="true" /> : <ArrowUp size={12} strokeWidth={2.25} aria-hidden="true" />}
      {(baja ? "−" : "+") + Math.abs(pct).toFixed(1).replace(".", ",")} %
    </span>
  );
}

function TablaProductos({ titulo, demo, filas, conVariacion, moneda }: { titulo: string; demo?: boolean; filas: ProductoFila[]; conVariacion: boolean; moneda: string }) {
  return (
    <div className={demo ? "bloque-tabla bloque-tabla--demo" : "bloque-tabla"}>
      <p className="bloque-tabla__cab">
        <span className={demo ? "sello sello--demo" : "sello"}>{demo ? "Demo · ficticio" : "Real"}</span>
        <span className="bloque-tabla__titulo">{titulo}</span>
      </p>
      <table className="tabla">
        <thead>
          <tr>
            <th scope="col">Producto</th>
            <th scope="col" className="num">Unid.</th>
            <th scope="col" className="num">Ingresos</th>
            <th scope="col" className="num">Part.</th>
            {conVariacion && <th scope="col" className="num">Variación</th>}
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => (
            <tr key={f.producto}>
              <th scope="row">{f.producto}</th>
              <td className="num">{f.unidades}</td>
              <td className="num">{moneda} {f.ingresos.toFixed(2)}</td>
              <td className="num">{f.participacion_pct !== null ? `${f.participacion_pct.toFixed(1)} %` : "—"}</td>
              {conVariacion && <td className="num"><Variacion pct={f.variacion_pct} /></td>}
            </tr>
          ))}
          {filas.length === 0 && (
            <tr><td colSpan={conVariacion ? 5 : 4} className="lista__vacia">Sin productos en este periodo.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export function ReportesView() {
  const [periodo, setPeriodo] = useState<string>("este_mes");
  const [personalizarPeriodo, setPersonalizarPeriodo] = useState(false);
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFin, setPeriodoFin] = useState("");
  const [comparar, setComparar] = useState(false);
  const [compararCon, setCompararCon] = useState<string>("mes_anterior");
  const [origen, setOrigen] = useState<ParametrosReporte["origen"]>("todos");

  const [reporte, setReporte] = useState<ReporteVentas | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [descargando, setDescargando] = useState(false);
  const [errorDescarga, setErrorDescarga] = useState<string | null>(null);

  const periodoEfectivo = personalizarPeriodo ? (periodoInicio && periodoFin ? `${periodoInicio}/${periodoFin}` : "") : periodo;
  const parametros: ParametrosReporte | null = periodoEfectivo
    ? { periodo: periodoEfectivo, comparar_con: comparar ? compararCon : undefined, origen }
    : null;

  const generar = async () => {
    if (!parametros) return;
    setCargando(true);
    setError(null);
    try {
      setReporte(await reporteVentas(parametros));
    } catch (e) {
      setError(e instanceof ErrorAPI ? e.message : "No se pudo generar el reporte.");
      setReporte(null);
    } finally {
      setCargando(false);
    }
  };

  const descargar = async () => {
    if (!parametros) return;
    setDescargando(true);
    setErrorDescarga(null);
    try {
      await descargarReporteCsv(parametros);
    } catch (e) {
      setErrorDescarga(e instanceof ErrorAPI ? e.message : "No se pudo descargar el CSV.");
    } finally {
      setDescargando(false);
    }
  };

  const secciones = reporte ? (Object.entries(reporte.origenes) as [string, NonNullable<ReporteVentas["origenes"]["real"]>][]) : [];
  const conVariacion = reporte ? "variacion_ingresos" in reporte.total_combinado : false;

  return (
    <section className="vista">
      <div className="col">
        <header className="chat__cabecera">
          <h1 className="titulo">Reportes</h1>
          <p className="meta">Datos reales y demo siempre por separado; el total combinado es una suma explícita.</p>
        </header>

        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            void generar();
          }}
        >
          <label className="campo">
            <span>Periodo</span>
            {personalizarPeriodo ? (
              <span className="campo__rango">
                <input type="date" value={periodoInicio} onChange={(e) => setPeriodoInicio(e.target.value)} required />
                <span>a</span>
                <input type="date" value={periodoFin} onChange={(e) => setPeriodoFin(e.target.value)} required />
              </span>
            ) : (
              <select value={periodo} onChange={(e) => setPeriodo(e.target.value)}>
                {PRESETS_PERIODO.map((p) => <option key={p} value={p}>{ETIQUETAS_PRESET[p]}</option>)}
              </select>
            )}
          </label>
          <label className="campo campo--casilla">
            <input type="checkbox" checked={personalizarPeriodo} onChange={(e) => setPersonalizarPeriodo(e.target.checked)} />
            <span>Rango personalizado</span>
          </label>

          <label className="campo campo--casilla">
            <input type="checkbox" checked={comparar} onChange={(e) => setComparar(e.target.checked)} />
            <span>Comparar con otro periodo</span>
          </label>
          {comparar && (
            <label className="campo">
              <span>Periodo de comparación</span>
              <select value={compararCon} onChange={(e) => setCompararCon(e.target.value)}>
                {PRESETS_PERIODO.map((p) => <option key={p} value={p}>{ETIQUETAS_PRESET[p]}</option>)}
              </select>
            </label>
          )}

          <label className="campo">
            <span>Origen</span>
            <select value={origen} onChange={(e) => setOrigen(e.target.value as ParametrosReporte["origen"])}>
              <option value="todos">Todos</option>
              <option value="real">Solo real</option>
              <option value="demo">Solo demo</option>
            </select>
          </label>

          <div className="form__acciones">
            <button type="submit" className="boton boton--principal" disabled={!parametros || cargando}>
              {cargando ? <RotateCw size={15} strokeWidth={2} className="girar" aria-hidden="true" /> : null} Generar reporte
            </button>
            <button type="button" className="boton boton--linea" disabled={!parametros || !reporte || descargando} onClick={() => void descargar()}>
              <Download size={15} strokeWidth={1.75} aria-hidden="true" /> {descargando ? "Generando CSV…" : "Descargar CSV"}
            </button>
          </div>
          {errorDescarga && <p className="compositor__error" role="alert">{errorDescarga}</p>}
        </form>

        {error && (
          <div className="banner banner--err" role="alert">
            <p>{error}</p>
            <button type="button" className="boton boton--linea" onClick={() => void generar()}>Reintentar</button>
          </div>
        )}

        {reporte && (
          <div className="reporte">
            {reporte.advertencia && <p className="pastilla pastilla--aviso">{reporte.advertencia}</p>}

            <figure className="cifra">
              <figcaption className="cifra__etiqueta">Total combinado · {reporte.periodo.inicio} a {reporte.periodo.fin}</figcaption>
              <p className="cifra__fila">
                <span className="cifra__valor">{reporte.moneda} {reporte.total_combinado.ingresos.toFixed(2)}</span>
                {conVariacion && <Variacion pct={reporte.total_combinado.variacion_ingresos_pct} />}
              </p>
              {reporte.total_combinado.ingresos_anterior !== undefined && (
                <p className="cifra__contexto">frente a {reporte.moneda} {reporte.total_combinado.ingresos_anterior.toFixed(2)} en el periodo anterior</p>
              )}
            </figure>
            <div className="cifras cifras--reporte">
              <figure className="dato-tile"><figcaption>Unidades</figcaption><p>{reporte.total_combinado.unidades}</p></figure>
              <figure className="dato-tile"><figcaption>Número de ventas</figcaption><p>{reporte.total_combinado.numero_ventas}</p></figure>
              {reporte.producto_lider && <figure className="dato-tile"><figcaption>Producto líder</figcaption><p className="dato-tile__texto">{reporte.producto_lider}</p></figure>}
            </div>

            <div className="tablas">
              {secciones.map(([nombre, seccion]) => (
                <TablaProductos
                  key={nombre}
                  titulo={`${nombre === "real" ? "Datos reales" : "Datos ficticios de demostración"} · total ${reporte.moneda} ${seccion.total.ingresos.toFixed(2)}`}
                  demo={nombre === "demo"}
                  filas={seccion.productos}
                  conVariacion={conVariacion}
                  moneda={reporte.moneda}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
