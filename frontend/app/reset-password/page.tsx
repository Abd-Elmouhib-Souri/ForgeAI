"use client";

import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeLanguageSwitch from "@/components/forge/ForgeLanguageSwitch";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const content = {
  fr: {
    title: "Nouveau mot de passe",
    subtitle: "Choisissez un nouveau mot de passe pour votre compte ForgeAI.",
    newPassword: "Nouveau mot de passe",
    newPlaceholder: "Minimum 8 caractères",
    confirmPassword: "Confirmer le mot de passe",
    confirmPlaceholder: "Répétez le mot de passe",
    missingToken: "Token de réinitialisation manquant.",
    missingTokenBox: "Token manquant. Ouvrez le lien reçu par email.",
    tooShort: "Le mot de passe doit contenir au moins 8 caractères.",
    mismatch: "Les mots de passe ne correspondent pas.",
    submit: "Réinitialiser le mot de passe",
    loading: "Réinitialisation...",
    error: "Erreur lors de la réinitialisation.",
    unknown: "Erreur inconnue.",
    back: "Retour à la connexion",
    redirect: "Redirection vers la connexion...",
    sideTitle: "Réinitialisation sécurisée",
    sideText:
      "Après validation, vous pourrez vous reconnecter à votre espace ForgeAI avec votre nouveau mot de passe.",
    fallback: "Chargement...",
  },
  en: {
    title: "New password",
    subtitle: "Choose a new password for your ForgeAI account.",
    newPassword: "New password",
    newPlaceholder: "Minimum 8 characters",
    confirmPassword: "Confirm password",
    confirmPlaceholder: "Repeat password",
    missingToken: "Missing reset token.",
    missingTokenBox: "Missing token. Open the link received by email.",
    tooShort: "Password must contain at least 8 characters.",
    mismatch: "Passwords do not match.",
    submit: "Reset password",
    loading: "Resetting...",
    error: "Error while resetting password.",
    unknown: "Unknown error.",
    back: "Back to login",
    redirect: "Redirecting to login...",
    sideTitle: "Secure reset",
    sideText:
      "After validation, you will be able to log back into your ForgeAI workspace with your new password.",
    fallback: "Loading...",
  },
};

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { lang } = useForgeLanguage();
  const t = content[lang];

  const token = searchParams.get("token") || "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setIsLoading(true);
    setMessage("");
    setError("");

    if (!token) {
      setError(t.missingToken);
      setIsLoading(false);
      return;
    }

    if (newPassword.length < 8) {
      setError(t.tooShort);
      setIsLoading(false);
      return;
    }

    if (newPassword !== confirmPassword) {
      setError(t.mismatch);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/auth/reset-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
          new_password: newPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || t.error);
      }

      setMessage(data.message || t.redirect);

      setTimeout(() => {
        router.push("/login");
      }, 2000);
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
          <span className="forge-eyebrow">🔑 ForgeAI</span>
          <h1 className="forge-hero-title mt-4">
            {t.sideTitle}
            <span className="forge-gradient-text block">Account</span>
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

          {!token && (
            <div className="mb-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
              {t.missingTokenBox}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="forge-field">
              <label className="forge-label">{t.newPassword}</label>

              <input
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
                minLength={8}
                placeholder={t.newPlaceholder}
                className="forge-input"
              />
            </div>

            <div className="forge-field">
              <label className="forge-label">{t.confirmPassword}</label>

              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                minLength={8}
                placeholder={t.confirmPlaceholder}
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
              disabled={isLoading || !token}
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

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <main className="forge-page flex min-h-screen items-center justify-center">
          <p className="forge-badge">Chargement...</p>
        </main>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}