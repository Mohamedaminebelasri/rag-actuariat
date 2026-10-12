/**
 * seuils-config.ts — Seuils du feu tricolore (onglet Analyse uniquement).
 *
 * Deux natures de seuil, à ne jamais confondre dans l'UI :
 * - LÉGAL (Solvabilité II) : verrouillé.
 * - CONVENTIONNEL (repère de marché) : fixe, non réglable par l'utilisateur.
 */

/** Ratio SCR/MCR < ce seuil = exigence légale Solvabilité II non couverte. */
export const SEUIL_LEGAL = 100;

/** Ratio SCR ≥ ce seuil = zone "solide" par convention de marché (pas une
 * règle légale). Fixé à 200 %. Pour le changer : modifier cette constante. */
export const SEUIL_VERT_SCR_DEFAUT = 200;
