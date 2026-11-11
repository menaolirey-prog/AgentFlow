import { useEffect, useState } from "react";

export function useMediaQuery(consulta: string): boolean {
  const [coincide, setCoincide] = useState(() => matchMedia(consulta).matches);
  useEffect(() => {
    const mq = matchMedia(consulta);
    const alCambiar = () => setCoincide(mq.matches);
    alCambiar();
    mq.addEventListener("change", alCambiar);
    return () => mq.removeEventListener("change", alCambiar);
  }, [consulta]);
  return coincide;
}
