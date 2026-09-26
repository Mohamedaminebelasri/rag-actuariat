"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { AXES_RADAR, KPI_PAR_ID, kpisSociete } from "@/data/analyse-demo";
import { kpiLabelCourt } from "@/lib/analyse-utils";

const PALETTE = ["#2563eb", "#16a34a", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#db2777", "#65a30d"];

const LARGEUR = 480;
const HAUTEUR = 340;
const CENTER_X = LARGEUR / 2;
const CENTER_Y = HAUTEUR / 2;
const RAYON = HAUTEUR / 2 - 56;

function pointSurAxe(indexAxe: number, nbAxes: number, ratio: number) {
  const angle = (Math.PI * 2 * indexAxe) / nbAxes - Math.PI / 2;
  const r = RAYON * Math.max(0, Math.min(1, ratio));
  return { x: CENTER_X + r * Math.cos(angle), y: CENTER_Y + r * Math.sin(angle), cos: Math.cos(angle), sin: Math.sin(angle) };
}

/** Port de radar_comparatif() (charts.py, Reflex) — radar SVG maison
 * (pas de recharts), légende cliquable pour masquer/afficher une société. */
export function RadarComparatif({ societesComparees }: { societesComparees: string[] }) {
  const [masquees, setMasquees] = useState<string[]>([]);

  const axesLabels = AXES_RADAR.map((id) => kpiLabelCourt(KPI_PAR_ID[id]));
  const nbAxes = AXES_RADAR.length;

  // Échelle commune : max sur TOUTES les sociétés comparées (visibles ou
  // non), pour que masquer/afficher une société ne redimensionne pas les
  // autres.
  const maxParAxe = AXES_RADAR.map((id) =>
    Math.max(...societesComparees.map((s) => kpisSociete(s)[id]?.valeur ?? 0), 0.01)
  );

  const couleurs: Record<string, string> = Object.fromEntries(
    societesComparees.map((s, i) => [s, PALETTE[i % PALETTE.length]])
  );

  const toggle = (soc: string) =>
    setMasquees((prev) => (prev.includes(soc) ? prev.filter((s) => s !== soc) : [...prev, soc]));

  return (
    <div className="bg-surface border border-border rounded-[var(--radius-lg)] p-5 w-full">
      <div className="flex items-center gap-3 flex-wrap mb-2">
        <span className="font-body text-base font-medium text-text-primary">Profil de risque comparé</span>
        <span className="flex-1" />
        {societesComparees.map((soc) => (
          <button
            key={soc}
            onClick={() => toggle(soc)}
            className={cn(
              "flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs hover:bg-surface-hover transition-opacity",
              masquees.includes(soc) ? "opacity-35" : "opacity-100"
            )}
          >
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: couleurs[soc] }} />
            {soc}
          </button>
        ))}
      </div>

      <svg viewBox={`0 0 ${LARGEUR} ${HAUTEUR}`} width="100%" height={HAUTEUR} className="mx-auto block" role="img" aria-label="Radar comparatif du profil de risque">
        {/* Grille polaire (anneaux concentriques) */}
        {[0.25, 0.5, 0.75, 1].map((f) => (
          <polygon
            key={f}
            points={Array.from({ length: nbAxes }, (_, i) => {
              const p = pointSurAxe(i, nbAxes, f);
              return `${p.x},${p.y}`;
            }).join(" ")}
            fill="none"
            stroke="var(--border)"
            strokeWidth={1}
          />
        ))}
        {/* Axes + labels */}
        {axesLabels.map((label, i) => {
          const bord = pointSurAxe(i, nbAxes, 1);
          const labelPt = pointSurAxe(i, nbAxes, 1.12);
          // Étiquette ancrée vers l'extérieur : jamais par-dessus le polygone.
          const ancre = labelPt.cos > 0.3 ? "start" : labelPt.cos < -0.3 ? "end" : "middle";
          const dx = ancre === "start" ? 8 : ancre === "end" ? -8 : 0;
          const dy = labelPt.sin < -0.3 ? -6 : labelPt.sin > 0.3 ? 12 : 0;
          return (
            <g key={label}>
              <line x1={CENTER_X} y1={CENTER_Y} x2={bord.x} y2={bord.y} stroke="var(--border)" strokeWidth={1} />
              <text
                x={labelPt.x + dx}
                y={labelPt.y + dy}
                textAnchor={ancre}
                dominantBaseline="middle"
                fontSize={14}
                fontFamily="var(--font-body)"
                fill="var(--text-secondary)"
              >
                {label}
              </text>
            </g>
          );
        })}
        {/* Polygones par société */}
        {societesComparees
          .filter((soc) => !masquees.includes(soc))
          .map((soc) => {
            const kpis = kpisSociete(soc);
            const points = AXES_RADAR.map((id, i) => {
              const v = kpis[id]?.valeur ?? 0;
              const ratio = v / maxParAxe[i];
              const p = pointSurAxe(i, nbAxes, ratio);
              return `${p.x},${p.y}`;
            }).join(" ");
            return (
              <polygon
                key={soc}
                points={points}
                fill={couleurs[soc]}
                fillOpacity={0.15}
                stroke={couleurs[soc]}
                strokeWidth={2}
              />
            );
          })}
      </svg>
    </div>
  );
}
