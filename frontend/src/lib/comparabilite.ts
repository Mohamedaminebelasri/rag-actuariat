/**
 * comparabilite.ts — Règles de comparaison entre sociétés (Décisions 149-155).
 *
 * `donnees-extraites.json` porte la matrice de compatibilité par KPI et par
 * axe (activité, forme juridique, modèle de capital, périmètre) : le front-end
 * l'applique, il ne la recalcule pas. Verdicts : C (comparable), R (avec
 * réserve), N (non comparable), NA (sans objet pour certaines sociétés).
 */

import { DEMO_SFCR, kpisSociete } from "@/data/analyse-demo";
import {
  DONNEES_EXTRAITES,
  type AxeCompat,
  type GroupePairs,
  type VerdictCompat,
} from "@/lib/donnees-extraites-utils";

export const LIBELLE_AXE: Record<AxeCompat, string> = {
  activite: "Activité",
  forme: "Forme juridique",
  modele: "Modèle de capital",
  perimetre: "Périmètre",
};

export type NoteCompat = { axe: AxeCompat; verdict: VerdictCompat; note: string };

export type CompatKpi = {
  /** Pire verdict parmi les axes sur lesquels les sociétés sélectionnées diffèrent. */
  verdict: VerdictCompat;
  /** Un axe différent est « sans objet » : un 0 s'affiche « sans objet ». */
  sansObjet: boolean;
  /** Notes des axes différents non comparables (N puis R), les plus graves d'abord. */
  notes: NoteCompat[];
};

const COMPATIBLE: CompatKpi = { verdict: "C", sansObjet: false, notes: [] };

/** Valeur d'une société sur un axe de la matrice. Pour `charge_sinistres`,
 * l'axe « activité » compare la classe de sinistres (vie = prestations,
 * non-vie = sinistres survenus), pas l'activité brute. */
function valeurAxe(societe: string, axe: AxeCompat, kpiId: string): string | null {
  const info = DEMO_SFCR[societe];
  if (!info) return null;
  switch (axe) {
    case "activite": {
      if (kpiId === "charge_sinistres") {
        return DONNEES_EXTRAITES.compatibilite.classeSinistres[info.type] ?? info.type;
      }
      return info.type;
    }
    case "forme":
      return info.famille;
    case "modele":
      return info.modele;
    case "perimetre":
      return info.perimetre;
  }
}

/** Le KPI a-t-il un sens pour l'activité de la société ? (Décision 158,
 * `compatibilite.activitesApplicables` : ex. S/P non-vie seulement pour les
 * sociétés Non-vie et Santé/prévoyance.) Vrai pour tout KPI sans restriction. */
export function kpiApplicable(kpiId: string, societe: string): boolean {
  const activites = DONNEES_EXTRAITES.compatibilite.activitesApplicables?.[kpiId];
  if (!activites) return true;
  const type = DEMO_SFCR[societe]?.type;
  return !!type && activites.includes(type);
}

/** Compatibilité d'un KPI pour une sélection : pire verdict de
 * `compatibilite.matrice[kpi][axe]` sur les axes où les sociétés diffèrent.
 * Les sociétés pour lesquelles le KPI est sans objet (kpiApplicable) ne
 * comptent pas : elles n'entrent dans aucune comparaison. */
export function compatibiliteKpi(kpiId: string, societesSelection: string[]): CompatKpi {
  const { matrice, axes, ordreVerdicts } = DONNEES_EXTRAITES.compatibilite;
  const regles = matrice[kpiId];
  const societes = societesSelection.filter((s) => kpiApplicable(kpiId, s));
  if (!regles || societes.length < 2) return COMPATIBLE;

  let pire: VerdictCompat = "C";
  let sansObjet = false;
  const notes: NoteCompat[] = [];
  for (const axe of axes) {
    const regle = regles[axe];
    if (!regle) continue;
    const valeurs = new Set(societes.map((s) => valeurAxe(s, axe, kpiId)).filter((v) => v !== null));
    if (valeurs.size < 2) continue; // les sociétés ne diffèrent pas sur cet axe
    if (regle.verdict === "NA") sansObjet = true;
    if (ordreVerdicts[regle.verdict] > ordreVerdicts[pire]) pire = regle.verdict;
    if ((regle.verdict === "N" || regle.verdict === "R") && regle.note) {
      notes.push({ axe, verdict: regle.verdict, note: regle.note });
    }
  }
  notes.sort((a, b) => ordreVerdicts[b.verdict] - ordreVerdicts[a.verdict]);
  return { verdict: pire, sansObjet, notes };
}

/** Texte d'une note de compatibilité (une ligne par axe). */
export function texteNotesCompat(notes: NoteCompat[]): string {
  return notes.map((n) => `${LIBELLE_AXE[n.axe]} : ${n.note}`).join("\n\n");
}

// ───────────────────────── Groupes de pairs ─────────────────────────

/** Groupe de pairs (activité · modèle · périmètre) d'une société, ou null. */
export function groupePairsDe(societe: string): GroupePairs | null {
  const id = DEMO_SFCR[societe]?.groupePairs;
  if (!id) return null;
  return DONNEES_EXTRAITES.groupesPairs.find((g) => g.id === id) ?? null;
}

/** La société de référence + ses pairs les plus proches en TAILLE, `max` sociétés
 * au total : écart de SCR total (M€) le plus faible par rapport à la référence ;
 * pairs sans SCR en dernier ; égalité (ou SCR de la référence absent) : ordre
 * alphabétique. Ne sert qu'à choisir quelles sociétés afficher : le calcul de
 * « Position parmi les pairs » utilise, lui, tout le groupe de pairs. */
export function pairsLesPlusProches(reference: string, max: number): string[] {
  const groupe = groupePairsDe(reference);
  if (!groupe) return [reference];
  const scr = (s: string): number | null => {
    const v = kpisSociete(s)["scr_total"]?.valeur;
    return typeof v === "number" && Number.isFinite(v) ? v : null;
  };
  const ref = scr(reference);
  const ecart = (s: string): number | null => {
    const v = scr(s);
    return ref === null || v === null ? null : Math.abs(v - ref);
  };
  const autres = groupe.societes
    .filter((s) => s !== reference)
    .sort((a, b) => {
      const ea = ecart(a);
      const eb = ecart(b);
      if (ea === null && eb === null) return a.localeCompare(b, "fr");
      if (ea === null) return 1;
      if (eb === null) return -1;
      return ea - eb || a.localeCompare(b, "fr");
    });
  return [reference, ...autres.slice(0, Math.max(0, max - 1))];
}

/** Groupe de pairs partagé par TOUTES les sociétés données (null sinon). */
export function groupePairsCommun(societes: string[]): GroupePairs | null {
  if (societes.length === 0) return null;
  const premier = groupePairsDe(societes[0]);
  if (!premier) return null;
  return societes.every((s) => DEMO_SFCR[s]?.groupePairs === premier.id) ? premier : null;
}

// ───────────────────── Périmètre solo / groupe ─────────────────────

export type PartitionPerimetre = {
  /** Sociétés du périmètre retenu (toutes si la liste n'est pas mélangée). */
  gardees: string[];
  /** Sociétés de l'autre périmètre, écartées (vide si la liste n'est pas mélangée). */
  ecartees: string[];
  /** Périmètre retenu : le plus représenté, solo en cas d'égalité. */
  perimetre: "solo" | "groupe";
  /** La liste mélange solo et groupe. */
  melange: boolean;
};

/** Règle du périmètre majoritaire : solo et groupe ne se comparent ni ne se
 * moyennent entre eux (un groupe consolide ses filiales). Si la liste mélange
 * les deux, on ne garde que le périmètre le plus représenté (solo en cas
 * d'égalité) ; l'ordre d'entrée est conservé. */
export function perimetreMajoritaire(societes: string[]): PartitionPerimetre {
  const estGroupe = (s: string) => DEMO_SFCR[s]?.perimetre === "groupe";
  const groupes = societes.filter(estGroupe);
  const solos = societes.filter((s) => !estGroupe(s));
  const melange = solos.length > 0 && groupes.length > 0;
  const perimetre = groupes.length > solos.length ? "groupe" : "solo";
  if (!melange) return { gardees: societes, ecartees: [], perimetre, melange };
  return perimetre === "groupe"
    ? { gardees: groupes, ecartees: solos, perimetre, melange }
    : { gardees: solos, ecartees: groupes, perimetre, melange };
}
