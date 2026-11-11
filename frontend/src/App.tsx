import { ChevronRight, Menu, PanelRight } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ErrorAPI, crearConversacion, enviarMensaje as enviarMensajeApi, listarConversaciones, obtenerMensajes,
  listarEjecucionesDeConversacion,
} from "./api/cliente";
import type { ConversacionResumen } from "./api/tipos";
import { ChatView } from "./components/ChatView";
import { EjecucionesView } from "./components/EjecucionesView";
import { ListaConversaciones } from "./components/ListaConversaciones";
import { Sidebar, tituloConversacion, type Vista } from "./components/Sidebar";
import { ReportesView } from "./components/ReportesView";
import { ThemeSelector } from "./components/ThemeSelector";
import { ToolPanel } from "./components/ToolPanel";
import type { Turno } from "./tipos";
import { emparejarHistorial } from "./utils/historial";
import { useMediaQuery } from "./hooks/useMediaQuery";
import { useTema } from "./hooks/useTema";

const TITULOS: Record<Exclude<Vista, "agente">, string> = { conversaciones: "Conversaciones", ejecuciones: "Ejecuciones", reportes: "Reportes" };

export default function App() {
  const { preferencia, elegir } = useTema();
  const [vista, setVista] = useState<Vista>("agente");
  const [cajon, setCajon] = useState(false);
  const hayEspacio = useMediaQuery("(min-width: 1180px)");
  const movil = useMediaQuery("(max-width: 759px)");

  // ---- conversaciones (riel + pantalla «Conversaciones» + selector de «Ejecuciones») ----
  const [conversaciones, setConversaciones] = useState<ConversacionResumen[]>([]);
  const [cargandoConversaciones, setCargandoConversaciones] = useState(true);
  const [errorConversaciones, setErrorConversaciones] = useState<string | null>(null);

  const cargarConversaciones = useCallback(() => {
    setCargandoConversaciones(true);
    setErrorConversaciones(null);
    return listarConversaciones(50)
      .then((r) => setConversaciones(r))
      .catch((e: unknown) => setErrorConversaciones(e instanceof ErrorAPI ? e.message : "No se pudieron cargar las conversaciones."))
      .finally(() => setCargandoConversaciones(false));
  }, []);

  useEffect(() => {
    void cargarConversaciones();
  }, [cargarConversaciones]);

  // ---- panel de detalle de ejecución (solo con espacio en pantalla) ----
  const [panelEjecucionId, setPanelEjecucionId] = useState<string | null>(null);

  // ---- conversación activa (pantalla «Agente») ----
  const [activaId, setActivaId] = useState<string | null>(null);
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [cargandoHistorial, setCargandoHistorial] = useState(false);
  const [errorHistorial, setErrorHistorial] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [errorEnvio, setErrorEnvio] = useState<string | null>(null);

  const cargarHistorial = useCallback((id: string) => {
    setCargandoHistorial(true);
    setErrorHistorial(null);
    return Promise.all([obtenerMensajes(id, 50), listarEjecucionesDeConversacion(id, 50)])
      .then(([mensajes, ejecuciones]) => setTurnos(emparejarHistorial(mensajes, ejecuciones)))
      .catch((e: unknown) => setErrorHistorial(e instanceof ErrorAPI ? e.message : "No se pudo cargar la conversación."))
      .finally(() => setCargandoHistorial(false));
  }, []);

  const abrirConversacion = useCallback((id: string) => {
    setActivaId(id);
    setVista("agente");
    setCajon(false);
    setPanelEjecucionId(null);
    setErrorEnvio(null);
    void cargarHistorial(id);
  }, [cargarHistorial]);

  const nuevaConversacion = useCallback(() => {
    setActivaId(null);
    setTurnos([]);
    setErrorHistorial(null);
    setErrorEnvio(null);
    setVista("agente");
    setCajon(false);
    setPanelEjecucionId(null);
  }, []);

  const enviar = useCallback(async (contenido: string) => {
    setEnviando(true);
    setErrorEnvio(null);
    try {
      let id = activaId;
      if (!id) {
        id = (await crearConversacion()).id;
        setActivaId(id);
      }
      const r = await enviarMensajeApi(id, contenido);
      setTurnos((t) => [...t, {
        id: r.ejecucion_id ?? `envio-${t.length}`,
        pregunta: contenido,
        respuesta: r.respuesta,
        resumen: r.ejecucion_id
          ? { id: r.ejecucion_id, estado: r.estado, motivo: r.motivo, origen: r.origen, tokens: r.tokens_entrada + r.tokens_salida, duracionMs: r.duracion_ms, herramientasCount: r.herramientas.length }
          : null,
      }]);
      void cargarConversaciones(); // refresca contador de mensajes y orden en el riel, sin bloquear la respuesta
    } catch (e) {
      setErrorEnvio(e instanceof ErrorAPI ? e.message : "No se pudo enviar el mensaje.");
    } finally {
      setEnviando(false);
    }
  }, [activaId, cargarConversaciones]);

  const panelVisible = hayEspacio && vista === "agente" && panelEjecucionId !== null;

  useEffect(() => {
    if (!cajon) return;
    const alTeclear = (e: KeyboardEvent) => e.key === "Escape" && setCajon(false);
    addEventListener("keydown", alTeclear);
    return () => removeEventListener("keydown", alTeclear);
  }, [cajon]);

  const activaResumen = conversaciones.find((c) => c.id === activaId) ?? null;
  const tituloActivo = useMemo(() => {
    if (activaResumen) return tituloConversacion(activaResumen);
    if (turnos[0]) return turnos[0].pregunta;
    return "Nueva conversación";
  }, [activaResumen, turnos]);

  return (
    <div className={panelVisible ? "app app--con-panel" : "app"}>
      <a className="salto" href="#contenido">Saltar al contenido</a>

      <Sidebar
        vista={vista}
        onVista={(v) => { setVista(v); setCajon(false); }}
        conversaciones={conversaciones}
        cargando={cargandoConversaciones}
        error={errorConversaciones}
        onReintentar={cargarConversaciones}
        activaId={activaId}
        onConversacion={abrirConversacion}
        onNueva={nuevaConversacion}
        abierto={movil ? cajon : undefined}
        onCerrar={() => setCajon(false)}
      />

      <div className="zona">
        <header className="tope">
          {movil && (
            <button type="button" className="icono-boton" onClick={() => setCajon(true)} aria-label="Abrir navegación" aria-expanded={cajon}>
              <Menu size={18} strokeWidth={1.75} aria-hidden="true" />
            </button>
          )}
          <nav className="miga" aria-label="Ubicación">
            <span>{vista === "agente" ? "Agente" : TITULOS[vista]}</span>
            {vista === "agente" && (
              <>
                <ChevronRight size={14} strokeWidth={1.75} aria-hidden="true" />
                <span className="miga__actual">{tituloActivo}</span>
              </>
            )}
          </nav>
          <div className="tope__fin">
            {hayEspacio && vista === "agente" && panelEjecucionId && (
              <button type="button" className="icono-boton" onClick={() => setPanelEjecucionId(null)} aria-label="Cerrar detalle de ejecución">
                <PanelRight size={17} strokeWidth={1.75} aria-hidden="true" />
              </button>
            )}
            <ThemeSelector valor={preferencia} onChange={elegir} />
          </div>
        </header>

        <main id="contenido" className="principal">
          {vista === "agente" ? (
            <ChatView
              key={activaId ?? "nueva"}
              titulo={tituloActivo}
              turnos={turnos}
              cargandoHistorial={cargandoHistorial}
              errorHistorial={errorHistorial}
              onReintentarHistorial={() => activaId && void cargarHistorial(activaId)}
              enviando={enviando}
              errorEnvio={errorEnvio}
              panelDisponible={hayEspacio}
              seleccion={panelEjecucionId}
              onAbrirPanel={setPanelEjecucionId}
              onEnviar={enviar}
            />
          ) : vista === "conversaciones" ? (
            <ListaConversaciones
              conversaciones={conversaciones}
              cargando={cargandoConversaciones}
              error={errorConversaciones}
              onReintentar={cargarConversaciones}
              onAbrir={abrirConversacion}
              onNueva={nuevaConversacion}
            />
          ) : vista === "ejecuciones" ? (
            <EjecucionesView
              conversaciones={conversaciones}
              cargandoConversaciones={cargandoConversaciones}
              conversacionIdInicial={activaId}
            />
          ) : (
            <ReportesView />
          )}
        </main>
      </div>

      {panelVisible && panelEjecucionId && <ToolPanel ejecucionId={panelEjecucionId} onCerrar={() => setPanelEjecucionId(null)} />}
    </div>
  );
}
