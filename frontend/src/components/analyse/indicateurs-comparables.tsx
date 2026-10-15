"use client";

import type { KpiValeur } from "@/data/analyse-demo";
import { DONNEES_EXTRAITES } from "@/lib/donnees-extraites-utils";

type Indicateur = {
  cle: string;
  label: string;
  /** Texte affiché, ou null quand l'indicateur n'existe pas pour la société. */
  valeur: string | null;
  /** Précision sous la valeur (ex. ratio publié). */
  precision?: string;
  /** Valeur littérale (pas un nombre) : police plus petite pour ne pas déborder. */
  texte?: boolean;
};

const POSITION_MCR: Record<string, string> = {
  plancher_absolu: "Plancher absolu",
  plancher_25: "Plancher (25 % du SCR)",
  entre_25_45: "Dans le corridor (25–45 %)",
  plafond_45: "Plafond (45 % du SCR)",
};

function nombre(valeur: number, decimales: number): string {
  return valeur.toLocaleString("fr-FR", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
}

/** Ratios normalisés d'une société (champ indicateursParSociete du JSON),
 * comparables entre sociétés : valeurs neutres, jamais de feu tricolore. Un
 * indicateur absent (ex. S/P non-vie pour la vie) n'est pas affiché. */
export function IndicateursComparables({
  societe,
  kpis,
}: {
  societe: string;
  kpis: Record<string, KpiValeur>;
}) {
  const ind = DONNEES_EXTRAITES.indicateursParSociete[societe];
  if (!ind) return null;
  const definitions = DONNEES_EXTRAITES.definitionsIndicateurs;
  const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

  const sansMesures = num(ind.ratio_scr_sans_mesures_lt_pct);
  const ratioPublie = kpis["ratio_scr"]?.valeur;
  const impactVa = num(ind.impact_va_pts);
  const impactTransitoires = num(ind.impact_transitoires_pts);
  const marge = num(ind.marge_risque_sur_be_pct);
  const sp = num(ind.sp_nonvie_pct);
  const position = typeof ind.position_mcr === "string" ? ind.position_mcr : null;

  const indicateurs: Indicateur[] = [
    {
      cle: "ratio_scr_sans_mesures_lt_pct",
      label: "Ratio SCR sans mesures long terme",
      valeur: sansMesures === null ? null : `${nombre(sansMesures, 1)} %`,
      precision:
        sansMesures !== null && typeof ratioPublie === "number" && Number.isFinite(ratioPublie)
          ? `Ratio publié : ${nombre(ratioPublie, 1)} %`
          : undefined,
    },
    {
      cle: "impact_va_pts",
      label: "Impact de la correction pour volatilité",
      valeur: impactVa === null ? null : `${nombre(impactVa, 1)} pts`,
    },
    {
      cle: "impact_transitoires_pts",
      label: "Impact des mesures transitoires",
      valeur: impactTransitoires === null ? null : `${nombre(impactTransitoires, 1)} pts`,
    },
    {
      cle: "marge_risque_sur_be_pct",
      label: "Marge de risque / best estimate",
      valeur: marge === null ? null : `${nombre(marge, 2)} %`,
    },
    {
      cle: "sp_nonvie_pct",
      label: "Ratio S/P non-vie",
      valeur: sp === null ? null : `${nombre(sp, 1)} %`,
    },
    {
      cle: "position_mcr",
      label: "Position du MCR dans le corridor",
      valeur: position === null ? null : (POSITION_MCR[position] ?? position.replace(/_/g, " ")),
      texte: true,
    },
  ];
  const affiches = indicateurs.filter((i) => i.valeur !== null);
  if (affiches.length === 0) return null;

  return (
    <section aria-label="Indicateurs comparables" className="flex flex-col gap-3 w-full items-start mb-8">
      <h3 className="font-heading italic text-lg text-text-primary">Indicateurs comparables</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full">
        {affiches.map((i) => (
          <div
            key={i.cle}
            className="h-full flex flex-col bg-surface border border-border rounded-[var(--radius-lg)] p-[1.1em] shadow-[var(--shadow-sm)]"
          >
            <p className="text-sm font-medium text-text-secondary">{i.label}</p>
            <p
              className={`font-mono font-bold mt-1 leading-tight text-text-primary ${i.texte ? "text-base" : "text-[1.5rem]"}`}
            >
              {i.valeur}
            </p>
            {i.precision && <p className="text-xs font-mono text-text-secondary mt-1">{i.precision}</p>}
            {definitions[i.cle] && (
              <p className="text-xs text-text-tertiary mt-2 leading-relaxed">{definitions[i.cle]}</p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
