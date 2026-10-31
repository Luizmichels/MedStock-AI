export const ICON_PATHS = {
  dashboard:
    "M5 3h4a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2zM15 3h4a2 2 0 012 2v2a2 2 0 01-2 2h-4a2 2 0 01-2-2V5a2 2 0 012-2zM15 11h4a2 2 0 012 2v6a2 2 0 01-2 2h-4a2 2 0 01-2-2v-6a2 2 0 012-2zM5 15h4a2 2 0 012 2v2a2 2 0 01-2 2H5a2 2 0 01-2-2v-2a2 2 0 012-2z",
  previsoes: "M3 17l6-6 4 4 8-8M14 7h7v7",
  exportar: "M12 4v11M7 10l5 5 5-5M4 15v5h16v-5",
  importar: "M12 15V4M7 9l5-5 5 5M4 15v5h16v-5",
  usuarios:
    "M5.5 8a3.5 3.5 0 107 0a3.5 3.5 0 10-7 0M2.5 20c.8-3.6 3.3-5.5 6.5-5.5s5.7 1.9 6.5 5.5M16 4.5a3.5 3.5 0 010 7M18 14.8c1.9.8 3 2.6 3.5 5.2",
  hospitais: "M4 21V5l8-2v18M12 8h8v13M2 21h20M8 8h.01M8 12h.01M8 16h.01M16 12h.01M16 16h.01",
  logout: "M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10",
  configuracoes:
    "M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z",
} as const;

export type IconName = keyof typeof ICON_PATHS;

export function Icon({
  name,
  size = 18,
  className,
}: {
  name: IconName;
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}
