"use client";

import { useState, KeyboardEvent } from "react";

type Message = {
  role: "user" | "assistant";
  text: string;
};

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  const send = async () => {
    if (!input.trim() || isSending) return;
    const nextMessages: Message[] = [
      ...messages,
      { role: "user", text: input },
    ];
    setMessages(nextMessages);
    setIsSending(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: input }),
      });
      const data = await res.json();
      const assistantText =
        data?.text ||
        data?.reply ||
        data?.content ||
        data?.message ||
        JSON.stringify(data);
      setMessages([
        ...nextMessages,
        { role: "assistant", text: assistantText },
      ]);
    } catch (err) {
      setMessages([
        ...nextMessages,
        { role: "assistant", text: "Sorry, something went wrong." },
      ]);
    } finally {
      setInput("");
      setIsSending(false);
    }
  };

  const handleKey = (evt: KeyboardEvent<HTMLInputElement>) => {
    if (evt.key === "Enter") {
      evt.preventDefault();
      send();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-b from-rose-50 to-white">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={msg.role === "user" ? "text-right" : "text-left"}
          >
            <span className="inline-block px-3 py-2 rounded-2xl shadow-sm bg-white/80">
              {msg.text}
            </span>
          </div>
        ))}
      </div>
      <div className="p-3 flex gap-2 border-t bg-white">
        <input
          value={input}
          onChange={(evt) => setInput(evt.target.value)}
          onKeyDown={handleKey}
          placeholder="Talk to me..."
          className="flex-1 border rounded-full px-4 py-2"
        />
        <button
          onClick={send}
          disabled={isSending}
          className="px-4 py-2 bg-rose-500 text-white rounded-full disabled:opacity-60"
        >
          Send
        </button>
      </div>
    </div>
  );
}
