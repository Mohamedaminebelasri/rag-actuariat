/**
 * analyse-utils.ts — Port des fonctions de formatage/logique de
 * test_markdrop/sfcr_app/analyse/state.py (Reflex, commit c83d3ef).
 */

import {
  CATEGORIES,
  DEMO_SFCR,
  KPI_DEFINITIONS,
  KPI_IDS_PAR_CATEGORIE,
  KPI_PAR_ID,
  kpisSociete,
  toutesLesSocietes,
  type KpiDefinition,
  type ModeleCapital,
  type TypeSociete,
} from "@/data/analyse-demo";

// Sens de "meilleure valeur" par KPI — utilisé UNIQUEMENT pour la mise en
// surbrillance meilleur/pire du tableau comparatif. Beaucoup de KPIs en
// montant absolu (SCR, fonds propres, primes...) dépendent avant tout de la
// taille de l'assureur : les qualifier de "meilleurs/pires" serait trompeur,
// donc ils restent "neutre" (affichés sans badge de classement). Seuls les
// ratios et le surplus (une mesure de marge de sécurité) sont classés.
export const SENS_KPI: Record<string, "higher" | "lower"> = {
  ratio_scr: "higher",
  ratio_mcr: "higher",
  scr_diversification: "lower", // stocké négatif : plus négatif = plus de bénéfice
};

export const CATEGORIE_LABELS: Record<string, string> = {
  Tous: "Tous",
  E: "Capital",
  D: "Valorisation",
  C: "Risques",
  A: "Activité",
};

export function formatValeur(
  valeur: number,
  unite: string,
  valeurBrute?: number | null,
  uniteBrute?: string | null,
): string {
  if (unite === "%") {
    return `${formatNombre(valeur, 1)} %`;
  }
  // Afficher la valeur brute (telle que dans le PDF) quand elle est disponible
  if (valeurBrute != null) {
    const u = uniteBrute ?? unite;
    if (u === "K€" || u === "€") return `${formatNombre(valeurBrute, 0)} ${u}`;
    return `${formatNombre(valeurBrute, 1)} ${u}`;
  }
  if (unite === "M€") {
    return `${formatNombre(valeur, 1)} M€`;
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
  // ratio_scr / ratio_mcr : plus haut = meilleur
  if (valeur >= 150) return "success";
  if (valeur >= 100) return "warning";
  return "danger";
}

export function formatVariation(variation: number, unit: string): string {
  const signe = variation >= 0 ? "+" : "";
  return `${signe}${variation.toFixed(unit === "Md€" || unit === "M€" ? 1 : 1)} ${unit}`;
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

    const div = kpis["scr_diversification"];
    if (div) {
      const valeursDiv = societes.map((s) => kpisSociete(s)["scr_diversification"]?.valeur ?? 0);
      const moyenneDiv = valeursDiv.reduce((a, b) => a + b, 0) / valeursDiv.length;
      if (div.valeur > moyenneDiv + 5) {
        resultat.push({ type: "attention", texte: `${soc} : effet de diversification inférieur à la moyenne du panel` });
      }
    }

    const ratioMcr = kpis["ratio_mcr"];
    if (ratioMcr && ratioMcr.valeur >= 200) {
      resultat.push({ type: "conforme", texte: `${soc} : ratio MCR solide (${ratioMcr.valeur.toFixed(0)} %)` });
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

// ───────────────────────── Idée 1 : statuts (feux) et tendance ─────────────────────────

export type StatutKpi = { couleur: Exclude<CouleurSeuil, "neutre">; libelle: string };

/** Statut « feu tricolore » — uniquement pour les KPIs qui ont un seuil
 * (ratio SCR, ratio MCR). Seuils réglementaires Solvabilité II. */
export function statutKpi(kpiId: string, valeur: number): StatutKpi | null {
  const couleur = couleurSeuil(kpiId, valeur);
  if (couleur === "neutre") return null;
  const libelles = { success: "Solide", warning: "Vigilance", danger: "Sous le seuil" };
  return { couleur, libelle: libelles[couleur] };
}

export type SentimentVariation = "amelioration" | "degradation" | "stable" | "neutre";

/** La flèche suit le SIGNE de la variation, mais sa COULEUR dépend du sens
 * « bon/mauvais » du KPI : un ratio S/P qui monte est une dégradation. Les
 * KPIs sans sens clair (montants liés à la taille) restent neutres. */
export function sentimentVariation(kpiId: string, variation: number, unite: string): SentimentVariation {
  const sens = SENS_KPI[kpiId];
  if (!sens) return "neutre";
  const seuilStable = unite === "pts" ? 0.5 : 0.01;
  if (Math.abs(variation) < seuilStable) return "stable";
  const bon = sens === "higher" ? variation > 0 : variation < 0;
  return bon ? "amelioration" : "degradation";
}

// ───────────────────────── Idée 3 : filtres et comparabilité ─────────────────────────

export type FiltresSocietes = { type: TypeSociete | "Tous"; modele: ModeleCapital | "Tous" };
export const FILTRES_VIDES: FiltresSocietes = { type: "Tous", modele: "Tous" };

export function societesFiltrees(filtres: FiltresSocietes): string[] {
  return toutesLesSocietes().filter((nom) => {
    const info = DEMO_SFCR[nom];
    return (
      (filtres.type === "Tous" || info.type === filtres.type) &&
      (filtres.modele === "Tous" || info.modele === filtres.modele)
    );
  });
}

/** Message de prudence quand on compare des sociétés peu comparables. */
export function avertissementComparabilite(societes: string[]): string | null {
  const infos = societes.map((s) => DEMO_SFCR[s]).filter(Boolean);
  const modeles = new Set(infos.map((i) => i.modele));
  const types = new Set(infos.map((i) => i.type));
  const messages: string[] = [];
  if (modeles.size > 1) {
    messages.push(
      "Ces assureurs n'utilisent pas le même modèle de capital (formule standard et modèle interne) : leurs SCR et leurs ratios se comparent avec prudence."
    );
  }
  if (types.has("Vie") && types.has("Non-vie")) {
    messages.push("Activités vie et non-vie mélangées : le ratio S/P et le profil de risque sont peu comparables.");
  }
  return messages.length > 0 ? messages.join(" ") : null;
}

// ───────────────────────── Idée 2 : classement et distribution ─────────────────────────

export const KPIS_CLASSABLES = KPI_DEFINITIONS.filter((k) => SENS_KPI[k.id] !== undefined);

export type PointDistribution = { societe: string; valeur: number };

export type Classement = {
  rang: number;
  total: number;
  /** Part des autres sociétés du groupe qui font moins bien (0-100). */
  percentile: number;
  mediane: number;
  points: PointDistribution[];
};

/** Rang de `societe` sur `kpiId` parmi `groupe` (la société y est toujours incluse). */
export function classement(kpiId: string, societe: string, groupe: string[]): Classement | null {
  const sens = SENS_KPI[kpiId];
  if (!sens) return null;
  const noms = groupe.includes(societe) ? groupe : [...groupe, societe];
  const points: PointDistribution[] = [];
  for (const nom of noms) {
    const v = kpisSociete(nom)[kpiId]?.valeur;
    if (v !== undefined) points.push({ societe: nom, valeur: v });
  }
  if (!points.some((p) => p.societe === societe)) return null;

  const triees = [...points].sort((a, b) => (sens === "higher" ? b.valeur - a.valeur : a.valeur - b.valeur));
  const rang = triees.findIndex((p) => p.societe === societe) + 1;
  const total = points.length;
  const percentile = total > 1 ? Math.round(((total - rang) / (total - 1)) * 100) : 100;
  return { rang, total, percentile, mediane: mediane_(points.map((p) => p.valeur)), points };
}
