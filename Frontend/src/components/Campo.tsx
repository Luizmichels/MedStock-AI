/** Campo com o rótulo "no entalhe" da borda, igual ao da tela de login. */
export default function Campo({
  label,
  erro,
  children,
}: {
  label: string;
  erro?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative">
      <label className="absolute -top-2 left-3 z-[1] bg-white px-1 text-[11px] text-muted">{label}</label>
      {children}
      {erro && (
        <div className="absolute left-1/2 top-12 z-[3] -translate-x-1/2 whitespace-nowrap rounded-md border border-brand bg-white px-[18px] py-[9px] text-[13px] text-ink shadow-[0_6px_18px_rgba(10,37,64,.12)]">
          {erro}
        </div>
      )}
    </div>
  );
}
