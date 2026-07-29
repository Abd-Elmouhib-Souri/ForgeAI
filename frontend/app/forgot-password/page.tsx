"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeLanguageSwitch from "@/components/forge/ForgeLanguageSwitch";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const content = {
  fr: {
    eyebrow: "Récupération",
    title: "Mot de passe oublié",
    subtitle:
      "Entrez votre email. Si un compte existe, un lien de réinitialisation sera envoyé.",
    email: "Adresse email",
    placeholder: "exemple@gmail.com",
    submit: "Envoyer le lien",
    loading: "Envoi en cours...",
    error: "Erreur lors de la demande.",
    unknown: "Erreur inconnue.",
    back: "Retour à la connexion",
    sideTitle: "Sécurité du compte",
    sideText:
      "Pour protéger votre espace ForgeAI, le lien de réinitialisation est envoyé uniquement à l’adresse associée au compte.",
  },
  en: {
    eyebrow: "Recovery",
    title: "Forgot password",
    subtitle:
      "Enter your email. If an account exists, a reset link will be sent.",
    email: "Email address",
    placeholder: "example@gmail.com",
    submit: "Send link",
    loading: "Sending...",
    error: "Error while requesting password reset.",
    unknown: "Unknown error.",
    back: "Back to login",
    sideTitle: "Account security",
    sideText:
      "To protect your ForgeAI workspace, the reset link is sent only to the email address associated with the account.",
  },
};

export default function ForgotPasswordPage() {
  const { lang } = useForgeLanguage();
  const t = content[lang];

  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setIsLoading(true);
    setMessage("");
    setError("");

    try {
      const response = await fetch(`${API_URL}/auth/forgot-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || t.error);
      }

      setMessage(data.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.unknown);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="forge-page relative flex min-h-screen items-center justify-center px-6 py-10">
      <div className="forge-blob forge-blob-blue left-[-90px] top-[-90px] h-72 w-72" />
      <div className="forge-blob forge-blob-pink right-[-80px] top-20 h-80 w-80" />
      <div className="forge-blob forge-blob-yellow bottom-[-80px] left-1/2 h-64 w-64" />

      <section className="relative z-10 grid w-full max-w-6xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="hidden lg:block">
          <span className="forge-eyebrow">🔐 {t.eyebrow}</span>
          <h1 className="forge-hero-title mt-4">
            {t.sideTitle}
            <span className="forge-gradient-text block">ForgeAI</span>
          </h1>
          <p className="forge-hero-description">{t.sideText}</p>
        </div>

        <div className="forge-form-card">
          <div className="mb-8 flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-black text-sky-600">ForgeAI</p>
              <h1 className="mt-1 text-4xl font-black tracking-tight text-slate-950">
                {t.title}
              </h1>
              <p className="mt-3 max-w-sm text-sm font-semibold leading-6 text-slate-500">
                {t.subtitle}
              </p>
            </div>

            <ForgeLanguageSwitch />
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="forge-field">
              <label className="forge-label">{t.email}</label>

              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                placeholder={t.placeholder}
                className="forge-input"
              />
            </div>

            {message && (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">
                {message}
              </div>
            )}

            {error && (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="forge-btn forge-btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? t.loading : t.submit}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link
              href="/login"
              className="text-sm font-black text-sky-600 hover:underline"
            >
              {t.back}
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}