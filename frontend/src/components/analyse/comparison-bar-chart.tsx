"use client";

import { KPI_DEFINITIONS, KPI_PAR_ID, kpisSociete } from "@/data/analyse-demo";

const HAUTEUR = 260;

/** Port de bar_chart_comparatif() (charts.py, Reflex) — barres verticales
 * SVG maison avec ligne de seuil réglementaire optionnelle. */
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
  const donnees = societesComparees.map((soc) => ({ societe: soc, valeur: kpisSociete(soc)[kpiId]?.valeur ?? 0 }));
  const seuil = def?.seuilReglementaire ?? null;
  const maxValeur = Math.max(...donnees.map((d) => d.valeur), seuil ?? 0, 0.01);

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
            style={{ bottom: `${(seuil / maxValeur) * 100}%` }}
          >
            <span className="text-[10px] text-danger bg-surface px-1 -translate-y-1/2">Seuil réglementaire</span>
          </div>
        )}
        <div className="flex items-end gap-4 h-full w-full">
          {donnees.map((d) => (
            <div key={d.societe} className="flex-1 flex flex-col items-center gap-2 h-full justify-end">
              <span className="text-xs font-mono text-text-primary">
                {d.valeur.toFixed(2)}
                {def?.unite === "%" ? " %" : ""}
              </span>
              <div
                className="w-full rounded-t-md bg-accent transition-all"
                style={{ height: `${Math.max(2, (Math.abs(d.valeur) / maxValeur) * (HAUTEUR - 40))}px` }}
              />
              <span className="text-[11px] text-text-secondary font-body text-center leading-tight">{d.societe}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
