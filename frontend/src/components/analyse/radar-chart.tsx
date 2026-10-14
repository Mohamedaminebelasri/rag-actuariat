"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { AXES_RADAR, KPI_PAR_ID, kpisSociete } from "@/data/analyse-demo";
import { kpiLabelCourt, valeurDisponible } from "@/lib/analyse-utils";

// Palette volontairement SANS signification de risque (pas de vert/orange/
// rouge, déjà pris par le feu tricolore) : bleu, violet, turquoise, gris
// ardoise, chacun en 2 teintes pour distinguer jusqu'à 8 sociétés.
const PALETTE = [
  "#2563eb", // bleu
  "#7c3aed", // violet
  "#0891b2", // turquoise
  "#475569", // gris ardoise
  "#60a5fa", // bleu clair
  "#a78bfa", // violet clair
  "#22d3ee", // turquoise clair
  "#94a3b8", // gris ardoise clair
];

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

/** Profil d'une société sur les axes du radar. Un module ABSENT (n/d) n'est
 * jamais ramené à 0 : la société est alors « incomplète » et n'est pas
 * dessinée (une forme rétractée vers le centre se lirait « sans risque »).
 * Un 0 réel, lui, reste un 0 dessiné. */
type Profil =
  | { soc: string; complet: true; valeurs: number[] }
  | { soc: string; complet: false; absents: string[] };

/** Port de radar_comparatif() (charts.py, Reflex) — radar SVG maison
 * (pas de recharts), légende cliquable pour masquer/afficher une société. */
export function RadarComparatif({ societesComparees }: { societesComparees: string[] }) {
  const [masquees, setMasquees] = useState<string[]>([]);

  const axesLabels = AXES_RADAR.map((id) => kpiLabelCourt(KPI_PAR_ID[id]));
  const nbAxes = AXES_RADAR.length;

  const profils: Profil[] = societesComparees.map((soc) => {
    const kpis = kpisSociete(soc);
    const valeurs = AXES_RADAR.map((id) => valeurDisponible(kpis, id));
    const absents = axesLabels.filter((_, i) => valeurs[i] === null);
    if (absents.length > 0) return { soc, complet: false, absents };
    return { soc, complet: true, valeurs: valeurs.filter((v): v is number => v !== null) };
  });
  const completes = profils.filter((p): p is Extract<Profil, { complet: true }> => p.complet);

  // Échelle commune par axe : max sur les sociétés au profil COMPLET de la
  // sélection (visibles ou masquées), pour que masquer/afficher une société
  // ne redimensionne pas les autres. Sans société complète ou si tout vaut 0,
  // le max reste 0 : le ratio est alors 0 (jamais de division par 0 ni NaN).
  const maxParAxe = AXES_RADAR.map((_, i) => Math.max(0, ...completes.map((p) => p.valeurs[i])));

  // Couleurs attribuées par POSITION dans la sélection (stables, même pour
  // une société incomplète qui n'est pas dessinée).
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
        {profils.map((p) =>
          p.complet ? (
            <button
              key={p.soc}
              onClick={() => toggle(p.soc)}
              className={cn(
                "flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs hover:bg-surface-hover transition-opacity",
                masquees.includes(p.soc) ? "opacity-35" : "opacity-100"
              )}
            >
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: couleurs[p.soc] }} />
              {p.soc}
            </button>
          ) : (
            <span
              key={p.soc}
              title={`Modules n/d : ${p.absents.join(", ")}`}
              className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs text-text-tertiary cursor-help"
            >
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ border: "1.5px solid var(--text-tertiary)" }}
                aria-hidden="true"
              />
              {p.soc} — profil incomplet
              <span className="sr-only">. Modules n/d : {p.absents.join(", ")}</span>
            </span>
          )
        )}
      </div>

      {completes.length === 0 ? (
        <p className="text-sm text-text-secondary text-center py-10">
          Aucune société sélectionnée n&apos;a un profil de risque complet.
        </p>
      ) : (
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
          {/* Polygones : uniquement les sociétés complètes et non masquées */}
          {completes
            .filter((p) => !masquees.includes(p.soc))
            .map((p) => {
              const points = p.valeurs
                .map((v, i) => {
                  const max = maxParAxe[i];
                  const pt = pointSurAxe(i, nbAxes, max > 0 ? v / max : 0);
                  return `${pt.x},${pt.y}`;
                })
                .join(" ");
              return (
                <polygon
                  key={p.soc}
                  points={points}
                  fill={couleurs[p.soc]}
                  fillOpacity={0.15}
                  stroke={couleurs[p.soc]}
                  strokeWidth={2}
                />
              );
            })}
        </svg>
      )}
    </div>
  );
}
