"use client";

import { ShieldCheck, Sparkles, Calculator, UserCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { formatValeurReelle, type KpiExtrait } from "@/lib/donnees-extraites-utils";
import type { Correction } from "@/lib/use-corrections";
import type { ValidationHumaine } from "@/lib/use-validations-humaines";

/**
 * Une ligne = un KPI réellement extrait pour une société.
 *
 * Lien vers la source : l'onglet Documents ne sait aujourd'hui naviguer
 * que jusqu'à Groupama (seule société de son arborescence de démonstration
 * — voir sfcrTree dans documents/page.tsx). Pour ne pas proposer un lien
 * mort sur les 33 autres sociétés, la carte n'est cliquable QUE pour
 * Groupama ; ailleurs, chapitre/page restent affichés en texte seul.
 */
export function KpiLigne({
  id,
  label,
  kpi,
  societe,
  onSelect,
  correction,
  validationHumaine,
}: {
  id: string;
  label: string;
  kpi: KpiExtrait;
  societe: string;
  onSelect?: (id: string) => void;
  correction?: Correction | null;
  validationHumaine?: ValidationHumaine | null;
}) {
  const router = useRouter();
  const source =
    kpi.chapitreSource && kpi.pageSource
      ? `${kpi.chapitreSource}, p. ${kpi.pageSource}`
      : kpi.chapitreSource ?? (kpi.pageSource ? `p. ${kpi.pageSource}` : null);
  const lienActif = societe === "Groupama";

  const contenu = (
    <>
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-text-secondary leading-snug">{label}</p>
        <div className="flex items-center gap-1 flex-shrink-0">
          {validationHumaine ? (
            <span
              title={`Traité par ${validationHumaine.par} le ${new Date(validationHumaine.date).toLocaleDateString("fr-FR")}`}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium text-emerald-700 bg-emerald-50"
            >
              <UserCheck className="w-2.5 h-2.5" />
              Traité
            </span>
          ) : (
            <>
              {kpi.estCompose && kpi.composants && kpi.composants.length > 0 && (
                <span
                  title="Valeur calculée à partir de sous-lignes QRT"
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium text-blue-700 bg-blue-50"
                >
                  <Calculator className="w-2.5 h-2.5" />
                  Calculé
                </span>
              )}
              <span
                title={kpi.valide ? "Recoupé automatiquement (triple validation)" : "Extrait par IA, non recoupé"}
                className={cn(
                  "inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium",
                  kpi.valide ? "text-success bg-success-light" : "text-warning bg-warning-light"
                )}
              >
                {kpi.valide ? <ShieldCheck className="w-2.5 h-2.5" /> : <Sparkles className="w-2.5 h-2.5" />}
                {kpi.valide ? "Vérifié" : "Extrait"}
              </span>
            </>
          )}
        </div>
      </div>
      <p className="font-mono text-xl font-bold text-text-primary mt-1">
        {formatValeurReelle(kpi.valeur, kpi.unite)}
      </p>
      {source && <p className="text-[11px] text-text-tertiary mt-1.5">Source : {source}</p>}
      {correction && (
        <p className="text-[11px] text-blue-600 mt-1">
          Corrigé : {correction.valeurCorrigee}{correction.commentaire ? ` — ${correction.commentaire}` : ""}
        </p>
      )}
    </>
  );

  const handleClick = onSelect
    ? () => onSelect(id)
    : lienActif
      ? () => router.push(`/documents?company=${encodeURIComponent(societe)}&kpi=${encodeURIComponent(id)}`)
      : undefined;

  if (!handleClick) {
    return (
      <div className="text-left bg-surface border border-border rounded-[var(--radius-lg)] p-4 shadow-[var(--shadow-sm)]">
        {contenu}
      </div>
    );
  }

  return (
    <button
      onClick={handleClick}
      title={onSelect ? "Voir le détail et la source PDF" : "Voir la source dans les Annexes QRT"}
      className="text-left w-full bg-surface border border-border rounded-[var(--radius-lg)] p-4 shadow-[var(--shadow-sm)] transition-all hover:shadow-[var(--shadow-md)] hover:-translate-y-px"
    >
      {contenu}
    </button>
  );
}
