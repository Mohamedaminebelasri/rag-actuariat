"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { AXES_RADAR, DEMO_SFCR, KPI_PAR_ID, kpisSociete } from "@/data/analyse-demo";
import { kpiLabelCourt } from "@/lib/analyse-utils";
import { DONNEES_EXTRAITES } from "@/lib/donnees-extraites-utils";
import { perimetreMajoritaire } from "@/lib/comparabilite";
import { AvertissementKpi } from "./avertissement-kpi";
import { CarteAgrandissable } from "./carte-agrandissable";
import { GlypheForme, PointForme } from "./radar-formes";

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
type Avert = { modules: string[]; note: string } | null;
type Profil = { soc: string; avert: Avert } & (
  | { etat: "dessine"; parts: number[] }
  | { etat: "modele-interne" | "parts-absentes" | "autre-perimetre"; info: string }
);
type Dessine = Extract<Profil, { etat: "dessine" }>;

type Geometrie = {
  W: number; H: number; cx: number; cy: number; R: number;
  police: number; grad: number; k: number; pointR: number;
};
const G_NORMALE: Geometrie = { W: 480, H: 340, cx: 240, cy: 170, R: 114, police: 14, grad: 10, k: 1.12, pointR: 3 };
const G_GRANDE: Geometrie = { W: 880, H: 600, cx: 440, cy: 305, R: 205, police: 17, grad: 12, k: 1.13, pointR: 6.2 };
const G_ETROITE: Geometrie = { W: 520, H: 500, cx: 260, cy: 250, R: 128, police: 14, grad: 10, k: 1.17, pointR: 5.2 };

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

/** Radar en PARTS du SCR de base (profil de risque, pas la taille) — SVG maison
 * (pas de recharts). Vue normale : légende cliquable pour masquer/afficher une
 * société. Vue agrandie : radar plus grand, remplissage léger, une forme de
 * point par société, mise en avant d'une société (survol/clic dans la légende
 * ou survol d'une ligne du tableau), puis le tableau des parts. */
export function RadarComparatif({ societesComparees }: { societesComparees: string[] }) {
  const [masquees, setMasquees] = useState<string[]>([]);
  const [survol, setSurvol] = useState<string | null>(null);
  const [epingle, setEpingle] = useState<string | null>(null);

  const axesLabels = AXES_PARTS.map((id) => kpiLabelCourt(KPI_PAR_ID[id]));

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
  // dessinables, seul le périmètre majoritaire est dessiné (règle partagée avec
  // les moyennes du tableau comparatif).
  const partition = perimetreMajoritaire(brut.filter((b) => b.parts !== null).map((b) => b.soc));
  const { melange, perimetre: perimetreRetenu } = partition;

  const profils: Profil[] = brut.map(({ soc, parts }) => {
    const kpis = kpisSociete(soc);
    const concernes = AXES_PARTS.flatMap((id, i) =>
      kpis[id]?.avertissement ? [{ label: axesLabels[i], note: kpis[id].noteAvertissement ?? "" }] : []
    );
    const avert: Avert =
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
    if (partition.ecartees.includes(soc)) {
      return { soc, avert, etat: "autre-perimetre", info: "périmètre différent : non comparable" };
    }
    return { soc, avert, etat: "dessine", parts };
  });
  const dessinees = profils.filter((p): p is Dessine => p.etat === "dessine");

  // Échelle commune à tous les axes : de 0 au plus grand pourcentage de la
  // sélection (sociétés dessinées, visibles ou masquées — masquer ne
  // redimensionne pas), arrondi à la dizaine supérieure. Jamais 0 ni NaN.
  const maxPct = Math.max(0, ...dessinees.flatMap((p) => p.parts));
  const echelle = Math.min(100, Math.max(10, Math.ceil(maxPct / 10) * 10));
  // Pas des anneaux : divise l'échelle (pas d'anneau final tassé contre le précédent).
  const pasAnneau = echelle <= 50 ? 10 : echelle % 20 === 0 ? 20 : echelle % 30 === 0 ? 30 : 10;
  const anneaux: number[] = [];
  for (let v = pasAnneau; v <= echelle; v += pasAnneau) anneaux.push(v);
  if (anneaux[anneaux.length - 1] !== echelle) anneaux.push(echelle);

  // Couleurs attribuées par POSITION dans la sélection (stables, même pour une
  // société non dessinée).
  const couleurs: Record<string, string> = Object.fromEntries(
    societesComparees.map((s, i) => [s, PALETTE[i % PALETTE.length]])
  );
  const noteMelange = melange
    ? `Solo et groupes sont mélangés : seul le périmètre « ${perimetreRetenu === "solo" ? "solo" : "groupe"} » est dessiné, un radar de groupe ne se compare qu'à d'autres groupes.`
    : null;

  return (
    <CarteAgrandissable titre="Profil de risque (parts du SCR de base)" nom="le radar">
      {({ agrandi, ouvrir }) => (
        <CorpsRadar
          agrandi={agrandi}
          ouvrir={ouvrir}
          societesComparees={societesComparees}
          profils={profils}
          dessinees={dessinees}
          axesLabels={axesLabels}
          couleurs={couleurs}
          echelle={echelle}
          anneaux={anneaux}
          noteMelange={noteMelange}
          masquees={masquees}
          setMasquees={setMasquees}
          survol={survol}
          setSurvol={setSurvol}
          epingle={epingle}
          setEpingle={setEpingle}
        />
      )}
    </CarteAgrandissable>
  );
}

function CorpsRadar({
  agrandi, ouvrir, societesComparees, profils, dessinees, axesLabels, couleurs, echelle, anneaux,
  noteMelange, masquees, setMasquees, survol, setSurvol, epingle, setEpingle,
}: {
  agrandi: boolean;
  ouvrir: () => void;
  societesComparees: string[];
  profils: Profil[];
  dessinees: Dessine[];
  axesLabels: string[];
  couleurs: Record<string, string>;
  echelle: number;
  anneaux: number[];
  noteMelange: string | null;
  masquees: string[];
  setMasquees: React.Dispatch<React.SetStateAction<string[]>>;
  survol: string | null;
  setSurvol: (s: string | null) => void;
  epingle: string | null;
  setEpingle: React.Dispatch<React.SetStateAction<string | null>>;
}) {
  const [etroit, setEtroit] = useState(false);
  useEffect(() => {
    if (!agrandi) return;
    const maj = () => setEtroit(window.innerWidth < 640);
    maj();
    window.addEventListener("resize", maj);
    return () => window.removeEventListener("resize", maj);
  }, [agrandi]);

  const nbAxes = axesLabels.length;
  const G = !agrandi ? G_NORMALE : etroit ? G_ETROITE : G_GRANDE;
  const axesAffiches = agrandi ? axesLabels.map((l) => l.replace(/^SCR — /, "")) : axesLabels;
  const actif = agrandi ? (survol ?? epingle) : null;
  const toggleMasque = (soc: string) =>
    setMasquees((prev) => (prev.includes(soc) ? prev.filter((s) => s !== soc) : [...prev, soc]));
  const basculerEpingle = (soc: string) => setEpingle((p) => (p === soc ? null : soc));
  // Survol souris seulement : sur écran tactile, c'est le tap (clic) qui épingle.
  const survolSouris = (soc: string | null) => (e: React.PointerEvent) => {
    if (e.pointerType === "mouse") setSurvol(soc);
  };

  const pointSurAxe = (i: number, ratio: number, k = 1) => {
    const angle = (Math.PI * 2 * i) / nbAxes - Math.PI / 2;
    const r = G.R * k * Math.max(0, Math.min(1, ratio));
    return { x: G.cx + r * Math.cos(angle), y: G.cy + r * Math.sin(angle), cos: Math.cos(angle), sin: Math.sin(angle) };
  };

  // Agrandi : toutes les sociétés dessinées (la mise en avant remplace le
  // masquage), la société mise en avant en dernier (au-dessus des autres).
  const tracees = agrandi
    ? [...dessinees].sort((a, b) => Number(a.soc === actif) - Number(b.soc === actif))
    : dessinees.filter((p) => !masquees.includes(p.soc));
  const forme = (soc: string) => societesComparees.indexOf(soc);
  const libelleEtat = (p: Profil) =>
    p.etat === "modele-interne" ? "modèle interne" : p.etat === "autre-perimetre" ? "périmètre différent" : "parts indisponibles";

  return (
    <>
      <div className="flex items-center gap-x-3 gap-y-1 flex-wrap mb-2">
        {profils.map((p) => (
          // Le marqueur d'avertissement est un frère du bouton de légende (jamais
          // un bouton dans un bouton) ; il garde sa pleine opacité si masquée.
          <span key={p.soc} className="inline-flex items-center">
            {p.etat === "dessine" ? (
              agrandi ? (
                <button
                  onPointerEnter={survolSouris(p.soc)}
                  onPointerLeave={survolSouris(null)}
                  onClick={() => basculerEpingle(p.soc)}
                  aria-pressed={epingle === p.soc}
                  className={cn(
                    "flex items-center gap-1.5 px-2 py-1 rounded-full text-sm transition-colors hover:bg-surface-hover",
                    actif === p.soc ? "bg-surface-secondary text-text-primary font-medium" : "text-text-secondary",
                    actif !== null && actif !== p.soc && "opacity-60"
                  )}
                >
                  <GlypheForme forme={forme(p.soc)} couleur={couleurs[p.soc]} />
                  {p.soc}
                </button>
              ) : (
                <button
                  onClick={() => toggleMasque(p.soc)}
                  className={cn(
                    "flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs hover:bg-surface-hover transition-opacity",
                    masquees.includes(p.soc) ? "opacity-35" : "opacity-100"
                  )}
                >
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: couleurs[p.soc] }} />
                  {p.soc}
                </button>
              )
            ) : (
              <span
                title={p.info.charAt(0).toUpperCase() + p.info.slice(1)}
                className={cn(
                  "flex items-center gap-1.5 px-2 rounded-full text-text-tertiary cursor-help",
                  agrandi ? "py-1 text-sm" : "py-0.5 text-xs"
                )}
              >
                {agrandi ? (
                  <GlypheForme forme={0} creux />
                ) : (
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ border: "1.5px solid var(--text-tertiary)" }}
                    aria-hidden="true"
                  />
                )}
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
      {agrandi && dessinees.length > 0 && (
        <p className="text-xs text-text-tertiary mb-2">
          Survolez ou touchez une société (légende ou tableau) pour mettre son tracé en avant ; un second clic
          réinitialise.
        </p>
      )}

      {dessinees.length === 0 ? (
        <p className="text-sm text-text-secondary text-center py-10">
          Aucune société sélectionnée n&apos;a un profil en parts comparable (modèle interne ou périmètre différent).
        </p>
      ) : (
        <>
          <svg
            viewBox={`0 0 ${G.W} ${G.H}`}
            width="100%"
            style={{ height: "auto", maxHeight: agrandi ? "62vh" : G_NORMALE.H }}
            className={cn(
              "mx-auto block overflow-visible",
              !agrandi && "cursor-zoom-in rounded-md focus-visible:outline-2 focus-visible:outline-accent"
            )}
            role={agrandi ? "img" : "button"}
            tabIndex={agrandi ? undefined : 0}
            aria-label={
              agrandi
                ? "Radar agrandi du profil de risque, en parts du SCR de base"
                : "Agrandir le radar : profil de risque comparé, en parts du SCR de base"
            }
            onClick={agrandi ? undefined : ouvrir}
            onKeyDown={
              agrandi
                ? undefined
                : (e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      ouvrir();
                    }
                  }
            }
          >
            {/* Grille polaire : anneaux gradués en % de la somme des modules */}
            {anneaux.map((v) => (
              <polygon
                key={v}
                points={Array.from({ length: nbAxes }, (_, i) => {
                  const p = pointSurAxe(i, v / echelle);
                  return `${p.x},${p.y}`;
                }).join(" ")}
                fill="none"
                stroke={agrandi ? "var(--border-hover)" : "var(--border)"}
                strokeWidth={1}
              />
            ))}
            {/* Axes + labels */}
            {axesAffiches.map((label, i) => {
              const bord = pointSurAxe(i, 1);
              const lp = pointSurAxe(i, 1, G.k);
              // Étiquette ancrée vers l'extérieur : jamais par-dessus le polygone.
              const ancre = lp.cos > 0.3 ? "start" : lp.cos < -0.3 ? "end" : "middle";
              const dx = ancre === "start" ? 8 : ancre === "end" ? -8 : 0;
              const lignes = lignesLabel(label, etroit && agrandi);
              const dy = lp.sin < -0.3 ? -6 - (lignes.length - 1) * (G.police + 2) : lp.sin > 0.3 ? (agrandi ? 14 : 12) : 0;
              return (
                <g key={label}>
                  <line x1={G.cx} y1={G.cy} x2={bord.x} y2={bord.y} stroke={agrandi ? "var(--border-hover)" : "var(--border)"} strokeWidth={1} />
                  <text
                    x={lp.x + dx}
                    y={lp.y + dy}
                    textAnchor={ancre}
                    dominantBaseline="middle"
                    fontSize={G.police}
                    fontFamily="var(--font-body)"
                    fontWeight={agrandi ? 500 : undefined}
                    fill={agrandi ? "var(--text-primary)" : "var(--text-secondary)"}
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
            {/* Graduation des anneaux (le long du premier axe) */}
            {anneaux.map((v) => {
              const p = pointSurAxe(0, v / echelle);
              return (
                <text
                  key={`g${v}`}
                  x={p.x + 4}
                  y={p.y + (agrandi ? 4 : 11)}
                  fontSize={G.grad}
                  fontFamily="var(--font-mono)"
                  fill="var(--text-tertiary)"
                >
                  {v} %
                </text>
              );
            })}
            {/* Polygones ; sommets avec valeur au survol */}
            {tracees.map((p) => {
              const att = actif !== null && actif !== p.soc;
              const opacite = att ? 0.2 : 1;
              const sommets = p.parts.map((v, i) => ({ v, pt: pointSurAxe(i, v / echelle) }));
              return (
                <g key={p.soc}>
                  <polygon
                    points={sommets.map((s) => `${s.pt.x},${s.pt.y}`).join(" ")}
                    fill={couleurs[p.soc]}
                    fillOpacity={!agrandi ? 0.15 : att ? 0.03 : actif === p.soc ? 0.14 : 0.06}
                    stroke={couleurs[p.soc]}
                    strokeWidth={agrandi ? (actif === p.soc ? 3.5 : 2) : 2}
                    opacity={opacite}
                  />
                  {sommets.map((s, i) => (
                    <PointForme
                      key={i}
                      forme={agrandi ? forme(p.soc) : 0}
                      cx={s.pt.x}
                      cy={s.pt.y}
                      r={agrandi && actif === p.soc ? G.pointR + 1.5 : G.pointR}
                      couleur={couleurs[p.soc]}
                      opacite={opacite}
                      titre={`${p.soc} — ${axesLabels[i]} : ${pct(s.v)}`}
                    />
                  ))}
                </g>
              );
            })}
          </svg>

          {noteMelange && (
            <p role="note" className="mt-2 text-xs leading-relaxed text-text-secondary">
              {noteMelange}
            </p>
          )}

          {/* Parts en % : une ligne par société (survol = mise en avant en vue agrandie) */}
          <div className="mt-3 overflow-x-auto">
            <table className={cn("w-full", agrandi ? "text-sm" : "text-xs")}>
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left font-medium text-text-tertiary py-1.5 pr-3">Part du SCR de base</th>
                  {axesAffiches.map((label) => (
                    <th key={label} className="text-right font-medium text-text-tertiary py-1.5 px-2">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dessinees.map((p) => (
                  <tr
                    key={p.soc}
                    onPointerEnter={agrandi ? survolSouris(p.soc) : undefined}
                    onPointerLeave={agrandi ? survolSouris(null) : undefined}
                    onClick={agrandi ? () => basculerEpingle(p.soc) : undefined}
                    className={cn(
                      "border-b border-border last:border-0 transition-colors",
                      agrandi && "cursor-pointer",
                      actif === p.soc && "bg-surface-secondary",
                      actif !== null && actif !== p.soc && "opacity-60",
                      !agrandi && masquees.includes(p.soc) && "opacity-35"
                    )}
                  >
                    <td className="py-1.5 pr-3 text-text-secondary whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5">
                        {agrandi ? (
                          <GlypheForme forme={forme(p.soc)} couleur={couleurs[p.soc]} />
                        ) : (
                          <span
                            className="inline-block w-2 h-2 rounded-full"
                            style={{ background: couleurs[p.soc] }}
                            aria-hidden="true"
                          />
                        )}
                        {p.soc}
                      </span>
                    </td>
                    {p.parts.map((v, i) => (
                      <td key={i} className="text-right font-mono text-text-primary py-1.5 px-2">
                        {pct(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
