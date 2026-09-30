"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/app/admin/_components/Button";

import { AdminApiError, adminRequest, setAdminToken } from "@/lib/admin-api";

// Sprint 7.1 login flow (2FA mandatory for admins):
//   credentials -> "totp" (code from the authenticator app)
//   credentials -> "enroll" (first login: scan the QR code, confirm a code)
type Step = "credentials" | "totp" | "enroll";

type Enrollment = {
  token: string;
  secret: string;
  qr_svg: string;
};

function errorMessage(status: number, detail: unknown, fallback: string) {
  return new AdminApiError(status, detail, fallback).message;
}

export default function AdminLoginPage() {
  const router = useRouter();

  const [step, setStep] = useState<Step>("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);

  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function openSession(accessToken: string) {
    setAdminToken(accessToken);
    router.replace("/admin/dashboard");
  }

  function backToCredentials() {
    setStep("credentials");
    setCode("");
    setEnrollment(null);
    setError("");
  }

  // Step 1 (and step 2 resend with the code).
  async function submitLogin() {
    const { status, ok, data } = await adminRequest("/admin/login", {
      body: { email, password, two_factor_code: step === "totp" ? code : undefined },
    });

    if (status === 401 && data?.detail?.reason === "totp_required") {
      setStep("totp");
      return;
    }
    if (status === 429) {
      throw new Error("Trop de tentatives. Patientez quelques minutes avant de réessayer.");
    }
    if (!ok) {
      throw new Error(errorMessage(status, data?.detail, "Connexion refusée."));
    }

    if (data?.requires_2fa_setup && data?.enrollment_token) {
      // First admin login: generate the secret and its QR code.
      const setup = await adminRequest("/admin/2fa/setup", { token: data.enrollment_token });
      if (!setup.ok) {
        throw new Error(errorMessage(setup.status, setup.data?.detail, "Configuration 2FA impossible."));
      }
      setEnrollment({
        token: data.enrollment_token,
        secret: setup.data.secret,
        qr_svg: setup.data.qr_svg,
      });
      setStep("enroll");
      return;
    }

    if (!data?.access_token) throw new Error("Session admin manquante.");
    openSession(data.access_token);
  }

  // Step 3: confirm the first code to turn 2FA on.
  async function submitEnrollment() {
    if (!enrollment) return;
    const { status, ok, data } = await adminRequest("/admin/2fa/enable", {
      token: enrollment.token,
      body: { code },
    });
    if (!ok) throw new Error(errorMessage(status, data?.detail, "Code invalide."));
    openSession(data.access_token);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      if (step === "enroll") await submitEnrollment();
      else await submitLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const inputClass =
    "mt-1 w-full rounded-lg border border-white/10 bg-white/10 px-4 py-3 text-sm outline-none transition focus:border-red-300";

  const codeInput = (
    <input
      type="text"
      inputMode="numeric"
      autoComplete="one-time-code"
      maxLength={6}
      value={code}
      onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
      required
      autoFocus
      placeholder="123456"
      className={`${inputClass} text-center text-lg tracking-widest`}
    />
  );

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 px-6 py-10 text-white">
      <div className="absolute -left-32 -top-32 h-80 w-80 animate-pulse rounded-full bg-red-500/20 blur-3xl" />
      <div className="absolute -bottom-32 -right-32 h-80 w-80 animate-pulse rounded-full bg-cyan-500/20 blur-3xl" />

      <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-white/10 p-8 shadow-2xl backdrop-blur-xl">
        <div className="mb-8 text-center">
          <p className="text-sm font-medium text-red-300">Console d&apos;administration</p>
          <h1 className="mt-1 text-4xl font-bold tracking-tight">ForgeAI Admin</h1>
          <p className="mt-3 text-sm text-white/60">
            {step === "enroll"
              ? "Première connexion : activez la double authentification."
              : "Accès réservé aux administrateurs."}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {step === "credentials" && (
            <>
              <div>
                <label className="text-sm text-white/70">E-mail administrateur</label>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  autoComplete="username"
                  placeholder="admin@exemple.com"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="text-sm text-white/70">Mot de passe</label>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className={inputClass}
                />
              </div>
            </>
          )}

          {step === "totp" && (
            <div>
              <label className="text-sm text-white/70">
                Code de votre application d&apos;authentification
              </label>
              {codeInput}
            </div>
          )}

          {step === "enroll" && enrollment && (
            <div className="space-y-3">
              <ol className="list-decimal space-y-1 pl-5 text-sm text-white/70">
                <li>Ouvrez Google Authenticator, Microsoft Authenticator ou une application équivalente.</li>
                <li>Scannez ce QR code.</li>
                <li>Saisissez le code à 6 chiffres affiché.</li>
              </ol>
              {/* SVG generated by our own admin API (segno), never user input. */}
              <div
                className="mx-auto w-48 rounded-lg bg-white p-2 [&>svg]:h-auto [&>svg]:w-full"
                dangerouslySetInnerHTML={{ __html: enrollment.qr_svg }}
              />
              <p className="break-all text-center text-xs text-white/50">
                Clé manuelle : <span className="font-mono text-white/80">{enrollment.secret}</span>
              </p>
              {codeInput}
            </div>
          )}

          {step !== "credentials" && (
            <Button variant="ghost" size="sm" icon={ArrowLeft} className="-ml-3" onClick={backToCredentials}>
              Retour à la connexion
            </Button>
          )}

          {error && (
            <div className="rounded-lg border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200">
              {error}
            </div>
          )}

          <Button type="submit" variant="primary" block loading={isSubmitting} className="h-11">
            {isSubmitting
              ? "Vérification..."
              : step === "credentials"
                ? "Se connecter"
                : step === "totp"
                  ? "Vérifier le code"
                  : "Activer la 2FA et se connecter"}
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-white/40">Espace sécurisé — ForgeAI</p>
      </div>
    </main>
  );
}
