/**
 * analyse-utils.ts — Port des fonctions de formatage/logique de
 * test_markdrop/sfcr_app/analyse/state.py (Reflex, commit c83d3ef).
 */

import { CATEGORIES, KPI_DEFINITIONS, KPI_IDS_PAR_CATEGORIE, KPI_PAR_ID, kpisSociete, type KpiDefinition } from "@/data/analyse-demo";

// Sens de "meilleure valeur" par KPI — utilisé UNIQUEMENT pour la mise en
// surbrillance meilleur/pire du tableau comparatif. Beaucoup de KPIs en
// montant absolu (SCR, fonds propres, primes...) dépendent avant tout de la
// taille de l'assureur : les qualifier de "meilleurs/pires" serait trompeur,
// donc ils restent "neutre" (affichés sans badge de classement). Seuls les
// ratios et le surplus (une mesure de marge de sécurité) sont classés.
export const SENS_KPI: Record<string, "higher" | "lower"> = {
  ratio_scr: "higher",
  ratio_mcr: "higher",
  surplus_capital: "higher",
  diversification: "lower", // stocké négatif : plus négatif = plus de bénéfice
  ratio_sp: "lower",
};

export const CATEGORIE_LABELS: Record<string, string> = {
  Tous: "Tous",
  E: "Capital",
  D: "Valorisation",
  C: "Risques",
  A: "Activité",
};

export function formatValeur(valeur: number, unite: string): string {
  if (unite === "%") {
    return `${formatNombre(valeur, 1)} %`;
  }
  return `${formatNombre(valeur, 2)} Md€`;
}

function formatNombre(valeur: number, decimales: number): string {
  const fixe = valeur.toFixed(decimales);
  const [entier, decimal] = fixe.split(".");
  const entierEspace = entier.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return decimal !== undefined ? `${entierEspace},${decimal}` : entierEspace;
}

export type CouleurSeuil = "success" | "warning" | "danger" | "neutre";

/** Couleur sémantique de la VALEUR principale — uniquement pour les 3 KPIs
 * avec un seuil réglementaire explicite (ratio_scr/mcr/sp). Les autres KPIs
 * utilisent une couleur neutre : leur "bon" niveau ne se juge pas dans
 * l'absolu. */
export function couleurSeuil(kpiId: string, valeur: number): CouleurSeuil {
  const def = KPI_PAR_ID[kpiId];
  if (!def || def.seuilReglementaire === null) return "neutre";
  if (kpiId === "ratio_sp") {
    // plus bas = meilleur
    if (valeur <= 95) return "success";
    if (valeur <= 105) return "warning";
    return "danger";
  }
  // ratio_scr / ratio_mcr : plus haut = meilleur
  if (valeur >= 150) return "success";
  if (valeur >= 100) return "warning";
  return "danger";
}

export function formatVariation(variation: number, unit: string): string {
  const signe = variation >= 0 ? "+" : "";
  return `${signe}${variation.toFixed(1)} ${unit}`;
}

export function kpiLabelCourt(def: KpiDefinition): string {
  return def.label
    .replace("SCR souscription ", "")
    .replace("SCR risque de ", "")
    .replace("SCR risque ", "");
}

export type CelluleKpi = {
  societe: string;
  valeurStr: string;
  rang: number;
  estMeilleur: boolean;
  estPire: boolean;
};

export type LigneKpi = {
  kpiId: string;
  kpiLabel: string;
  unite: string;
  cellules: CelluleKpi[];
  moyenneStr: string;
  medianeStr: string;
  seuilStr: string;
  aSeuil: boolean;
  // clé de tri interne : valeur (ou null) par société, dans le même ordre
  // que `societes`, utilisée par triLignes() ci-dessous.
  valeursParSociete: Record<string, number | null>;
};

/** Port de AnalyseState.tableau_comparatif (state.py, Reflex) —
 * {code_categorie: [LigneKPI]}. */
export function buildTableauComparatif(
  societes: string[],
  filtreCategorie: string
): Record<string, LigneKpi[]> {
  const resultat: Record<string, LigneKpi[]> = Object.fromEntries(CATEGORIES.map((c) => [c.code, []]));
  if (societes.length < 2) return resultat;

  const idsFiltres = new Set(
    filtreCategorie === "Tous" ? KPI_DEFINITIONS.map((k) => k.id) : KPI_IDS_PAR_CATEGORIE[filtreCategorie] ?? []
  );

  for (const kdef of KPI_DEFINITIONS) {
    if (!idsFiltres.has(kdef.id)) continue;
    const valeursParSociete: Record<string, number> = {};
    for (const soc of societes) {
      const brut = kpisSociete(soc)[kdef.id];
      if (brut !== undefined) valeursParSociete[soc] = brut.valeur;
    }
    if (Object.keys(valeursParSociete).length === 0) continue;

    const sens = SENS_KPI[kdef.id];
    const valeursTriees = sens
      ? Object.values(valeursParSociete).sort((a, b) => (sens === "higher" ? b - a : a - b))
      : [];

    const cellules: CelluleKpi[] = societes.map((soc) => {
      const v = valeursParSociete[soc];
      if (v === undefined) {
        return { societe: soc, valeurStr: "—", rang: 0, estMeilleur: false, estPire: false };
      }
      const rang = sens ? valeursTriees.indexOf(v) + 1 : 0;
      return {
        societe: soc,
        valeurStr: formatValeur(v, kdef.unite),
        rang,
        estMeilleur: !!sens && rang === 1,
        estPire: !!sens && rang === valeursTriees.length && valeursTriees.length > 1,
      };
    });

    const vals = Object.values(valeursParSociete);
    const moyenne = vals.reduce((a, b) => a + b, 0) / vals.length;
    const mediane = mediane_(vals);
    const seuil = kdef.seuilReglementaire;

    resultat[kdef.categorie].push({
      kpiId: kdef.id,
      kpiLabel: kdef.label,
      unite: kdef.unite,
      cellules,
      moyenneStr: formatValeur(moyenne, kdef.unite),
      medianeStr: formatValeur(mediane, kdef.unite),
      seuilStr: seuil !== null ? formatValeur(seuil, kdef.unite) : "",
      aSeuil: seuil !== null,
      valeursParSociete: Object.fromEntries(societes.map((s) => [s, valeursParSociete[s] ?? null])),
    });
  }
  return resultat;
}

function mediane_(vals: number[]): number {
  const triees = [...vals].sort((a, b) => a - b);
  const n = triees.length;
  const milieu = Math.floor(n / 2);
  return n % 2 === 0 ? (triees[milieu - 1] + triees[milieu]) / 2 : triees[milieu];
}

export type Alerte = { type: "critique" | "attention" | "conforme"; texte: string };

/** Port de AnalyseState.alertes (state.py, Reflex) — règles simples et
 * transparentes (pas de modèle statistique complexe) : variation négative
 * significative, écart notable à la moyenne du panel sur un KPI à seuil. */
export function buildAlertes(societes: string[]): Alerte[] {
  if (societes.length < 2) return [];
  const resultat: Alerte[] = [];

  for (const soc of societes) {
    const kpis = kpisSociete(soc);

    const ratioScr = kpis["ratio_scr"];
    if (ratioScr?.variation !== null && ratioScr?.variation !== undefined && ratioScr.variation <= -10) {
      resultat.push({
        type: "attention",
        texte: `${soc} : ratio SCR en baisse de ${Math.abs(ratioScr.variation).toFixed(0)} pts sur la période`,
      });
    }
    if (ratioScr && ratioScr.valeur < 100) {
      resultat.push({
        type: "critique",
        texte: `${soc} : ratio SCR sous le seuil réglementaire de 100 % (${ratioScr.valeur.toFixed(0)} %)`,
      });
    }

    const div = kpis["diversification"];
    if (div) {
      const valeursDiv = societes.map((s) => kpisSociete(s)["diversification"]?.valeur ?? 0);
      const moyenneDiv = valeursDiv.reduce((a, b) => a + b, 0) / valeursDiv.length;
      if (div.valeur > moyenneDiv + 5) {
        resultat.push({ type: "attention", texte: `${soc} : effet de diversification inférieur à la moyenne du panel` });
      }
    }

    const ratioSp = kpis["ratio_sp"];
    if (ratioSp && ratioSp.valeur <= 90) {
      resultat.push({ type: "conforme", texte: `${soc} : ratio S/P maîtrisé (${ratioSp.valeur.toFixed(0)} %)` });
    }
  }
  return resultat;
}

/** Trie les lignes d'une catégorie par la colonne (société) donnée. */
export function trierLignes(lignes: LigneKpi[], colonne: string, ascendant: boolean): LigneKpi[] {
  if (!colonne) return lignes;
  return [...lignes].sort((a, b) => {
    const va = a.valeursParSociete[colonne];
    const vb = b.valeursParSociete[colonne];
    if (va === null && vb === null) return 0;
    if (va === null) return ascendant ? -1 : 1;
    if (vb === null) return ascendant ? 1 : -1;
    return ascendant ? va - vb : vb - va;
  });
}
