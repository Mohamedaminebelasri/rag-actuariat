"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { AvertissementKpi } from "./avertissement-kpi";

/** Série dessinée : une société avec ses parts (une par axe). */
export type SerieRadar = {
  soc: string;
  couleur: string;
  /** Rang dans la sélection : choisit la forme du point (en plus de la couleur). */
  forme: number;
  parts: number[];
  avert: { modules: string[]; note: string } | null;
};

/** Société non dessinée (modèle interne, périmètre minoritaire…) : puce creuse. */
export type SocieteNonTracee = {
  soc: string;
  libelle: string;
  info: string;
  avert: { modules: string[]; note: string } | null;
};

const NB_FORMES = 8;

/** Points d'un polygone-forme centré en (cx, cy) de « rayon » r, pour les formes
 * autres que le rond. Accessibilité daltonisme : forme ET couleur. */
function pointsForme(forme: number, cx: number, cy: number, r: number): string {
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
function PointForme({
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
function GlypheForme({ forme, couleur, creux }: { forme: number; couleur?: string; creux?: boolean }) {
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

function pct(valeur: number): string {
  return `${valeur.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
}

/** Libellé d'axe sur 1 ou 2 lignes (étroit : coupé à l'espace le plus central). */
function lignesLabel(label: string, etroit: boolean): string[] {
  if (!etroit || label.length <= 14) return [label];
  const milieu = label.length / 2;
  let meilleur = -1;
  for (let i = 0; i < label.length; i += 1) {
    if (label[i] === " " && (meilleur === -1 || Math.abs(i - milieu) < Math.abs(meilleur - milieu))) meilleur = i;
  }
  return meilleur === -1 ? [label] : [label.slice(0, meilleur), label.slice(meilleur + 1)];
}

/** Vue agrandie du radar (fenêtre modale en portail) : tracés plus grands,
 * remplissage très léger pour voir les superpositions, une forme de point par
 * société, mise en avant d'une société au survol / au clic dans la légende. */
export function RadarAgrandi({
  axes,
  series,
  nonTracees,
  echelle,
  anneaux,
  noteMelange,
  onClose,
}: {
  axes: string[];
  series: SerieRadar[];
  nonTracees: SocieteNonTracee[];
  echelle: number;
  anneaux: number[];
  noteMelange: string | null;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const [survol, setSurvol] = useState<string | null>(null);
  const [epingle, setEpingle] = useState<string | null>(null);
  const [etroit, setEtroit] = useState(false);
  const actif = survol ?? epingle;

  // Écran étroit (mobile) : géométrie compacte et libellés d'axe sur 2 lignes.
  useEffect(() => {
    const maj = () => setEtroit(window.innerWidth < 640);
    maj();
    window.addEventListener("resize", maj);
    return () => window.removeEventListener("resize", maj);
  }, []);

  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);
  const fermer = useCallback(() => onCloseRef.current(), []);

  // Échap ferme (sauf si une note d'avertissement ouverte doit se fermer
  // d'abord), scroll du fond bloqué, focus piégé puis rendu à l'ouverture.
  useEffect(() => {
    const precedent = document.activeElement as HTMLElement | null;
    const ancienOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialogRef.current?.focus();

    const surClavier = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (document.querySelector('[role="dialog"][aria-label="Valeur non comparable"]')) return;
        fermer();
        return;
      }
      if (e.key !== "Tab" || !dialogRef.current) return;
      const focalisables = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>('button, [href], [tabindex]:not([tabindex="-1"])')
      ).filter((el) => !el.hasAttribute("disabled"));
      if (focalisables.length === 0) {
        e.preventDefault();
        return;
      }
      const premier = focalisables[0];
      const dernier = focalisables[focalisables.length - 1];
      const courant = document.activeElement;
      if (e.shiftKey && (courant === premier || courant === dialogRef.current)) {
        e.preventDefault();
        dernier.focus();
      } else if (!e.shiftKey && courant === dernier) {
        e.preventDefault();
        premier.focus();
      } else if (!dialogRef.current.contains(courant)) {
        e.preventDefault();
        premier.focus();
      }
    };
    document.addEventListener("keydown", surClavier);
    return () => {
      document.removeEventListener("keydown", surClavier);
      document.body.style.overflow = ancienOverflow;
      precedent?.focus?.();
    };
  }, [fermer]);

  const nbAxes = axes.length;
  const G = etroit
    ? { W: 520, H: 500, cx: 260, cy: 250, R: 128, police: 14, pointR: 5.2, grad: 10, k: 1.17 }
    : { W: 880, H: 600, cx: 440, cy: 305, R: 205, police: 17, pointR: 6.2, grad: 12, k: 1.13 };

  const pointSurAxe = (i: number, ratio: number, k = 1) => {
    const angle = (Math.PI * 2 * i) / nbAxes - Math.PI / 2;
    const r = G.R * k * Math.max(0, Math.min(1.2, ratio));
    return { x: G.cx + r * Math.cos(angle), y: G.cy + r * Math.sin(angle), cos: Math.cos(angle), sin: Math.sin(angle) };
  };

  // La société mise en avant est dessinée en dernier (au-dessus des autres).
  const ordre = [...series].sort((a, b) => Number(a.soc === actif) - Number(b.soc === actif));
  const basculer = (soc: string) => setEpingle((p) => (p === soc ? null : soc));

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-0 sm:p-6"
      onClick={(e) => {
        if (e.target === e.currentTarget) fermer();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Radar agrandi : profil de risque (parts du SCR de base)"
        tabIndex={-1}
        className="relative w-full h-full sm:w-[90vw] sm:h-auto sm:max-h-[90vh] sm:max-w-[1200px] bg-surface sm:rounded-2xl shadow-2xl sm:border border-border flex flex-col overflow-hidden outline-none"
      >
        <div className="flex items-center gap-3 px-4 sm:px-5 py-3 border-b border-border flex-shrink-0">
          <h3 className="font-heading text-lg text-text-primary flex-1 min-w-0 truncate">
            Profil de risque (parts du SCR de base)
          </h3>
          <button
            onClick={fermer}
            aria-label="Fermer le radar agrandi"
            className="w-8 h-8 rounded-full flex items-center justify-center text-text-secondary hover:bg-surface-hover"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 min-h-0 overflow-auto p-3 sm:p-5 flex flex-col lg:flex-row gap-4 lg:gap-6">
          <svg
            viewBox={`0 0 ${G.W} ${G.H}`}
            className="block w-full lg:flex-1 min-w-0 h-auto max-h-[70vh] self-center"
            role="img"
            aria-label="Radar agrandi du profil de risque, en parts du SCR de base"
          >
            {anneaux.map((v) => (
              <polygon
                key={v}
                points={Array.from({ length: nbAxes }, (_, i) => {
                  const p = pointSurAxe(i, v / echelle);
                  return `${p.x},${p.y}`;
                }).join(" ")}
                fill="none"
                stroke="var(--border-hover)"
                strokeWidth={1}
              />
            ))}
            {axes.map((label, i) => {
              const bord = pointSurAxe(i, 1);
              const lp = pointSurAxe(i, 1, G.k);
              const ancre = lp.cos > 0.3 ? "start" : lp.cos < -0.3 ? "end" : "middle";
              const dx = ancre === "start" ? 8 : ancre === "end" ? -8 : 0;
              const lignes = lignesLabel(label, etroit);
              const dy0 = lp.sin < -0.3 ? -6 - (lignes.length - 1) * (G.police + 2) : lp.sin > 0.3 ? 14 : 0;
              return (
                <g key={label}>
                  <line x1={G.cx} y1={G.cy} x2={bord.x} y2={bord.y} stroke="var(--border-hover)" strokeWidth={1} />
                  <text
                    x={lp.x + dx}
                    y={lp.y + dy0}
                    textAnchor={ancre}
                    dominantBaseline="middle"
                    fontSize={G.police}
                    fontFamily="var(--font-body)"
                    fontWeight={500}
                    fill="var(--text-primary)"
                  >
                    {lignes.map((l, k) => (
                      <tspan key={k} x={lp.x + dx} dy={k === 0 ? 0 : G.police + 2}>
                        {l}
                      </tspan>
                    ))}
                  </text>
                </g>
              );
            })}
            {anneaux.map((v) => {
              const p = pointSurAxe(0, v / echelle);
              return (
                <text
                  key={`g${v}`}
                  x={p.x + 5}
                  y={p.y + 4}
                  fontSize={G.grad}
                  fontFamily="var(--font-mono)"
                  fill="var(--text-tertiary)"
                >
                  {v} %
                </text>
              );
            })}
            {ordre.map((s) => {
              const att = actif !== null && actif !== s.soc;
              const opacite = att ? 0.2 : 1;
              const sommets = s.parts.map((v, i) => ({ v, pt: pointSurAxe(i, v / echelle) }));
              return (
                <g key={s.soc}>
                  <polygon
                    points={sommets.map((p) => `${p.pt.x},${p.pt.y}`).join(" ")}
                    fill={s.couleur}
                    fillOpacity={att ? 0.03 : actif === s.soc ? 0.14 : 0.06}
                    stroke={s.couleur}
                    strokeWidth={actif === s.soc ? 3.5 : 2}
                    opacity={opacite}
                  />
                  {sommets.map((p, i) => (
                    <PointForme
                      key={i}
                      forme={s.forme}
                      cx={p.pt.x}
                      cy={p.pt.y}
                      r={actif === s.soc ? G.pointR + 1.5 : G.pointR}
                      couleur={s.couleur}
                      opacite={opacite}
                      titre={`${s.soc} — ${axes[i]} : ${pct(p.v)}`}
                    />
                  ))}
                </g>
              );
            })}
          </svg>

          <div className="lg:w-64 flex-shrink-0 flex flex-col gap-1">
            <p className="text-xs text-text-tertiary mb-1">
              Survolez ou touchez une société pour mettre son tracé en avant ; un second clic réinitialise.
            </p>
            {series.map((s) => (
              <span key={s.soc} className="inline-flex items-center">
                <button
                  onPointerEnter={(e) => e.pointerType === "mouse" && setSurvol(s.soc)}
                  onPointerLeave={() => setSurvol(null)}
                  onClick={() => basculer(s.soc)}
                  aria-pressed={epingle === s.soc}
                  className={cn(
                    "flex-1 min-w-0 flex items-center gap-2 px-2 py-1.5 rounded-[var(--radius-md)] text-sm text-left transition-colors hover:bg-surface-hover",
                    actif === s.soc ? "bg-surface-secondary text-text-primary font-medium" : "text-text-secondary",
                    actif !== null && actif !== s.soc && "opacity-60"
                  )}
                >
                  <GlypheForme forme={s.forme} couleur={s.couleur} />
                  <span className="truncate">{s.soc}</span>
                </button>
                {s.avert && (
                  <AvertissementKpi titre={`Modules concernés : ${s.avert.modules.join(", ")}`} note={s.avert.note} />
                )}
              </span>
            ))}
            {nonTracees.map((n) => (
              <span key={n.soc} className="inline-flex items-center">
                <span
                  title={n.info.charAt(0).toUpperCase() + n.info.slice(1)}
                  className="flex-1 min-w-0 flex items-center gap-2 px-2 py-1.5 text-sm text-text-tertiary cursor-help"
                >
                  <GlypheForme forme={0} creux />
                  <span className="truncate">
                    {n.soc} — {n.libelle}
                  </span>
                  <span className="sr-only">. {n.info}</span>
                </span>
                {n.avert && (
                  <AvertissementKpi titre={`Modules concernés : ${n.avert.modules.join(", ")}`} note={n.avert.note} />
                )}
              </span>
            ))}
            {noteMelange && (
              <p role="note" className="mt-2 text-xs leading-relaxed text-text-secondary">
                {noteMelange}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
