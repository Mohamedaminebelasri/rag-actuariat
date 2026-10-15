"use client";

import type { CSSProperties } from "react";
import { cn } from "@/lib/utils";
import { KPI_DEFINITIONS, KPI_PAR_ID, kpisSociete } from "@/data/analyse-demo";
import { formatValeur, valeurDisponible } from "@/lib/analyse-utils";
import { AvertissementKpi } from "./avertissement-kpi";
import { CarteAgrandissable } from "./carte-agrandissable";
import { compatibiliteKpi, kpiApplicable, texteNotesCompat } from "@/lib/comparabilite";

// Hauteur de la zone de tracé (barres + étiquettes ; les noms sont en dessous).
const HAUTEUR_NORMALE = 260;
const HAUTEUR_AGRANDIE = 480;
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
function etiquetteValeur(valeur: number, unite: string, decimales?: number): string {
  const texte = formatValeur(valeur, unite, null, null, decimales);
  const i = texte.lastIndexOf(" ");
  return i === -1 ? texte : `${texte.slice(0, i).replace(/ /g, ESPACE_INSECABLE)} ${texte.slice(i + 1)}`;
}

/** Port de bar_chart_comparatif() (charts.py, Reflex) — barres verticales
 * maison de part et d'autre d'une ligne zéro, avec ligne de seuil
 * réglementaire optionnelle. Une valeur ABSENTE (n/d) est écrite « n/d » sans
 * barre — jamais dessinée comme un 0. */
function CorpsBarres({
  societesComparees,
  kpiId,
  agrandi,
}: {
  societesComparees: string[];
  kpiId: string;
  agrandi: boolean;
}) {
  const HAUTEUR = agrandi ? HAUTEUR_AGRANDIE : HAUTEUR_NORMALE;
  const def = KPI_PAR_ID[kpiId];
  const unite = def?.unite ?? "M€";
  // valeur === null : absente (clé manquante ou non finie). Un 0 réel reste 0.
  // avertissement : valeur sur une base non comparable (marqueur, la barre reste dessinée).
  const donnees = societesComparees.map((soc) => {
    const kpis = kpisSociete(soc);
    // Décision 158 — KPI sans objet pour l'activité (ex. S/P non-vie d'un
    // assureur vie) : écrit « sans objet », sans barre, hors échelle.
    const applicable = kpiApplicable(kpiId, soc);
    return {
      societe: soc,
      valeur: applicable ? valeurDisponible(kpis, kpiId) : null,
      sansObjet: !applicable && kpis[kpiId] !== undefined,
      avertissement: !!kpis[kpiId]?.avertissement,
      note: kpis[kpiId]?.noteAvertissement ?? null,
    };
  });
  const seuil = def?.seuilReglementaire ?? null;
  // Compatibilité du KPI choisi pour la sélection (note neutre : N / R).
  const compat = compatibiliteKpi(kpiId, societesComparees);
  const noteCompat = texteNotesCompat(compat.notes);

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
    <>
      {(compat.verdict === "N" || compat.verdict === "R") && noteCompat && (
        <p role="note" className="mb-3 whitespace-pre-line text-xs leading-relaxed text-text-secondary">
          <span className="font-medium text-text-primary">
            {compat.verdict === "N" ? "Non comparable pour cette sélection" : "À comparer avec réserve"}
          </span>
          {" — "}
          {noteCompat}
        </p>
      )}

      {/* Zone de tracé */}
      <div className="relative" style={{ height: HAUTEUR }}>
        <div className="absolute inset-0 flex gap-4">
          {donnees.map((d) => {
            if (d.valeur === null) {
              // n/d près de la ligne zéro, du côté où il y a de la place.
              return (
                <div key={d.societe} className="relative flex-1 min-w-0 h-full">
                  <span
                    className={cn("absolute left-0 right-0 font-mono text-text-tertiary text-center", agrandi ? "text-sm" : "text-xs")}
                    style={
                      toutNegatif
                        ? { top: yZero + ECART_ETIQUETTE }
                        : { bottom: HAUTEUR - yZero + ECART_ETIQUETTE }
                    }
                    title={
                      d.sansObjet
                        ? "Indicateur sans objet pour l'activité de cette société"
                        : "Valeur non extraite du rapport SFCR"
                    }
                  >
                    {d.sansObjet ? "sans objet" : "n/d"}
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
                  className={cn("absolute left-0 right-0 font-mono text-text-primary text-center leading-tight", agrandi ? "text-sm" : "text-xs")}
                  style={
                    auDessus
                      ? { bottom: HAUTEUR - haut + ECART_ETIQUETTE }
                      : { top: haut + hauteurBarre + ECART_ETIQUETTE }
                  }
                >
                  {etiquetteValeur(d.valeur, unite, def?.decimales)}
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
            className={cn("flex-1 min-w-0 text-text-secondary font-body text-center leading-tight", agrandi ? "text-sm" : "text-[11px]")}
          >
            {d.societe}
          </span>
        ))}
      </div>
    </>
  );
}

/** Comparaison d'un KPI entre les sociétés sélectionnées : carte agrandissable
 * avec son sélecteur de KPI (le KPI choisi vit dans le parent : conservé à
 * l'agrandissement). */
export function ComparisonBarChart({
  societesComparees,
  kpiId,
  onChangeKpi,
}: {
  societesComparees: string[];
  kpiId: string;
  onChangeKpi: (id: string) => void;
}) {
  return (
    <CarteAgrandissable
      titre="Comparaison par KPI"
      nom="la comparaison par KPI"
      actions={
        <select
          value={kpiId}
          onChange={(e) => onChangeKpi(e.target.value)}
          aria-label="KPI comparé"
          className="text-sm border border-border rounded-[var(--radius-md)] px-2.5 py-1.5 bg-surface text-text-primary font-body max-w-full"
        >
          {KPI_DEFINITIONS.map((k) => (
            <option key={k.id} value={k.id}>
              {k.label}
            </option>
          ))}
        </select>
      }
    >
      {({ agrandi }) => <CorpsBarres societesComparees={societesComparees} kpiId={kpiId} agrandi={agrandi} />}
    </CarteAgrandissable>
  );
}