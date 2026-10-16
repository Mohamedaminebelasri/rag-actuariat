/**
 * csv-export.ts — Export CSV de l'Analyse (individuelle et comparative).
 *
 * Fichier pensé pour Excel en français : séparateur « ; », virgule décimale,
 * UTF-8 avec BOM (accents), fins de ligne CRLF, champs entre guillemets si
 * besoin. Règles :
 * - valeur ABSENTE = cellule vide (jamais 0) ; un 0 réel reste 0 ;
 * - valeur avec avertissement (base non comparable) identifiée dans le fichier ;
 * - mêmes chiffres, mêmes libellés et mêmes sociétés que l'écran ;
 * - pas de colonnes « variation » (aucun exercice N-1) ni « confiance ».
 */

import {
  CATEGORIES,
  KPI_DEFINITIONS,
  KPI_IDS_PAR_CATEGORIE,
  KPI_PAR_ID,
  kpisSociete,
} from "@/data/analyse-demo";
import { valeurDisponible } from "@/lib/analyse-utils";
import { compatibiliteKpi, texteNotesCompat } from "@/lib/comparabilite";

const SEPARATEUR = ";";
const FIN_DE_LIGNE = "\r\n";
const BOM = "﻿";

/** Champ texte : entre guillemets s'il contient « ; », « " » ou un saut de ligne ;
 * neutralise les débuts de formule (= + - @) que Excel exécuterait. */
function champ(texte: string): string {
  let t = texte.replace(/\s*\n+\s*/g, " | ");
  if (/^[=+\-@\t]/.test(t)) t = `'${t}`;
  return /[;"\r\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t;
}

/** Nombre en notation française (virgule décimale, 3 décimales au plus, sans
 * bruit de virgule flottante). Absent → cellule vide. */
function nombre(v: number | null): string {
  if (v === null) return "";
  return String(Math.round(v * 1000) / 1000).replace(".", ",");
}

function ligne(cellules: string[]): string {
  return cellules.join(SEPARATEUR);
}

function nomFichier(base: string): string {
  return `${base.replace(/[\\/:*?"<>|]/g, "").replace(/\s+/g, "_")}.csv`;
}

function telecharger(lignes: string[], nom: string) {
  const blob = new Blob([BOM + lignes.join(FIN_DE_LIGNE) + FIN_DE_LIGNE], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nom;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const LIBELLE_CATEGORIE = Object.fromEntries(CATEGORIES.map((c) => [c.code, c.label]));

/** Export d'une société : un indicateur par ligne, tous les indicateurs (un
 * indicateur absent = valeur vide). */
export function exporterCsvIndividuel(societe: string) {
  const kpis = kpisSociete(societe);
  const lignes = [
    ligne(
      [
        "Société",
        "Catégorie",
        "Code",
        "Indicateur",
        "Valeur",
        "Unité",
        "Valeur brute du rapport",
        "Unité du rapport",
        "Page source",
        "Avertissement",
        "Note d'avertissement",
      ].map(champ)
    ),
  ];
  for (const def of KPI_DEFINITIONS) {
    const kpi = kpis[def.id];
    const valeur = valeurDisponible(kpis, def.id);
    const brute = kpi && valeur !== null ? (kpi.valeurBrute ?? null) : null;
    lignes.push(
      ligne([
        champ(societe),
        champ(LIBELLE_CATEGORIE[def.categorie] ?? def.categorie),
        champ(def.code),
        champ(kpi?.libelle ?? def.label),
        nombre(valeur),
        champ(def.unite),
        brute !== null ? nombre(brute) : "",
        brute !== null && kpi?.uniteBrute ? champ(kpi.uniteBrute) : "",
        kpi && valeur !== null && kpi.pageSource ? String(kpi.pageSource) : "",
        kpi?.avertissement ? "Valeur non comparable" : "",
        kpi?.avertissement ? champ(kpi.noteAvertissement ?? "") : "",
      ])
    );
  }
  telecharger(lignes, nomFichier(`analyse_${societe}`));
}

/** Export de la comparaison : les sociétés AFFICHÉES (dans l'ordre de la
 * sélection) en colonnes, les indicateurs du tableau en lignes (catégorie
 * filtrée le cas échéant ; ligne omise si aucune société n'a de valeur, comme
 * à l'écran). */
export function exporterCsvComparatif(societes: string[], filtreCategorie = "Tous") {
  if (societes.length < 2) return;
  const ids = new Set(
    filtreCategorie === "Tous" ? KPI_DEFINITIONS.map((k) => k.id) : (KPI_IDS_PAR_CATEGORIE[filtreCategorie] ?? [])
  );
  const lignes = [
    ligne(
      [
        "Catégorie",
        "Code",
        "Indicateur",
        "Unité",
        ...societes,
        "Valeurs non comparables (société)",
        "Notes d'avertissement",
        "Comparabilité de la sélection",
        "Note de comparabilité",
      ].map(champ)
    ),
  ];
  for (const def of KPI_DEFINITIONS) {
    if (!ids.has(def.id) || !KPI_PAR_ID[def.id]) continue;
    const valeurs = societes.map((s) => valeurDisponible(kpisSociete(s), def.id));
    if (valeurs.every((v) => v === null)) continue;
    const compat = compatibiliteKpi(def.id, societes);
    const cellules = societes.map((s, i) => {
      // Zéro « sans objet » (ex. module non-vie d'une société vie) : même mention qu'à l'écran.
      if (compat.sansObjet && valeurs[i] === 0) return "sans objet";
      return nombre(valeurs[i]);
    });
    const avertis = societes.filter((s) => kpisSociete(s)[def.id]?.avertissement);
    const verdict =
      compat.verdict === "N" ? "non comparable" : compat.verdict === "R" ? "à comparer avec réserve" : "comparable";
    lignes.push(
      ligne([
        champ(LIBELLE_CATEGORIE[def.categorie] ?? def.categorie),
        champ(def.code),
        champ(def.label),
        champ(def.unite),
        ...cellules,
        champ(avertis.join(", ")),
        champ(
          avertis
            .map((s) => `${s} : ${kpisSociete(s)[def.id]?.noteAvertissement ?? "valeur non comparable"}`)
            .join(" | ")
        ),
        champ(verdict),
        champ(texteNotesCompat(compat.notes)),
      ])
    );
  }
  telecharger(lignes, nomFichier("analyse_comparative"));
}
