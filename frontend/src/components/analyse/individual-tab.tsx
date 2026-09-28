"use client";

import { useState } from "react";
import { CircleCheck, Download, FileSearch, FileText } from "lucide-react";
import { CATEGORIES, KPI_DEFINITIONS, kpisSociete, listeSfcrDisponibles } from "@/data/analyse-demo";
import { KpiCard } from "./kpi-card";
import { ScrBreakdownChart } from "./scr-breakdown-chart";
import { PositionMarche } from "./position-marche";
import { LegendeStatuts } from "./legende-statuts";
import { exporterCsvIndividuel } from "@/lib/csv-export";

/** Port de analyse_individuelle() (individuelle.py, Reflex). */
export function IndividualTab() {
  const [societe, setSociete] = useState("");
  const sfcrDisponibles = listeSfcrDisponibles();
  const label = sfcrDisponibles.find((s) => s.id === societe)?.label ?? "";
  const kpis = kpisSociete(societe);

  return (
    <div className="flex flex-col gap-4 w-full items-start">
      {/* Sélecteur */}
      <div className="bg-surface border border-border rounded-[var(--radius-lg)] shadow-[var(--shadow-sm)] px-[1.2em] py-[1em] w-full">
        <div className="flex items-center gap-3 w-full">
          <FileText className="w-[18px] h-[18px] text-text-secondary flex-shrink-0" />
          <select
            value={societe}
            onChange={(e) => setSociete(e.target.value)}
            className="flex-1 min-w-0 text-sm border border-border rounded-[var(--radius-md)] px-3 py-2 bg-surface text-text-primary font-body"
          >
            <option value="">Sélectionnez un rapport SFCR…</option>
            {sfcrDisponibles.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
          {societe && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-success-light text-success text-xs font-medium whitespace-nowrap">
              <CircleCheck className="w-[13px] h-[13px]" />
              Chargé
            </span>
          )}
        </div>
      </div>

      {!societe ? (
        <div className="flex flex-col items-center justify-center gap-2 w-full" style={{ minHeight: "40vh" }}>
          <FileSearch className="w-9 h-9 text-text-tertiary" />
          <p className="text-base font-medium text-text-secondary mt-2">
            Sélectionnez un rapport SFCR pour voir l&apos;analyse
          </p>
        </div>
      ) : (
        <div className="w-full flex flex-col items-start">
          <div className="flex items-center w-full mt-6 mb-2">
            <h2 className="font-heading italic text-2xl text-text-primary">{label}</h2>
            <span className="flex-1" />
            <button
              onClick={() => exporterCsvIndividuel(societe)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] border border-border text-sm font-medium text-text-secondary hover:bg-surface-hover transition-colors"
            >
              <Download className="w-[15px] h-[15px]" />
              Exporter (CSV)
            </button>
          </div>

          {/* <PositionMarche key={societe} societe={societe} /> */}
          <LegendeStatuts />

          {CATEGORIES.map((c) => {
            const kpisCategorie = KPI_DEFINITIONS.filter((k) => k.categorie === c.code && kpis[k.id] !== undefined);
            if (kpisCategorie.length === 0) return null;
            return (
              <div key={c.code} className="flex flex-col gap-3 w-full items-start mb-8">
                <h3 className="font-heading italic text-lg text-text-primary">
                  {c.code} — {c.label}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full">
                  {kpisCategorie.map((k) => (
                    <KpiCard key={k.id} def={k} valeur={kpis[k.id]} societe={societe} />
                  ))}
                </div>
              </div>
            );
          })}

          <hr className="w-full border-border my-4" />
          <p className="font-heading italic text-lg text-text-primary mb-4">
            Décomposition du SCR par module de risque
          </p>
          <ScrBreakdownChart kpis={kpis} />
        </div>
      )}
    </div>
  );
}
