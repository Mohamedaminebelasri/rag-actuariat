"use client";

import { ShieldCheck, Sparkles, PenLine } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatValeurBrute, type KpiExtrait } from "@/lib/donnees-extraites-utils";
import type { Correction } from "@/lib/use-corrections";

/**
 * Une ligne = un KPI réellement extrait pour une société.
 *
 * Cliquer ouvre le modal PDF (géré par le parent via onSelect).
 * Si une correction existe, elle est affichée avec un badge "Corrigé".
 */
export function KpiLigne({
  id,
  label,
  kpi,
  societe,
  onSelect,
  correction,
}: {
  id: string;
  label: string;
  kpi: KpiExtrait;
  societe: string;
  onSelect?: (kpiId: string) => void;
  correction?: Correction | null;
}) {
  const source =
    kpi.chapitreSource && kpi.pageSource
      ? `${kpi.chapitreSource}, p. ${kpi.pageSource}`
      : kpi.chapitreSource ?? (kpi.pageSource ? `p. ${kpi.pageSource}` : null);
  const lienActif = kpi.pageSource != null && onSelect;

  const valeurAffichee = correction
    ? correction.valeurCorrigee
    : formatValeurBrute(kpi.valeurBrute, kpi.uniteBrute, kpi.valeur, kpi.unite);

  const contenu = (
    <>
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-text-secondary leading-snug">{label}</p>
        <div className="flex items-center gap-1 flex-shrink-0">
          {correction && (
            <span
              title={`Corrigé manuellement${correction.commentaire ? ` : ${correction.commentaire}` : ""}`}
              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-medium text-accent bg-accent/10"
            >
              <PenLine className="w-2.5 h-2.5" />
              Corrigé
            </span>
          )}
          <span
            title={
              kpi.valide
                ? "Recoupé automatiquement (triple validation)"
                : "Extrait automatiquement, à vérifier manuellement"
            }
            className={cn(
              "inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium",
              kpi.valide ? "text-success bg-success-light" : "text-warning bg-warning-light"
            )}
          >
            {kpi.valide ? <ShieldCheck className="w-2.5 h-2.5" /> : <Sparkles className="w-2.5 h-2.5" />}
            {kpi.valide ? "Vérifié" : "À vérifier"}
          </span>
        </div>
      </div>
      <p className={cn("font-mono text-xl font-bold mt-1", correction ? "text-accent" : "text-text-primary")}>
        {valeurAffichee}
      </p>
      {correction && (
        <p className="text-[10px] text-text-tertiary mt-0.5 line-through">
          Avant : {formatValeurBrute(kpi.valeurBrute, kpi.uniteBrute, kpi.valeur, kpi.unite)}
        </p>
      )}
      {source && <p className="text-[11px] text-text-tertiary mt-1.5">Source : {source}</p>}
    </>
  );

  if (!lienActif) {
    return (
      <div className="text-left bg-surface border border-border rounded-[var(--radius-lg)] p-4 shadow-[var(--shadow-sm)]">
        {contenu}
      </div>
    );
  }

  return (
    <button
      onClick={() => onSelect(id)}
      title="Voir la source PDF"
      className="text-left w-full bg-surface border border-border rounded-[var(--radius-lg)] p-4 shadow-[var(--shadow-sm)] transition-all hover:shadow-[var(--shadow-md)] hover:-translate-y-px"
    >
      {contenu}
    </button>
  );
}
