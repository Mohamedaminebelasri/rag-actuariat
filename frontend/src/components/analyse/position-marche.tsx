"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { KPI_PAR_ID, kpisSociete, type KpiDefinition } from "@/data/analyse-demo";
import {
  FILTRES_VIDES,
  KPIS_CLASSABLES,
  SENS_KPI,
  classement,
  formatValeur,
  societesFiltrees,
  statutKpi,
  type Classement,
  type FiltresSocietes,
} from "@/lib/analyse-utils";
import { FiltresSocietesBar } from "./filtres-societes";

const PASTILLE_STATUT: Record<string, string> = {
  success: "bg-success-light text-success",
  warning: "bg-warning-light text-warning",
  danger: "bg-danger-light text-danger",
};

const ordinal = (n: number) => (n === 1 ? "1er" : `${n}e`);

function valeurCourte(v: number, unite: string): string {
  if (unite === "%") return `${Math.round(v)} %`;
  return `${Math.abs(v) < 10 ? v.toFixed(1) : Math.round(v)} Md€`;
}

/** Idée 2 : classement de la société parmi ses pairs + distribution du
 * marché (chaque point = une société ; la société analysée est en couleur). */
export function PositionMarche({ societe }: { societe: string }) {
  const [kpiId, setKpiId] = useState("ratio_scr");
  const [filtres, setFiltres] = useState<FiltresSocietes>(FILTRES_VIDES);

  const def = KPI_PAR_ID[kpiId];
  const groupe = useMemo(() => societesFiltrees(filtres), [filtres]);
  const cls = useMemo(() => classement(kpiId, societe, groupe), [kpiId, societe, groupe]);
  const valeurSociete = kpisSociete(societe)[kpiId]?.valeur;
  const statut = valeurSociete !== undefined ? statutKpi(kpiId, valeurSociete) : null;
  const sens = SENS_KPI[kpiId];

  return (
    <section
      aria-label="Position parmi les pairs"
      className="bg-surface border border-border rounded-[var(--radius-lg)] shadow-[var(--shadow-sm)] p-5 w-full mb-6"
    >
      <div className="flex items-center gap-3 flex-wrap mb-3">
        <h3 className="font-heading italic text-lg text-text-primary">Position parmi les pairs</h3>
        <span className="flex-1" />
        <select
          aria-label="Indicateur à classer"
          value={kpiId}
          onChange={(e) => setKpiId(e.target.value)}
          className="text-sm border border-border rounded-[var(--radius-md)] px-2.5 py-1.5 bg-surface text-text-primary font-body"
        >
          {KPIS_CLASSABLES.map((k) => (
            <option key={k.id} value={k.id}>
              {k.label}
            </option>
          ))}
        </select>
      </div>

      <FiltresSocietesBar
        filtres={filtres}
        onChange={setFiltres}
        resume={`Pairs : ${cls?.total ?? 0} société${(cls?.total ?? 0) > 1 ? "s" : ""}`}
      />

      {!cls || valeurSociete === undefined ? (
        <p className="text-sm text-text-secondary mt-6">Pas de donnée pour cet indicateur.</p>
      ) : (
        <>
          <div className="flex items-end gap-x-6 gap-y-2 flex-wrap mt-5">
            <p className="font-mono text-4xl font-bold text-text-primary leading-none">
              {ordinal(cls.rang)}
              <span className="text-base font-medium text-text-tertiary"> / {cls.total}</span>
            </p>
            <div className="flex flex-col gap-1">
              <p className="text-sm text-text-primary">
                {cls.total > 1 ? (
                  <>
                    Fait mieux que <span className="font-mono font-bold">{cls.percentile} %</span> des autres sociétés
                  </>
                ) : (
                  "Aucun autre pair avec ces filtres"
                )}
              </p>
              <p className="text-xs text-text-tertiary">
                {def.label} : <span className="font-mono">{formatValeur(valeurSociete, def.unite)}</span> ·{" "}
                {sens === "higher" ? "plus haut = meilleur" : "plus bas = meilleur"}
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

          {cls.total < 3 && (
            <p className="text-xs text-warning mt-3" role="note">
              Échantillon trop petit (moins de 3 sociétés) : le classement n&apos;est pas fiable. Élargis les filtres.
            </p>
          )}

          <DotPlot cls={cls} societe={societe} def={def} />

          <p className="text-[11px] text-text-tertiary mt-1">
            Chaque point est une société. Trait pointillé gris : médiane du groupe
            {def.seuilReglementaire !== null ? " · trait rouge : seuil réglementaire" : ""}.
          </p>
        </>
      )}
    </section>
  );
}

function DotPlot({ cls, societe, def }: { cls: Classement; societe: string; def: KpiDefinition }) {
  const L = 720;
  const H = 176;
  const PAD = 40;
  const AXE = 120;
  const R = 7;
  const NB_BINS = 14;

  const valeurs = cls.points.map((p) => p.valeur);
  const seuil = def.seuilReglementaire;
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
  const points = [...cls.points]
    .sort((a, b) => a.valeur - b.valeur)
    .map((p) => {
      const bin = Math.min(NB_BINS - 1, Math.floor(((p.valeur - min) / (max - min)) * NB_BINS));
      const rang = compteurs.get(bin) ?? 0;
      compteurs.set(bin, rang + 1);
      return { ...p, cx: x(p.valeur), cy: AXE - R - 4 - rang * (2 * R + 2), moi: p.societe === societe };
    });

  const ticks = Array.from({ length: 5 }, (_, i) => min + ((max - min) * i) / 4);
  const ancre = (px: number) => (px < 70 ? "start" : px > L - 70 ? "end" : "middle");
  const moi = points.find((p) => p.moi);

  return (
    <svg
      viewBox={`0 0 ${L} ${H}`}
      className="w-full h-auto mt-4"
      role="img"
      aria-label={`Distribution de ${def.label} : ${societe} est ${ordinal(cls.rang)} sur ${cls.total}`}
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
            {valeurCourte(t, def.unite)}
          </text>
        </g>
      ))}

      {/* Médiane */}
      <line
        x1={x(cls.mediane)}
        y1={22}
        x2={x(cls.mediane)}
        y2={AXE}
        stroke="var(--text-secondary)"
        strokeWidth={1}
        strokeDasharray="4 4"
      />
      <text
        x={x(cls.mediane)}
        y={14}
        textAnchor={ancre(x(cls.mediane))}
        fontSize={12}
        fontFamily="var(--font-body)"
        fill="var(--text-secondary)"
        stroke="var(--surface)"
        strokeWidth={4}
        paintOrder="stroke"
      >
        Médiane {valeurCourte(cls.mediane, def.unite)}
      </text>

      {/* Seuil réglementaire */}
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
            Seuil {valeurCourte(seuil, def.unite)}
          </text>
        </g>
      )}

      {/* Sociétés */}
      {points
        .filter((p) => !p.moi)
        .map((p) => (
          <circle key={p.societe} cx={p.cx} cy={p.cy} r={R} fill="var(--text-tertiary)" fillOpacity={0.55}>
            <title>{`${p.societe} : ${formatValeur(p.valeur, def.unite)}`}</title>
          </circle>
        ))}
      {moi && (
        <g>
          <circle cx={moi.cx} cy={moi.cy} r={R + 3} fill="var(--accent)" stroke="var(--surface)" strokeWidth={2}>
            <title>{`${moi.societe} : ${formatValeur(moi.valeur, def.unite)}`}</title>
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
  );
}
