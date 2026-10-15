/**
 * position-pairs.ts — « Position parmi les pairs » (Analyse individuelle).
 *
 * Rang d'une société dans SON groupe de pairs (activité · modèle de capital ·
 * périmètre, champ `groupePairs` du JSON), jamais parmi toutes les sociétés.
 * Classement seulement si le groupe compte au moins SEUIL_PAIRS sociétés et
 * si au moins SEUIL_PAIRS d'entre elles ont une valeur comparable : une
 * valeur absente n'est pas 0, une valeur avec avertissement n'est jamais
 * classée. Trois familles d'indicateurs :
 * - classés (« mieux / moins bien ») : sens higher, lower ou zero (plus
 *   proche de 0 = mieux) ;
 * - neutres : position affichée (rang par valeur décroissante) sans jugement ;
 * - jamais classés (ratio MCR, MCR en % du SCR, montants) : absents de la liste.
 */
import { DEMO_SFCR, KPI_PAR_ID, kpisSociete } from "@/data/analyse-demo";
import { DONNEES_EXTRAITES, type GroupePairs } from "@/lib/donnees-extraites-utils";
import { groupePairsDe, kpiApplicable } from "@/lib/comparabilite";

/** Taille minimale d'un groupe de pairs pour classer (Décision 157). */
export const SEUIL_PAIRS = 5;

export type SensPosition = "higher" | "lower" | "zero" | "neutre";

export type IndicateurPosition = {
  /** id de KPI (kpisParSociete) ou clé d'indicateur (indicateursParSociete). */
  id: string;
  label: string;
  unite: "%" | "pts";
  decimales?: number;
  sens: SensPosition;
  source: "kpi" | "indicateur";
  /** Indicateur : KPIs dont un avertissement rend la valeur non comparable. */
  kpisSources?: string[];
  /** Seuil réglementaire dessiné en rouge (ratios SCR). */
  seuil?: number;
  /** Précision de lecture affichée sous la position. */
  note?: string;
  /** Suite de phrase quand la société n'a pas de valeur (après son nom). */
  raisonAbsence?: string;
};

const MODULES = ["scr_marche", "scr_contrepartie", "scr_souscription_vie", "scr_souscription_sante", "scr_souscription_nonvie"];

const labelKpi = (id: string) => KPI_PAR_ID[id]?.label ?? id;

export const INDICATEURS_POSITION: IndicateurPosition[] = [
  // Classés
  {
    id: "ratio_scr_sans_mesures_lt",
    label: labelKpi("ratio_scr_sans_mesures_lt"),
    unite: "%",
    sens: "higher",
    source: "kpi",
    seuil: 100,
    note: "Base homogène (sans correction pour volatilité ni mesure transitoire) : indicateur à privilégier.",
  },
  {
    id: "ratio_scr",
    label: "Ratio SCR publié",
    unite: "%",
    sens: "higher",
    source: "kpi",
    seuil: 100,
    note:
      "Le ratio publié est amélioré par la correction pour volatilité et les mesures transitoires, que toutes les sociétés n'appliquent pas : préférer le ratio sans mesures de long terme.",
  },
  {
    id: "impact_mesures_lt_pts",
    label: "Effet cumulé des mesures de long terme",
    unite: "pts",
    sens: "zero",
    source: "indicateur",
    kpisSources: ["ratio_scr"],
    note: "Plus proche de 0 = ratio SCR moins dépendant de la correction pour volatilité et des mesures transitoires.",
  },
  {
    id: "part_t1_non_restreint_pct",
    label: "Part des fonds propres de niveau 1 non restreint",
    unite: "%",
    sens: "higher",
    source: "indicateur",
    kpisSources: ["fonds_propres_t1_nr", "fonds_propres_eligibles"],
  },
  {
    id: "sp_nonvie",
    label: labelKpi("sp_nonvie"),
    unite: "%",
    sens: "lower",
    source: "kpi",
    note: "Sinistres rapportés aux primes, activités non-vie seulement.",
  },
  // Neutres : position sans « mieux / moins bien »
  {
    id: "diversification_sur_modules_pct",
    label: "Diversification / somme des modules",
    unite: "%",
    sens: "neutre",
    source: "indicateur",
    kpisSources: ["scr_diversification", ...MODULES],
    note: "Dépend surtout du nombre de risques portés : ni bon ni mauvais en soi.",
  },
  {
    id: "scr_sur_primes_plus_be_pct",
    label: "SCR / (primes + best estimate)",
    unite: "%",
    decimales: 2,
    sens: "neutre",
    source: "indicateur",
    kpisSources: ["scr_total", "primes_acquises_brutes", "best_estimate"],
    note: "Intensité en capital de l'activité : ni bonne ni mauvaise en soi.",
  },
  {
    id: "marge_risque_sur_be",
    label: labelKpi("marge_risque_sur_be"),
    unite: "%",
    decimales: 2,
    sens: "neutre",
    source: "kpi",
  },
  { id: "impact_va", label: labelKpi("impact_va"), unite: "pts", sens: "neutre", source: "kpi" },
  {
    id: "impact_transitoires",
    label: labelKpi("impact_transitoires"),
    unite: "pts",
    sens: "neutre",
    source: "kpi",
    raisonAbsence: "n'applique pas de mesure transitoire : pas de valeur à situer.",
  },
];

export const INDICATEUR_POSITION_PAR_ID: Record<string, IndicateurPosition> = Object.fromEntries(
  INDICATEURS_POSITION.map((i) => [i.id, i])
);

/** Indicateurs proposés pour une société (le S/P non-vie seulement pour les
 * activités où il a un sens). */
export function indicateursPositionPour(societe: string): IndicateurPosition[] {
  return INDICATEURS_POSITION.filter((i) => i.source !== "kpi" || kpiApplicable(i.id, societe));
}

type ValeurSociete = { valeur: number | null; avertissement: boolean };

/** Valeur d'un indicateur pour une société : null si absente ou non finie
 * (jamais 0 par défaut) ; avertissement si la valeur ou un KPI source en porte un. */
export function valeurIndicateur(ind: IndicateurPosition, societe: string): ValeurSociete {
  const kpis = kpisSociete(societe);
  const fini = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
  if (ind.source === "kpi") {
    if (!kpiApplicable(ind.id, societe)) return { valeur: null, avertissement: false };
    const k = kpis[ind.id];
    return { valeur: fini(k?.valeur), avertissement: !!k?.avertissement };
  }
  const v = fini(DONNEES_EXTRAITES.indicateursParSociete[societe]?.[ind.id]);
  return { valeur: v, avertissement: (ind.kpisSources ?? []).some((id) => !!kpis[id]?.avertissement) };
}

export type PointPosition = { societe: string; valeur: number };

export type ResultatPosition =
  | { statut: "non_classable"; raison: string; groupe: GroupePairs | null }
  | {
      statut: "ok";
      groupe: GroupePairs;
      valeur: number;
      rang: number;
      total: number;
      /** Part des autres sociétés du groupe qui font moins bien (0-100) ; null si neutre. */
      percentile: number | null;
      mediane: number;
      points: PointPosition[];
      /** Sociétés du groupe écartées (valeur non comparable). */
      nonComparables: string[];
      /** Sociétés du groupe sans valeur pour cet indicateur. */
      sansValeur: string[];
    };

function mediane(vals: number[]): number {
  const t = [...vals].sort((a, b) => a - b);
  const m = Math.floor(t.length / 2);
  return t.length % 2 === 0 ? (t[m - 1] + t[m]) / 2 : t[m];
}

/** Clé de tri : plus petite = meilleure position (rang 1). */
function cleTri(sens: SensPosition, v: number): number {
  if (sens === "lower") return v;
  if (sens === "zero") return Math.abs(v);
  return -v; // higher, et neutre (rang par valeur décroissante)
}

export function positionParmiPairs(indicateurId: string, societe: string): ResultatPosition {
  const ind = INDICATEUR_POSITION_PAR_ID[indicateurId];
  const info = DEMO_SFCR[societe];
  const groupe = groupePairsDe(societe);
  if (!ind || !info) return { statut: "non_classable", raison: "Indicateur ou société inconnu.", groupe };
  if (!groupe) {
    return { statut: "non_classable", raison: "Aucun groupe de pairs défini pour cette société.", groupe };
  }
  // Modèle interne (calibrage propre à chaque société) et comptes de groupe :
  // jamais classés ; petit groupe de pairs : pas de classement fiable.
  const raisons: string[] = [];
  if (info.modele === "Modèle interne") {
    raisons.push("calcule son SCR avec son propre modèle interne, non comparable d'une société à l'autre");
  }
  if (info.perimetre === "groupe") {
    raisons.push("publie des comptes consolidés de groupe, qui ne se comparent qu'à d'autres groupes");
  }
  if (raisons.length > 0 || groupe.petitEchantillon || groupe.n < SEUIL_PAIRS) {
    const taille = groupe.n === 1 ? "ne compte qu'une société" : `ne compte que ${groupe.n} sociétés`;
    return {
      statut: "non_classable",
      groupe,
      raison:
        `Pas de classement possible : ${raisons.length > 0 ? `${societe} ${raisons.join(" et ")} ; ` : ""}` +
        `son groupe de pairs ${taille} (il en faut au moins ${SEUIL_PAIRS}).`,
    };
  }
  if (ind.source === "kpi" && !kpiApplicable(ind.id, societe)) {
    return { statut: "non_classable", groupe, raison: `Indicateur sans objet pour une société ${info.type}.` };
  }

  const propre = valeurIndicateur(ind, societe);
  if (propre.valeur === null) {
    return {
      statut: "non_classable",
      groupe,
      raison: ind.raisonAbsence
        ? `${societe} ${ind.raisonAbsence}`
        : `Pas de valeur de cet indicateur pour ${societe}.`,
    };
  }
  if (propre.avertissement) {
    return {
      statut: "non_classable",
      groupe,
      raison: "Valeur non comparable aux autres sociétés (voir la note de la valeur) : jamais classée.",
    };
  }

  const points: PointPosition[] = [];
  const nonComparables: string[] = [];
  const sansValeur: string[] = [];
  for (const s of groupe.societes) {
    const v = valeurIndicateur(ind, s);
    if (v.valeur === null) sansValeur.push(s);
    else if (v.avertissement) nonComparables.push(s);
    else points.push({ societe: s, valeur: v.valeur });
  }
  if (points.length < SEUIL_PAIRS) {
    return {
      statut: "non_classable",
      groupe,
      raison: `Pas de classement possible : seulement ${points.length} société${points.length > 1 ? "s" : ""} du groupe ${points.length > 1 ? "ont" : "a"} une valeur comparable pour cet indicateur (il en faut au moins ${SEUIL_PAIRS}).`,
    };
  }

  const triees = [...points].sort((a, b) => cleTri(ind.sens, a.valeur) - cleTri(ind.sens, b.valeur));
  // Ex aequo : même rang (le meilleur).
  const cle = cleTri(ind.sens, propre.valeur);
  const rang = triees.findIndex((p) => cleTri(ind.sens, p.valeur) === cle) + 1;
  const total = points.length;
  const percentile = ind.sens === "neutre" ? null : Math.round(((total - rang) / (total - 1)) * 100);
  return {
    statut: "ok",
    groupe,
    valeur: propre.valeur,
    rang,
    total,
    percentile,
    mediane: mediane(points.map((p) => p.valeur)),
    points,
    nonComparables,
    sansValeur,
  };
}
