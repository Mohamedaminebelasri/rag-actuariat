"use client";

import { CircleCheck, CircleX, Minus, TrendingDown, TriangleAlert, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import type { KpiDefinition, KpiValeur } from "@/data/analyse-demo";
// import { ConfidenceBadge } from "./confidence-badge"; // masqué (cf. JSX commenté plus bas)
import { AvertissementKpi } from "./avertissement-kpi";
import {
  couleurSeuil,
  formatValeur,
  formatVariation,
  sentimentVariation,
  statutKpi,
  texteInfobulleSeuil,
  type SentimentVariation,
} from "@/lib/analyse-utils";
import { SEUIL_VERT_SCR_DEFAUT } from "@/lib/seuils-config";

// Exportés : réutilisés tels quels par le tableau comparatif (comparative-table.tsx)
// pour que ratio_scr/ratio_mcr aient EXACTEMENT les mêmes couleurs/icônes que les cartes.
export const COULEUR_VALEUR: Record<string, string> = {
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

// Icône dédoublant la couleur (accessibilité : jamais la couleur seule).
export const ICONE_STATUT: Record<string, typeof CircleCheck> = {
  success: CircleCheck,
  warning: TriangleAlert,
  danger: CircleX,
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
 * Feu tricolore (bande + pastille + icône) pour ratio_scr/ratio_mcr
 * uniquement ; tendance toujours affichée (même "—" faute de N-1
 * disponible, jamais une flèche inventée). */
export function KpiCard({
  def,
  valeur,
  seuilVertScr = SEUIL_VERT_SCR_DEFAUT,
}: {
  def: KpiDefinition;
  valeur: KpiValeur;
  societe: string;
  seuilVertScr?: number;
}) {
  const couleur = couleurSeuil(def.id, valeur.valeur, seuilVertScr);
  const statut = statutKpi(def.id, valeur.valeur, seuilVertScr);
  const infobulleSeuil = statut ? texteInfobulleSeuil(def.id, couleur, seuilVertScr) : null;
  const IconeStatut = statut ? ICONE_STATUT[statut.couleur] : null;

  // Tendance : un seul exercice (2025) en base aujourd'hui -> valeur.variation
  // est toujours null. Le code lit quand même le champ (jamais une flèche
  // inventée si une vraie variation N-1 arrive un jour côté données).
  const aVariation = valeur.variation !== null && valeur.variation !== undefined;
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

  const valeurManquante = valeur.valeur === null || valeur.valeur === undefined || Number.isNaN(valeur.valeur);

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
      {valeurManquante ? (
        <p className="font-mono text-[1.75rem] font-bold mt-0.5 leading-tight text-text-tertiary">n/d</p>
      ) : (
        <p
          className={cn("font-mono text-[1.75rem] font-bold mt-0.5 leading-tight", COULEUR_VALEUR[couleur])}
          title={infobulleSeuil ?? undefined}
        >
          {formatValeur(valeur.valeur, def.unite, valeur.valeurBrute, valeur.uniteBrute)}
          {valeur.avertissement && <AvertissementKpi note={valeur.noteAvertissement} className="ml-2" />}
        </p>
      )}
      <div className="flex items-center gap-x-2 gap-y-1 flex-wrap mt-1.5 min-h-[1.4em]">
        {statut && IconeStatut && (
          <span
            className={cn(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium",
              PASTILLE_STATUT[statut.couleur]
            )}
            title={infobulleSeuil ?? undefined}
          >
            <IconeStatut className="w-3 h-3" aria-hidden="true" />
            {statut.libelle}
          </span>
        )}
        {!aVariation ? (
          <span
            className="inline-flex items-center gap-1 text-xs font-medium text-text-tertiary"
            title="Tendance indisponible : un seul exercice (2025)"
          >
            —<span className="sr-only">Tendance indisponible : un seul exercice (2025)</span>
          </span>
        ) : (
          IconeTendance && (
            <span className="inline-flex items-center gap-1" title={LIBELLE_TENDANCE[sentiment]}>
              <IconeTendance className={cn("w-3.5 h-3.5", COULEUR_TENDANCE[sentiment])} aria-hidden="true" />
              <span className={cn("text-xs font-medium font-mono", COULEUR_TENDANCE[sentiment])}>
                {formatVariation(valeur.variation!, valeur.variationUnit)}
              </span>
              <span className="text-[11px] text-text-tertiary">vs N-1</span>
              <span className="sr-only">{LIBELLE_TENDANCE[sentiment]}</span>
            </span>
          )
        )}
      </div>
      <p className="text-xs text-text-tertiary mt-2 leading-relaxed">{def.description}</p>
    </div>
  );
}
