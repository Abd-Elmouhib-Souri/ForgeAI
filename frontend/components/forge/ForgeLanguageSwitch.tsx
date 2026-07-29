"use client";

import { useForgeLanguage } from "@/lib/language-context";

export default function ForgeLanguageSwitch() {
  const { lang, setLang } = useForgeLanguage();

  return (
    <div className="forge-language-switch" aria-label="Language selector">
      <button
        type="button"
        onClick={() => setLang("fr")}
        className={
          lang === "fr"
            ? "forge-language-button forge-language-button-active"
            : "forge-language-button"
        }
      >
        FR
      </button>

      <button
        type="button"
        onClick={() => setLang("en")}
        className={
          lang === "en"
            ? "forge-language-button forge-language-button-active"
            : "forge-language-button"
        }
      >
        EN
      </button>
    </div>
  );
}