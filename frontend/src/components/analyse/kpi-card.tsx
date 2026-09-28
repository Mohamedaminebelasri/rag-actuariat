"use client";

import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import type { KpiDefinition, KpiValeur } from "@/data/analyse-demo";
import { ConfidenceBadge } from "./confidence-badge";
import {
  couleurSeuil,
  formatValeur,
  formatVariation,
  sentimentVariation,
  statutKpi,
  type SentimentVariation,
} from "@/lib/analyse-utils";

const COULEUR_VALEUR: Record<string, string> = {
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
  neutre: "text-text-primary",
};

// Feu tricolore : bande de couleur à gauche de la carte + pastille de statut.
const BORDURE_STATUT: Record<string, string> = {
  success: "border-l-4 border-l-success",
  warning: "border-l-4 border-l-warning",
  danger: "border-l-4 border-l-danger",
};

const PASTILLE_STATUT: Record<string, string> = {
  success: "bg-success-light text-success",
  warning: "bg-warning-light text-warning",
  danger: "bg-danger-light text-danger",
};

// La flèche suit le signe ; sa couleur dit si c'est bon ou mauvais pour CE KPI.
const COULEUR_TENDANCE: Record<SentimentVariation, string> = {
  amelioration: "text-success",
  degradation: "text-danger",
  stable: "text-text-tertiary",
  neutre: "text-text-tertiary",
};

const LIBELLE_TENDANCE: Record<SentimentVariation, string> = {
  amelioration: "Amélioration par rapport à N-1",
  degradation: "Dégradation par rapport à N-1",
  stable: "Stable par rapport à N-1",
  neutre: "Évolution par rapport à N-1",
};

/** Port de kpi_card() (individuelle.py, Reflex) — porte le lien intelligent
 * vers /documents?company=...&kpi=... (cf. analyse/page.tsx d'origine).
 * Idée 1 : feu tricolore (bande + pastille) et flèche de tendance dont la
 * couleur tient compte du sens du KPI. */
export function KpiCard({ def, valeur, societe }: { def: KpiDefinition; valeur: KpiValeur; societe: string }) {
  const couleur = couleurSeuil(def.id, valeur.valeur);
  const statut = statutKpi(def.id, valeur.valeur);
  const aVariation = valeur.variation !== null;
  const sentiment: SentimentVariation = aVariation
    ? sentimentVariation(def.id, valeur.variation!, valeur.variationUnit)
    : "neutre";
  const IconeTendance = !aVariation
    ? null
    : sentiment === "stable"
      ? Minus
      : valeur.variation! >= 0
        ? TrendingUp
        : TrendingDown;

  return (
    <div
      className={cn(
        "text-left h-full flex flex-col bg-surface border border-border rounded-[var(--radius-lg)] p-[1.1em] shadow-[var(--shadow-sm)]",
        statut && BORDURE_STATUT[statut.couleur]
      )}
    >
      <div className="flex items-center w-full">
        <span className="font-mono text-[11px] font-bold text-text-tertiary">{def.code}</span>
        <span className="flex-1" />
        {/* <ConfidenceBadge confiance={valeur.confiance} chapitre={valeur.chapitreSource} page={valeur.pageSource} /> */}
      </div>
      <p className="text-sm font-medium text-text-secondary mt-2.5">{def.label}</p>
      <p className={cn("font-mono text-[1.75rem] font-bold mt-0.5 leading-tight", COULEUR_VALEUR[couleur])}>
        {formatValeur(valeur.valeur, def.unite, valeur.valeurBrute, valeur.uniteBrute)}
      </p>
      <div className="flex items-center gap-x-2 gap-y-1 flex-wrap mt-1.5 min-h-[1.4em]">
        {statut && (
          <span
            className={cn(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium",
              PASTILLE_STATUT[statut.couleur]
            )}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-current" aria-hidden="true" />
            {statut.libelle}
          </span>
        )}
        {aVariation && IconeTendance && (
          <span className="inline-flex items-center gap-1" title={LIBELLE_TENDANCE[sentiment]}>
            <IconeTendance className={cn("w-3.5 h-3.5", COULEUR_TENDANCE[sentiment])} aria-hidden="true" />
            <span className={cn("text-xs font-medium font-mono", COULEUR_TENDANCE[sentiment])}>
              {formatVariation(valeur.variation!, valeur.variationUnit)}
            </span>
            <span className="text-[11px] text-text-tertiary">vs N-1</span>
            <span className="sr-only">{LIBELLE_TENDANCE[sentiment]}</span>
          </span>
        )}
      </div>
      <p className="text-xs text-text-tertiary mt-2 leading-relaxed">{def.description}</p>
    </div>
  );
}
