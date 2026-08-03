import type { ChatMessage, ChatResponse } from "../types";

export class ChatApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function sendChat(messages: ChatMessage[]): Promise<ChatResponse> {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });

  const raw = await res.text();
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new ChatApiError(res.status, raw || "(empty response)");
  }

  if (!res.ok) {
    const detail = (data as { detail?: string })?.detail ?? JSON.stringify(data);
    throw new ChatApiError(res.status, detail);
  }

  return data as ChatResponse;
}
