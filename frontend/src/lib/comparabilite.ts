/**
 * comparabilite.ts — Règles de comparaison entre sociétés (Décisions 149-155).
 *
 * `donnees-extraites.json` porte la matrice de compatibilité par KPI et par
 * axe (activité, forme juridique, modèle de capital, périmètre) : le front-end
 * l'applique, il ne la recalcule pas. Verdicts : C (comparable), R (avec
 * réserve), N (non comparable), NA (sans objet pour certaines sociétés).
 */

import { DEMO_SFCR } from "@/data/analyse-demo";
import { DONNEES_EXTRAITES, type AxeCompat, type VerdictCompat } from "@/lib/donnees-extraites-utils";

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

/** Compatibilité d'un KPI pour une sélection : pire verdict de
 * `compatibilite.matrice[kpi][axe]` sur les axes où les sociétés diffèrent. */
export function compatibiliteKpi(kpiId: string, societes: string[]): CompatKpi {
  const { matrice, axes, ordreVerdicts } = DONNEES_EXTRAITES.compatibilite;
  const regles = matrice[kpiId];
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
