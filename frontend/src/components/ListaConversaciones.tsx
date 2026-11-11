import { MessageSquare, RotateCw } from "lucide-react";
import type { ConversacionResumen } from "../api/tipos";
import { tituloConversacion } from "./Sidebar";

type Props = {
  conversaciones: ConversacionResumen[];
  cargando: boolean;
  error: string | null;
  onReintentar: () => void;
  onAbrir: (id: string) => void;
  onNueva: () => void;
};

/** Pantalla «Conversaciones»: la misma lista del riel, completa y a ancho de columna. */
export function ListaConversaciones({ conversaciones, cargando, error, onReintentar, onAbrir, onNueva }: Props) {
  return (
    <section className="vista">
      <div className="col">
        <header className="chat__cabecera">
          <h1 className="titulo">Conversaciones</h1>
          <p className="meta">Crea una, o reanuda una de las que ya existen.</p>
        </header>

        <button type="button" className="nueva nueva--ancha" onClick={onNueva}>
          Nueva conversación
        </button>

        {cargando ? (
          <p className="carga-vista"><RotateCw size={15} strokeWidth={2} className="girar" aria-hidden="true" /> Cargando conversaciones…</p>
        ) : error ? (
          <div className="banner banner--err" role="alert">
            <p>{error}</p>
            <button type="button" className="boton boton--linea" onClick={onReintentar}>Reintentar</button>
          </div>
        ) : conversaciones.length === 0 ? (
          <p className="vacio-discreto">Aún no hay conversaciones. Crea la primera para empezar a preguntar por tus ventas.</p>
        ) : (
          <ul className="lista">
            {conversaciones.map((c) => (
              <li key={c.id}>
                <button type="button" className="lista__fila" onClick={() => onAbrir(c.id)}>
                  <MessageSquare size={16} strokeWidth={1.75} aria-hidden="true" />
                  <span className="lista__titulo">{tituloConversacion(c)}</span>
                  <span className="lista__meta">{c.mensajes} mensajes</span>
                  <span className="lista__meta">{new Date(c.creada_en).toLocaleString("es-PE", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
