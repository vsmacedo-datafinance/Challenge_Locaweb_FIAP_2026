"use client";

import { MessageCircle, Send, X } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import type { FormEvent } from "react";
import { renderBold } from "@/lib/boldText";
import type { ChatMessage, ChatResponse } from "@/lib/types";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const next: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next }),
      });
      const data: ChatResponse = await res.json();
      setMessages([...next, { role: "assistant", content: data.reply }]);
    } catch {
      setMessages([...next, { role: "assistant", content: "Não consegui conectar com a IA agora. Tenta de novo em um instante." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {open && (
        <div className="fixed bottom-24 right-6 z-[70] flex h-[32rem] w-96 max-w-[calc(100vw-3rem)] flex-col overflow-hidden rounded-chronos border border-line bg-panel shadow-2xl">
          <div className="flex items-center gap-3 border-b border-line px-4 py-3">
            <Image
              src="/chroninho-avatar.webp"
              alt="Chroninho"
              width={32}
              height={32}
              className="flex-none rounded-full border border-line bg-bg2 object-contain p-1"
            />
            <div className="flex-1">
              <div className="font-sora text-[0.85rem] font-semibold">Chroninho</div>
              <div className="text-[0.68rem] text-mut">Assistente do Chronos</div>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Fechar chat"
              className="text-mut hover:text-txt"
            >
              <X size={18} />
            </button>
          </div>

          <div className="flex-1 space-y-2 overflow-y-auto p-3">
            <div className="max-w-[85%] rounded-xl bg-bg2 px-3 py-2 text-[0.82rem] leading-relaxed text-[#c7ccda]">
              Oi! Sou o Chroninho. Pergunta sobre previsão de volume, risco de OLA ou tendências que eu consulto os
              dados do dashboard pra responder.
            </div>
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[85%] rounded-xl px-3 py-2 text-[0.82rem] leading-relaxed ${
                  m.role === "user" ? "ml-auto bg-cyan-soft text-txt" : "bg-bg2 text-[#c7ccda]"
                }`}
              >
                {m.role === "assistant" ? renderBold(m.content) : m.content}
              </div>
            ))}
            {loading && <div className="max-w-[85%] rounded-xl bg-bg2 px-3 py-2 text-[0.82rem] text-mut">Pensando…</div>}
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2 border-t border-line p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Pergunte algo ao Chroninho..."
              disabled={loading}
              className="flex-1 rounded-lg border border-line bg-bg2 px-3 py-2 text-[0.82rem] text-txt placeholder:text-mut2 focus:outline-none focus:ring-1 focus:ring-cyan"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              aria-label="Enviar"
              className="flex items-center justify-center rounded-lg bg-cyan-soft px-3 text-cyan disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Fechar chat" : "Abrir chat com o Chroninho"}
        className="fixed bottom-6 right-6 z-[70] flex h-14 w-14 items-center justify-center rounded-full border-2 border-cyan/40 bg-panel text-cyan shadow-[0_0_16px_rgba(69,224,230,.25)] transition hover:border-cyan"
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>
    </>
  );
}
