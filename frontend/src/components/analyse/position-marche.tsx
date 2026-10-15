"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatValeur, statutKpi } from "@/lib/analyse-utils";
import {
  INDICATEUR_POSITION_PAR_ID,
  SEUIL_PAIRS,
  indicateursPositionPour,
  positionParmiPairs,
  type IndicateurPosition,
  type PointPosition,
} from "@/lib/position-pairs";

const PASTILLE_STATUT: Record<string, string> = {
  success: "bg-success-light text-success",
  warning: "bg-warning-light text-warning",
  danger: "bg-danger-light text-danger",
};

const ordinal = (n: number) => (n === 1 ? "1er" : `${n}e`);

const LIBELLE_SENS: Record<IndicateurPosition["sens"], string> = {
  higher: "plus haut = mieux",
  lower: "plus bas = mieux",
  zero: "plus proche de 0 = mieux",
  neutre: "indicateur neutre : ni mieux ni moins bien",
};

/** Valeur d'axe : unité réelle de l'indicateur (jamais « Md€ »), décimales
 * adaptées à l'étendue affichée. */
function valeurCourte(v: number, ind: IndicateurPosition, etendue: number): string {
  const decimales = etendue < 2 ? 2 : etendue < 20 ? 1 : 0;
  return formatValeur(v, ind.unite, null, null, decimales);
}

/** Position de la société dans SON groupe de pairs (activité · modèle ·
 * périmètre), classement seulement à partir de 5 sociétés comparables
 * (lib/position-pairs.ts). Couleurs neutres ; seuls le ratio SCR (pastille
 * du feu tricolore) et le trait rouge du seuil de 100 % des ratios SCR
 * reprennent les couleurs réglementaires. */
export function PositionMarche({ societe }: { societe: string }) {
  const indicateurs = useMemo(() => indicateursPositionPour(societe), [societe]);
  const [indicateurId, setIndicateurId] = useState("ratio_scr_sans_mesures_lt");
  const ind = INDICATEUR_POSITION_PAR_ID[indicateurId] ?? indicateurs[0];
  const res = useMemo(() => positionParmiPairs(ind.id, societe), [ind.id, societe]);
  const statut = res.statut === "ok" && ind.id === "ratio_scr" ? statutKpi("ratio_scr", res.valeur) : null;
  const classe = ind.sens !== "neutre";

  return (
    <section
      aria-label="Position parmi les pairs"
      className="bg-surface border border-border rounded-[var(--radius-lg)] shadow-[var(--shadow-sm)] p-5 w-full mb-6"
    >
      <div className="flex items-center gap-3 flex-wrap mb-1">
        <h3 className="font-heading italic text-lg text-text-primary">Position parmi les pairs</h3>
        <span className="flex-1" />
        <select
          aria-label="Indicateur à situer"
          value={ind.id}
          onChange={(e) => setIndicateurId(e.target.value)}
          className="text-sm border border-border rounded-[var(--radius-md)] px-2.5 py-1.5 bg-surface text-text-primary font-body max-w-full"
        >
          <optgroup label="Classés">
            {indicateurs
              .filter((i) => i.sens !== "neutre")
              .map((i) => (
                <option key={i.id} value={i.id}>
                  {i.label}
                </option>
              ))}
          </optgroup>
          <optgroup label="Position sans jugement">
            {indicateurs
              .filter((i) => i.sens === "neutre")
              .map((i) => (
                <option key={i.id} value={i.id}>
                  {i.label}
                </option>
              ))}
          </optgroup>
        </select>
      </div>

      {res.groupe && (
        <p className="text-xs text-text-tertiary">
          Pairs : groupe <span className="font-medium text-text-secondary">{res.groupe.id}</span> ({res.groupe.n}{" "}
          société{res.groupe.n > 1 ? "s" : ""})
        </p>
      )}

      {res.statut !== "ok" ? (
        <p role="note" className="mt-5 flex items-start gap-1.5 text-sm text-text-secondary leading-relaxed">
          <Info className="w-4 h-4 mt-0.5 flex-shrink-0 text-text-tertiary" aria-hidden="true" />
          <span>{res.raison}</span>
        </p>
      ) : (
        <>
          <div className="flex items-end gap-x-6 gap-y-2 flex-wrap mt-5">
            <p className="font-mono text-4xl font-bold text-text-primary leading-none">
              {ordinal(res.rang)}
              <span className="text-base font-medium text-text-tertiary"> / {res.total}</span>
            </p>
            <div className="flex flex-col gap-1 min-w-0">
              <p className="text-sm text-text-primary">
                {classe && res.percentile !== null ? (
                  <>
                    Fait mieux que <span className="font-mono font-bold">{res.percentile} %</span> des autres sociétés
                    du groupe
                  </>
                ) : (
                  <>
                    {ordinal(res.rang)} valeur la plus élevée du groupe ·{" "}
                    {res.valeur > res.mediane
                      ? "au-dessus de la médiane"
                      : res.valeur < res.mediane
                        ? "en dessous de la médiane"
                        : "égale à la médiane"}
                  </>
                )}
              </p>
              <p className="text-xs text-text-tertiary">
                {ind.label} :{" "}
                <span className="font-mono">{formatValeur(res.valeur, ind.unite, null, null, ind.decimales)}</span> ·{" "}
                {LIBELLE_SENS[ind.sens]}
              </p>
            </div>
            {statut && (
              <span
                className={cn(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium",
                  PASTILLE_STATUT[statut.couleur]
                )}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current" aria-hidden="true" />
                {statut.libelle}
              </span>
            )}
          </div>

          {ind.note && <p className="text-xs text-text-secondary mt-3 leading-relaxed">{ind.note}</p>}
          {res.nonComparables.length > 0 && (
            <p className="text-xs text-text-tertiary mt-1.5">
              Hors classement (valeur non comparable) : {res.nonComparables.join(", ")}.
            </p>
          )}
          {res.sansValeur.length > 0 && (
            <p className="text-xs text-text-tertiary mt-1.5">
              Sans valeur pour cet indicateur : {res.sansValeur.join(", ")}.
            </p>
          )}

          <DotPlot points={res.points} mediane={res.mediane} societe={societe} ind={ind} rang={res.rang} total={res.total} />

          <p className="text-[11px] text-text-tertiary mt-1">
            Chaque point est une société du groupe de pairs (classement à partir de {SEUIL_PAIRS} valeurs
            comparables). Trait pointillé gris : médiane du groupe
            {ind.seuil !== undefined ? " · trait rouge : seuil réglementaire" : ""}.
          </p>
        </>
      )}
    </section>
  );
}

/** Largeur réelle du conteneur : le graphique est dessiné à sa taille (texte
 * lisible sur mobile, pas un SVG réduit). */
function useLargeur(): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [largeur, setLargeur] = useState(720);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new ResizeObserver(([e]) => setLargeur(Math.max(240, Math.round(e.contentRect.width))));
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return [ref, largeur];
}

function DotPlot({
  points: pointsGroupe,
  mediane,
  societe,
  ind,
  rang,
  total,
}: {
  points: PointPosition[];
  mediane: number;
  societe: string;
  ind: IndicateurPosition;
  rang: number;
  total: number;
}) {
  const [ref, L] = useLargeur();
  const PAD = L < 480 ? 24 : 40;
  const R = 7;
  const PAS = 2 * R + 2;
  const NB_BINS = Math.max(6, Math.round(L / 52));

  const valeurs = pointsGroupe.map((p) => p.valeur);
  const seuil = ind.seuil ?? null;
  let min = Math.min(...valeurs, ...(seuil !== null ? [seuil] : []));
  let max = Math.max(...valeurs, ...(seuil !== null ? [seuil] : []));
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const marge = (max - min) * 0.06;
  min -= marge;
  max += marge;
  const x = (v: number) => PAD + ((v - min) / (max - min)) * (L - 2 * PAD);

  // Empilement des points dans des « cases » de valeurs voisines.
  const compteurs = new Map<number, number>();
  const empiles = [...pointsGroupe]
    .sort((a, b) => a.valeur - b.valeur)
    .map((p) => {
      const bin = Math.min(NB_BINS - 1, Math.floor(((p.valeur - min) / (max - min)) * NB_BINS));
      const niveau = compteurs.get(bin) ?? 0;
      compteurs.set(bin, niveau + 1);
      return { ...p, cx: x(p.valeur), niveau, moi: p.societe === societe };
    });
  const pile = Math.max(1, ...compteurs.values());
  // Hauteur : libellé de la médiane, nom de la société, pile de points, axe et graduations.
  const AXE = 44 + pile * PAS;
  const H = AXE + (seuil !== null ? 44 : 26);
  const points = empiles.map((p) => ({ ...p, cy: AXE - R - 4 - p.niveau * PAS }));

  const nbTicks = L < 480 ? 3 : 5;
  const ticks = Array.from({ length: nbTicks }, (_, i) => min + ((max - min) * i) / (nbTicks - 1));
  const ancre = (px: number) => (px < 70 ? "start" : px > L - 70 ? "end" : "middle");
  const moi = points.find((p) => p.moi);
  const etendue = max - min;

  return (
    <div ref={ref} className="w-full mt-4">
      <svg
        width={L}
        height={H}
        viewBox={`0 0 ${L} ${H}`}
        className="block max-w-full h-auto"
        role="img"
        aria-label={`Distribution de ${ind.label} dans le groupe de pairs : ${societe} est ${ordinal(rang)} sur ${total}`}
      >
        {/* Axe */}
        <line x1={PAD} y1={AXE} x2={L - PAD} y2={AXE} stroke="var(--border-hover)" strokeWidth={1} />
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={x(t)} y1={AXE} x2={x(t)} y2={AXE + 4} stroke="var(--border-hover)" />
            <text
              x={x(t)}
              y={AXE + 17}
              textAnchor={ancre(x(t))}
              fontSize={12}
              fontFamily="var(--font-mono)"
              fill="var(--text-tertiary)"
            >
              {valeurCourte(t, ind, etendue)}
            </text>
          </g>
        ))}

        {/* Médiane */}
        <line
          x1={x(mediane)}
          y1={22}
          x2={x(mediane)}
          y2={AXE}
          stroke="var(--text-secondary)"
          strokeWidth={1}
          strokeDasharray="4 4"
        />
        <text
          x={x(mediane)}
          y={14}
          textAnchor={ancre(x(mediane))}
          fontSize={12}
          fontFamily="var(--font-body)"
          fill="var(--text-secondary)"
          stroke="var(--surface)"
          strokeWidth={4}
          paintOrder="stroke"
        >
          Médiane {valeurCourte(mediane, ind, etendue)}
        </text>

        {/* Seuil réglementaire (ratios SCR) */}
        {seuil !== null && (
          <g>
            <line x1={x(seuil)} y1={30} x2={x(seuil)} y2={AXE} stroke="var(--danger)" strokeWidth={1.5} />
            <text
              x={x(seuil)}
              y={AXE + 36}
              textAnchor={ancre(x(seuil))}
              fontSize={12}
              fontFamily="var(--font-body)"
              fontWeight={600}
              fill="var(--danger)"
            >
              Seuil {valeurCourte(seuil, ind, etendue)}
            </text>
          </g>
        )}

        {/* Sociétés du groupe */}
        {points
          .filter((p) => !p.moi)
          .map((p) => (
            <circle key={p.societe} cx={p.cx} cy={p.cy} r={R} fill="var(--text-tertiary)" fillOpacity={0.55}>
              <title>{`${p.societe} : ${formatValeur(p.valeur, ind.unite, null, null, ind.decimales)}`}</title>
            </circle>
          ))}
        {moi && (
          <g>
            <circle cx={moi.cx} cy={moi.cy} r={R + 3} fill="var(--accent)" stroke="var(--surface)" strokeWidth={2}>
              <title>{`${moi.societe} : ${formatValeur(moi.valeur, ind.unite, null, null, ind.decimales)}`}</title>
            </circle>
            <text
              x={moi.cx}
              y={moi.cy - R - 9}
              textAnchor={ancre(moi.cx)}
              fontSize={13}
              fontWeight={700}
              fontFamily="var(--font-body)"
              fill="var(--accent)"
              stroke="var(--surface)"
              strokeWidth={4}
              paintOrder="stroke"
            >
              {moi.societe}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
