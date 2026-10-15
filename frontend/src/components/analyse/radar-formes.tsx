"use client";

/** Formes de points du radar agrandi : une forme par société EN PLUS de la
 * couleur (accessibilité daltonisme), reprise à l'identique dans la légende. */

export const NB_FORMES = 8;

/** Points d'un polygone-forme centré en (cx, cy) de « rayon » r, pour les formes
 * autres que le rond. Accessibilité daltonisme : forme ET couleur. */
export function pointsForme(forme: number, cx: number, cy: number, r: number): string {
  const poly = (pts: [number, number][]) => pts.map(([x, y]) => `${(cx + x * r).toFixed(1)},${(cy + y * r).toFixed(1)}`).join(" ");
  switch (forme % NB_FORMES) {
    case 1: // carré
      return poly([[-0.85, -0.85], [0.85, -0.85], [0.85, 0.85], [-0.85, 0.85]]);
    case 2: // triangle pointe en haut
      return poly([[0, -1.1], [1, 0.8], [-1, 0.8]]);
    case 3: // losange
      return poly([[0, -1.15], [1.05, 0], [0, 1.15], [-1.05, 0]]);
    case 4: // triangle pointe en bas
      return poly([[-1, -0.8], [1, -0.8], [0, 1.1]]);
    case 5: // croix
      return poly([
        [-0.35, -1], [0.35, -1], [0.35, -0.35], [1, -0.35], [1, 0.35], [0.35, 0.35],
        [0.35, 1], [-0.35, 1], [-0.35, 0.35], [-1, 0.35], [-1, -0.35], [-0.35, -0.35],
      ]);
    case 6: // hexagone
      return poly(Array.from({ length: 6 }, (_, k) => [Math.cos((Math.PI / 3) * k), Math.sin((Math.PI / 3) * k)] as [number, number]));
    case 7: // étoile à 5 branches
      return poly(
        Array.from({ length: 10 }, (_, k) => {
          const rayon = k % 2 === 0 ? 1.15 : 0.5;
          const a = -Math.PI / 2 + (Math.PI / 5) * k;
          return [rayon * Math.cos(a), rayon * Math.sin(a)] as [number, number];
        })
      );
    default:
      return "";
  }
}

/** Point de série : rond pour la forme 0, sinon polygone (carré, triangle…). */
export function PointForme({
  forme, cx, cy, r, couleur, opacite = 1, titre,
}: {
  forme: number; cx: number; cy: number; r: number; couleur: string; opacite?: number; titre?: string;
}) {
  const contour = { stroke: "var(--surface)", strokeWidth: 1.25, opacity: opacite };
  return forme % NB_FORMES === 0 ? (
    <circle cx={cx} cy={cy} r={r} fill={couleur} {...contour}>
      {titre && <title>{titre}</title>}
    </circle>
  ) : (
    <polygon points={pointsForme(forme, cx, cy, r)} fill={couleur} {...contour}>
      {titre && <title>{titre}</title>}
    </polygon>
  );
}

/** Pastille de légende : même forme que les points du radar. */
export function GlypheForme({ forme, couleur, creux }: { forme: number; couleur?: string; creux?: boolean }) {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" className="flex-shrink-0">
      {creux ? (
        <circle cx="7" cy="7" r="4.5" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5" />
      ) : forme % NB_FORMES === 0 ? (
        <circle cx="7" cy="7" r="4.6" fill={couleur} />
      ) : (
        <polygon points={pointsForme(forme, 7, 7, 4.8)} fill={couleur} />
      )}
    </svg>
  );
}
