import { useChatStore } from "../store";
import { MessageBubble } from "./MessageBubble";
import { AssistantTurn } from "./AssistantTurn";

export function Thread() {
  const turns = useChatStore((s) => s.turns);

  return (
    <div className="py-8 flex flex-col gap-7">
      {turns.map((turn) =>
        turn.role === "user" ? (
          <MessageBubble key={turn.id} content={turn.content} />
        ) : (
          <AssistantTurn key={turn.id} turn={turn} />
        ),
      )}
    </div>
  );
}
