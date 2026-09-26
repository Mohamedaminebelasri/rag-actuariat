"use client";

import { TrendingUp, TrendingDown } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import type { KpiDefinition, KpiValeur } from "@/data/analyse-demo";
import { ConfidenceBadge } from "./confidence-badge";
import { couleurSeuil, formatValeur, formatVariation } from "@/lib/analyse-utils";

const COULEUR_VALEUR: Record<string, string> = {
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
  neutre: "text-text-primary",
};

/** Port de kpi_card() (individuelle.py, Reflex) — porte le lien intelligent
 * vers /documents?company=...&kpi=... (cf. analyse/page.tsx d'origine). */
export function KpiCard({ def, valeur, societe }: { def: KpiDefinition; valeur: KpiValeur; societe: string }) {
  const router = useRouter();
  const couleur = couleurSeuil(def.id, valeur.valeur);
  const aVariation = valeur.variation !== null;
  const variationPositive = aVariation && valeur.variation! >= 0;

  return (
    <button
      onClick={() =>
        router.push(`/documents?company=${encodeURIComponent(societe)}&kpi=${encodeURIComponent(def.id)}`)
      }
      title="Voir la source dans les Annexes QRT"
      className="text-left h-full flex flex-col bg-surface border border-border rounded-[var(--radius-lg)] p-[1.1em] shadow-[var(--shadow-sm)] transition-all hover:shadow-[var(--shadow-md)] hover:-translate-y-px"
    >
      <div className="flex items-center w-full">
        <span className="font-mono text-[11px] font-bold text-text-tertiary">{def.code}</span>
        <span className="flex-1" />
        <ConfidenceBadge confiance={valeur.confiance} chapitre={valeur.chapitreSource} page={valeur.pageSource} />
      </div>
      <p className="text-sm font-medium text-text-secondary mt-2.5">{def.label}</p>
      <p className={cn("font-mono text-[1.75rem] font-bold mt-0.5 leading-tight", COULEUR_VALEUR[couleur])}>
        {formatValeur(valeur.valeur, def.unite)}
      </p>
      {aVariation ? (
        <div className="flex items-center gap-1 mt-1.5">
          {variationPositive ? (
            <TrendingUp className="w-3.5 h-3.5 text-success" />
          ) : (
            <TrendingDown className="w-3.5 h-3.5 text-danger" />
          )}
          <span className={cn("text-xs font-medium font-mono", variationPositive ? "text-success" : "text-danger")}>
            {formatVariation(valeur.variation!, valeur.variationUnit)}
          </span>
          <span className="text-[11px] text-text-tertiary">vs N-1</span>
        </div>
      ) : (
        <div className="h-[1.4em] mt-1.5" />
      )}
      <p className="text-xs text-text-tertiary mt-2 leading-relaxed">{def.description}</p>
    </button>
  );
}
