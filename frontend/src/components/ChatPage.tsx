import { useEffect } from "react";
import { useChatStore } from "../store";
import { Topbar } from "./Topbar";
import { Hero } from "./Hero";
import { Thread } from "./Thread";
import { Composer } from "./Composer";

export function ChatPage() {
  const turns = useChatStore((s) => s.turns);

  useEffect(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }, [turns]);

  return (
    <>
      <Topbar />
      <Hero />
      <div className="max-w-[1100px] mx-auto px-10 pb-10">
        <Thread />
        <Composer />
      </div>
    </>
  );
}
