/**
 * analyse-demo.ts — Données RÉELLES de l'onglet Analyse.
 *
 * Ce module lit donnees-extraites.json (snapshot de kpis.db) et expose les
 * mêmes types et fonctions que l'ancienne version demo, pour que tous les
 * composants d'Analyse continuent de fonctionner sans modification.
 *
 * Différences avec l'ancienne version demo :
 * - 34 sociétés réelles (au lieu de 5 mock + 6 fictives)
 * - 22 types de KPIs réels (au lieu de 20 inventés)
 * - Valeurs en M€ (pas en Md€)
 * - Pas de données de variation N-1 (variation = null)
 * - Confiance = "verified" si kpis.db.validated=true, sinon "extracted"
 */

import {
  DONNEES_EXTRAITES,
  KPI_LABELS_REELS,
  type KpiExtrait,
} from "@/lib/donnees-extraites-utils";

// ────────────────────────── Catégories d'affichage ──────────────────────────

export type Categorie = {
  code: "E" | "D" | "C" | "A";
  label: string;
};

export const CATEGORIES: Categorie[] = [
  { code: "E", label: "Gestion du capital" },
  { code: "D", label: "Valorisation Solvabilité II" },
  { code: "C", label: "Profil de risque" },
  { code: "A", label: "Activité et résultats" },
];

// Mapping catégorie réelle kpis.db → catégorie d'affichage
const MAPPING_CATEGORIE: Record<string, Categorie["code"]> = {
  solvabilité: "E",
  fonds_propres: "E",
  scr: "C",
  mcr: "E",
  provisions: "D",
  activité: "A",
};

// Exceptions : certains KPIs SCR sont mieux placés dans E (capital)
const EXCEPTIONS_CATEGORIE: Record<string, Categorie["code"]> = {
  scr_total: "E",
};

function categorieAffichage(kpiId: string, catReelle: string): Categorie["code"] {
  return EXCEPTIONS_CATEGORIE[kpiId] ?? MAPPING_CATEGORIE[catReelle] ?? "A";
}

// ────────────────────────── Définitions de KPIs ──────────────────────────

export type KpiDefinition = {
  id: string;
  categorie: Categorie["code"];
  code: string;
  label: string;
  unite: "%" | "M€";
  description: string;
  seuilReglementaire: number | null;
};

// Codes d'affichage par catégorie (E1, E2, ... D1, D2, ... etc.)
const compteurs: Record<string, number> = { E: 0, D: 0, C: 0, A: 0 };
function codeAffichage(cat: Categorie["code"]): string {
  compteurs[cat] += 1;
  return `${cat}${compteurs[cat]}`;
}

// Descriptions lisibles
const DESCRIPTIONS: Record<string, string> = {
  ratio_scr: "Fonds propres éligibles / SCR",
  ratio_mcr: "Fonds propres éligibles / MCR",
  fonds_propres_eligibles: "Total des fonds propres éligibles",
  fonds_propres_t1_nr: "Fonds propres Tier 1 non restreint",
  fonds_propres_t1_r: "Fonds propres Tier 1 restreint",
  fonds_propres_t2: "Fonds propres Tier 2",
  fonds_propres_t3: "Fonds propres Tier 3",
  scr_total: "Capital de solvabilité requis",
  mcr: "Minimum de capital requis",
  scr_marche: "Risque de marché",
  scr_contrepartie: "Risque de défaut de contrepartie",
  scr_operationnel: "Risque opérationnel",
  scr_souscription_vie: "Risque de souscription vie",
  scr_souscription_nonvie: "Risque de souscription non-vie",
  scr_souscription_sante: "Risque de souscription santé",
  scr_diversification: "Réduction du SCR grâce à la diversification",
  best_estimate: "Provisions techniques — meilleure estimation",
  marge_risque: "Marge de risque réglementaire",
  provisions_techniques: "Best Estimate + marge de risque",
  primes_acquises_brutes: "Primes brutes émises sur l'exercice",
  charge_sinistres: "Charge de sinistres sur l'exercice",
  resultat_technique: "Résultat technique de l'exercice",
};

// Seuils réglementaires
const SEUILS: Record<string, number> = {
  ratio_scr: 100.0,
  ratio_mcr: 100.0,
};

// Ordre d'affichage souhaité au sein de chaque catégorie
const ORDRE_KPIS = [
  // E — Capital
  "ratio_scr", "ratio_mcr", "scr_total", "mcr",
  "fonds_propres_eligibles", "fonds_propres_t1_nr", "fonds_propres_t1_r",
  "fonds_propres_t2", "fonds_propres_t3",
  // D — Valorisation
  "best_estimate", "marge_risque", "provisions_techniques",
  // C — Profil de risque
  "scr_souscription_nonvie", "scr_souscription_vie", "scr_souscription_sante",
  "scr_marche", "scr_contrepartie", "scr_operationnel", "scr_diversification",
  // A — Activité
  "primes_acquises_brutes", "charge_sinistres", "resultat_technique",
];

// Détermine la catégorie d'un KPI à partir du premier exemple trouvé dans les données
function detecterCategorieReelle(kpiId: string): string {
  for (const kpis of Object.values(DONNEES_EXTRAITES.kpisParSociete)) {
    const k = kpis[kpiId];
    if (k) return k.categorie;
  }
  return "activité";
}

function buildKpiDefinitions(): KpiDefinition[] {
  // Réinitialiser les compteurs
  compteurs.E = 0; compteurs.D = 0; compteurs.C = 0; compteurs.A = 0;

  const defsMap = new Map<string, KpiDefinition>();

  for (const kpiId of ORDRE_KPIS) {
    if (!KPI_LABELS_REELS[kpiId]) continue;
    const catReelle = detecterCategorieReelle(kpiId);
    const cat = categorieAffichage(kpiId, catReelle);
    const isPct = kpiId.startsWith("ratio_") || kpiId === "scr_diversification";
    defsMap.set(kpiId, {
      id: kpiId,
      categorie: cat,
      code: codeAffichage(cat),
      label: KPI_LABELS_REELS[kpiId],
      unite: isPct ? "%" : "M€",
      description: DESCRIPTIONS[kpiId] ?? KPI_LABELS_REELS[kpiId],
      seuilReglementaire: SEUILS[kpiId] ?? null,
    });
  }

  return [...defsMap.values()];
}

export const KPI_DEFINITIONS: KpiDefinition[] = buildKpiDefinitions();

export const KPI_PAR_ID: Record<string, KpiDefinition> = Object.fromEntries(
  KPI_DEFINITIONS.map((k) => [k.id, k])
);

export const KPI_IDS_PAR_CATEGORIE: Record<string, string[]> = Object.fromEntries(
  CATEGORIES.map((c) => [c.code, KPI_DEFINITIONS.filter((k) => k.categorie === c.code).map((k) => k.id)])
);

// Les 5+ axes du radar (sous-ensemble du profil de risque)
export const AXES_RADAR = [
  "scr_souscription_nonvie",
  "scr_souscription_vie",
  "scr_souscription_sante",
  "scr_marche",
  "scr_contrepartie",
  "scr_operationnel",
];

// ────────────────────────── Valeurs de KPIs ──────────────────────────

export type KpiValeur = {
  valeur: number;
  variation: number | null;
  variationUnit: string;
  chapitreSource: string;
  pageSource: number | null;
  confiance: "verified" | "extracted";
  dateExtraction: string;
};

function kpiExtraitVersKpiValeur(k: KpiExtrait): KpiValeur {
  return {
    valeur: k.valeur,
    variation: null,
    variationUnit: k.unite === "pct" ? "pts" : "M€",
    chapitreSource: k.chapitreSource ?? "",
    pageSource: k.pageSource,
    confiance: k.valide ? "verified" : "extracted",
    dateExtraction: DONNEES_EXTRAITES.genereLe.split("T")[0],
  };
}

// ────────────────────────── Filtres société ──────────────────────────

export type TypeSociete = "Vie" | "Non-vie" | "Mixte" | "Mutuelle";
export type ModeleCapital = "Formule standard" | "Modèle interne";
export const TYPES_SOCIETE: TypeSociete[] = ["Vie", "Non-vie", "Mixte", "Mutuelle"];
export const MODELES_CAPITAL: ModeleCapital[] = ["Formule standard", "Modèle interne"];

// Mapping du champ `type` de kpis.db vers TypeSociete d'affichage
function typeAffichage(typeDb: string): TypeSociete {
  const t = typeDb.toLowerCase();
  if (t === "mutuelle") return "Mutuelle";
  if (t === "groupe") return "Mixte";
  return "Mixte"; // "entité" et autres → Mixte par défaut
}

// ────────────────────────── Structure société ──────────────────────────

export type SocieteDemo = {
  annee: number;
  type: TypeSociete;
  modele: ModeleCapital;
  kpis: Record<string, KpiValeur>;
};

function buildSocietes(): Record<string, SocieteDemo> {
  const resultat: Record<string, SocieteDemo> = {};
  for (const societe of DONNEES_EXTRAITES.societes) {
    const kpisReels = DONNEES_EXTRAITES.kpisParSociete[societe.name] ?? {};
    const kpisConvertis: Record<string, KpiValeur> = {};
    for (const [id, k] of Object.entries(kpisReels)) {
      kpisConvertis[id] = kpiExtraitVersKpiValeur(k);
    }
    // Année : prendre celle du premier KPI trouvé
    const premierKpi = Object.values(kpisReels)[0];
    resultat[societe.name] = {
      annee: premierKpi?.annee ?? 2025,
      type: typeAffichage(societe.type),
      modele: "Formule standard", // par défaut — à enrichir si kpis.db stocke cette info
      kpis: kpisConvertis,
    };
  }
  return resultat;
}

export const DEMO_SFCR: Record<string, SocieteDemo> = buildSocietes();

// ────────────────────────── API publique ──────────────────────────

export type SfcrDisponible = { id: string; label: string; annee: number; disponible: boolean };

export function listeSfcrDisponibles(): SfcrDisponible[] {
  return Object.entries(DEMO_SFCR)
    .map(([nom, info]) => ({
      id: nom,
      label: `${nom} — SFCR ${info.annee}`,
      annee: info.annee,
      disponible: true,
    }))
    .sort((a, b) => a.id.localeCompare(b.id, "fr"));
}

export function kpisSociete(nom: string): Record<string, KpiValeur> {
  return DEMO_SFCR[nom]?.kpis ?? {};
}

export function toutesLesSocietes(): string[] {
  return Object.keys(DEMO_SFCR).sort((a, b) => a.localeCompare(b, "fr"));
}
