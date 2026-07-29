"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import PublicOnlyPage from "@/components/auth/PublicOnlyPage";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeLanguageSwitch from "@/components/forge/ForgeLanguageSwitch";

const content = {
  fr: {
    defaultMessage:
      "Nous avons envoyé un lien de vérification à votre adresse email.",
    newLink: "Nouveau lien envoyé.",
    resendError: "Impossible de renvoyer le lien pour le moment.",
    title: "Vérifiez votre email",
    subtitle:
      "Cliquez sur le lien reçu par email pour activer votre compte avant de vous connecter.",
    resend: "Renvoyer le lien",
    sending: "Envoi...",
    back: "Retour à la connexion",
    fallback: "Chargement...",
    sideTitle: "Dernière étape avant ForgeAI",
    sideText:
      "La vérification email protège votre compte et confirme que vous pouvez recevoir les notifications importantes.",
  },
  en: {
    defaultMessage:
      "We sent a verification link to your email address.",
    newLink: "New link sent.",
    resendError: "Unable to resend the link for now.",
    title: "Verify your email",
    subtitle:
      "Click the link received by email to activate your account before logging in.",
    resend: "Resend link",
    sending: "Sending...",
    back: "Back to login",
    fallback: "Loading...",
    sideTitle: "Last step before ForgeAI",
    sideText:
      "Email verification protects your account and confirms that you can receive important notifications.",
  },
};

function CheckEmailContent() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email") || "";

  const { lang } = useForgeLanguage();
  const t = useMemo(() => content[lang], [lang]);

  const [message, setMessage] = useState(t.defaultMessage);
  const [isSending, setIsSending] = useState(false);

  const handleResend = async () => {
    if (!email) return;

    try {
      setIsSending(true);

      const res = await api.post("/auth/resend-verification", { email });

      setMessage(res.data.message || t.newLink);
    } catch {
      setMessage(t.resendError);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <PublicOnlyPage>
      <main className="forge-page relative flex min-h-screen items-center justify-center px-6 py-10">
        <div className="forge-blob forge-blob-blue left-[-90px] top-[-90px] h-72 w-72" />
        <div className="forge-blob forge-blob-pink right-[-80px] top-20 h-80 w-80" />
        <div className="forge-blob forge-blob-yellow bottom-[-80px] left-1/2 h-64 w-64" />

        <section className="relative z-10 grid w-full max-w-6xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="hidden lg:block">
            <span className="forge-eyebrow">✉️ ForgeAI</span>
            <h1 className="forge-hero-title mt-4">
              {t.sideTitle}
              <span className="forge-gradient-text block">Email</span>
            </h1>
            <p className="forge-hero-description">{t.sideText}</p>
          </div>

          <div className="forge-form-card text-center">
            <div className="mb-6 flex justify-end">
              <ForgeLanguageSwitch />
            </div>

            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-sky-100 text-3xl">
              ✉️
            </div>

            <p className="text-sm font-black text-sky-600">ForgeAI</p>

            <h1 className="mt-2 text-4xl font-black tracking-tight text-slate-950">
              {t.title}
            </h1>

            <p className="mt-4 text-sm font-semibold leading-6 text-slate-500">
              {message}
            </p>

            {email && (
              <p className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm font-black text-sky-700">
                {email}
              </p>
            )}

            <p className="mt-4 text-xs font-semibold leading-5 text-slate-400">
              {t.subtitle}
            </p>

            <div className="mt-6 space-y-3">
              <button
                type="button"
                onClick={handleResend}
                disabled={isSending || !email}
                className="forge-btn forge-btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSending ? t.sending : t.resend}
              </button>

              <Link href="/login" className="forge-btn forge-btn-secondary w-full">
                {t.back}
              </Link>
            </div>
          </div>
        </section>
      </main>
    </PublicOnlyPage>
  );
}

export default function CheckEmailPage() {
  return (
    <Suspense
      fallback={
        <main className="forge-page flex min-h-screen items-center justify-center">
          <p className="forge-badge">Chargement...</p>
        </main>
      }
    >
      <CheckEmailContent />
    </Suspense>
  );
}