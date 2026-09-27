"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  MessageSquare,
  BarChart3,
  FileText,
  Database,
  UploadCloud,
  Shield,
  Sun,
  Moon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";

const tabs = [
  {
    label: "Chat",
    href: "/chat",
    icon: MessageSquare,
    description: "Interroger les rapports SFCR",
  },
  {
    label: "Analyse",
    href: "/analyse",
    icon: BarChart3,
    description: "Dashboard & KPIs comparatifs",
  },
  {
    label: "Base de données",
    labelCourt: "Données",
    href: "/base-donnees",
    icon: Database,
    description: "Tous les KPIs extraits, par société",
  },
  {
    label: "Documents",
    href: "/documents",
    icon: FileText,
    description: "Explorer les rapports par chapitre",
  },
  {
    label: "Ajouter un PDF",
    labelCourt: "Ajouter",
    href: "/upload",
    icon: UploadCloud,
    description: "Déposer un nouveau rapport SFCR",
  },
];

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
        <Shield className="w-4 h-4 text-accent-foreground" />
      </div>
      <div>
        <h1 className="font-heading text-lg leading-tight text-text-primary">
          Corpus SFCR
        </h1>
        <p className="text-xs text-text-tertiary">Iconcilio</p>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isDark, setIsDark] = useState(false);

  // Thème initial : choix mémorisé, sinon préférence du système.
  // (Le script du <head> applique déjà data-theme avant l'affichage.)
  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem("theme");
    } catch {
      /* stockage indisponible : on suit le système */
    }
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setIsDark(stored ? stored === "dark" : systemDark);
  }, []);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* stockage indisponible : le choix vaut pour cette session */
    }
  };

  // Redirect root to /chat
  const isRoot = pathname === "/";
  const isActive = (href: string) =>
    pathname === href || (isRoot && href === "/chat");

  const themeLabel = isDark ? "Mode clair" : "Mode sombre";

  return (
    <div className="flex h-dvh flex-col md:flex-row">
      {/* Barre du haut (mobile) */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 border-b border-border bg-surface">
        <Logo />
        <button
          onClick={toggleTheme}
          aria-label={themeLabel}
          className="w-9 h-9 flex items-center justify-center rounded-[var(--radius-md)] text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
        >
          {isDark ? <Sun className="w-[18px] h-[18px]" /> : <Moon className="w-[18px] h-[18px]" />}
        </button>
      </header>

      {/* Sidebar (ordinateur) */}
      <aside className="hidden md:flex w-[var(--sidebar-width)] flex-shrink-0 border-r border-border bg-surface flex-col">
        {/* Logo / Title */}
        <div className="px-5 py-5 border-b border-border">
          <Logo />
        </div>

        {/* Navigation */}
        <nav aria-label="Navigation principale" className="flex-1 px-3 py-4 space-y-1">
          {tabs.map((tab) => {
            const active = isActive(tab.href);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] text-sm transition-colors",
                  active
                    ? "bg-accent-light text-accent font-medium"
                    : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                )}
              >
                <tab.icon className="w-[18px] h-[18px] flex-shrink-0" />
                <div>
                  <span className="block leading-snug">{tab.label}</span>
                  <span className="block text-[11px] leading-tight mt-0.5 text-text-secondary">
                    {tab.description}
                  </span>
                </div>
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-3 py-3 border-t border-border">
          <button
            onClick={toggleTheme}
            className="flex items-center gap-2 px-3 py-2 rounded-[var(--radius-md)] text-sm text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors w-full"
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            <span>{themeLabel}</span>
          </button>
          <div className="mt-2 px-3">
            <p className="text-[10px] text-text-tertiary">
              Propulsé par Gemini & Qdrant
            </p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-h-0 overflow-auto bg-background">{children}</main>

      {/* Barre d'onglets du bas (mobile) */}
      <nav
        aria-label="Navigation principale"
        className="md:hidden flex border-t border-border bg-surface pb-[env(safe-area-inset-bottom)]"
      >
        {tabs.map((tab) => {
          const active = isActive(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex-1 flex flex-col items-center gap-0.5 py-2 text-[11px] transition-colors",
                active ? "text-accent font-medium" : "text-text-secondary"
              )}
            >
              <tab.icon className="w-5 h-5" />
              <span className="text-center leading-tight">
                {"labelCourt" in tab && tab.labelCourt ? tab.labelCourt : tab.label}
              </span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
