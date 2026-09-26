/**
 * analyse-demo.ts — Port TypeScript de test_markdrop/sfcr_app/analyse/data.py
 * (Reflex, commit c83d3ef).
 *
 * ⚠️ DONNÉES DE DÉMONSTRATION — valeurs mock inventées pour le développement
 * de l'interface, jamais de vraies valeurs extraites d'un rapport SFCR. Le
 * bandeau "Données de démonstration" reste visible tant que ce module n'est
 * pas remplacé par un vrai appel backend (kpis.db) — hors périmètre de la
 * migration Reflex -> Next.js.
 *
 * Certains identifiants de KPI sont alignés sur les clés réelles de
 * src/data/kpi-sources.json (scr_total, scr_souscription_vie/nonvie,
 * primes_acquises_brutes) plutôt que sur les ids d'origine de data.py
 * (scr, scr_vie, scr_nonvie, primes_brutes) — uniquement pour que le lien
 * intelligent Analyse -> Documents continue de retrouver la bonne page
 * source sur Groupama (seule société avec de vraies données dans
 * kpi-sources.json). Aucune autre valeur ni logique n'est modifiée.
 */

export type Categorie = {
  code: "E" | "D" | "C" | "A";
  label: string;
};

// Les 4 catégories, dans l'ordre d'affichage demandé (identique à data.py)
export const CATEGORIES: Categorie[] = [
  { code: "E", label: "Gestion du capital" },
  { code: "D", label: "Valorisation Solvabilité II" },
  { code: "C", label: "Profil de risque" },
  { code: "A", label: "Activité et résultats" },
];

export type KpiDefinition = {
  id: string;
  categorie: Categorie["code"];
  code: string;
  label: string;
  unite: "%" | "Md€";
  description: string;
  seuilReglementaire: number | null;
};

export const KPI_DEFINITIONS: KpiDefinition[] = [
  // E — Gestion du capital
  { id: "ratio_scr", categorie: "E", code: "E1", label: "Ratio SCR", unite: "%", description: "Fonds propres éligibles / SCR", seuilReglementaire: 100.0 },
  { id: "ratio_mcr", categorie: "E", code: "E2", label: "Ratio MCR", unite: "%", description: "Fonds propres éligibles / MCR", seuilReglementaire: 100.0 },
  { id: "scr_total", categorie: "E", code: "E3", label: "SCR", unite: "Md€", description: "Capital de solvabilité requis", seuilReglementaire: null },
  { id: "mcr", categorie: "E", code: "E4", label: "MCR", unite: "Md€", description: "Minimum de capital requis", seuilReglementaire: null },
  { id: "fonds_propres_eligibles", categorie: "E", code: "E5", label: "Fonds propres éligibles", unite: "Md€", description: "Total des fonds propres éligibles", seuilReglementaire: null },
  { id: "fonds_propres_t1", categorie: "E", code: "E6", label: "Fonds propres Tier 1", unite: "Md€", description: "Fonds propres de meilleure qualité", seuilReglementaire: null },
  { id: "fonds_propres_t2", categorie: "E", code: "E7", label: "Fonds propres Tier 2", unite: "Md€", description: "Fonds propres de qualité intermédiaire", seuilReglementaire: null },
  { id: "surplus_capital", categorie: "E", code: "E8", label: "Surplus de capital", unite: "Md€", description: "Fonds propres − SCR", seuilReglementaire: null },
  // D — Valorisation Solvabilité II
  { id: "best_estimate", categorie: "D", code: "D1", label: "Best Estimate total", unite: "Md€", description: "Provisions techniques — meilleure estimation", seuilReglementaire: null },
  { id: "marge_risque", categorie: "D", code: "D2", label: "Marge de risque", unite: "Md€", description: "Marge de risque réglementaire", seuilReglementaire: null },
  { id: "provisions_techniques", categorie: "D", code: "D3", label: "Total provisions techniques", unite: "Md€", description: "Best Estimate + marge de risque", seuilReglementaire: null },
  { id: "total_actifs", categorie: "D", code: "D4", label: "Total actifs (Solva II)", unite: "Md€", description: "Total actifs en valeur Solvabilité II", seuilReglementaire: null },
  // C — Profil de risque
  { id: "scr_souscription_nonvie", categorie: "C", code: "C1", label: "SCR souscription non-vie", unite: "Md€", description: "Risque de souscription non-vie", seuilReglementaire: null },
  { id: "scr_souscription_vie", categorie: "C", code: "C2", label: "SCR souscription vie", unite: "Md€", description: "Risque de souscription vie", seuilReglementaire: null },
  { id: "scr_marche", categorie: "C", code: "C3", label: "SCR risque de marché", unite: "Md€", description: "Risque de marché", seuilReglementaire: null },
  { id: "scr_contrepartie", categorie: "C", code: "C4", label: "SCR risque de contrepartie", unite: "Md€", description: "Risque de défaut de contrepartie", seuilReglementaire: null },
  { id: "scr_operationnel", categorie: "C", code: "C5", label: "SCR risque opérationnel", unite: "Md€", description: "Risque opérationnel", seuilReglementaire: null },
  { id: "diversification", categorie: "C", code: "C6", label: "Effet de diversification", unite: "%", description: "Réduction du SCR grâce à la diversification", seuilReglementaire: null },
  // A — Activité et résultats
  { id: "primes_acquises_brutes", categorie: "A", code: "A1", label: "Primes brutes émises", unite: "Md€", description: "Primes brutes émises sur l'exercice", seuilReglementaire: null },
  { id: "ratio_sp", categorie: "A", code: "A2", label: "Ratio S/P", unite: "%", description: "Sinistres / Primes (ratio combiné)", seuilReglementaire: 100.0 },
];

export const KPI_PAR_ID: Record<string, KpiDefinition> = Object.fromEntries(
  KPI_DEFINITIONS.map((k) => [k.id, k])
);

export const KPI_IDS_PAR_CATEGORIE: Record<string, string[]> = Object.fromEntries(
  CATEGORIES.map((c) => [c.code, KPI_DEFINITIONS.filter((k) => k.categorie === c.code).map((k) => k.id)])
);

// Les 5 axes du radar chart (sous-ensemble du profil de risque C1-C5)
export const AXES_RADAR = ["scr_souscription_nonvie", "scr_souscription_vie", "scr_marche", "scr_contrepartie", "scr_operationnel"];

export type KpiValeur = {
  valeur: number;
  variation: number | null;
  variationUnit: string;
  chapitreSource: string;
  pageSource: number | null;
  confiance: "verified" | "extracted";
  dateExtraction: string;
};

function kpi(
  valeur: number,
  variation: number | null,
  variationUnit: string,
  chapitre: string,
  page: number | null,
  confiance: "verified" | "extracted"
): KpiValeur {
  return { valeur, variation, variationUnit, chapitreSource: chapitre, pageSource: page, confiance, dateExtraction: "2026-09-25" };
}

// Filtres "pairs" : deux dimensions qui rendent une comparaison pertinente ou non
// (une société en modèle interne et une autre en formule standard ne se
// comparent qu'avec prudence).
export type TypeSociete = "Vie" | "Non-vie" | "Mixte" | "Mutuelle";
export type ModeleCapital = "Formule standard" | "Modèle interne";
export const TYPES_SOCIETE: TypeSociete[] = ["Vie", "Non-vie", "Mixte", "Mutuelle"];
export const MODELES_CAPITAL: ModeleCapital[] = ["Formule standard", "Modèle interne"];

export type SocieteDemo = {
  annee: number;
  /** ⚠️ Attribut de démonstration — à remplacer par les vraies métadonnées de kpis.db. */
  type: TypeSociete;
  /** ⚠️ Attribut de démonstration — à remplacer par les vraies métadonnées de kpis.db. */
  modele: ModeleCapital;
  kpis: Record<string, KpiValeur>;
};

// --- DONNÉES DE DÉMONSTRATION — 5 assureurs mock, aucune valeur réelle ---
const DEMO_BASE: Record<string, SocieteDemo> = {
  Groupama: {
    annee: 2023,
    type: "Mixte",
    modele: "Modèle interne",
    kpis: {
      ratio_scr: kpi(267.0, 12.0, "pts", "E.2", 89, "verified"),
      ratio_mcr: kpi(589.0, 8.0, "pts", "E.2", 90, "verified"),
      scr_total: kpi(6.02, -0.3, "Md€", "E.2", 89, "verified"),
      mcr: kpi(2.71, 0.1, "Md€", "E.2", 90, "extracted"),
      fonds_propres_eligibles: kpi(16.08, 1.1, "Md€", "E.1", 87, "verified"),
      fonds_propres_t1: kpi(13.4, 0.9, "Md€", "E.1", 87, "extracted"),
      fonds_propres_t2: kpi(2.68, 0.2, "Md€", "E.1", 87, "extracted"),
      surplus_capital: kpi(10.06, 1.4, "Md€", "E.2", 89, "verified"),
      best_estimate: kpi(69.0, 2.1, "Md€", "D.2", 78, "verified"),
      marge_risque: kpi(2.38, 0.1, "Md€", "D.2", 79, "extracted"),
      provisions_techniques: kpi(71.4, 2.2, "Md€", "D.2", 78, "verified"),
      total_actifs: kpi(94.6, 3.5, "Md€", "D.1", 75, "extracted"),
      scr_souscription_nonvie: kpi(2.47, 0.15, "Md€", "C.1", 85, "verified"),
      scr_souscription_vie: kpi(1.46, -0.05, "Md€", "C.1", 85, "extracted"),
      scr_marche: kpi(4.68, 0.3, "Md€", "C.1", 85, "verified"),
      scr_contrepartie: kpi(0.79, 0.02, "Md€", "C.1", 85, "extracted"),
      scr_operationnel: kpi(0.68, 0.04, "Md€", "C.1", 85, "extracted"),
      diversification: kpi(-38.0, -1.5, "pts", "C.1", 85, "verified"),
      primes_acquises_brutes: kpi(16.9, 0.8, "Md€", "A.1", 12, "verified"),
      ratio_sp: kpi(94.2, -1.8, "pts", "A.1", 14, "extracted"),
    },
  },
  "AXA France": {
    annee: 2023,
    type: "Mixte",
    modele: "Modèle interne",
    kpis: {
      ratio_scr: kpi(198.0, -5.0, "pts", "E.2", 91, "extracted"),
      ratio_mcr: kpi(410.0, 3.0, "pts", "E.2", 92, "extracted"),
      scr_total: kpi(9.8, 0.4, "Md€", "E.2", 91, "verified"),
      mcr: kpi(4.4, 0.2, "Md€", "E.2", 92, "extracted"),
      fonds_propres_eligibles: kpi(19.4, 0.5, "Md€", "E.1", 88, "verified"),
      fonds_propres_t1: kpi(15.9, 0.4, "Md€", "E.1", 88, "extracted"),
      fonds_propres_t2: kpi(3.5, 0.1, "Md€", "E.1", 88, "extracted"),
      surplus_capital: kpi(9.6, 0.1, "Md€", "E.2", 91, "verified"),
      best_estimate: kpi(102.0, 4.5, "Md€", "D.2", 80, "extracted"),
      marge_risque: kpi(3.1, 0.2, "Md€", "D.2", 81, "extracted"),
      provisions_techniques: kpi(105.1, 4.7, "Md€", "D.2", 80, "verified"),
      total_actifs: kpi(138.2, 5.1, "Md€", "D.1", 76, "extracted"),
      scr_souscription_nonvie: kpi(3.1, 0.2, "Md€", "C.1", 86, "extracted"),
      scr_souscription_vie: kpi(2.9, -0.1, "Md€", "C.1", 86, "extracted"),
      scr_marche: kpi(6.2, 0.5, "Md€", "C.1", 86, "verified"),
      scr_contrepartie: kpi(1.1, 0.05, "Md€", "C.1", 86, "extracted"),
      scr_operationnel: kpi(0.9, 0.03, "Md€", "C.1", 86, "extracted"),
      diversification: kpi(-29.0, 1.0, "pts", "C.1", 86, "extracted"),
      primes_acquises_brutes: kpi(24.3, -0.6, "Md€", "A.1", 13, "verified"),
      ratio_sp: kpi(101.5, 2.1, "pts", "A.1", 15, "extracted"),
    },
  },
  "CNP Assurances": {
    annee: 2023,
    type: "Vie",
    modele: "Formule standard",
    kpis: {
      ratio_scr: kpi(228.0, 6.0, "pts", "E.2", 90, "verified"),
      ratio_mcr: kpi(470.0, 10.0, "pts", "E.2", 91, "extracted"),
      scr_total: kpi(13.9, -0.2, "Md€", "E.2", 90, "verified"),
      mcr: kpi(6.2, -0.1, "Md€", "E.2", 91, "extracted"),
      fonds_propres_eligibles: kpi(31.7, 1.8, "Md€", "E.1", 87, "verified"),
      fonds_propres_t1: kpi(27.1, 1.5, "Md€", "E.1", 87, "extracted"),
      fonds_propres_t2: kpi(4.6, 0.3, "Md€", "E.1", 87, "extracted"),
      surplus_capital: kpi(17.8, 2.0, "Md€", "E.2", 90, "verified"),
      best_estimate: kpi(280.0, 6.2, "Md€", "D.2", 77, "extracted"),
      marge_risque: kpi(5.9, 0.3, "Md€", "D.2", 78, "extracted"),
      provisions_techniques: kpi(285.9, 6.5, "Md€", "D.2", 77, "verified"),
      total_actifs: kpi(410.5, 8.9, "Md€", "D.1", 74, "extracted"),
      scr_souscription_nonvie: kpi(0.4, 0.02, "Md€", "C.1", 84, "extracted"),
      scr_souscription_vie: kpi(9.8, 0.4, "Md€", "C.1", 84, "verified"),
      scr_marche: kpi(7.1, 0.2, "Md€", "C.1", 84, "verified"),
      scr_contrepartie: kpi(0.6, 0.01, "Md€", "C.1", 84, "extracted"),
      scr_operationnel: kpi(0.7, 0.02, "Md€", "C.1", 84, "extracted"),
      diversification: kpi(-34.0, -0.5, "pts", "C.1", 84, "verified"),
      primes_acquises_brutes: kpi(35.6, 1.9, "Md€", "A.1", 11, "verified"),
      ratio_sp: kpi(89.7, -0.9, "pts", "A.1", 13, "extracted"),
    },
  },
  Covéa: {
    annee: 2023,
    type: "Mixte",
    modele: "Modèle interne",
    kpis: {
      ratio_scr: kpi(305.0, 15.0, "pts", "E.2", 92, "verified"),
      ratio_mcr: kpi(640.0, 20.0, "pts", "E.2", 93, "extracted"),
      scr_total: kpi(5.4, 0.1, "Md€", "E.2", 92, "verified"),
      mcr: kpi(2.4, 0.05, "Md€", "E.2", 93, "extracted"),
      fonds_propres_eligibles: kpi(16.5, 1.9, "Md€", "E.1", 89, "verified"),
      fonds_propres_t1: kpi(14.2, 1.6, "Md€", "E.1", 89, "extracted"),
      fonds_propres_t2: kpi(2.3, 0.3, "Md€", "E.1", 89, "extracted"),
      surplus_capital: kpi(11.1, 1.8, "Md€", "E.2", 92, "verified"),
      best_estimate: kpi(28.5, 0.9, "Md€", "D.2", 79, "extracted"),
      marge_risque: kpi(1.2, 0.05, "Md€", "D.2", 80, "extracted"),
      provisions_techniques: kpi(29.7, 1.0, "Md€", "D.2", 79, "verified"),
      total_actifs: kpi(41.3, 1.5, "Md€", "D.1", 75, "extracted"),
      scr_souscription_nonvie: kpi(2.9, 0.1, "Md€", "C.1", 85, "verified"),
      scr_souscription_vie: kpi(0.5, 0.01, "Md€", "C.1", 85, "extracted"),
      scr_marche: kpi(2.6, 0.1, "Md€", "C.1", 85, "verified"),
      scr_contrepartie: kpi(0.5, 0.01, "Md€", "C.1", 85, "extracted"),
      scr_operationnel: kpi(0.4, 0.01, "Md€", "C.1", 85, "extracted"),
      diversification: kpi(-25.0, 0.8, "pts", "C.1", 85, "extracted"),
      primes_acquises_brutes: kpi(14.1, 0.5, "Md€", "A.1", 12, "verified"),
      ratio_sp: kpi(97.8, 3.2, "pts", "A.1", 14, "extracted"),
    },
  },
  MACSF: {
    annee: 2023,
    type: "Mutuelle",
    modele: "Formule standard",
    kpis: {
      ratio_scr: kpi(521.0, 22.0, "pts", "E.2", 88, "verified"),
      ratio_mcr: kpi(2084.0, 60.0, "pts", "E.2", 89, "extracted"),
      scr_total: kpi(0.44, 0.02, "Md€", "E.2", 88, "verified"),
      mcr: kpi(0.11, 0.005, "Md€", "E.2", 89, "extracted"),
      fonds_propres_eligibles: kpi(2.29, 0.15, "Md€", "E.1", 86, "verified"),
      fonds_propres_t1: kpi(2.29, 0.15, "Md€", "E.1", 86, "extracted"),
      fonds_propres_t2: kpi(0.0, 0.0, "Md€", "E.1", 86, "extracted"),
      surplus_capital: kpi(1.85, 0.13, "Md€", "E.2", 88, "verified"),
      best_estimate: kpi(0.88, 0.04, "Md€", "D.2", 76, "extracted"),
      marge_risque: kpi(0.14, 0.01, "Md€", "D.2", 77, "extracted"),
      provisions_techniques: kpi(1.02, 0.05, "Md€", "D.2", 76, "verified"),
      total_actifs: kpi(3.4, 0.2, "Md€", "D.1", 73, "extracted"),
      scr_souscription_nonvie: kpi(0.0, 0.0, "Md€", "C.1", 83, "extracted"),
      scr_souscription_vie: kpi(0.02, 0.001, "Md€", "C.1", 83, "extracted"),
      scr_marche: kpi(0.5, 0.03, "Md€", "C.1", 83, "verified"),
      scr_contrepartie: kpi(0.004, 0.0, "Md€", "C.1", 83, "extracted"),
      scr_operationnel: kpi(0.002, 0.0, "Md€", "C.1", 83, "extracted"),
      diversification: kpi(-12.0, 0.3, "pts", "C.1", 83, "extracted"),
      primes_acquises_brutes: kpi(0.43, 0.02, "Md€", "A.1", 10, "verified"),
      ratio_sp: kpi(76.4, -2.1, "pts", "A.1", 12, "extracted"),
    },
  },
};

// --- Sociétés FICTIVES (noms inventés, valeurs générées à partir de quelques
// paramètres cohérents entre eux) : elles donnent assez de "pairs" pour
// démontrer le classement, la distribution et les filtres. ---
type ParamsFictive = {
  annee: number;
  type: TypeSociete;
  modele: ModeleCapital;
  fp: number; // fonds propres éligibles (Md€)
  scr: number;
  mcr: number;
  partT1: number; // part de Tier 1 dans les fonds propres (0-1)
  be: number;
  rm: number;
  actifs: number;
  primes: number;
  sp: number; // ratio S/P (%)
  poids: [number, number, number, number, number]; // non-vie, vie, marché, contrepartie, opérationnel (somme = 1)
  divers: number; // effet de diversification (%, négatif)
  dRatio: number; // variation N-1 du ratio SCR (pts)
  dSp: number; // variation N-1 du ratio S/P (pts)
};

const arrondi = (v: number, d = 2) => Math.round(v * 10 ** d) / 10 ** d;

function societeFictive(p: ParamsFictive): SocieteDemo {
  const somme = p.scr / (1 + p.divers / 100);
  const [nv, v, m, c, o] = p.poids.map((w) => arrondi(somme * w, 3));
  const dMd = (x: number) => arrondi(x * 0.03, 3);
  return {
    annee: p.annee,
    type: p.type,
    modele: p.modele,
    kpis: {
      ratio_scr: kpi(arrondi((p.fp / p.scr) * 100, 1), p.dRatio, "pts", "E.2", 60, "verified"),
      ratio_mcr: kpi(arrondi((p.fp / p.mcr) * 100, 1), arrondi(p.dRatio * 1.5, 1), "pts", "E.2", 61, "verified"),
      scr_total: kpi(p.scr, dMd(p.scr), "Md€", "E.2", 60, "verified"),
      mcr: kpi(p.mcr, dMd(p.mcr), "Md€", "E.2", 61, "extracted"),
      fonds_propres_eligibles: kpi(p.fp, dMd(p.fp), "Md€", "E.1", 58, "verified"),
      fonds_propres_t1: kpi(arrondi(p.fp * p.partT1), dMd(p.fp * p.partT1), "Md€", "E.1", 58, "extracted"),
      fonds_propres_t2: kpi(arrondi(p.fp * (1 - p.partT1)), dMd(p.fp * (1 - p.partT1)), "Md€", "E.1", 58, "extracted"),
      surplus_capital: kpi(arrondi(p.fp - p.scr), dMd(p.fp - p.scr), "Md€", "E.2", 60, "verified"),
      best_estimate: kpi(p.be, dMd(p.be), "Md€", "D.2", 50, "verified"),
      marge_risque: kpi(p.rm, dMd(p.rm), "Md€", "D.2", 51, "extracted"),
      provisions_techniques: kpi(arrondi(p.be + p.rm), dMd(p.be + p.rm), "Md€", "D.2", 50, "verified"),
      total_actifs: kpi(p.actifs, dMd(p.actifs), "Md€", "D.1", 47, "extracted"),
      scr_souscription_nonvie: kpi(nv, dMd(nv), "Md€", "C.1", 55, "verified"),
      scr_souscription_vie: kpi(v, dMd(v), "Md€", "C.1", 55, "extracted"),
      scr_marche: kpi(m, dMd(m), "Md€", "C.1", 55, "verified"),
      scr_contrepartie: kpi(c, dMd(c), "Md€", "C.1", 55, "extracted"),
      scr_operationnel: kpi(o, dMd(o), "Md€", "C.1", 55, "extracted"),
      diversification: kpi(p.divers, 0.5, "pts", "C.1", 55, "verified"),
      primes_acquises_brutes: kpi(p.primes, dMd(p.primes), "Md€", "A.1", 9, "verified"),
      ratio_sp: kpi(p.sp, p.dSp, "pts", "A.1", 11, "extracted"),
    },
  };
}

const DEMO_FICTIVES: Record<string, SocieteDemo> = {
  "Ponant Assurances": societeFictive({ annee: 2023, type: "Non-vie", modele: "Formule standard", fp: 2.4, scr: 1.3, mcr: 0.45, partT1: 0.92, be: 3.1, rm: 0.12, actifs: 4.8, primes: 2.2, sp: 91, poids: [0.55, 0.02, 0.28, 0.09, 0.06], divers: -22, dRatio: 6, dSp: -1.2 }),
  "Vallier Mutuelle": societeFictive({ annee: 2023, type: "Mutuelle", modele: "Formule standard", fp: 0.62, scr: 0.38, mcr: 0.14, partT1: 0.97, be: 0.71, rm: 0.03, actifs: 1.05, primes: 0.66, sp: 96, poids: [0.3, 0.05, 0.4, 0.14, 0.11], divers: -18, dRatio: -4, dSp: 1.5 }),
  "Armorique Vie": societeFictive({ annee: 2023, type: "Vie", modele: "Modèle interne", fp: 5.9, scr: 3.6, mcr: 1.4, partT1: 0.85, be: 41.0, rm: 0.9, actifs: 47.5, primes: 3.4, sp: 78, poids: [0.02, 0.33, 0.5, 0.08, 0.07], divers: -30, dRatio: -12, dSp: -0.5 }),
  "Néomut": societeFictive({ annee: 2023, type: "Mutuelle", modele: "Formule standard", fp: 0.21, scr: 0.22, mcr: 0.08, partT1: 0.9, be: 0.33, rm: 0.02, actifs: 0.5, primes: 0.29, sp: 104, poids: [0.35, 0.03, 0.38, 0.14, 0.1], divers: -15, dRatio: -9, dSp: 3 }),
  "Kerlann Vie": societeFictive({ annee: 2023, type: "Vie", modele: "Formule standard", fp: 1.5, scr: 0.82, mcr: 0.31, partT1: 0.8, be: 11.4, rm: 0.3, actifs: 13.2, primes: 0.9, sp: 82, poids: [0.02, 0.3, 0.5, 0.1, 0.08], divers: -27, dRatio: 9, dSp: -1 }),
  "Sablier Assurances": societeFictive({ annee: 2023, type: "Mixte", modele: "Modèle interne", fp: 9.8, scr: 4.7, mcr: 1.9, partT1: 0.88, be: 52, rm: 1.6, actifs: 63, primes: 9.1, sp: 93, poids: [0.3, 0.18, 0.36, 0.09, 0.07], divers: -33, dRatio: 3, dSp: -0.8 }),
};

export const DEMO_SFCR: Record<string, SocieteDemo> = { ...DEMO_BASE, ...DEMO_FICTIVES };

export type SfcrDisponible = { id: string; label: string; annee: number; disponible: boolean };

export function listeSfcrDisponibles(): SfcrDisponible[] {
  return Object.entries(DEMO_SFCR).map(([nom, info]) => ({
    id: nom,
    label: `${nom} — SFCR ${info.annee}`,
    annee: info.annee,
    disponible: true,
  }));
}

export function kpisSociete(nom: string): Record<string, KpiValeur> {
  return DEMO_SFCR[nom]?.kpis ?? {};
}

export function toutesLesSocietes(): string[] {
  return Object.keys(DEMO_SFCR);
}
