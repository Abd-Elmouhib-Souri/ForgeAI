"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ForgeLang = "fr" | "en";

type LanguageContextValue = {
  lang: ForgeLang;
  setLang: (lang: ForgeLang) => void;
  isFrench: boolean;
  isEnglish: boolean;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<ForgeLang>("fr");

  useEffect(() => {
    const saved = window.localStorage.getItem("forgeai_lang");

    if (saved === "fr" || saved === "en") {
      setLangState(saved);
      document.documentElement.lang = saved;
    }
  }, []);

  const setLang = (newLang: ForgeLang) => {
    setLangState(newLang);
    window.localStorage.setItem("forgeai_lang", newLang);
    document.documentElement.lang = newLang;
  };

  const value = useMemo(
    () => ({
      lang,
      setLang,
      isFrench: lang === "fr",
      isEnglish: lang === "en",
    }),
    [lang]
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useForgeLanguage() {
  const context = useContext(LanguageContext);

  if (!context) {
    throw new Error("useForgeLanguage must be used inside LanguageProvider");
  }

  return context;
}