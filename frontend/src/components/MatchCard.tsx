import { useTranslation } from "react-i18next";
import type { Match } from "../types";
import { colorFor } from "../lib/colorFor";

export function MatchCard({ match }: { match: Match }) {
  const { t } = useTranslation();
  const label = match.collections?.[0] || match.camera_model || t("match.untitled");
  const fileName = match.file_path.split("/").pop();

  const pills = [
    match.camera_model,
    match.rating != null ? t("match.rating", { value: match.rating }) : null,
    match.similarity != null ? t("match.similarity", { value: match.similarity }) : null,
    ...(match.keywords || []).slice(0, 2),
  ].filter((p): p is string => Boolean(p));

  return (
    <div
      className="relative rounded-xl overflow-hidden aspect-[4/5] flex flex-col justify-end p-4 transition-transform duration-200 hover:-translate-y-1 hover:scale-[1.015]"
      style={{ background: colorFor(match.id) }}
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: "linear-gradient(180deg, transparent 40%, rgba(0,0,0,0.75) 100%)" }}
      />
      <div className="absolute top-3.5 left-4 right-4 font-serif font-medium text-[1.35rem] leading-[1.1] text-white/90 z-10">
        {label}
      </div>
      <div className="relative z-10 font-mono text-[0.6rem] text-white/50 mb-2 break-all">
        {fileName}
      </div>
      <div className="relative z-10 text-[0.8rem] text-white/90 mb-2 leading-snug">
        {match.caption ? match.caption : <em className="text-white/55 not-italic">{t("match.noCaption")}</em>}
      </div>
      <div className="relative z-10 flex flex-wrap gap-[5px]">
        {pills.map((p, i) => (
          <span
            key={i}
            className={
              "text-[0.65rem] px-[9px] py-[3px] rounded-full border backdrop-blur-sm " +
              (i === 1
                ? "bg-brand border-brand text-white"
                : "bg-black/35 border-white/[0.18] text-white/85")
            }
          >
            {p}
          </span>
        ))}
      </div>
    </div>
  );
}
