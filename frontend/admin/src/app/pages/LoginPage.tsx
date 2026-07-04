import {
  type CSSProperties,
  type FormEvent,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { ChevronUp, Languages, Moon, Palette, Sun } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/shared/auth";
import { getErrorMessage } from "@/shared/api/errors";
import { useAdminLocale } from "@/shared/i18n/useAdminLocale";
import { useTheme } from "@/shared/theme";
import { Button } from "@/shared/ui/Button";
import { TextField } from "@/shared/ui/FormFields";
import { InlineMessage } from "@/shared/ui/InlineMessage";
import { AccentPicker } from "@/shared/ui/AccentPicker";
import { LanguagePicker } from "@/shared/ui/LanguagePicker";
import { ThemeToggle } from "@/shared/ui/ThemeToggle";
import "./LoginPage.css";

export function LoginPage() {
  const { t } = useTranslation("common");
  const { isAuthenticated, login } = useAuth();
  const location = useLocation();
  const { locale } = useAdminLocale();
  const { accent, resolvedTheme } = useTheme();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  const localeLabel = t(`preferences.language.options.${locale}`);
  const accentLabel = t(`preferences.accentOptions.${accent}`);
  const themeLabel =
    resolvedTheme === "dark"
      ? t("preferences.theme.dark")
      : t("preferences.theme.light");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(username, password);
    } catch (err) {
      setError(getErrorMessage(err, t("login.errorFallback")));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!preferencesOpen) {
      return undefined;
    }

    function handlePointerDown(event: MouseEvent) {
      const target = event.target as Node;
      if (
        triggerRef.current?.contains(target) ||
        panelRef.current?.contains(target)
      ) {
        return;
      }

      setPreferencesOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }

      event.preventDefault();
      setPreferencesOpen(false);
      window.setTimeout(() => {
        triggerRef.current?.focus();
      }, 0);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [preferencesOpen]);

  if (isAuthenticated) {
    const from = (location.state as { from?: string } | null)?.from;
    return <Navigate replace to={from ?? "/"} />;
  }

  return (
    <div className="login-aurora relative flex min-h-full items-center justify-center overflow-hidden p-6">
      {/* Orbital blobs – each orbits the viewport centre at its own radius & speed */}
      <div
        className="login-aurora__blob w-[60vmax] h-[60vmax]
        bg-primary/30 dark:bg-primary/20"
        style={{ "--r": "28vmax", animation: "orbit 22s linear infinite" } as CSSProperties}
      />
      <div
        className="login-aurora__blob w-[50vmax] h-[50vmax]
        bg-primary-subtle/45 dark:bg-primary-subtle/25"
        style={
          {
            "--r": "22vmax",
            animation: "orbit 28s linear infinite",
            animationDelay: "-9s",
          } as CSSProperties
        }
      />
      <div
        className="login-aurora__blob w-[45vmax] h-[45vmax]
        bg-primary-hover/25 dark:bg-primary-hover/15"
        style={
          {
            "--r": "16vmax",
            animation: "orbit 18s linear infinite",
            animationDelay: "-4s",
          } as CSSProperties
        }
      />

      {/* Card + robot strip */}
      <div className="relative w-full max-w-[400px]">
        {/* Robot loop animation (Mega Man X) — pick up box → carry to belt → turn back → repeat */}
        <div className="login-robot" aria-hidden="true">
          <div className="login-robot__scene">
            <div className="login-robot__belt" />
            <div className="login-robot__belt-leg login-robot__belt-leg--l" />
            <div className="login-robot__belt-leg login-robot__belt-leg--r" />
            <div className="login-robot__platform" />
            <div className="login-robot__bot-shadow" />
            <div className="login-robot__bot">
              <div className="login-robot__bot-antenna" />
              <div className="login-robot__bot-visor" />
              <div className="login-robot__bot-head" />
              <div className="login-robot__bot-body" />
              <div className="login-robot__box-carry" />
              <div className="login-robot__bot-leg login-robot__bot-leg--l" />
              <div className="login-robot__bot-leg login-robot__bot-leg--r" />
              <div className="login-robot__bot-arm">
                <div className="login-robot__bot-claw login-robot__bot-claw--l" />
                <div className="login-robot__bot-claw login-robot__bot-claw--r" />
              </div>
            </div>
            <div className="login-robot__box" />
            <div className="login-robot__box-new" />
          </div>
        </div>

        {/* Card */}
        <div className="relative w-full rounded-[2px] border border-border bg-surface px-8 pt-10 pb-8 animate-card-enter">
          <div className="mb-8 text-center">
            <div
              className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-[2px]
            bg-primary text-text-inverse text-lg font-bold"
            >
              AI
            </div>
            <h1 className="m-0 text-[22px] font-bold text-text">
              {t("login.title")}
            </h1>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            {error && <InlineMessage tone="error">{error}</InlineMessage>}

            <TextField
              label={t("login.username")}
              placeholder={t("login.usernamePlaceholder")}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
            />

            <TextField
              label={t("login.password")}
              type="password"
              placeholder={t("login.passwordPlaceholder")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              disabled={loading}
            >
              {loading ? t("login.submitting") : t("login.submit")}
            </Button>
          </form>

          <div
            className="login-preferences mt-6"
            role="group"
            aria-label={t("login.preferences.ariaLabel")}
          >
            <button
              ref={triggerRef}
              type="button"
              className="login-preferences__trigger"
              aria-expanded={preferencesOpen}
              aria-controls={panelId}
              aria-haspopup="dialog"
              aria-label={t(
                preferencesOpen
                  ? "login.preferences.closePanel"
                  : "login.preferences.openPanel",
                {
                  locale: localeLabel,
                  accent: accentLabel,
                  theme: themeLabel,
                },
              )}
              onClick={() => setPreferencesOpen((value) => !value)}
            >
              <span className="login-preferences__summary" aria-hidden="true">
                <Languages size={14} />
                <span className="login-preferences__locale-chip">
                  {localeLabel}
                </span>
                <span
                  className={`login-preferences__accent-swatch login-preferences__accent-swatch--${accent}`}
                />
                <Palette size={14} />
                {resolvedTheme === "dark" ? (
                  <Moon size={14} />
                ) : (
                  <Sun size={14} />
                )}
                <ChevronUp
                  className={
                    preferencesOpen
                      ? "login-preferences__chevron login-preferences__chevron--open"
                      : "login-preferences__chevron"
                  }
                  size={14}
                />
              </span>
            </button>

            {preferencesOpen ? (
              <div
                id={panelId}
                ref={panelRef}
                role="dialog"
                aria-label={t("login.preferences.panelLabel")}
                className="login-preferences__panel"
              >
                <div className="login-preferences__section">
                  <span className="login-preferences__label">
                    {t("login.preferences.language")}
                  </span>
                  <LanguagePicker className="login-preferences__language-picker" />
                </div>

                <div className="login-preferences__section">
                  <span className="login-preferences__label">
                    {t("login.preferences.accent")}
                  </span>
                  <AccentPicker className="login-preferences__accent-picker" />
                </div>

                <div className="login-preferences__section">
                  <span className="login-preferences__label">
                    {t("login.preferences.theme")}
                  </span>
                  <ThemeToggle placement="inline" />
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
