/**
 * seuils-config.ts — Seuils du feu tricolore (onglet Analyse uniquement).
 *
 * Deux natures de seuil, à ne jamais confondre dans l'UI :
 * - LÉGAL (Solvabilité II) : verrouillé, jamais modifiable par l'utilisateur.
 * - CONVENTIONNEL (repère de marché) : modifiable, persisté en localStorage.
 */

/** Ratio SCR/MCR < ce seuil = exigence légale Solvabilité II non couverte.
 * Verrouillé — ne jamais exposer de réglage pour cette valeur. */
export const SEUIL_LEGAL = 100;

/** Ratio SCR ≥ ce seuil = zone "solide" par convention de marché (pas une
 * règle légale). Valeur par défaut ; modifiable via le panneau Seuils. */
export const SEUIL_VERT_SCR_DEFAUT = 200;

/** Largeur (en points de %) de la zone "proche du seuil" modifiable, de
 * part et d'autre de celui-ci — évite l'effet de falaise visuel. Élargie
 * de 5 à 10 points (retour utilisateur) pour couvrir SGAM AG2R LA MONDIALE
 * (191 %) et Allianz Vie (192 %), pas seulement Crédit Agricole Assurances
 * (195 %). */
export const MARGE_PROCHE_SEUIL = 10;

const CLE_STOCKAGE = "iconcilio-analyse-seuil-vert-scr";

/** Lit le seuil vert stocké par l'utilisateur. Jamais d'exception : si le
 * stockage est indisponible (navigation privée, quota, SSR...), retombe
 * silencieusement sur la valeur par défaut. */
export function lireSeuilVertStocke(): number {
  try {
    const brut = window.localStorage.getItem(CLE_STOCKAGE);
    if (brut === null) return SEUIL_VERT_SCR_DEFAUT;
    const valeur = Number(brut);
    return Number.isFinite(valeur) && valeur > SEUIL_LEGAL ? valeur : SEUIL_VERT_SCR_DEFAUT;
  } catch {
    return SEUIL_VERT_SCR_DEFAUT;
  }
}

/** Écrit le seuil vert choisi. Échec silencieux si le stockage est
 * indisponible — l'état React reste la source de vérité pour la session
 * en cours, seule la persistance entre sessions est perdue. */
export function ecrireSeuilVertStocke(valeur: number): void {
  try {
    window.localStorage.setItem(CLE_STOCKAGE, String(valeur));
  } catch {
    // stockage indisponible : pas bloquant, pas de remontée d'erreur à l'UI
  }
}

export function reinitialiserSeuilVertStocke(): void {
  try {
    window.localStorage.removeItem(CLE_STOCKAGE);
  } catch {
    // idem
  }
}
