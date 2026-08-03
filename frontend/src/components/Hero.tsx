import { useTranslation } from "react-i18next";

export function Hero() {
  const { t } = useTranslation();
  return (
    <div className="px-10 pt-16 pb-10 border-b border-line">
      <h1 className="font-serif font-normal text-[clamp(2.6rem,7vw,5.2rem)] leading-[0.98] tracking-[-0.02em] mb-[18px] max-w-[16ch]">
        {t("hero.title")}
      </h1>
      <div className="text-ink-muted text-base max-w-[56ch] leading-relaxed">
        {t("hero.lede")}
      </div>
    </div>
  );
}
