import { BarChart3, ChevronRight, MessageSquare, MessagesSquare, ListTree, Plus, RotateCw } from "lucide-react";
import { useState } from "react";
import type { ConversacionResumen } from "../api/tipos";
import { agruparFecha, formatoCuando, type Grupo } from "../utils/fecha";
import { MarcaTile } from "./Marca";

export type Vista = "agente" | "conversaciones" | "ejecuciones" | "reportes";

const ITEMS: { vista: Vista; etiqueta: string; Icono: typeof MessageSquare }[] = [
  { vista: "agente", etiqueta: "Agente", Icono: MessageSquare },
  { vista: "conversaciones", etiqueta: "Conversaciones", Icono: MessagesSquare },
  { vista: "ejecuciones", etiqueta: "Ejecuciones", Icono: ListTree },
  { vista: "reportes", etiqueta: "Reportes", Icono: BarChart3 },
];
const GRUPOS: Grupo[] = ["Hoy", "Ayer", "Anteriores"];

export const tituloConversacion = (c: ConversacionResumen) => c.inicio?.trim() || "Conversación sin mensajes";

type Props = {
  vista: Vista;
  onVista: (v: Vista) => void;
  conversaciones: ConversacionResumen[];
  cargando: boolean;
  error: string | null;
  onReintentar: () => void;
  activaId: string | null;
  onConversacion: (id: string) => void;
  onNueva: () => void;
  abierto?: boolean;
  onCerrar?: () => void;
};

export function Sidebar({ vista, onVista, conversaciones, cargando, error, onReintentar, activaId, onConversacion, onNueva, abierto, onCerrar }: Props) {
  const [cerrados, setCerrados] = useState<Grupo[]>([]);
  const alternar = (g: Grupo) => setCerrados((c) => (c.includes(g) ? c.filter((x) => x !== g) : [...c, g]));

  return (
    <>
      {abierto && <div className="telon" onClick={onCerrar} aria-hidden="true" />}
      <aside className={abierto ? "riel riel--abierto" : "riel"} aria-label="Navegación">
        <div className="marca">
          <MarcaTile size={34} />
          <span className="marca__texto">
            <span className="marca__nombre">AgentFlow</span>
            <span className="marca__lema">Agentes para el negocio</span>
          </span>
        </div>

        <nav aria-label="Principal" className="riel__nav">
          {ITEMS.map(({ vista: v, etiqueta, Icono }) => (
            <button key={v} type="button" className="nav-item" aria-current={vista === v ? "page" : undefined} onClick={() => onVista(v)}>
              <Icono size={17} strokeWidth={1.75} aria-hidden="true" />
              <span>{etiqueta}</span>
            </button>
          ))}
        </nav>

        <button type="button" className="nueva" onClick={onNueva}>
          <Plus size={16} strokeWidth={2} aria-hidden="true" /> Nueva conversación
        </button>

        <div className="recientes">
          <h2 className="recientes__rotulo">Recientes</h2>
          {cargando ? (
            <p className="recientes__estado"><RotateCw size={13} strokeWidth={2} className="girar" aria-hidden="true" /> Cargando…</p>
          ) : error ? (
            <p className="recientes__estado recientes__estado--err">
              {error} <button type="button" onClick={onReintentar}>Reintentar</button>
            </p>
          ) : conversaciones.length === 0 ? (
            <p className="recientes__estado">Aún no hay conversaciones.</p>
          ) : (
            GRUPOS.map((g) => {
              const items = conversaciones.filter((c) => agruparFecha(c.creada_en) === g);
              if (!items.length) return null;
              const cerrado = cerrados.includes(g);
              return (
                <section key={g} className="grupo">
                  <button type="button" className="grupo__cabecera" aria-expanded={!cerrado} onClick={() => alternar(g)}>
                    <ChevronRight size={13} strokeWidth={2.25} className="grupo__flecha" aria-hidden="true" />
                    <span>{g}</span>
                    <span className="grupo__cuenta">{items.length}</span>
                  </button>
                  {!cerrado && (
                    <ul>
                      {items.map((c) => (
                        <li key={c.id}>
                          <button
                            type="button"
                            className="reciente"
                            aria-current={vista === "agente" && activaId === c.id ? "true" : undefined}
                            onClick={() => onConversacion(c.id)}
                          >
                            <MessageSquare size={14} strokeWidth={1.75} aria-hidden="true" />
                            <span className="reciente__titulo">{tituloConversacion(c)}</span>
                            <span className="reciente__cuando">{formatoCuando(c.creada_en, g)}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              );
            })
          )}
        </div>

        <div className="riel__pie">
          <p className="sesion">
            <span className="sesion__punto" aria-hidden="true" />
            <span>
              <span className="sesion__titulo">Sesión local</span>
              <span className="sesion__nota">Clave compartida · un usuario</span>
            </span>
          </p>
        </div>
      </aside>
    </>
  );
}
