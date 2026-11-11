import { Monitor, Moon, Sun } from "lucide-react";
import type { Preferencia } from "../hooks/useTema";

const OPCIONES: { valor: Preferencia; etiqueta: string; Icono: typeof Sun }[] = [
  { valor: "claro", etiqueta: "Claro", Icono: Sun },
  { valor: "sistema", etiqueta: "Sistema", Icono: Monitor },
  { valor: "oscuro", etiqueta: "Oscuro", Icono: Moon },
];

/** Selector visible de tema (radiogroup). La preferencia se guarda en localStorage. */
export function ThemeSelector({ valor, onChange }: { valor: Preferencia; onChange: (p: Preferencia) => void }) {
  return (
    <div className="tema" role="radiogroup" aria-label="Tema de la interfaz">
      {OPCIONES.map(({ valor: v, etiqueta, Icono }) => (
        <button
          key={v}
          type="button"
          role="radio"
          aria-checked={valor === v}
          aria-label={etiqueta}
          title={etiqueta}
          className="tema__opcion"
          onClick={() => onChange(v)}
        >
          <Icono size={15} strokeWidth={1.75} aria-hidden="true" />
        </button>
      ))}
    </div>
  );
}
