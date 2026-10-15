"use client";

import type { CSSProperties } from "react";
import { cn } from "@/lib/utils";
import { KPI_DEFINITIONS, KPI_PAR_ID, kpisSociete } from "@/data/analyse-demo";
import { formatValeur, valeurDisponible } from "@/lib/analyse-utils";
import { AvertissementKpi } from "./avertissement-kpi";

// Hauteur de la zone de tracé (barres + étiquettes ; les noms sont en dessous).
const HAUTEUR = 260;
// Place réservée aux étiquettes : au-dessus des barres positives, en dessous
// des barres négatives (2 lignes de texte + écart).
const MARGE_ETIQUETTE = 36;
const ECART_ETIQUETTE = 4;
// Une valeur 0 réelle garde une fine barre visible.
const BARRE_MIN = 2;
const ESPACE_INSECABLE = "\u00A0";

/** Hachures des valeurs négatives : même motif que le graphique de
 * décomposition du SCR (scr-breakdown-chart.tsx), dans la couleur d'accent. */
function hachureNegative(): CSSProperties {
  return {
    backgroundImage:
      "repeating-linear-gradient(45deg, var(--accent) 0, var(--accent) 2px, transparent 2px, transparent 7px)",
  };
}

/** Étiquette de barre via formatValeur (format français + unité). Les
 * séparateurs de milliers deviennent insécables : seule l'espace avant
 * l'unité peut passer à la ligne dans une colonne étroite (mobile). */
function etiquetteValeur(valeur: number, unite: string): string {
  const texte = formatValeur(valeur, unite);
  const i = texte.lastIndexOf(" ");
  return i === -1 ? texte : `${texte.slice(0, i).replace(/ /g, ESPACE_INSECABLE)} ${texte.slice(i + 1)}`;
}

/** Port de bar_chart_comparatif() (charts.py, Reflex) — barres verticales
 * maison de part et d'autre d'une ligne zéro, avec ligne de seuil
 * réglementaire optionnelle. Une valeur ABSENTE (n/d) est écrite « n/d » sans
 * barre — jamais dessinée comme un 0. */
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

  // Échelle sur l'étendue réelle des valeurs DISPONIBLES (+ seuil éventuel),
  // zéro inclus : tout positif → zéro en bas ; tout négatif → zéro en haut,
  // les barres pendent ; mixte → zéro entre les deux. Étendue nulle → 1.
  const valeurs = donnees.flatMap((d) => (d.valeur === null ? [] : [d.valeur]));
  const min = Math.min(0, ...valeurs);
  const max = Math.max(0, ...valeurs, seuil ?? 0);
  const etendue = max - min > 0 ? max - min : 1;
  const toutNegatif = min < 0 && max === 0;
  const margeBas = min < 0 ? MARGE_ETIQUETTE : 0;
  const hauteurUtile = HAUTEUR - (toutNegatif ? 0 : MARGE_ETIQUETTE) - margeBas;
  // Ordonnée (px depuis le haut de la zone de tracé) d'une valeur. Barres,
  // ligne zéro et ligne de seuil utilisent toutes cette même fonction.
  const y = (v: number) => HAUTEUR - margeBas - ((v - min) / etendue) * hauteurUtile;
  const yZero = y(0);

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

      {/* Zone de tracé */}
      <div className="relative" style={{ height: HAUTEUR }}>
        <div className="absolute inset-0 flex gap-4">
          {donnees.map((d) => {
            if (d.valeur === null) {
              // n/d près de la ligne zéro, du côté où il y a de la place.
              return (
                <div key={d.societe} className="relative flex-1 min-w-0 h-full">
                  <span
                    className="absolute left-0 right-0 text-xs font-mono text-text-tertiary text-center"
                    style={
                      toutNegatif
                        ? { top: yZero + ECART_ETIQUETTE }
                        : { bottom: HAUTEUR - yZero + ECART_ETIQUETTE }
                    }
                    title="Valeur non extraite du rapport SFCR"
                  >
                    n/d
                  </span>
                </div>
              );
            }

            const auDessus = d.valeur > 0 || (d.valeur === 0 && !toutNegatif);
            const hauteurBarre = Math.max(BARRE_MIN, Math.abs(y(d.valeur) - yZero));
            const haut = auDessus ? yZero - hauteurBarre : yZero;
            return (
              <div key={d.societe} className="relative flex-1 min-w-0 h-full">
                <span
                  className="absolute left-0 right-0 text-xs font-mono text-text-primary text-center leading-tight"
                  style={
                    auDessus
                      ? { bottom: HAUTEUR - haut + ECART_ETIQUETTE }
                      : { top: haut + hauteurBarre + ECART_ETIQUETTE }
                  }
                >
                  {etiquetteValeur(d.valeur, unite)}
                  {d.avertissement && <AvertissementKpi note={d.note} className="ml-0.5" />}
                </span>
                <div
                  className={cn("absolute left-0 right-0 transition-all", auDessus ? "rounded-t-md bg-accent" : "rounded-b-md")}
                  style={{ top: haut, height: hauteurBarre, ...(auDessus ? {} : hachureNegative()) }}
                />
              </div>
            );
          })}
        </div>

        {/* Ligne zéro */}
        <div
          className="absolute left-0 right-0 border-t border-border pointer-events-none"
          style={{ top: yZero }}
          aria-hidden="true"
        />

        {seuil !== null && (
          <div
            className="absolute left-0 right-0 border-t border-dashed border-danger flex items-center pointer-events-none"
            style={{ top: y(seuil) }}
          >
            <span className="text-[10px] text-danger bg-surface px-1 -translate-y-1/2">Seuil réglementaire</span>
          </div>
        )}
      </div>

      {/* Noms des sociétés : rangée séparée, alignée sur les colonnes. */}
      <div className="flex gap-4 mt-2">
        {donnees.map((d) => (
          <span
            key={d.societe}
            className="flex-1 min-w-0 text-[11px] text-text-secondary font-body text-center leading-tight"
          >
            {d.societe}
          </span>
        ))}
      </div>
    </div>
  );
}
