import { useCallback, useEffect, useState } from "react";

export type Preferencia = "claro" | "sistema" | "oscuro";
const CLAVE = "agentflow.tema";

function leer(): Preferencia {
  try {
    const v = localStorage.getItem(CLAVE);
    return v === "claro" || v === "oscuro" || v === "sistema" ? v : "sistema";
  } catch {
    return "sistema"; // almacenamiento bloqueado: la interfaz funciona igual
  }
}

function aplicar(p: Preferencia) {
  const oscuro = p === "oscuro" || (p === "sistema" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = oscuro ? "dark" : "light";
}

export function useTema() {
  const [preferencia, setPreferencia] = useState<Preferencia>(leer);

  useEffect(() => {
    aplicar(preferencia);
    if (preferencia !== "sistema") return;
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const alCambiar = () => aplicar("sistema");
    mq.addEventListener("change", alCambiar);
    return () => mq.removeEventListener("change", alCambiar);
  }, [preferencia]);

  const elegir = useCallback((p: Preferencia) => {
    setPreferencia(p);
    try {
      localStorage.setItem(CLAVE, p);
    } catch {
      /* sin persistencia: solo vale para esta sesión */
    }
  }, []);

  return { preferencia, elegir };
}
