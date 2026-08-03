export function MessageBubble({ content }: { content: string }) {
  return (
    <div className="msg-rise">
      <div className="inline-block bg-surface border border-line rounded-[10px] px-4 py-[11px] text-[0.92rem] text-ink">
        {content}
      </div>
    </div>
  );
}
