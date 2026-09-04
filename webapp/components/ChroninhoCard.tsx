import Image from "next/image";
import { renderBold } from "@/lib/boldText";
import type { ChroninhoMessageData } from "@/lib/types";

const ESTADO_STYLES: Record<string, string> = {
  ok: "bg-cyan-soft text-cyan",
  atento: "bg-amber-soft text-amber",
  alerta: "bg-red-soft text-red",
};

export default function ChroninhoCard({ message }: { message: ChroninhoMessageData }) {
  return (
    <div className="relative mb-5 flex gap-4 rounded-chronos border border-line bg-gradient-to-br from-[#12161f] to-[#161b28] p-4 pl-5">
      <span className="absolute bottom-3 left-0 top-3 w-[3px] rounded bg-red" />
      <Image
        src="/chroninho-avatar.webp"
        alt="Chroninho"
        width={62}
        height={62}
        className="flex-none rounded-full border-2 border-line bg-bg2 object-contain p-1"
      />
      <div>
        <div className="mb-1.5 flex items-center gap-2">
          <b className="font-sora text-[0.85rem]">Chroninho</b>
          <span
            className={`rounded-full px-2.5 py-1 text-[0.64rem] font-semibold ${ESTADO_STYLES[message.estado]}`}
          >
            {message.estado_label}
          </span>
        </div>
        <p className="text-[0.88rem] leading-relaxed text-[#c7ccda]">{renderBold(message.message)}</p>
      </div>
    </div>
  );
}
