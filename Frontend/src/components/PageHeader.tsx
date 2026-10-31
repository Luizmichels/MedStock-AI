export default function PageHeader({
  title,
  subtitle,
  acoes,
}: {
  title: string;
  subtitle: string;
  acoes?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-[26px] font-extrabold -tracking-[0.01em] text-navy">{title}</h1>
        <p className="mt-1 text-sm text-muted">{subtitle}</p>
      </div>
      {acoes}
    </div>
  );
}
