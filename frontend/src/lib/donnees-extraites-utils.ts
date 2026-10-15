/**
 * donnees-extraites-utils.ts — Types, libellés et helpers pour l'onglet
 * "Base de données" (liste des KPIs réellement extraits de kpis.db).
 *
 * Contrairement à analyse-demo.ts (données de démonstration inventées),
 * ce module lit frontend/src/data/donnees-extraites.json : un snapshot
 * généré en lecture seule depuis kpis.db (voir le champ `genereLe`).
 * Ce n'est pas une connexion live à la base — il faut régénérer ce
 * fichier après chaque mise à jour de kpis.db (même logique que
 * kpi-sources.json, déjà utilisé par l'onglet Documents).
 */

import donneesExtraitesJson from "@/data/donnees-extraites.json";

export type Societe = {
  id: number;
  name: string;
  /** Forme juridique courte (SA, SE, SAM, Mutuelle, Groupe…). */
  type: string;
  groupe: string | null;
  country: string;
  /** Vie / Non-vie / Santé/prévoyance / Mixte. */
  typeActivite?: string;
  scrMethod?: string;
  formeJuridique?: string;
  familleJuridique?: string;
  /** solo / groupe. */
  perimetre?: string;
  /** Formule standard / Modèle interne. */
  modeleCapital?: string;
  groupeParent?: string | null;
  /** Société du panel qui la consolide déjà (double comptage à éviter). */
  consolideDans?: string | null;
  /** Clé de groupe de pairs : activité · modèle · périmètre. */
  groupePairs?: string;
};

export type GroupePairs = {
  id: string;
  societes: string[];
  n: number;
  /** n < 5 : médiane peu fiable. */
  petitEchantillon: boolean;
};

export type VerdictCompat = "C" | "R" | "N" | "NA";
export type AxeCompat = "activite" | "forme" | "modele" | "perimetre";

export type Compatibilite = {
  axes: AxeCompat[];
  /** Ordre de gravité : C < NA < R < N. */
  ordreVerdicts: Record<VerdictCompat, number>;
  /** Activité → classe de sinistres (axe « activité » de charge_sinistres). */
  classeSinistres: Record<string, string>;
  regle: string;
  matrice: Record<string, Partial<Record<AxeCompat, { verdict: VerdictCompat; note: string | null }>>>;
};

/** Ratios normalisés d'une société (clés absentes = non calculables). */
export type IndicateursSociete = {
  ratio_scr_sans_mesures_lt_pct?: number;
  impact_va_pts?: number;
  impact_transitoires_pts?: number;
  impact_mesures_lt_pts?: number;
  marge_risque_sur_be_pct?: number;
  sp_nonvie_pct?: number;
  position_mcr?: string | null;
  /** La société applique une mesure transitoire (provisions techniques ou taux). */
  mesure_transitoire?: boolean;
  /** Part (%) de chaque module dans la somme des modules de base ; null pour
   * les modèles internes (parts non comparables). */
  composition_modules_pct?: Record<string, number> | null;
  [cle: string]: unknown;
};

export type Composant = {
  label: string;
  codeQrt: string | null;
  valeur: number;
  unite: string;
  pageSource: number | null;
  operation: string;
};

export type KpiExtrait = {
  valeur: number;
  unite: string;
  categorie: string;
  annee: number;
  pageSource: number | null;
  chapitreSource: string | null;
  valide: boolean;
  valeurBrute: number | null;
  uniteBrute: string | null;
  estCompose?: boolean;
  composants?: Composant[] | null;
  /** PDF spécifique à CE KPI, quand il diffère du PDF par défaut de la
   * société (cf. PDF_PAR_SOCIETE). null/absent = utiliser le PDF par
   * défaut — c'est le cas pour l'immense majorité des KPIs. */
  sourcePdf?: string | null;
  /** KPI calculé sur une base non comparable aux autres sociétés (ex.
   * modèle interne, avant diversification inter-risques et avant impôt)
   * — à signaler visuellement, jamais à masquer ni traiter comme une
   * valeur normale. Voir noteAvertissement pour le détail. */
  avertissement?: boolean;
  noteAvertissement?: string | null;
  /** Libellé à afficher à la place du nom générique du KPI (ex. « SCR
   * minimal consolidé du groupe » pour le mcr d'un groupe). */
  libelle?: string | null;
};

type DonneesExtraites = {
  genereLe: string;
  societes: Societe[];
  kpisParSociete: Record<string, Record<string, KpiExtrait>>;
  indicateursParSociete: Record<string, IndicateursSociete>;
  definitionsIndicateurs: Record<string, string>;
  groupesPairs: GroupePairs[];
  compatibilite: Compatibilite;
};

export const DONNEES_EXTRAITES = donneesExtraitesJson as unknown as DonneesExtraites;

// Ordre d'affichage des catégories réelles de kpis.db (colonne `category`).
export const CATEGORIES_REELLES: { code: string; label: string }[] = [
  { code: "solvabilité", label: "Solvabilité" },
  { code: "fonds_propres", label: "Fonds propres" },
  { code: "scr", label: "SCR — Profil de risque" },
  { code: "mcr", label: "MCR" },
  { code: "provisions", label: "Provisions techniques" },
  { code: "activité", label: "Activité et résultats" },
];

// Libellés lisibles des 21 kpi_name réels de kpis.db (colonne `kpi_name`).
export const KPI_LABELS_REELS: Record<string, string> = {
  ratio_scr: "Ratio SCR",
  ratio_mcr: "Ratio MCR",
  fonds_propres_eligibles: "Fonds propres éligibles",
  fonds_propres_t1_nr: "Fonds propres Tier 1 non restreint",
  fonds_propres_t1_r: "Fonds propres Tier 1 restreint",
  fonds_propres_t2: "Fonds propres Tier 2",
  fonds_propres_t3: "Fonds propres Tier 3",
  scr_total: "SCR total",
  scr_marche: "SCR — Risque de marché",
  scr_contrepartie: "SCR — Risque de contrepartie",
  scr_operationnel: "SCR — Risque opérationnel",
  scr_souscription_vie: "SCR — Souscription vie",
  scr_souscription_nonvie: "SCR — Souscription non-vie",
  scr_souscription_sante: "SCR — Souscription santé",
  scr_diversification: "Effet de diversification",
  mcr: "MCR",
  best_estimate: "Best estimate",
  marge_risque: "Marge de risque",
  provisions_techniques: "Provisions techniques",
  primes_acquises_brutes: "Primes acquises brutes",
  charge_sinistres: "Charge de sinistres",
};

export const NB_KPIS_ATTENDUS = Object.keys(KPI_LABELS_REELS).length;

function formatNombreEspace(valeur: number, decimales: number): string {
  const fixe = valeur.toFixed(decimales);
  const [entier, decimal] = fixe.split(".");
  const entierEspace = entier.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return decimal !== undefined ? `${entierEspace},${decimal}` : entierEspace;
}

/** kpis.db stocke les unités "pct" et "M€" (pas "%"/"Md€" comme les données
 * de démo de l'onglet Analyse) — formatage dédié pour rester fidèle aux
 * valeurs réelles. */
export function formatValeurReelle(valeur: number, unite: string): string {
  if (unite === "pct") return `${formatNombreEspace(valeur, 1)} %`;
  if (unite === "M€") return `${formatNombreEspace(valeur, 1)} M€`;
  return `${formatNombreEspace(valeur, 2)} ${unite}`;
}

/** Formate la valeur brute (telle qu'elle apparaît dans le PDF).
 * Quand valeurBrute est null (ex. pourcentages), on tombe sur formatValeurReelle. */
export function formatValeurBrute(
  valeurBrute: number | null,
  uniteBrute: string | null,
  valeur: number,
  unite: string,
): string {
  if (valeurBrute == null) return formatValeurReelle(valeur, unite);
  const raw = uniteBrute ?? unite;
  const u = raw === "euros bruts" || raw === "euro brut" ? "€" : raw;
  // Les valeurs brutes K€ sont des entiers — pas de décimales inutiles
  if (u === "K€" || u === "€") return `${formatNombreEspace(valeurBrute, 0)} ${u}`;
  return `${formatNombreEspace(valeurBrute, 1)} ${u}`;
}

export function societesTriees(): Societe[] {
  return [...DONNEES_EXTRAITES.societes].sort((a, b) => a.name.localeCompare(b.name, "fr"));
}

export const GROUPE_TOUS = "TOUS";
export const GROUPE_INDEPENDANTES = "INDEPENDANTES";

/** Groupes réels (sociétés multi-entités) triés par taille décroissante,
 * puis le pseudo-groupe "sociétés indépendantes". */
export function groupesDisponibles(): { valeur: string; label: string; nb: number }[] {
  const comptes = new Map<string, number>();
  for (const s of DONNEES_EXTRAITES.societes) {
    if (s.groupe) comptes.set(s.groupe, (comptes.get(s.groupe) ?? 0) + 1);
  }
  const groupes = [...comptes.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "fr"))
    .map(([label, nb]) => ({ valeur: label, label, nb }));
  const nbIndependantes = DONNEES_EXTRAITES.societes.filter((s) => !s.groupe).length;
  return [...groupes, { valeur: GROUPE_INDEPENDANTES, label: "Sociétés indépendantes", nb: nbIndependantes }];
}

/** Sociétés correspondant au groupe sélectionné et au texte de recherche
 * (recherche = filtre libre par nom, indépendant du groupe). */
export function societesFiltrees(groupe: string, recherche: string): Societe[] {
  const q = recherche.trim().toLowerCase();
  return societesTriees().filter((s) => {
    const matchGroupe =
      groupe === GROUPE_TOUS ||
      (groupe === GROUPE_INDEPENDANTES ? !s.groupe : s.groupe === groupe);
    const matchRecherche = q === "" || s.name.toLowerCase().includes(q);
    return matchGroupe && matchRecherche;
  });
}

export function kpisDe(nomSociete: string): Record<string, KpiExtrait> {
  return DONNEES_EXTRAITES.kpisParSociete[nomSociete] ?? {};
}

export type Couverture = { extraits: number; valides: number; total: number };

export function couvertureKpis(nomSociete: string): Couverture {
  const kpis = Object.values(kpisDe(nomSociete));
  return {
    extraits: kpis.length,
    valides: kpis.filter((k) => k.valide).length,
    total: NB_KPIS_ATTENDUS,
  };
}

/** Une société est marquée "Nouveau" (= ajoutée à chaud via l'onglet
 * Upload, jamais relue à la main) si AUCUN de ses KPIs n'a `valide: true`.
 *
 * Vérifié sur la base actuelle (34 sociétés au 27/09/2026) : toutes les
 * sociétés déjà relues manuellement ont au moins un KPI validé, donc ce
 * critère n'a jamais de faux positif. Le script d'extraction à chaud
 * (extraire_un_pdf.py, Décision 106) force validated=0 sur tous les KPIs
 * insérés, donc une nouvelle société est exactement dans ce cas.
 */
export function estNouvelleSociete(nomSociete: string): boolean {
  const kpis = Object.values(kpisDe(nomSociete));
  if (kpis.length === 0) return false; // société sans KPI extrait : pas "nouvelle", juste vide
  return kpis.every((k) => !k.valide);
}

export const STATS_GLOBALES = {
  nbSocietes: DONNEES_EXTRAITES.societes.length,
  nbKpis: Object.values(DONNEES_EXTRAITES.kpisParSociete).reduce((acc, k) => acc + Object.keys(k).length, 0),
  nbGroupes: groupesDisponibles().filter((g) => g.valeur !== GROUPE_INDEPENDANTES).length,
};

function telecharger(contenu: string, nomFichier: string) {
  const blob = new Blob([contenu], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nomFichier;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exporterCsvSociete(nomSociete: string) {
  const kpis = kpisDe(nomSociete);
  const lignes = ["categorie,kpi,valeur,unite,annee,chapitre_source,page_source,valide"];
  for (const [id, k] of Object.entries(kpis)) {
    const label = KPI_LABELS_REELS[id] ?? id;
    lignes.push(
      [k.categorie, label, k.valeur, k.unite, k.annee, k.chapitreSource ?? "", k.pageSource ?? "", k.valide].join(",")
    );
  }
  telecharger(lignes.join("\n"), `donnees_${nomSociete.replace(/[^\w-]+/g, "_")}.csv`);
}
