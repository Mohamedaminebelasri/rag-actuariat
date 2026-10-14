"use client";

import type { CSSProperties } from "react";
import type { KpiValeur } from "@/data/analyse-demo";
import { AvertissementKpi } from "./avertissement-kpi";

// Palette neutre (même palette que le radar comparatif, radar-chart.tsx) :
// aucun rouge/orange/vert, ces couleurs sont réservées au feu tricolore des
// seuils SCR/MCR. Les montants de décomposition n'ont pas de sens de risque.
const PALETTE_MODULES = ["#2563eb", "#0891b2", "#7c3aed", "#475569", "#60a5fa", "#a78bfa"];

// Couleur des hachures (diversification + ajustement calculé) : un ton neutre
// existant (token Ivory --text-secondary), jamais une couleur de seuil.
const COULEUR_HACHURE = "var(--text-secondary)";

function hachureStyle(): CSSProperties {
  return {
    backgroundImage: `repeating-linear-gradient(45deg, ${COULEUR_HACHURE} 0, ${COULEUR_HACHURE} 2px, transparent 2px, transparent 7px)`,
  };
}

function formatMontant(valeur: number): string {
  const abs = Math.abs(valeur).toLocaleString("fr-FR", { maximumFractionDigits: 0 });
  return valeur < 0 ? `−${abs} M€` : `${abs} M€`;
}

// Les 5 modules de souscription/marché/contrepartie dont la complétude
// conditionne le calcul de l'ajustement (diversification et opérationnel
// sont comptés séparément, cf. mission).
const MODULES_5: { id: string; label: string }[] = [
  { id: "scr_souscription_nonvie", label: "SCR non-vie" },
  { id: "scr_souscription_sante", label: "SCR santé" },
  { id: "scr_souscription_vie", label: "SCR vie" },
  { id: "scr_marche", label: "SCR marché" },
  { id: "scr_contrepartie", label: "SCR contrepartie" },
];

// KPIs qui entrent dans le calcul de la ligne « ajustements » (5 modules +
// diversification + opérationnel + total). Si l'un d'eux porte un
// avertissement (base non comparable), la différence n'a plus de sens.
const IDS_AJUSTEMENT = [...MODULES_5.map((m) => m.id), "scr_diversification", "scr_operationnel", "scr_total"];

/** Marqueur « valeur non comparable » (champ avertissement du KPI). */
type Avert = { note: string | null };

type Ligne =
  | { kind: "nd"; label: string }
  | { kind: "module"; label: string; valeur: number; couleur: string; avert?: Avert }
  | { kind: "hachure"; label: string; valeur: number; infobulle?: string; avert?: Avert }
  | { kind: "total"; label: string; valeur: number; avert?: Avert }
  | { kind: "non-calcule"; label: string };

/** Port de scr_decomposition (state.py) + graphique_decomposition_scr()
 * (charts.py, Reflex) — barres horizontales SVG maison (pas de recharts).
 * kpis vient de donnees-extraites.json (via analyse-demo.ts) : un module non
 * extrait est simplement ABSENT de l'objet (jamais stocké à 0 ou null). */
export function ScrBreakdownChart({ kpis }: { kpis: Record<string, KpiValeur> }) {
  if (Object.keys(kpis).length === 0) return null;

  const manquants = MODULES_5.filter((m) => kpis[m.id] === undefined);
  const decompositionIncomplete = manquants.length > 0;

  const avertDe = (id: string): Avert | undefined =>
    kpis[id]?.avertissement ? { note: kpis[id].noteAvertissement ?? null } : undefined;
  const ajustementIncoherent = IDS_AJUSTEMENT.some((id) => kpis[id]?.avertissement);

  // MODULES_5 est déjà dans l'ordre d'affichage voulu : non-vie, santé, vie,
  // marché, contrepartie.
  const lignes: Ligne[] = [];
  MODULES_5.forEach((m, i) => {
    const v = kpis[m.id]?.valeur;
    if (v === undefined) lignes.push({ kind: "nd", label: m.label });
    else if (v !== 0)
      lignes.push({ kind: "module", label: m.label, valeur: v, couleur: PALETTE_MODULES[i], avert: avertDe(m.id) });
  });

  // Diversification : montant négatif en M€ (jamais un pourcentage).
  const diversification = kpis["scr_diversification"]?.valeur;
  if (diversification === undefined) lignes.push({ kind: "nd", label: "Diversification" });
  else if (diversification !== 0)
    lignes.push({ kind: "hachure", label: "Diversification", valeur: diversification, avert: avertDe("scr_diversification") });

  const operationnel = kpis["scr_operationnel"]?.valeur;
  if (operationnel === undefined) lignes.push({ kind: "nd", label: "SCR opérationnel" });
  else if (operationnel !== 0)
    lignes.push({
      kind: "module",
      label: "SCR opérationnel",
      valeur: operationnel,
      couleur: PALETTE_MODULES[5],
      avert: avertDe("scr_operationnel"),
    });

  const scrTotal = kpis["scr_total"]?.valeur;
  if (scrTotal === undefined) lignes.push({ kind: "nd", label: "SCR total" });
  else lignes.push({ kind: "total", label: "SCR total", valeur: scrTotal, avert: avertDe("scr_total") });

  // Ajustement calculé : seulement si les 5 modules + diversification +
  // opérationnel + total sont TOUS extraits, et si l'écart est significatif
  // (≥ 1 % du SCR total) — sinon il n'apporte rien et peut induire en erreur.
  // Jamais calculé si un des KPIs utilisés porte un avertissement : la
  // différence mélangerait des bases incohérentes (ex. modules avant
  // diversification, total après) ; une ligne grise le dit à la place.
  if (ajustementIncoherent) {
    lignes.push({ kind: "non-calcule", label: "Ajustement non calculé : modules sur base modèle interne" });
  } else if (!decompositionIncomplete && diversification !== undefined && operationnel !== undefined && scrTotal !== undefined) {
    const sommeModules = MODULES_5.reduce((acc, m) => acc + (kpis[m.id]?.valeur ?? 0), 0);
    const ajustement = scrTotal - (sommeModules + diversification + operationnel);
    if (Math.abs(ajustement) >= 0.01 * Math.abs(scrTotal)) {
      lignes.push({
        kind: "hachure",
        label: "Absorption des pertes et autres ajustements (calculé)",
        valeur: ajustement,
        infobulle:
          "Valeur calculée par différence, non extraite du PDF (inclut l'absorption des pertes par les provisions techniques et les impôts différés)",
      });
    }
  }

  const maxAbs = Math.max(
    ...lignes
      .filter((l) => l.kind !== "nd" && l.kind !== "non-calcule")
      .map((l) => Math.abs((l as { valeur: number }).valeur)),
    0.01
  );

  return (
    <div className="bg-surface border border-border rounded-[var(--radius-lg)] p-5 w-full">
      {decompositionIncomplete && (
        <p className="text-xs text-text-tertiary mb-3">
          Décomposition incomplète : module(s) non extrait(s) : {manquants.map((m) => m.label).join(", ")}
        </p>
      )}
      <div className="flex flex-col gap-3">
        {lignes.map((l, i) => {
          if (l.kind === "nd") {
            return (
              <div key={l.label} className="flex items-center gap-3">
                <span className="w-44 flex-shrink-0 text-xs text-text-secondary font-body text-right">{l.label}</span>
                <div className="flex-1 h-6 flex items-center">
                  <span className="text-xs text-text-tertiary italic">n/d</span>
                </div>
                <span className="w-28 flex-shrink-0 text-xs font-mono text-text-tertiary text-right">n/d</span>
              </div>
            );
          }

          if (l.kind === "non-calcule") {
            return (
              <p key={l.label} className="text-xs italic text-text-tertiary sm:pl-[11.75rem]">
                {l.label}
              </p>
            );
          }

          const negatif = l.valeur < 0;
          const pct = (Math.abs(l.valeur) / maxAbs) * 100;
          const estHachure = l.kind === "hachure";
          const estTotal = l.kind === "total";
          const labelClass = estTotal ? "font-bold text-text-primary" : "text-text-secondary";
          const valeurClass = estTotal ? "font-bold text-text-primary" : "text-text-primary";

          return (
            <div key={`${l.label}-${i}`} className="flex items-center gap-3">
              <span className={`w-44 flex-shrink-0 text-xs font-body text-right ${labelClass}`} title={"infobulle" in l ? l.infobulle : undefined}>
                {l.label}
              </span>
              <div className="flex-1 h-6 bg-surface-secondary rounded-md relative overflow-hidden">
                <div
                  className="h-full rounded-md transition-all"
                  style={{
                    width: `${pct}%`,
                    marginLeft: negatif ? "auto" : undefined,
                    background: estHachure ? undefined : estTotal ? "var(--text-primary)" : (l as { couleur?: string }).couleur,
                    ...(estHachure ? hachureStyle() : {}),
                  }}
                  title={"infobulle" in l ? l.infobulle : undefined}
                />
              </div>
              <span className={`w-28 flex-shrink-0 flex items-center justify-end gap-1 text-xs font-mono ${valeurClass}`}>
                {l.avert && <AvertissementKpi note={l.avert.note} />}
                {formatMontant(l.valeur)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
