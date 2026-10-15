"use client";

import { cn } from "@/lib/utils";
import { kpisSociete } from "@/data/analyse-demo";
import { valeurDisponible } from "@/lib/analyse-utils";
import { AvertissementKpi } from "./avertissement-kpi";
import { CarteAgrandissable } from "./carte-agrandissable";

// Palette NEUTRE (famille bleu / violet / gris ardoise du radar), du plus foncé
// (T1 non restreint, meilleure qualité) au plus clair (T3). Jamais de
// rouge/orange/vert : réservés au feu tricolore des ratios SCR/MCR.
const TIERS = [
  { id: "fonds_propres_t1_nr", court: "T1 NR", label: "T1 non restreint", couleur: "#2563eb" },
  { id: "fonds_propres_t1_r", court: "T1 R", label: "T1 restreint", couleur: "#60a5fa" },
  { id: "fonds_propres_t2", court: "T2", label: "T2", couleur: "#c4b5fd" },
  { id: "fonds_propres_t3", court: "T3", label: "T3", couleur: "#e2e8f0" },
] as const;

const BASE = "somme des 4 Tiers";

function fmtPct(v: number): string {
  return `${v.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
}
function fmtM(v: number): string {
  return `${v.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} M€`;
}

type LigneTiers = {
  societe: string;
  /** Montant par Tier ; null = clé absente (jamais ramené à 0). */
  montants: (number | null)[];
  absents: string[];
  total: number | null;
  parts: number[] | null;
  avert: { tiers: string[]; note: string } | null;
};

function ligneTiers(societe: string): LigneTiers {
  const kpis = kpisSociete(societe);
  const montants = TIERS.map((t) => valeurDisponible(kpis, t.id));
  const absents = TIERS.filter((_, i) => montants[i] === null).map((t) => t.label);
  const complet = absents.length === 0;
  const total = complet ? (montants as number[]).reduce((a, b) => a + b, 0) : null;
  const parts = complet && total !== null && total > 0 ? (montants as number[]).map((m) => (m / total) * 100) : null;
  const concernes = TIERS.flatMap((t) =>
    kpis[t.id]?.avertissement ? [{ label: t.label, note: kpis[t.id].noteAvertissement ?? "" }] : []
  );
  const avert =
    concernes.length > 0
      ? {
          tiers: concernes.map((c) => c.label),
          note: Array.from(new Set(concernes.map((c) => c.note).filter((n) => n !== ""))).join("\n\n"),
        }
      : null;
  return { societe, montants, absents, total, parts, avert };
}

/** Qualité des fonds propres par Tier : une barre empilée à 100 % par société
 * (T1 non restreint / T1 restreint / T2 / T3), part = montant / somme des 4
 * Tiers. Ordre = ordre de la sélection (ni classement, ni tri, ni médiane). */
export function TiersComparatif({ societesComparees }: { societesComparees: string[] }) {
  const lignes = societesComparees.map(ligneTiers);

  return (
    <CarteAgrandissable titre="Qualité des fonds propres par Tier" nom="le graphique des fonds propres par Tier">
      {({ agrandi }) => (
        <>
          <p className="text-xs text-text-tertiary mb-3">
            Le T1 non restreint est le capital de meilleure qualité ; T2 et T3 sont plafonnés. Parts calculées sur la{" "}
            {BASE}.
          </p>

          <ul className="flex flex-wrap gap-x-4 gap-y-1 mb-4 text-xs text-text-secondary" aria-label="Légende des Tiers">
            {TIERS.map((t) => (
              <li key={t.id} className="inline-flex items-center gap-1.5">
                <span
                  className="inline-block w-3 h-3 rounded-sm border border-border-hover"
                  style={{ background: t.couleur }}
                  aria-hidden="true"
                />
                {t.label}
              </li>
            ))}
          </ul>

          <ul className="flex flex-col gap-3">
            {lignes.map((l) => {
              const resume = TIERS.map(
                (t, i) =>
                  `${t.label} : ${l.montants[i] === null ? "non disponible" : fmtM(l.montants[i] as number)}${
                    l.parts ? ` (${fmtPct(l.parts[i])})` : ""
                  }`
              ).join(" · ");
              return (
                <li key={l.societe}>
                  <div className="flex items-baseline justify-between gap-3 mb-1">
                    <span className="min-w-0 flex items-center">
                      <span className={cn("font-medium text-text-primary truncate", agrandi ? "text-base" : "text-sm")}>
                        {l.societe}
                      </span>
                      {l.avert && (
                        <AvertissementKpi
                          titre={`Tiers concernés : ${l.avert.tiers.join(", ")}`}
                          note={l.avert.note}
                          className="ml-1"
                        />
                      )}
                    </span>
                    {l.parts ? (
                      <span
                        className={cn("font-mono whitespace-nowrap text-text-secondary", agrandi ? "text-sm" : "text-xs")}
                        title={`Part du T1 non restreint : ${fmtPct(l.parts[0])} (base : ${BASE})`}
                      >
                        T1 NR {fmtPct(l.parts[0])}
                      </span>
                    ) : (
                      <span className="text-xs text-text-tertiary whitespace-nowrap">données incomplètes</span>
                    )}
                  </div>

                  {l.parts ? (
                    <div
                      role="img"
                      aria-label={`${l.societe} — ${resume} (parts sur la ${BASE})`}
                      title={`${resume} — parts sur la ${BASE}`}
                      className={cn(
                        "flex w-full overflow-hidden rounded-md border border-border-hover bg-surface-secondary",
                        agrandi ? "h-9" : "h-5"
                      )}
                    >
                      {TIERS.map((t, i) =>
                        l.parts![i] > 0 ? (
                          <div
                            key={t.id}
                            style={{ width: `${l.parts![i]}%`, background: t.couleur }}
                            title={`${t.label} : ${fmtM(l.montants[i] as number)} · ${fmtPct(l.parts![i])} (base : ${BASE})`}
                            className="h-full border-r border-surface last:border-r-0"
                          />
                        ) : null
                      )}
                    </div>
                  ) : (
                    <div
                      role="img"
                      aria-label={`${l.societe} : données incomplètes${
                        l.absents.length > 0 ? ` (Tier absent : ${l.absents.join(", ")})` : ""
                      }`}
                      title={
                        l.absents.length > 0
                          ? `Données incomplètes — Tier absent : ${l.absents.join(", ")}. Parts non calculées.`
                          : "Données incomplètes — parts non calculables."
                      }
                      className={cn(
                        "w-full rounded-md border border-dashed border-border-hover",
                        agrandi ? "h-9" : "h-5"
                      )}
                      style={{
                        backgroundImage:
                          "repeating-linear-gradient(45deg, var(--text-tertiary) 0, var(--text-tertiary) 2px, transparent 2px, transparent 7px)",
                        opacity: 0.45,
                      }}
                    />
                  )}
                </li>
              );
            })}
          </ul>

          {agrandi && (
            <div className="mt-5 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left font-medium text-text-tertiary py-1.5 pr-3">Société</th>
                    {TIERS.map((t) => (
                      <th key={t.id} className="text-right font-medium text-text-tertiary py-1.5 px-2 whitespace-nowrap">
                        {t.label}
                      </th>
                    ))}
                    <th className="text-right font-medium text-text-tertiary py-1.5 pl-2 whitespace-nowrap">
                      Somme des 4 Tiers
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {lignes.map((l) => (
                    <tr key={l.societe} className="border-b border-border last:border-0">
                      <td className="py-1.5 pr-3 text-text-primary whitespace-nowrap">{l.societe}</td>
                      {l.montants.map((m, i) => (
                        <td key={i} className="text-right font-mono py-1.5 px-2 text-text-secondary whitespace-nowrap">
                          {m === null ? (
                            <span className="text-text-tertiary">n/d</span>
                          ) : (
                            <>
                              {fmtM(m)}
                              {l.parts && <span className="text-text-tertiary"> · {fmtPct(l.parts[i])}</span>}
                            </>
                          )}
                        </td>
                      ))}
                      <td className="text-right font-mono py-1.5 pl-2 text-text-primary whitespace-nowrap">
                        {l.total === null ? <span className="text-text-tertiary">n/d</span> : fmtM(l.total)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </CarteAgrandissable>
  );
}
