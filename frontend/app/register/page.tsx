"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api-error";
import PublicOnlyPage from "@/components/auth/PublicOnlyPage";
import { useForgeLanguage } from "@/lib/language-context";
import ForgeLanguageSwitch from "@/components/forge/ForgeLanguageSwitch";

const content = {
  fr: {
    small: "Bienvenue sur",
    title: "Créer un compte ForgeAI",
    subtitle:
      "Rejoignez votre espace IA pour analyser, structurer et présenter vos idées de startup.",
    fullName: "Nom complet",
    fullNamePlaceholder: "Votre nom",
    email: "Email",
    emailPlaceholder: "vous@exemple.com",
    role: "Profil",
    entrepreneur: "Entrepreneur",
    student: "Étudiant / PFE",
    consultant: "Consultant",
    password: "Mot de passe",
    passwordPlaceholder: "Minimum 6 caractères",
    submit: "Créer mon compte",
    submitting: "Création...",
    already: "Déjà inscrit ?",
    login: "Se connecter",
    error: "Erreur lors de l'inscription.",
    badge: "Votre idée mérite un vrai plan",
    cardTitle: "De l’idée au dossier complet",
    cardText:
      "ForgeAI vous aide à générer analyse de marché, SWOT, BMC, backlog, architecture et livrables exportables.",
  },
  en: {
    small: "Welcome to",
    title: "Create your ForgeAI account",
    subtitle:
      "Join your AI workspace to analyze, structure and present your startup ideas.",
    fullName: "Full name",
    fullNamePlaceholder: "Your name",
    email: "Email",
    emailPlaceholder: "you@example.com",
    role: "Profile",
    entrepreneur: "Entrepreneur",
    student: "Student / Final Project",
    consultant: "Consultant",
    password: "Password",
    passwordPlaceholder: "Minimum 6 characters",
    submit: "Create my account",
    submitting: "Creating...",
    already: "Already registered?",
    login: "Log in",
    error: "Registration error.",
    badge: "Your idea deserves a real plan",
    cardTitle: "From idea to complete file",
    cardText:
      "ForgeAI helps you generate market analysis, SWOT, BMC, backlog, architecture and exportable deliverables.",
  },
};

export default function RegisterPage() {
  const router = useRouter();
  const { lang } = useForgeLanguage();

  const t = useMemo(() => content[lang], [lang]);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("entrepreneur");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();

    setError("");
    setIsSubmitting(true);

    try {
      await api.post("/auth/register", {
        full_name: fullName,
        email,
        password,
        role,
      });

      router.replace(`/check-email?email=${encodeURIComponent(email)}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, t.error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PublicOnlyPage>
      <main className="forge-page relative flex min-h-screen items-center justify-center px-6 py-10">
        <div className="forge-blob forge-blob-blue left-[-90px] top-[-90px] h-72 w-72" />
        <div className="forge-blob forge-blob-pink forge-animate-soft-pulse right-[-80px] top-20 h-80 w-80" />
        <div className="forge-blob forge-blob-yellow bottom-[-80px] left-1/2 h-64 w-64" />

        <section className="relative z-10 grid w-full max-w-6xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="hidden lg:block">
            <span className="forge-eyebrow">✨ {t.badge}</span>
            <h1 className="forge-hero-title mt-4">
              {t.cardTitle}
              <span className="forge-gradient-text block">ForgeAI</span>
            </h1>
            <p className="forge-hero-description">{t.cardText}</p>
          </div>

          <div className="forge-form-card">
            <div className="mb-8 flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-black text-sky-600">{t.small}</p>
                <h1 className="mt-1 text-4xl font-black tracking-tight text-slate-950">
                  ForgeAI
                </h1>
                <p className="mt-3 max-w-sm text-sm font-semibold leading-6 text-slate-500">
                  {t.subtitle}
                </p>
              </div>

              <ForgeLanguageSwitch />
            </div>

            <form onSubmit={handleRegister} className="space-y-4">
              <div className="forge-field">
                <label className="forge-label">{t.fullName}</label>
                <input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  placeholder={t.fullNamePlaceholder}
                  className="forge-input"
                />
              </div>

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
                <label className="forge-label">{t.role}</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="forge-select"
                >
                  <option value="entrepreneur">{t.entrepreneur}</option>
                  <option value="student">{t.student}</option>
                  <option value="consultant">{t.consultant}</option>
                </select>
              </div>

              <div className="forge-field">
                <label className="forge-label">{t.password}</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  placeholder={t.passwordPlaceholder}
                  className="forge-input"
                />
              </div>

              {error && (
                <p className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="forge-btn forge-btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? t.submitting : t.submit}
              </button>
            </form>

            <p className="mt-6 text-center text-sm font-semibold text-slate-500">
              {t.already}{" "}
              <Link
                href="/login"
                className="font-black text-sky-600 hover:underline"
              >
                {t.login}
              </Link>
            </p>
          </div>
        </section>
      </main>
    </PublicOnlyPage>
  );
}





