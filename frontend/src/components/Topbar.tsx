import { useTranslation } from "react-i18next";

export function Topbar() {
  const { t } = useTranslation();
  return (
    <div className="flex justify-between items-center px-10 py-5 border-b border-line">
      <div className="font-serif font-semibold text-lg tracking-tight">
        loupe<span className="text-brand">.</span>
      </div>
      <nav className="flex gap-[22px] text-[0.78rem] text-ink-muted uppercase tracking-[0.08em]">
        <span>{t("nav.archive")}</span>
        <span>{t("nav.curator")}</span>
      </nav>
    </div>
  );
}
