"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeLanguageSwitch from "@/components/forge/ForgeLanguageSwitch";

const content = {
  fr: {
    loading: "Connexion avec Google en cours...",
    missing:
      "Token Google manquant. Redirection vers la page de connexion...",
    failed:
      "Connexion Google échouée. Redirection vers la page de connexion...",
    title: "Google OAuth",
    subtitle:
      "ForgeAI finalise la connexion sécurisée avec votre compte Google.",
    fallback: "Chargement...",
  },
  en: {
    loading: "Signing in with Google...",
    missing: "Missing Google token. Redirecting to login...",
    failed: "Google login failed. Redirecting to login...",
    title: "Google OAuth",
    subtitle:
      "ForgeAI is finalizing the secure connection with your Google account.",
    fallback: "Loading...",
  },
};

function OAuthCallbackContent() {
  const router = useRouter();
  const { completeOAuthLogin } = useAuth();
  const { lang } = useForgeLanguage();

  const t = useMemo(() => content[lang], [lang]);

  const [message, setMessage] = useState(t.loading);

  useEffect(() => {
    setMessage(t.loading);
  }, [t.loading]);

  useEffect(() => {
    const handleOAuthCallback = async () => {
      const success = await completeOAuthLogin();

      if (success) {
        router.replace("/dashboard");
      } else {
        setMessage(t.failed);
        setTimeout(() => router.replace("/login"), 1500);
      }
    };

    handleOAuthCallback();
  }, [completeOAuthLogin, router, t.failed]);

  return (
    <main className="forge-page relative flex min-h-screen items-center justify-center px-6 py-10">
      <div className="forge-blob forge-blob-blue left-[-90px] top-[-90px] h-72 w-72" />
      <div className="forge-blob forge-blob-pink right-[-80px] top-20 h-80 w-80" />
      <div className="forge-blob forge-blob-yellow bottom-[-80px] left-1/2 h-64 w-64" />

      <div className="forge-form-card relative z-10 text-center">
        <div className="mb-6 flex justify-end">
          <ForgeLanguageSwitch />
        </div>

        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-sky-100 text-3xl">
          🔐
        </div>

        <h1 className="text-4xl font-black tracking-tight text-slate-950">
          {t.title}
        </h1>

        <p className="mt-3 text-sm font-semibold leading-6 text-slate-500">
          {t.subtitle}
        </p>

        <div className="mt-6 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm font-bold text-sky-700">
          {message}
        </div>
      </div>
    </main>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <main className="forge-page flex min-h-screen items-center justify-center">
          <p className="forge-badge">Chargement...</p>
        </main>
      }
    >
      <OAuthCallbackContent />
    </Suspense>
  );
}
