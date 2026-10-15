"use client";

import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { DEMO_SFCR, kpisSociete } from "@/data/analyse-demo";
import { couleurSeuil, valeurDisponible } from "@/lib/analyse-utils";
import { DONNEES_EXTRAITES } from "@/lib/donnees-extraites-utils";
import { SEUIL_LEGAL, SEUIL_VERT_SCR_DEFAUT } from "@/lib/seuils-config";
import { AvertissementKpi } from "./avertissement-kpi";
import { CarteAgrandissable } from "./carte-agrandissable";

// ───────────────────────── Treemap « squarified » ─────────────────────────

type Boite = { id: string; aire: number };
type Rect = { id: string; x: number; y: number; w: number; h: number };

/** Pire rapport d'aspect d'une rangée de rectangles posée sur le côté `cote`. */
function pireAspect(aires: number[], cote: number): number {
  const s = aires.reduce((a, b) => a + b, 0);
  const max = Math.max(...aires);
  const min = Math.min(...aires);
  return Math.max((cote * cote * max) / (s * s), (s * s) / (cote * cote * min));
}

/** Algorithme « squarified » (Bruls, Huizing, van Wijk) : `boites` triées par
 * aire décroissante, dont les aires somment à w × h. */
function squarify(boites: Boite[], x: number, y: number, w: number, h: number): Rect[] {
  const sortie: Rect[] = [];
  let reste = boites;
  while (reste.length > 0) {
    const cote = Math.min(w, h);
    let rangee = [reste[0]];
    let i = 1;
    while (i < reste.length) {
      const candidate = [...rangee, reste[i]];
      if (pireAspect(candidate.map((b) => b.aire), cote) <= pireAspect(rangee.map((b) => b.aire), cote)) {
        rangee = candidate;
        i += 1;
      } else break;
    }
    const somme = rangee.reduce((a, b) => a + b.aire, 0);
    if (w >= h) {
      // Colonne à gauche : largeur = somme / hauteur.
      const cw = somme / h;
      let cy = y;
      for (const b of rangee) {
        const rh = b.aire / cw;
        sortie.push({ id: b.id, x, y: cy, w: cw, h: rh });
        cy += rh;
      }
      x += cw;
      w -= cw;
    } else {
      // Ligne en haut : hauteur = somme / largeur.
      const rh = somme / w;
      let cx = x;
      for (const b of rangee) {
        const rw = b.aire / rh;
        sortie.push({ id: b.id, x: cx, y, w: rw, h: rh });
        cx += rw;
      }
      y += rh;
      h -= rh;
    }
    reste = reste.slice(rangee.length);
  }
  return sortie;
}

// ───────────────────────── Composant ─────────────────────────

type Vue = "groupes" | "entites";

const FOND: Record<string, string> = {
  success: "var(--success-light)",
  warning: "var(--warning-light)",
  danger: "var(--danger-light)",
  neutre: "var(--surface-secondary)",
};
const TRAIT: Record<string, string> = {
  success: "var(--success)",
  warning: "var(--warning)",
  danger: "var(--danger)",
  neutre: "var(--border-hover)",
};

function fmt(v: number, d = 1): string {
  return v.toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
}

/** Treemap « Taille et solidité du panel » : un rectangle par société, surface =
 * primes acquises brutes, couleur = feu tricolore du ratio SCR. Aucune société
 * n'apparaît deux fois : vue « Groupes » = groupes + sociétés solo non
 * consolidées dans un groupe du panel ; vue « Entités » = sociétés solo. Les
 * filiales ne sont jamais emboîtées dans leur groupe (éliminations de
 * consolidation : les sommes ne correspondent pas). */
export function TreemapPanel({
  societesFiltrees,
  societesSelectionnees,
  seuilVertScr = SEUIL_VERT_SCR_DEFAUT,
}: {
  /** Sociétés qui passent les filtres actifs de l'Analyse comparative. */
  societesFiltrees: string[];
  societesSelectionnees: string[];
  seuilVertScr?: number;
}) {
  const [vue, setVue] = useState<Vue>("groupes");
  const [actif, setActif] = useState<string | null>(null);
  const [etroit, setEtroit] = useState(false);
  useEffect(() => {
    const maj = () => setEtroit(window.innerWidth < 640);
    maj();
    window.addEventListener("resize", maj);
    return () => window.removeEventListener("resize", maj);
  }, []);

  const W = etroit ? 360 : 900;
  const H = etroit ? 520 : 500;

  const { items, sansPrimes, rects } = useMemo(() => {
    const filtrees = new Set(societesFiltrees);
    const candidates = DONNEES_EXTRAITES.societes
      .filter((s) => filtrees.has(s.name))
      .filter((s) => {
        const info = DEMO_SFCR[s.name];
        if (!info) return false;
        // Vue Groupes : groupes + solo SANS consolideDans. Vue Entités : solo.
        if (vue === "entites") return info.perimetre === "solo";
        return info.perimetre === "groupe" || !info.consolideDans;
      })
      .map((s) => s.name);

    const elements = candidates.map((nom) => {
      const kpis = kpisSociete(nom);
      return {
        nom,
        primes: valeurDisponible(kpis, "primes_acquises_brutes"),
        ratio: valeurDisponible(kpis, "ratio_scr"),
        avert: kpis["ratio_scr"]?.avertissement ? (kpis["ratio_scr"].noteAvertissement ?? null) : undefined,
        perimetre: DEMO_SFCR[nom]?.perimetre ?? "solo",
      };
    });
    const dessinables = elements.filter((e) => e.primes !== null && e.primes > 0);
    const total = dessinables.reduce((a, e) => a + (e.primes as number), 0);
    // Tri par surface décroissante : exigé par l'algorithme, aucun rang affiché.
    const tries = [...dessinables].sort((a, b) => (b.primes as number) - (a.primes as number));
    const boites: Boite[] = tries.map((e) => ({ id: e.nom, aire: (((e.primes as number) / total) * W) * H }));
    return {
      items: new Map(elements.map((e) => [e.nom, e])),
      sansPrimes: elements.filter((e) => !(e.primes !== null && e.primes > 0)).map((e) => e.nom),
      rects: total > 0 ? squarify(boites, 0, 0, W, H) : [],
    };
  }, [societesFiltrees, vue, W, H]);

  const selection = new Set(societesSelectionnees);
  const detail = actif ? items.get(actif) : undefined;

  return (
    <CarteAgrandissable
      titre="Taille et solidité du panel"
      nom="le treemap du panel"
      actions={
        <div role="group" aria-label="Vue du treemap" className="inline-flex rounded-full border border-border p-0.5">
          {(
            [
              ["groupes", "Groupes"],
              ["entites", "Entités"],
            ] as const
          ).map(([v, label]) => (
            <button
              key={v}
              onClick={() => {
                setVue(v);
                setActif(null);
              }}
              aria-pressed={vue === v}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-medium transition-colors",
                vue === v ? "bg-accent-light text-accent" : "text-text-secondary hover:bg-surface-hover"
              )}
            >
              {label}
            </button>
          ))}
        </div>
      }
    >
      {({ agrandi }) => (
        <>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 mb-3 text-xs text-text-secondary" aria-label="Légende des couleurs">
            {[
              ["danger", `ratio SCR < ${SEUIL_LEGAL} %`],
              ["warning", `${SEUIL_LEGAL} – ${seuilVertScr} %`],
              ["success", `≥ ${seuilVertScr} %`],
              ["neutre", "ratio non disponible"],
            ].map(([c, label]) => (
              <li key={c} className="inline-flex items-center gap-1.5">
                <span
                  className="inline-block w-3 h-3 rounded-sm"
                  style={{ background: FOND[c], border: `1.5px solid ${TRAIT[c]}` }}
                  aria-hidden="true"
                />
                {label}
              </li>
            ))}
            <li className="inline-flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 rounded-sm border-[3px] border-text-primary" aria-hidden="true" />
              sélectionnée dans le comparatif
            </li>
          </ul>

          {rects.length === 0 ? (
            <p className="text-sm text-text-secondary text-center py-10">
              Aucune société ne correspond aux filtres dans cette vue.
            </p>
          ) : (
            <svg
              viewBox={`0 0 ${W} ${H}`}
              width="100%"
              style={{ height: "auto", maxHeight: agrandi ? "68vh" : undefined }}
              className="block mx-auto"
              role="group"
              aria-label={`Treemap de ${rects.length} sociétés, surface = primes acquises brutes, couleur = ratio SCR`}
              onPointerLeave={(e) => e.pointerType === "mouse" && setActif(null)}
            >
              {rects.map((r) => {
                const e = items.get(r.id)!;
                const couleur = e.ratio === null ? "neutre" : couleurSeuil("ratio_scr", e.ratio, seuilVertScr);
                const choisie = selection.has(r.id);
                const assezGrand = r.w >= 72 && r.h >= 34;
                const nbCar = Math.max(4, Math.floor((r.w - 12) / 6.6));
                const nom = r.id.length > nbCar ? `${r.id.slice(0, nbCar - 1)}…` : r.id;
                const resume = `${r.id} — primes : ${fmt(e.primes as number)} M€ · ratio SCR : ${
                  e.ratio === null ? "non disponible" : `${fmt(e.ratio, 0)} %`
                } · vue ${e.perimetre === "groupe" ? "groupe" : "entité"}`;
                return (
                  <g
                    key={r.id}
                    tabIndex={0}
                    role="button"
                    aria-label={resume}
                    onPointerEnter={(ev) => ev.pointerType === "mouse" && setActif(r.id)}
                    onClick={() => setActif((p) => (p === r.id ? null : r.id))}
                    onFocus={() => setActif(r.id)}
                    className="cursor-pointer outline-none"
                  >
                    <title>{resume}</title>
                    <rect
                      x={r.x + 1}
                      y={r.y + 1}
                      width={Math.max(0, r.w - 2)}
                      height={Math.max(0, r.h - 2)}
                      rx={4}
                      fill={FOND[couleur]}
                      stroke={choisie ? "var(--text-primary)" : TRAIT[couleur]}
                      strokeWidth={choisie ? 3 : actif === r.id ? 2.5 : 1.25}
                      strokeOpacity={choisie || actif === r.id ? 1 : 0.55}
                    />
                    {assezGrand && (
                      <>
                        <text x={r.x + 7} y={r.y + 18} fontSize={12} fontWeight={600} fill="var(--text-primary)">
                          {nom}
                        </text>
                        {r.h >= 48 && (
                          <text x={r.x + 7} y={r.y + 34} fontSize={11} fontFamily="var(--font-mono)" fill="var(--text-secondary)">
                            {e.ratio === null ? "n/d" : `${fmt(e.ratio, 0)} %`}
                          </text>
                        )}
                      </>
                    )}
                  </g>
                );
              })}
            </svg>
          )}

          {/* Détail de la société survolée / touchée (tap mobile) */}
          <div className="mt-3 min-h-[2.75rem] text-sm" aria-live="polite">
            {detail ? (
              <p className="flex items-center flex-wrap gap-x-2 gap-y-0.5 text-text-secondary">
                <span className="font-medium text-text-primary">{detail.nom}</span>
                <span>· primes {fmt(detail.primes as number)} M€</span>
                <span>
                  · ratio SCR {detail.ratio === null ? "non disponible" : `${fmt(detail.ratio, 0)} %`}
                </span>
                <span>· vue {detail.perimetre === "groupe" ? "groupe" : "entité"}</span>
                {detail.avert !== undefined && (
                  <AvertissementKpi note={detail.avert} titre={`Ratio SCR — ${detail.nom}`} />
                )}
              </p>
            ) : (
              <p className="text-xs text-text-tertiary">
                Survolez ou touchez un rectangle pour lire le détail · {rects.length} société
                {rects.length > 1 ? "s" : ""} affichée{rects.length > 1 ? "s" : ""}.
              </p>
            )}
          </div>

          {sansPrimes.length > 0 && (
            <p className="mt-1 text-xs text-text-tertiary">
              Non représentées (primes non disponibles) : {sansPrimes.join(", ")}.
            </p>
          )}
          <p className="mt-2 text-xs leading-relaxed text-text-tertiary">
            Taille = primes acquises brutes du panel ({DONNEES_EXTRAITES.societes.length} SFCR), pas part de marché du
            marché français. Couleur = ratio SCR.
            {vue === "entites" &&
              " Covéa et Groupama ne publient qu'un rapport de groupe : visibles seulement dans la vue Groupes."}
          </p>
        </>
      )}
    </CarteAgrandissable>
  );
}
