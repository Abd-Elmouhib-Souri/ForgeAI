import Link from "next/link";
import type { ButtonHTMLAttributes, ComponentProps, ReactNode } from "react";
import { LoaderCircle, type LucideIcon } from "lucide-react";

// The ONE button style of the admin console: every page uses <Button> or
// <ButtonLink>, so colours, sizes, keyboard focus and disabled/loading
// states stay identical everywhere.

export type ButtonVariant = "primary" | "secondary" | "warning" | "info" | "danger" | "success" | "ghost";
export type ButtonSize = "sm" | "md";

const BASE =
  "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg border font-medium " +
  "transition-colors duration-150 " +
  // Visible keyboard focus (Tab), invisible on mouse click.
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 " +
  "disabled:cursor-not-allowed disabled:opacity-50";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "border-red-500 bg-red-500 text-white hover:border-red-400 hover:bg-red-400",
  secondary: "border-white/15 bg-white/5 text-white/85 hover:bg-white/10 hover:text-white",
  warning: "border-amber-400/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20",
  info: "border-cyan-400/40 bg-cyan-500/10 text-cyan-200 hover:bg-cyan-500/20",
  danger: "border-red-400/40 bg-red-500/10 text-red-200 hover:bg-red-500/20",
  success: "border-emerald-400/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20",
  ghost: "border-transparent bg-transparent text-white/60 hover:bg-white/5 hover:text-white",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
};

// Same classes for a <button> and a <Link> (and for tests/other components).
export function buttonClass({
  variant = "secondary",
  size = "md",
  block = false,
  className = "",
}: { variant?: ButtonVariant; size?: ButtonSize; block?: boolean; className?: string } = {}) {
  return [BASE, VARIANTS[variant], SIZES[size], block ? "w-full" : "", className].filter(Boolean).join(" ");
}

type CommonProps = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: LucideIcon; // decorative: the text (or aria-label) carries the meaning
  block?: boolean;
  children?: ReactNode;
};

export function Button({
  variant,
  size,
  icon: Icon,
  block,
  loading = false,
  type = "button", // never submit a form by accident
  disabled,
  className,
  children,
  ...rest
}: CommonProps & { loading?: boolean } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const iconSize = size === "sm" ? 14 : 16;
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClass({ variant, size, block, className })}
      {...rest}
    >
      {loading ? (
        <LoaderCircle size={iconSize} className="animate-spin" aria-hidden="true" />
      ) : (
        Icon && <Icon size={iconSize} aria-hidden="true" />
      )}
      {children}
    </button>
  );
}

export function ButtonLink({
  variant,
  size,
  icon: Icon,
  block,
  className,
  children,
  ...rest
}: CommonProps & ComponentProps<typeof Link>) {
  return (
    <Link className={buttonClass({ variant, size, block, className })} {...rest}>
      {Icon && <Icon size={size === "sm" ? 14 : 16} aria-hidden="true" />}
      {children}
    </Link>
  );
}
