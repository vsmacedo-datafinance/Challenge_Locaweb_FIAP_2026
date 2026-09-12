export default function Topbar({ updatedAtLabel }: { updatedAtLabel: string }) {
  return (
    <header className="sticky top-0 z-[60] flex items-center gap-4 border-b border-line bg-[#0a0c11ed] px-6 py-3 backdrop-blur-md">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/chronos-logo.webp" alt="Chronos" className="h-6" />
      <div className="border-l border-line pl-3 text-[0.7rem] leading-tight text-mut">
        Central de Previsão
        <br />
        de Incidentes
      </div>
      <div className="ml-auto flex items-center gap-4 text-[0.76rem] text-mut">
        <span className="hidden items-center min-[900px]:inline-flex">
          <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-cyan shadow-[0_0_9px_#45E0E6]" />
          Modelos atualizados <b className="ml-1 text-txt">{updatedAtLabel}</b>
        </span>
        <span>
          <b className="text-txt">MVP · FIAP x Locaweb 2026</b>
        </span>
      </div>
    </header>
  );
}
