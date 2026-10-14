"use client";

import { KPI_DEFINITIONS, KPI_PAR_ID, kpisSociete } from "@/data/analyse-demo";
import { formatValeur, valeurDisponible } from "@/lib/analyse-utils";
import { AvertissementKpi } from "./avertissement-kpi";

const HAUTEUR = 260;

/** Étiquette de barre via formatValeur (format français + unité). Les
 * séparateurs de milliers deviennent insécables : seule l'espace avant
 * l'unité peut passer à la ligne dans une colonne étroite (mobile). */
function etiquetteValeur(valeur: number, unite: string): string {
  const texte = formatValeur(valeur, unite);
  const i = texte.lastIndexOf(" ");
  return i === -1 ? texte : `${texte.slice(0, i).replace(/ /g, " ")} ${texte.slice(i + 1)}`;
}

/** Port de bar_chart_comparatif() (charts.py, Reflex) — barres verticales
 * SVG maison avec ligne de seuil réglementaire optionnelle. Une valeur
 * ABSENTE (n/d) est écrite « n/d » sans barre — jamais dessinée comme un 0. */
export function ComparisonBarChart({
  societesComparees,
  kpiId,
  onChangeKpi,
}: {
  societesComparees: string[];
  kpiId: string;
  onChangeKpi: (id: string) => void;
}) {
  const def = KPI_PAR_ID[kpiId];
  const unite = def?.unite ?? "M€";
  // valeur === null : absente (clé manquante ou non finie). Un 0 réel reste 0.
  // avertissement : valeur sur une base non comparable (marqueur, la barre reste dessinée).
  const donnees = societesComparees.map((soc) => {
    const kpis = kpisSociete(soc);
    return {
      societe: soc,
      valeur: valeurDisponible(kpis, kpiId),
      avertissement: !!kpis[kpiId]?.avertissement,
      note: kpis[kpiId]?.noteAvertissement ?? null,
    };
  });
  const seuil = def?.seuilReglementaire ?? null;
  // Échelle : plus grande amplitude parmi les valeurs DISPONIBLES et le seuil
  // éventuel (les barres sont dessinées sur |valeur|). Sans valeur ni seuil, le
  // max reste 0 → échelle 1, donc aucune division par 0 ni NaN.
  const amplitudes = donnees.flatMap((d) => (d.valeur === null ? [] : [Math.abs(d.valeur)]));
  const maxValeur = Math.max(0, ...amplitudes, seuil ?? 0);
  const echelle = maxValeur > 0 ? maxValeur : 1;

  return (
    <div className="bg-surface border border-border rounded-[var(--radius-lg)] p-5 w-full">
      <div className="flex items-center gap-3 flex-wrap mb-4">
        <span className="font-body text-base font-medium text-text-primary">Comparaison par KPI</span>
        <span className="flex-1" />
        <select
          value={kpiId}
          onChange={(e) => onChangeKpi(e.target.value)}
          className="text-sm border border-border rounded-[var(--radius-md)] px-2.5 py-1.5 bg-surface text-text-primary font-body"
        >
          {KPI_DEFINITIONS.map((k) => (
            <option key={k.id} value={k.id}>
              {k.label}
            </option>
          ))}
        </select>
      </div>

      <div className="relative" style={{ height: HAUTEUR }}>
        {seuil !== null && (
          <div
            className="absolute left-0 right-0 border-t border-dashed border-danger flex items-center"
            style={{ bottom: `${(seuil / echelle) * 100}%` }}
          >
            <span className="text-[10px] text-danger bg-surface px-1 -translate-y-1/2">Seuil réglementaire</span>
          </div>
        )}
        <div className="flex items-end gap-4 h-full w-full">
          {donnees.map((d) => (
            <div key={d.societe} className="flex-1 min-w-0 flex flex-col items-center gap-2 h-full justify-end">
              {d.valeur === null ? (
                <span
                  className="text-xs font-mono text-text-tertiary text-center"
                  title="Valeur non extraite du rapport SFCR"
                >
                  n/d
                </span>
              ) : (
                <>
                  <span className="text-xs font-mono text-text-primary text-center leading-tight">
                    {etiquetteValeur(d.valeur, unite)}
                    {d.avertissement && <AvertissementKpi note={d.note} className="ml-0.5" />}
                  </span>
                  <div
                    className="w-full rounded-t-md bg-accent transition-all"
                    style={{ height: `${Math.max(2, (Math.abs(d.valeur) / echelle) * (HAUTEUR - 40))}px` }}
                  />
                </>
              )}
              <span className="text-[11px] text-text-secondary font-body text-center leading-tight">{d.societe}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
