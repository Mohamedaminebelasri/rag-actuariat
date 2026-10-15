/**
 * analyse-utils.ts — Port des fonctions de formatage/logique de
 * test_markdrop/sfcr_app/analyse/state.py (Reflex, commit c83d3ef).
 */

import {
  CATEGORIES,
  DEMO_SFCR,
  KPI_DEFINITIONS,
  KPI_IDS_PAR_CATEGORIE,
  kpisSociete,
  toutesLesSocietes,
  type KpiDefinition,
  type ModeleCapital,
  type Perimetre,
  type TypeSociete,
} from "@/data/analyse-demo";
import { SEUIL_LEGAL, SEUIL_VERT_SCR_DEFAUT } from "@/lib/seuils-config";
import { DONNEES_EXTRAITES } from "@/lib/donnees-extraites-utils";

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
    const raw = uniteBrute ?? unite;
    const u = raw === "euros bruts" || raw === "euro brut" ? "€" : raw;
    if (u === "K€" || u === "€") return `${formatNombre(valeurBrute, 0)} ${u}`;
    return `${formatNombre(valeurBrute, 1)} ${u}`;
  }
  if (unite === "M€") {
    return `${formatNombre(valeur, 1)} M€`;
  }
  if (unite === "Md€") {
    return `${formatNombre(valeur, 2)} Md€`;
  }
  // Unité inconnue : jamais de « Md€ » par défaut, on affiche l'unité réelle.
  return `${formatNombre(valeur, 1)} ${unite}`;
}

function formatNombre(valeur: number, decimales: number): string {
  const fixe = valeur.toFixed(decimales);
  const [entier, decimal] = fixe.split(".");
  const entierEspace = entier.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return decimal !== undefined ? `${entierEspace},${decimal}` : entierEspace;
}

export type CouleurSeuil = "success" | "warning" | "danger" | "neutre";

/** Couleur sémantique (feu tricolore) — UNIQUEMENT ratio_scr et ratio_mcr,
 * les 2 seuls KPIs avec un plancher légal Solvabilité II explicite. Tous
 * les autres KPIs (montants, parts, ratios calculés) restent neutres : un
 * montant n'est ni bon ni mauvais dans l'absolu, ça dépend de la taille.
 *
 * - ratio_scr : rouge < 100 % (légal) ; orange [100, seuilVert[ ;
 *   vert ≥ seuilVert (conventionnel, 200 % par défaut).
 * - ratio_mcr : 2 zones seulement, rouge < 100 %, vert ≥ 100 % (pas de zone
 *   orange).
 */
export function couleurSeuil(
  kpiId: string,
  valeur: number | null | undefined,
  seuilVertScr: number = SEUIL_VERT_SCR_DEFAUT
): CouleurSeuil {
  if (valeur === null || valeur === undefined || Number.isNaN(valeur)) return "neutre";
  if (kpiId === "ratio_scr") {
    if (valeur < SEUIL_LEGAL) return "danger";
    if (valeur < seuilVertScr) return "warning";
    return "success";
  }
  if (kpiId === "ratio_mcr") {
    return valeur < SEUIL_LEGAL ? "danger" : "success";
  }
  return "neutre";
}

/** Phrase d'info-bulle adaptée à la zone affichée (point 4 de la mission). */
export function texteInfobulleSeuil(kpiId: string, couleur: CouleurSeuil, seuilVertScr: number): string {
  if (kpiId === "ratio_mcr") {
    return couleur === "danger"
      ? "Rouge : sous 100 % = exigence légale non couverte (Solvabilité II, minimum de capital requis)."
      : "Vert : 100 % ou plus = minimum de capital requis couvert (Solvabilité II).";
  }
  // ratio_scr
  if (couleur === "danger") return "Rouge : sous 100 % = exigence légale non couverte (Solvabilité II).";
  if (couleur === "warning")
    return `Orange : entre 100 % et ${formatNombre(seuilVertScr, 0)} % — couvre l'exigence légale, sous le repère de marché.`;
  return `Vert : ${formatNombre(seuilVertScr, 0)} % ou plus = seuil conventionnel (repère de marché), pas une règle légale.`;
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

/** Valeur d'un KPI, ou `null` si elle est ABSENTE : clé manquante dans
 * `kpis`, valeur null/undefined ou non finie (NaN, ±Infinity). Un zéro réel
 * reste 0. À utiliser pour tout ce qui est dessiné — jamais `?? 0`, qui
 * confond « n/d » et « égal à zéro ». */
export function valeurDisponible(
  kpis: Record<string, { valeur: number | null | undefined } | undefined>,
  kpiId: string
): number | null {
  const v = kpis[kpiId]?.valeur;
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export type CelluleKpi = {
  societe: string;
  valeurStr: string;
  rang: number;
  estMeilleur: boolean;
  estPire: boolean;
  /** Valeur « non comparable » (champ avertissement) : affichée avec un
   * marqueur, exclue du rang, du meilleur/pire, de la moyenne et de la médiane. */
  avertissement: boolean;
  noteAvertissement: string | null;
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
  /** Exclusions de la moyenne/médiane (valeurs non comparables, sociétés déjà
   * consolidées, solo/groupe non mélangés) : texte d'infobulle, null si aucune. */
  noteAgregat: string | null;
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
    // Sociétés dont la valeur porte un avertissement (base non comparable) :
    // affichées, mais exclues du rang, du meilleur/pire, de la moyenne et de
    // la médiane.
    const nonComparables = new Set<string>();
    for (const soc of societes) {
      const brut = kpisSociete(soc)[kdef.id];
      if (brut !== undefined) {
        valeursParSociete[soc] = brut.valeur;
        if (brut.avertissement) nonComparables.add(soc);
      }
    }
    if (Object.keys(valeursParSociete).length === 0) continue;

    const valeursComparables = Object.entries(valeursParSociete)
      .filter(([soc]) => !nonComparables.has(soc))
      .map(([, v]) => v);

    const sens = SENS_KPI[kdef.id];
    const valeursTriees = sens
      ? [...valeursComparables].sort((a, b) => (sens === "higher" ? b - a : a - b))
      : [];

    const cellules: CelluleKpi[] = societes.map((soc) => {
      const v = valeursParSociete[soc];
      if (v === undefined) {
        return {
          societe: soc,
          valeurStr: "—",
          rang: 0,
          estMeilleur: false,
          estPire: false,
          avertissement: false,
          noteAvertissement: null,
        };
      }
      const avertissement = nonComparables.has(soc);
      const classable = !!sens && !avertissement;
      const rang = classable ? valeursTriees.indexOf(v) + 1 : 0;
      return {
        societe: soc,
        valeurStr: formatValeur(v, kdef.unite),
        rang,
        estMeilleur: classable && rang === 1,
        estPire: classable && rang === valeursTriees.length && valeursTriees.length > 1,
        avertissement,
        noteAvertissement: avertissement ? (kpisSociete(soc)[kdef.id]?.noteAvertissement ?? null) : null,
      };
    });

    // Agrégats (moyenne/médiane du panel) : hors valeurs non comparables, hors
    // sociétés dont le groupe consolidant est aussi dans la sélection (double
    // comptage), et sans mélanger solo et groupe (on garde le périmètre le plus
    // représenté, solo en cas d'égalité). « — » s'il ne reste rien.
    let socsAgregat = Object.keys(valeursParSociete).filter((s) => !nonComparables.has(s));
    const consolidees = socsAgregat.filter((s) => {
      const parent = DEMO_SFCR[s]?.consolideDans;
      return !!parent && parent !== s && valeursParSociete[parent] !== undefined && societes.includes(parent);
    });
    socsAgregat = socsAgregat.filter((s) => !consolidees.includes(s));
    const parPerimetre = (p: "solo" | "groupe") => socsAgregat.filter((s) => (DEMO_SFCR[s]?.perimetre ?? "solo") === p);
    const solo = parPerimetre("solo");
    const groupe = parPerimetre("groupe");
    let autrePerimetre: { n: number; nature: string } | null = null;
    if (solo.length > 0 && groupe.length > 0) {
      const garderGroupe = groupe.length > solo.length;
      const exclues = garderGroupe ? solo : groupe;
      autrePerimetre = { n: exclues.length, nature: garderGroupe ? "solo" : "de groupe" };
      socsAgregat = garderGroupe ? groupe : solo;
    }
    const valeursAgregat = socsAgregat.map((s) => valeursParSociete[s]);
    const pluriel = (n: number, mot: string, motPluriel = `${mot}s`) => `${n} ${n > 1 ? motPluriel : mot}`;
    const exclusions: string[] = [];
    if (nonComparables.size > 0) {
      exclusions.push(`${pluriel(nonComparables.size, "valeur")} non comparable${nonComparables.size > 1 ? "s" : ""}`);
    }
    if (consolidees.length > 0) {
      exclusions.push(
        `${pluriel(consolidees.length, "société")} déjà consolidée${consolidees.length > 1 ? "s" : ""} dans un groupe sélectionné`
      );
    }
    if (autrePerimetre) {
      exclusions.push(
        `${pluriel(autrePerimetre.n, "valeur")} ${autrePerimetre.nature} (solo et groupe ne se mélangent pas)`
      );
    }
    const noteAgregat = exclusions.length > 0 ? `hors ${exclusions.join(", ")}` : null;
    const aComparables = valeursAgregat.length > 0;
    const moyenne = aComparables ? valeursAgregat.reduce((a, b) => a + b, 0) / valeursAgregat.length : 0;
    const mediane = aComparables ? mediane_(valeursAgregat) : 0;
    const seuil = kdef.seuilReglementaire;

    resultat[kdef.categorie].push({
      kpiId: kdef.id,
      kpiLabel: kdef.label,
      unite: kdef.unite,
      cellules,
      moyenneStr: aComparables ? formatValeur(moyenne, kdef.unite) : "—",
      medianeStr: aComparables ? formatValeur(mediane, kdef.unite) : "—",
      seuilStr: seuil !== null ? formatValeur(seuil, kdef.unite) : "",
      aSeuil: seuil !== null,
      noteAgregat,
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

export type Alerte = { type: "critique" | "attention" | "info" | "conforme"; texte: string };

// Ordre d'affichage : critique, puis attention, puis info (conforme en dernier).
const ORDRE_ALERTES: Record<Alerte["type"], number> = { critique: 0, attention: 1, info: 2, conforme: 3 };

/** Part maximale de fonds propres de niveaux 2 + 3 dans la couverture du SCR
 * (plafond d'éligibilité de 50 %) ; seuil de déclenchement légèrement en
 * dessous pour absorber les arrondis des états publiés. */
const SEUIL_NIVEAUX_2_3_PCT = 49.5;
/** S/P non-vie au-delà duquel la marge pour couvrir les frais est faible. */
const SEUIL_SP_NONVIE_PCT = 85;

function nombreFr(valeur: number, decimales = 1): string {
  return valeur.toLocaleString("fr-FR", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
}

/** Règles d'alerte de l'Analyse comparative (validées, Décision 157), par
 * société de la sélection, à partir des KPI et des indicateurs normalisés
 * (indicateursParSociete). Aucune alerte sur une valeur qui porte un
 * avertissement (base non comparable). Pas de règle sur le ratio MCR (collé à
 * une borne réglementaire pour la plupart des solos) ni sur une évolution
 * (pas d'exercice N-1 aujourd'hui). */
export function buildAlertes(societes: string[]): Alerte[] {
  if (societes.length < 2) return [];
  const resultat: Alerte[] = [];

  for (const soc of societes) {
    const kpis = kpisSociete(soc);
    const ind = DONNEES_EXTRAITES.indicateursParSociete[soc];
    const fiable = (...ids: string[]) => ids.every((id) => !kpis[id]?.avertissement);
    const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

    // Seuil légal : ratio SCR publié sous 100 %.
    const ratioScr = valeurDisponible(kpis, "ratio_scr");
    if (ratioScr !== null && fiable("ratio_scr") && ratioScr < SEUIL_LEGAL) {
      resultat.push({
        type: "critique",
        texte: `${soc} : ratio SCR sous le seuil réglementaire de ${SEUIL_LEGAL} % (${ratioScr.toFixed(0)} %)`,
      });
    }

    // R1 : sans correction pour volatilité ni mesure transitoire, sous 100 %.
    const sansMesures = num(ind?.ratio_scr_sans_mesures_lt_pct);
    if (sansMesures !== null && fiable("ratio_scr") && sansMesures < SEUIL_LEGAL) {
      resultat.push({
        type: "critique",
        texte: `${soc} : sans correction pour volatilité ni mesure transitoire, le ratio SCR tombe à ${nombreFr(sansMesures)} % (sous ${SEUIL_LEGAL} %)`,
      });
    }

    // R2 : ratio SCR très dépendant des mesures de long terme.
    const impactLt = num(ind?.impact_mesures_lt_pts);
    if (impactLt !== null && impactLt <= -30 && fiable("ratio_scr")) {
      resultat.push({
        type: "attention",
        texte:
          `${soc} : le ratio SCR dépend fortement des mesures de long terme (${nombreFr(impactLt)} pts)` +
          (sansMesures !== null ? ` ; sans elles il serait de ${nombreFr(sansMesures)} %` : ""),
      });
    }

    // R3 : mesure transitoire en cours (attention si l'effet est important).
    const impactTransitoires = num(ind?.impact_transitoires_pts);
    if (ind?.mesure_transitoire === true && impactTransitoires !== null && fiable("ratio_scr")) {
      if (impactTransitoires <= -15) {
        resultat.push({
          type: "attention",
          texte: `${soc} : mesure transitoire en cours, qui s'éteint jusqu'en 2032 : le ratio publié baissera mécaniquement (${nombreFr(impactTransitoires)} pts)`,
        });
      } else {
        resultat.push({
          type: "info",
          texte: `${soc} : mesure transitoire en cours (effet faible : ${nombreFr(impactTransitoires)} pts)`,
        });
      }
    }

    // R4 : fonds propres de niveaux 2 + 3 au plafond d'éligibilité (50 % du SCR).
    const t2 = valeurDisponible(kpis, "fonds_propres_t2");
    const t3 = valeurDisponible(kpis, "fonds_propres_t3");
    const scrTotal = valeurDisponible(kpis, "scr_total");
    if (
      t2 !== null &&
      t3 !== null &&
      scrTotal !== null &&
      scrTotal > 0 &&
      fiable("fonds_propres_t2", "fonds_propres_t3", "scr_total")
    ) {
      const part = ((t2 + t3) / scrTotal) * 100;
      if (part >= SEUIL_NIVEAUX_2_3_PCT) {
        resultat.push({
          type: "attention",
          texte: `${soc} : les fonds propres de niveau 2 et 3 représentent ${nombreFr(part)} % du SCR, au plafond d'éligibilité de 50 %`,
        });
      }
    }

    // R5 : sinistres / primes très élevé, sociétés non-vie seulement.
    const sp = num(ind?.sp_nonvie_pct);
    if (
      sp !== null &&
      sp > SEUIL_SP_NONVIE_PCT &&
      DEMO_SFCR[soc]?.type === "Non-vie" &&
      fiable("charge_sinistres", "primes_acquises_brutes")
    ) {
      resultat.push({
        type: "attention",
        texte: `${soc} : sinistres / primes de ${nombreFr(sp)} % en non-vie, peu de marge pour couvrir les frais`,
      });
    }

    // R7 : MCR collé au plancher absolu → ratio MCR non significatif.
    if (ind?.position_mcr === "plancher_absolu" && fiable("mcr", "ratio_mcr")) {
      resultat.push({
        type: "info",
        texte: `${soc} : MCR collé au plancher absolu, le ratio MCR n'est pas significatif`,
      });
    }
  }
  // Tri stable : l'ordre de la sélection est conservé à niveau égal.
  return resultat
    .map((a, i) => ({ a, i }))
    .sort((x, y) => ORDRE_ALERTES[x.a.type] - ORDRE_ALERTES[y.a.type] || x.i - y.i)
    .map(({ a }) => a);
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
export function statutKpi(
  kpiId: string,
  valeur: number | null | undefined,
  seuilVertScr: number = SEUIL_VERT_SCR_DEFAUT
): StatutKpi | null {
  const couleur = couleurSeuil(kpiId, valeur, seuilVertScr);
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

export type FiltresSocietes = {
  type: TypeSociete | "Tous";
  modele: ModeleCapital | "Tous";
  perimetre: Perimetre | "Tous";
};
export const FILTRES_VIDES: FiltresSocietes = { type: "Tous", modele: "Tous", perimetre: "Tous" };

export function societesFiltrees(filtres: FiltresSocietes): string[] {
  return toutesLesSocietes().filter((nom) => {
    const info = DEMO_SFCR[nom];
    return (
      (filtres.type === "Tous" || info.type === filtres.type) &&
      (filtres.modele === "Tous" || info.modele === filtres.modele) &&
      (filtres.perimetre === "Tous" || info.perimetre === filtres.perimetre)
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
  if (new Set(infos.map((i) => i.perimetre)).size > 1) {
    messages.push("Entités solo et groupes consolidés mélangés : montants, diversification et MCR ne sont pas de même nature.");
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
