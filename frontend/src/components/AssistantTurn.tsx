import { useTranslation } from "react-i18next";
import type { Turn } from "../types";
import { MatchCard } from "./MatchCard";

function Dots() {
  return (
    <span className="inline-flex gap-1 items-center h-[14px]">
      <span className="dot w-1.5 h-1.5 rounded-full bg-ink-muted" style={{ animationDelay: "0s" }} />
      <span className="dot w-1.5 h-1.5 rounded-full bg-ink-muted" style={{ animationDelay: "0.15s" }} />
      <span className="dot w-1.5 h-1.5 rounded-full bg-ink-muted" style={{ animationDelay: "0.3s" }} />
    </span>
  );
}

export function AssistantTurn({ turn }: { turn: Turn }) {
  const { t } = useTranslation();

  if (turn.loading) {
    return (
      <div className="msg-rise">
        <Dots />
      </div>
    );
  }

  if (turn.error) {
    return (
      <div className="msg-rise">
        <span className="text-danger text-[0.9rem]">{turn.error}</span>
      </div>
    );
  }

  return (
    <div className="msg-rise">
      <div className="font-serif text-xl leading-relaxed font-normal max-w-[68ch] mb-[18px]">
        {turn.content}
      </div>

      {turn.structured_calls && turn.structured_calls.length > 0 && (
        <div className="font-mono text-[0.72rem] text-[#b8471f] bg-brand/[0.06] border border-brand-soft rounded-lg px-3 py-2.5 mb-[18px] whitespace-pre-wrap">
          {t("inspector.title")}
          {"\n"}
          {JSON.stringify(turn.structured_calls, null, 2)}
        </div>
      )}

      {turn.matches && turn.matches.length > 0 && (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(230px,1fr))] gap-3.5">
          {turn.matches.map((m) => (
            <MatchCard key={m.id} match={m} />
          ))}
        </div>
      )}
    </div>
  );
}
