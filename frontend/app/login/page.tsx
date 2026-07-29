"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import PublicOnlyPage from "@/components/auth/PublicOnlyPage";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api-error";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeLanguageSwitch from "@/components/forge/ForgeLanguageSwitch";

const content = {
  fr: {
    loading: "Chargement...",
    verified: "Email vérifié avec succès. Vous pouvez vous connecter.",
    titleSmall: "DotJcom",
    title: "Connexion à ForgeAI",
    subtitle:
      "Accédez à votre espace et continuez à transformer vos idées en projets structurés.",
    email: "Email",
    emailPlaceholder: "vous@exemple.com",
    password: "Mot de passe",
    passwordPlaceholder: "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022",
    forgot: "Mot de passe oublié ?",
    twoFactor: "Code de double authentification",
    twoFactorPlaceholder: "123456",
    backLogin: "Retour à la connexion",
    submit: "Se connecter",
    submitting: "Connexion...",
    verifyCode: "Vérifier le code",
    google: "Continuer avec Google",
    noAccount: "Pas encore de compte ?",
    createAccount: "Créer un compte",
    resendNeedEmail: "Entrez votre email avant de renvoyer le lien.",
    resendFallback:
      "Si un compte non vérifié existe, un nouveau lien a été envoyé.",
    resendError: "Impossible de renvoyer le lien de vérification.",
    resendSending: "Envoi en cours...",
    resend: "Renvoyer le lien de vérification",
    defaultError: "Erreur de connexion.",
    badge: "Espace sécurisé",
    cardTitle: "Votre copilote IA startup",
    cardText:
      "Retrouvez vos projets, vos analyses, vos scores, vos rapports et vos livrables exportables.",
  },
  en: {
    loading: "Loading...",
    verified: "Email verified successfully. You can now log in.",
    titleSmall: "DotJcom",
    title: "Login to ForgeAI",
    subtitle:
      "Access your workspace and keep turning your ideas into structured projects.",
    email: "Email",
    emailPlaceholder: "you@example.com",
    password: "Password",
    passwordPlaceholder: "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022",
    forgot: "Forgot password?",
    twoFactor: "Two-factor authentication code",
    twoFactorPlaceholder: "123456",
    backLogin: "Back to login",
    submit: "Log in",
    submitting: "Logging in...",
    verifyCode: "Verify code",
    google: "Continue with Google",
    noAccount: "No account yet?",
    createAccount: "Create account",
    resendNeedEmail: "Enter your email before resending the link.",
    resendFallback:
      "If an unverified account exists, a new link has been sent.",
    resendError: "Unable to resend the verification link.",
    resendSending: "Sending...",
    resend: "Resend verification link",
    defaultError: "Login error.",
    badge: "Secure workspace",
    cardTitle: "Your AI startup copilot",
    cardText:
      "Find your projects, analyses, scores, reports and exportable deliverables.",
  },
};

function LoginContent() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { lang } = useForgeLanguage();

  const t = useMemo(() => content[lang], [lang]);

  const rawNext = searchParams.get("next");
  const nextUrl = rawNext && rawNext.startsWith("/") ? rawNext : "/dashboard";
  const verified = searchParams.get("verified");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [twoFactorCode, setTwoFactorCode] = useState("");
  const [requiresTwoFactor, setRequiresTwoFactor] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);

  useEffect(() => {
    if (verified) {
      setInfo(t.verified);
    }
  }, [verified, t.verified]);

  const isEmailVerificationError =
    error.toLowerCase().includes("vérifier") ||
    error.toLowerCase().includes("verifier") ||
    error.toLowerCase().includes("verify");

  const handleGoogleLogin = () => {
    window.location.href = "http://localhost:8000/auth/google/login";
  };

  const handleResendVerification = async () => {
    if (!email) {
      setError(t.resendNeedEmail);
      return;
    }

    try {
      setIsResending(true);
      setError("");
      setInfo("");

      const res = await api.post("/auth/resend-verification", { email });
      setInfo(res.data.message || t.resendFallback);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, t.resendError));
    } finally {
      setIsResending(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setError("");
    setInfo("");
    setIsSubmitting(true);

    const result = await login(
      email,
      password,
      requiresTwoFactor ? twoFactorCode : undefined
    );

    setIsSubmitting(false);

    if (result.success) {
      router.replace(nextUrl);
    } else if (result.requiresTwoFactor) {
      setRequiresTwoFactor(true);
    } else {
      setError(result.error || t.defaultError);
    }
  };

  return (
    <PublicOnlyPage>
      <main className="forge-page relative flex min-h-screen items-center justify-center px-6 py-10">
        <div className="forge-blob forge-blob-blue forge-animate-soft-pulse left-[-90px] top-[-90px] h-72 w-72" />
        <div className="forge-blob forge-blob-pink forge-animate-soft-pulse right-[-80px] top-20 h-80 w-80" />
        <div className="forge-blob forge-blob-yellow bottom-[-80px] left-1/2 h-64 w-64" />

        <section className="relative z-10 grid w-full max-w-6xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="hidden lg:block">
            <span className="forge-eyebrow">🚀 {t.badge}</span>
            <h1 className="forge-hero-title mt-4">
              {t.cardTitle}
              <span className="forge-gradient-text block">ForgeAI</span>
            </h1>
            <p className="forge-hero-description">{t.cardText}</p>
          </div>

          <div className="forge-form-card">
            <div className="mb-8 flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-black text-sky-600">
                  {t.titleSmall}
                </p>
                <h1 className="mt-1 text-4xl font-black tracking-tight text-slate-950">
                  ForgeAI
                </h1>
                <p className="mt-3 max-w-sm text-sm font-semibold leading-6 text-slate-500">
                  {t.subtitle}
                </p>
              </div>

              <ForgeLanguageSwitch />
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {!requiresTwoFactor && (
                <>
                  <div className="forge-field">
                    <label className="forge-label">{t.email}</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder={t.emailPlaceholder}
                      className="forge-input"
                    />
                  </div>

                  <div className="forge-field">
                    <label className="forge-label">{t.password}</label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      placeholder={t.passwordPlaceholder}
                      className="forge-input"
                    />

                    <div className="mt-2 text-right">
                      <Link
                        href="/forgot-password"
                        className="text-sm font-black text-sky-600 hover:underline"
                      >
                        {t.forgot}
                      </Link>
                    </div>
                  </div>
                </>
              )}

              {requiresTwoFactor && (
                <div className="forge-field">
                  <label className="forge-label">{t.twoFactor}</label>
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={twoFactorCode}
                    onChange={(e) => setTwoFactorCode(e.target.value)}
                    required
                    autoFocus
                    placeholder={t.twoFactorPlaceholder}
                    className="forge-input text-center text-lg tracking-[0.45em]"
                  />

                  <button
                    type="button"
                    onClick={() => {
                      setRequiresTwoFactor(false);
                      setTwoFactorCode("");
                    }}
                    className="mt-2 text-left text-sm font-bold text-slate-500 underline hover:text-slate-950"
                  >
                    {t.backLogin}
                  </button>
                </div>
              )}

              {error && (
                <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
                  <p>{error}</p>

                  {isEmailVerificationError && !requiresTwoFactor && (
                    <button
                      type="button"
                      onClick={handleResendVerification}
                      disabled={isResending}
                      className="mt-2 font-black underline disabled:opacity-50"
                    >
                      {isResending ? t.resendSending : t.resend}
                    </button>
                  )}
                </div>
              )}

              {info && (
                <p className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">
                  {info}
                </p>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="forge-btn forge-btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting
                  ? t.submitting
                  : requiresTwoFactor
                    ? t.verifyCode
                    : t.submit}
              </button>

              {!requiresTwoFactor && (
                <button
                  type="button"
                  onClick={handleGoogleLogin}
                  className="forge-btn forge-btn-secondary w-full"
                >
                  {t.google}
                </button>
              )}
            </form>

            {!requiresTwoFactor && (
              <p className="mt-6 text-center text-sm font-semibold text-slate-500">
                {t.noAccount}{" "}
                <Link
                  href="/register"
                  className="font-black text-sky-600 hover:underline"
                >
                  {t.createAccount}
                </Link>
              </p>
            )}
          </div>
        </section>
      </main>
    </PublicOnlyPage>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="forge-page flex min-h-screen items-center justify-center">
          <p className="forge-badge">Chargement...</p>
        </main>
      }
    >
      <LoginContent />
    </Suspense>
  );
}





