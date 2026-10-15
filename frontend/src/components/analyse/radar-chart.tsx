"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { AXES_RADAR, DEMO_SFCR, KPI_PAR_ID, kpisSociete } from "@/data/analyse-demo";
import { kpiLabelCourt } from "@/lib/analyse-utils";
import { DONNEES_EXTRAITES } from "@/lib/donnees-extraites-utils";
import { AvertissementKpi } from "./avertissement-kpi";

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

function pct(valeur: number): string {
  return `${valeur.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
}

// Axes du radar : les modules réellement présents dans composition_modules_pct
// (parts de chaque module dans la somme des modules de base, total 100 %), dans
// l'ordre habituel. L'opérationnel n'en fait pas partie.
const CLES_COMPOSITION = new Set(
  Object.values(DONNEES_EXTRAITES.indicateursParSociete).flatMap((i) =>
    i.composition_modules_pct ? Object.keys(i.composition_modules_pct) : []
  )
);
const AXES_PARTS = AXES_RADAR.filter((id) => CLES_COMPOSITION.has(id));

/** Profil d'une société : dessiné (parts connues, périmètre retenu) ou non.
 * - modèle interne : composition_modules_pct = null (parts non comparables
 *   aux sociétés en formule standard) ;
 * - périmètre : un radar de groupe ne se compare qu'à d'autres groupes ;
 * `avert` : modules avec un avertissement (base non comparable) — le polygone
 * reste dessiné, la légende porte le marqueur. */
type Profil = {
  soc: string;
  avert: { modules: string[]; note: string } | null;
} & (
  | { etat: "dessine"; parts: number[] }
  | { etat: "modele-interne" | "parts-absentes" | "autre-perimetre"; info: string }
);

/** Radar en PARTS du SCR de base (profil de risque, pas la taille) — SVG maison
 * (pas de recharts), légende cliquable pour masquer/afficher une société. */
export function RadarComparatif({ societesComparees }: { societesComparees: string[] }) {
  const [masquees, setMasquees] = useState<string[]>([]);

  const axesLabels = AXES_PARTS.map((id) => kpiLabelCourt(KPI_PAR_ID[id]));
  const nbAxes = AXES_PARTS.length;

  // 1. Parts disponibles (composition connue pour tous les axes).
  const brut = societesComparees.map((soc) => {
    const composition = DONNEES_EXTRAITES.indicateursParSociete[soc]?.composition_modules_pct ?? null;
    const parts = composition
      ? AXES_PARTS.map((id) => {
          const v = composition[id];
          return typeof v === "number" && Number.isFinite(v) ? v : null;
        })
      : null;
    return { soc, parts: parts && parts.every((v) => v !== null) ? (parts as number[]) : null };
  });

  // 2. Périmètre : si solo et groupe se mélangent parmi les sociétés
  // dessinables, on garde le périmètre le plus représenté (solo en cas
  // d'égalité) — même règle que les moyennes du tableau comparatif.
  const dessinables = brut.filter((b) => b.parts !== null);
  const perimetreDe = (soc: string) => DEMO_SFCR[soc]?.perimetre ?? "solo";
  const nbSolo = dessinables.filter((b) => perimetreDe(b.soc) === "solo").length;
  const nbGroupe = dessinables.length - nbSolo;
  const melange = nbSolo > 0 && nbGroupe > 0;
  const perimetreRetenu: "solo" | "groupe" = nbGroupe > nbSolo ? "groupe" : "solo";

  const profils: Profil[] = brut.map(({ soc, parts }) => {
    const kpis = kpisSociete(soc);
    const concernes = AXES_PARTS.flatMap((id, i) =>
      kpis[id]?.avertissement ? [{ label: axesLabels[i], note: kpis[id].noteAvertissement ?? "" }] : []
    );
    const avert =
      concernes.length > 0
        ? {
            modules: concernes.map((m) => m.label),
            // Notes distinctes (souvent identiques pour tous les modules d'une société).
            note: Array.from(new Set(concernes.map((m) => m.note).filter((n) => n !== ""))).join("\n\n"),
          }
        : null;
    if (parts === null) {
      const modeleInterne = DEMO_SFCR[soc]?.modele === "Modèle interne";
      return modeleInterne
        ? {
            soc,
            avert,
            etat: "modele-interne",
            info: "modèle interne : parts non comparables aux sociétés en formule standard",
          }
        : { soc, avert, etat: "parts-absentes", info: "parts du SCR de base non disponibles" };
    }
    if (melange && perimetreDe(soc) !== perimetreRetenu) {
      return { soc, avert, etat: "autre-perimetre", info: "périmètre différent : non comparable" };
    }
    return { soc, avert, etat: "dessine", parts };
  });
  const dessinees = profils.filter((p): p is Extract<Profil, { etat: "dessine" }> => p.etat === "dessine");

  // Échelle commune à tous les axes : de 0 au plus grand pourcentage de la
  // sélection (sociétés dessinées, visibles ou masquées — masquer ne
  // redimensionne pas), arrondi à la dizaine supérieure. Jamais 0 ni NaN.
  const maxPct = Math.max(0, ...dessinees.flatMap((p) => p.parts));
  const echelle = Math.min(100, Math.max(10, Math.ceil(maxPct / 10) * 10));
  const pasAnneau = echelle > 50 ? 20 : 10;
  const anneaux: number[] = [];
  for (let v = pasAnneau; v <= echelle; v += pasAnneau) anneaux.push(v);
  if (anneaux[anneaux.length - 1] !== echelle) anneaux.push(echelle);

  // Couleurs attribuées par POSITION dans la sélection (stables, même pour une
  // société non dessinée).
  const couleurs: Record<string, string> = Object.fromEntries(
    societesComparees.map((s, i) => [s, PALETTE[i % PALETTE.length]])
  );

  const toggle = (soc: string) =>
    setMasquees((prev) => (prev.includes(soc) ? prev.filter((s) => s !== soc) : [...prev, soc]));

  const visibles = dessinees.filter((p) => !masquees.includes(p.soc));
  const libelleEtat = (p: Profil) =>
    p.etat === "modele-interne" ? "modèle interne" : p.etat === "autre-perimetre" ? "périmètre différent" : "parts indisponibles";

  return (
    <div className="bg-surface border border-border rounded-[var(--radius-lg)] p-5 w-full">
      <div className="flex items-center gap-3 flex-wrap mb-2">
        <span className="font-body text-base font-medium text-text-primary">Profil de risque (parts du SCR de base)</span>
        <span className="flex-1" />
        {profils.map((p) => (
          // Le marqueur d'avertissement est un frère du bouton de légende (jamais
          // un bouton dans un bouton) ; il garde sa pleine opacité si masquée.
          <span key={p.soc} className="inline-flex items-center">
            {p.etat === "dessine" ? (
              <button
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
                title={p.info.charAt(0).toUpperCase() + p.info.slice(1)}
                className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs text-text-tertiary cursor-help"
              >
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ border: "1.5px solid var(--text-tertiary)" }}
                  aria-hidden="true"
                />
                {p.soc} — {libelleEtat(p)}
                <span className="sr-only">. {p.info}</span>
              </span>
            )}
            {p.avert && (
              <AvertissementKpi
                titre={`Modules concernés : ${p.avert.modules.join(", ")}`}
                note={p.avert.note}
              />
            )}
          </span>
        ))}
      </div>

      {dessinees.length === 0 ? (
        <p className="text-sm text-text-secondary text-center py-10">
          Aucune société sélectionnée n&apos;a un profil en parts comparable (modèle interne ou périmètre différent).
        </p>
      ) : (
        <>
          <svg viewBox={`0 0 ${LARGEUR} ${HAUTEUR}`} width="100%" style={{ height: "auto", maxHeight: HAUTEUR }} className="mx-auto block overflow-visible" role="img" aria-label="Radar comparatif du profil de risque, en parts du SCR de base">
            {/* Grille polaire : anneaux gradués en % de la somme des modules */}
            {anneaux.map((v) => (
              <polygon
                key={v}
                points={Array.from({ length: nbAxes }, (_, i) => {
                  const p = pointSurAxe(i, nbAxes, v / echelle);
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
            {/* Graduation des anneaux (le long du premier axe) */}
            {anneaux.map((v) => {
              const p = pointSurAxe(0, nbAxes, v / echelle);
              return (
                <text
                  key={`g${v}`}
                  x={p.x + 4}
                  y={p.y + 11}
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  fill="var(--text-tertiary)"
                >
                  {v} %
                </text>
              );
            })}
            {/* Polygones : sociétés dessinées et non masquées ; sommets avec valeur au survol */}
            {visibles.map((p) => {
              const sommets = p.parts.map((v, i) => ({ v, pt: pointSurAxe(i, nbAxes, v / echelle) }));
              return (
                <g key={p.soc}>
                  <polygon
                    points={sommets.map((s) => `${s.pt.x},${s.pt.y}`).join(" ")}
                    fill={couleurs[p.soc]}
                    fillOpacity={0.15}
                    stroke={couleurs[p.soc]}
                    strokeWidth={2}
                  />
                  {sommets.map((s, i) => (
                    <circle key={i} cx={s.pt.x} cy={s.pt.y} r={3} fill={couleurs[p.soc]}>
                      <title>{`${p.soc} — ${axesLabels[i]} : ${pct(s.v)}`}</title>
                    </circle>
                  ))}
                </g>
              );
            })}
          </svg>

          {melange && (
            <p role="note" className="mt-2 text-xs leading-relaxed text-text-secondary">
              Solo et groupes sont mélangés : seul le périmètre « {perimetreRetenu === "solo" ? "solo" : "groupe"} » est
              dessiné, un radar de groupe ne se compare qu&apos;à d&apos;autres groupes.
            </p>
          )}

          {/* Valeurs en % : table courte sous le graphique */}
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left font-medium text-text-tertiary py-1.5 pr-3">Part du SCR de base</th>
                  {dessinees.map((p) => (
                    <th
                      key={p.soc}
                      className={cn(
                        "text-right font-medium text-text-secondary py-1.5 px-2 whitespace-nowrap",
                        masquees.includes(p.soc) && "opacity-35"
                      )}
                    >
                      <span
                        className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle"
                        style={{ background: couleurs[p.soc] }}
                        aria-hidden="true"
                      />
                      {p.soc}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {axesLabels.map((label, i) => (
                  <tr key={label} className="border-b border-border last:border-0">
                    <td className="py-1.5 pr-3 text-text-secondary">{label}</td>
                    {dessinees.map((p) => (
                      <td
                        key={p.soc}
                        className={cn(
                          "text-right font-mono text-text-primary py-1.5 px-2",
                          masquees.includes(p.soc) && "opacity-35"
                        )}
                      >
                        {pct(p.parts[i])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
