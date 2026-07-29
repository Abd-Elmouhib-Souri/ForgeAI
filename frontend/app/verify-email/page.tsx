"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api-error";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeLanguageSwitch from "@/components/forge/ForgeLanguageSwitch";

const content = {
  fr: {
    loadingMessage: "Vérification de votre email...",
    missingToken: "Token de vérification manquant.",
    success: "Email vérifié avec succès.",
    error: "Lien de vérification invalide ou expiré.",
    title: "Vérification email",
    redirect: "Redirection vers la connexion...",
    back: "Retour à la connexion",
    fallback: "Chargement...",
    sideTitle: "Activation du compte",
    sideText:
      "ForgeAI vérifie votre lien pour activer l’accès à votre espace personnel sécurisé.",
  },
  en: {
    loadingMessage: "Verifying your email...",
    missingToken: "Missing verification token.",
    success: "Email verified successfully.",
    error: "Invalid or expired verification link.",
    title: "Email verification",
    redirect: "Redirecting to login...",
    back: "Back to login",
    fallback: "Loading...",
    sideTitle: "Account activation",
    sideText:
      "ForgeAI checks your link to activate access to your secure personal workspace.",
  },
};

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { lang } = useForgeLanguage();

  const t = useMemo(() => content[lang], [lang]);

  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading"
  );
  const [message, setMessage] = useState(t.loadingMessage);

  useEffect(() => {
    setMessage(t.loadingMessage);
  }, [t.loadingMessage]);

  useEffect(() => {
    const verifyEmail = async () => {
      const token = searchParams.get("token");

      if (!token) {
        setStatus("error");
        setMessage(t.missingToken);
        return;
      }

      try {
        const response = await api.get(
          `/auth/verify-email?token=${encodeURIComponent(token)}`
        );

        setStatus("success");
        setMessage(response.data.message || t.success);

        setTimeout(() => {
          router.replace("/login?verified=1");
        }, 1800);
      } catch (err: unknown) {
        setStatus("error");
        setMessage(getApiErrorMessage(err, t.error));
      }
    };

    verifyEmail();
  }, [searchParams, router, t.error, t.missingToken, t.success]);

  return (
    <main className="forge-page relative flex min-h-screen items-center justify-center px-6 py-10">
      <div className="forge-blob forge-blob-blue left-[-90px] top-[-90px] h-72 w-72" />
      <div className="forge-blob forge-blob-pink right-[-80px] top-20 h-80 w-80" />
      <div className="forge-blob forge-blob-yellow bottom-[-80px] left-1/2 h-64 w-64" />

      <section className="relative z-10 grid w-full max-w-6xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="hidden lg:block">
          <span className="forge-eyebrow">✅ ForgeAI</span>
          <h1 className="forge-hero-title mt-4">
            {t.sideTitle}
            <span className="forge-gradient-text block">Secure</span>
          </h1>
          <p className="forge-hero-description">{t.sideText}</p>
        </div>

        <div className="forge-form-card text-center">
          <div className="mb-6 flex justify-end">
            <ForgeLanguageSwitch />
          </div>

          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-sky-100 text-3xl">
            {status === "loading" ? "â³" : status === "success" ? "✅" : "âš ï¸"}
          </div>

          <h1 className="text-4xl font-black tracking-tight text-slate-950">
            {t.title}
          </h1>

          <p
            className={
              status === "success"
                ? "mt-4 text-sm font-semibold leading-6 text-emerald-700"
                : status === "error"
                  ? "mt-4 text-sm font-semibold leading-6 text-red-700"
                  : "mt-4 animate-pulse text-sm font-semibold leading-6 text-slate-500"
            }
          >
            {message}
          </p>

          {status === "success" && (
            <p className="mt-3 text-xs font-semibold text-slate-400">
              {t.redirect}
            </p>
          )}

          {status === "error" && (
            <button
              className="forge-btn forge-btn-primary mt-6 w-full"
              onClick={() => router.replace("/login")}
            >
              {t.back}
            </button>
          )}
        </div>
      </section>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <main className="forge-page flex min-h-screen items-center justify-center">
          <p className="forge-badge">Chargement...</p>
        </main>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}





