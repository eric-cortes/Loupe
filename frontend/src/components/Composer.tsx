import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useChatStore } from "../store";

export function Composer() {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const sending = useChatStore((s) => s.sending);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setText("");
    await sendMessage(trimmed);
    textareaRef.current?.focus();
  };

  return (
    <form
      onSubmit={submit}
      className="sticky bottom-0 flex gap-[10px] pt-5 pb-7"
      style={{ background: "linear-gradient(180deg, transparent, rgb(var(--canvas)) 30%)" }}
    >
      <textarea
        ref={textareaRef}
        rows={2}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t("composer.placeholder")}
        className="flex-1 px-[18px] py-[15px] text-[0.95rem] font-sans rounded-xl border border-line bg-surface text-ink resize-none transition-colors focus:outline-none focus:border-brand-soft placeholder:text-ink-muted"
      />
      <button
        type="submit"
        disabled={sending}
        className="px-[26px] text-[0.9rem] font-semibold rounded-xl border-none bg-brand text-white cursor-pointer transition-colors hover:enabled:bg-brand-strong disabled:bg-line disabled:text-ink-muted disabled:cursor-default"
      >
        {t("composer.send")}
      </button>
    </form>
  );
}
