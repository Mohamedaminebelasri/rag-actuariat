"use client";

import type { KpiValeur } from "@/data/analyse-demo";

const COULEURS_SCR_MODULE: Record<string, string> = {
  "SCR non-vie": "#2563eb",
  "SCR vie": "#7c3aed",
  "SCR marché": "#0891b2",
  "SCR contrepartie": "#d97706",
  "SCR opérationnel": "#65a30d",
  Diversification: "#dc2626",
};

/** Port de scr_decomposition (state.py) + graphique_decomposition_scr()
 * (charts.py, Reflex) — barres horizontales SVG maison (pas de recharts). */
export function ScrBreakdownChart({ kpis }: { kpis: Record<string, KpiValeur> }) {
  if (Object.keys(kpis).length === 0) return null;

  const composantes: [string, string][] = [
    ["SCR non-vie", "scr_souscription_nonvie"],
    ["SCR vie", "scr_souscription_vie"],
    ["SCR marché", "scr_marche"],
    ["SCR contrepartie", "scr_contrepartie"],
    ["SCR opérationnel", "scr_operationnel"],
  ];
  const barres = composantes
    .filter(([, id]) => kpis[id] !== undefined)
    .map(([label, id]) => ({ module: label, valeur: kpis[id].valeur }));

  if (kpis["diversification"]) {
    const divPct = kpis["diversification"].valeur;
    const sommeBrute = barres.reduce((acc, b) => acc + b.valeur, 0);
    barres.push({ module: "Diversification", valeur: Math.round((sommeBrute * divPct) / 100 * 100) / 100 });
  }

  if (barres.length === 0) return null;

  const maxAbs = Math.max(...barres.map((b) => Math.abs(b.valeur)), 0.01);
  const largeurZone = 100; // % de la largeur disponible pour la barre

  return (
    <div className="bg-surface border border-border rounded-[var(--radius-lg)] p-5 w-full">
      <div className="flex flex-col gap-3">
        {barres.map((b) => {
          const pct = (Math.abs(b.valeur) / maxAbs) * largeurZone;
          const negatif = b.valeur < 0;
          const couleur = COULEURS_SCR_MODULE[b.module] ?? "#2563eb";
          return (
            <div key={b.module} className="flex items-center gap-3">
              <span className="w-36 flex-shrink-0 text-xs text-text-secondary font-body text-right">{b.module}</span>
              <div className="flex-1 h-6 bg-surface-secondary rounded-md relative overflow-hidden">
                <div
                  className="h-full rounded-md transition-all"
                  style={{
                    width: `${pct}%`,
                    background: couleur,
                    marginLeft: negatif ? "auto" : undefined,
                  }}
                />
              </div>
              <span className="w-20 flex-shrink-0 text-xs font-mono text-text-primary">{b.valeur.toFixed(2)} Md€</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
