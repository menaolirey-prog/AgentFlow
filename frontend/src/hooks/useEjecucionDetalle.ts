import { useEffect, useState } from "react";
import { ErrorAPI, detalleEjecucion } from "../api/cliente";
import type { EjecucionDetalle } from "../api/tipos";

/** Caché module-level compartida: si el panel y la traza piden la misma ejecución, solo se pide una vez. */
const cache = new Map<string, Promise<EjecucionDetalle>>();

function pedir(id: string): Promise<EjecucionDetalle> {
  let p = cache.get(id);
  if (!p) {
    p = detalleEjecucion(id).catch((e) => {
      cache.delete(id); // un fallo no se guarda en caché: permite reintentar
      throw e;
    });
    cache.set(id, p);
  }
  return p;
}

type Resultado =
  | { estado: "inactivo" }
  | { estado: "cargando" }
  | { estado: "listo"; detalle: EjecucionDetalle }
  | { estado: "error"; error: ErrorAPI };

/** Trae el detalle de una ejecución solo cuando `activo` es true (p. ej. al expandir). */
export function useEjecucionDetalle(id: string | null, activo: boolean): Resultado & { reintentar: () => void } {
  const [intento, setIntento] = useState(0);
  const [r, setR] = useState<Resultado>({ estado: "inactivo" });

  useEffect(() => {
    if (!id || !activo) {
      setR({ estado: "inactivo" });
      return;
    }
    let vivo = true;
    setR({ estado: "cargando" });
    pedir(id).then(
      (detalle) => vivo && setR({ estado: "listo", detalle }),
      (error) => vivo && setR({ estado: "error", error: error instanceof ErrorAPI ? error : new ErrorAPI(0, "error_desconocido", "No se pudo cargar.") }),
    );
    return () => {
      vivo = false;
    };
  }, [id, activo, intento]);

  return { ...r, reintentar: () => setIntento((n) => n + 1) };
}
