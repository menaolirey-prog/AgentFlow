/** Marca de AgentFlow: tres trazos de un registro de ventas que se encadenan, el del medio avanzado.
    Dibujada a mano (no es un icono de librería ni un glifo tipográfico). */
export function Marca({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3" y="4.5" width="14" height="3.6" rx="1.8" fill="currentColor" opacity="0.55" />
      <rect x="3" y="10.2" width="18" height="3.6" rx="1.8" fill="currentColor" />
      <rect x="3" y="15.9" width="9" height="3.6" rx="1.8" fill="currentColor" opacity="0.55" />
    </svg>
  );
}

export function MarcaTile({ size = 30 }: { size?: number }) {
  return (
    <span className="marca__tile" style={{ width: size, height: size }} aria-hidden="true">
      <Marca size={Math.round(size * 0.62)} />
    </span>
  );
}
