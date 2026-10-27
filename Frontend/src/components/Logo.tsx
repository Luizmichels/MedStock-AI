/**
 * Logo oficial do MedStock-AI (portado 1:1 de MedStock.logo() + CSS .ms-logo).
 * Selo arredondado navy + linha de tendência sky + ponto branco, com o wordmark
 * "MedStock" + "AI" em destaque.
 *
 * Variantes:
 *  - padrão  → selo 40px, texto 22px, fundo navy-900 (#0a2342)
 *  - size="lg" → selo 56px, texto 34px (tela de login)
 *  - dark    → selo 34px, texto 19px branco, fundo navy-800 (#123a66) (barra navy)
 */
export default function Logo({
  size = "sm",
  dark = false,
}: {
  size?: "sm" | "lg";
  dark?: boolean;
}) {
  const tamSelo = dark ? 34 : size === "lg" ? 56 : 40;
  const tamTexto = dark ? 19 : size === "lg" ? 34 : 22;
  const corSelo = dark ? "#123a66" : "#0a2342"; // navy-800 / navy-900
  const corTexto = dark ? "#ffffff" : "#0a2342"; // on-navy / navy-900
  const corAI = dark ? "#3fa2e3" : "#1c4f8a"; // sky-500 / navy-700

  return (
    <span className="inline-flex items-center gap-2.5 align-middle">
      <svg width={tamSelo} height={tamSelo} viewBox="0 0 40 40" aria-hidden="true" style={{ display: "block" }}>
        <rect width="40" height="40" rx="11" fill={corSelo} />
        <path
          d="M9 27l7-7 5 4 9-10"
          fill="none"
          stroke="#3fa2e3"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="30" cy="14" r="3" fill="#ffffff" />
      </svg>
      <span
        style={{
          fontWeight: 800,
          fontSize: tamTexto,
          letterSpacing: "-0.01em",
          color: corTexto,
          lineHeight: 1,
        }}
      >
        MedStock
        <b style={{ fontWeight: 800, color: corAI, marginLeft: 4 }}>AI</b>
      </span>
    </span>
  );
}
