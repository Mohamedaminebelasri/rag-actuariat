"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  MessageSquare,
  BarChart3,
  FileText,
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
    label: "Documents",
    href: "/documents",
    icon: FileText,
    description: "Explorer les rapports par chapitre",
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("theme");
    if (stored === "dark") {
      setIsDark(true);
      document.documentElement.setAttribute("data-theme", "dark");
    }
  }, []);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.setAttribute(
      "data-theme",
      next ? "dark" : "light"
    );
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  // Redirect root to /chat
  const isRoot = pathname === "/";

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-[var(--sidebar-width)] flex-shrink-0 border-r border-border bg-surface flex flex-col">
        {/* Logo / Title */}
        <div className="px-5 py-5 border-b border-border">
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
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {tabs.map((tab) => {
            const isActive =
              pathname === tab.href || (isRoot && tab.href === "/chat");
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] text-sm transition-colors",
                  isActive
                    ? "bg-accent-light text-accent font-medium"
                    : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                )}
              >
                <tab.icon className="w-[18px] h-[18px] flex-shrink-0" />
                <div>
                  <span className="block leading-snug">{tab.label}</span>
                  <span
                    className={cn(
                      "block text-[11px] leading-tight mt-0.5",
                      isActive ? "text-accent/70" : "text-text-tertiary"
                    )}
                  >
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
            {isDark ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
            <span>{isDark ? "Mode clair" : "Mode sombre"}</span>
          </button>
          <div className="mt-2 px-3">
            <p className="text-[10px] text-text-tertiary">
              Propulsé par Gemini & Qdrant
            </p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-background">{children}</main>
    </div>
  );
}
