"use client";

import { useState } from "react";
import { Download, TriangleAlert, Users, X } from "lucide-react";
import {
  CATEGORIE_LABELS,
  FILTRES_VIDES,
  avertissementComparabilite,
  societesFiltrees,
  type FiltresSocietes,
} from "@/lib/analyse-utils";
import { listeSfcrDisponibles } from "@/data/analyse-demo";
import { ComparativeTable } from "./comparative-table";
import { RadarComparatif } from "./radar-chart";
import { ComparisonBarChart } from "./comparison-bar-chart";
import { AlertsPanel } from "./alerts-panel";
import { FiltresSocietesBar } from "./filtres-societes";
import { exporterCsvComparatif } from "@/lib/csv-export";

const MAX_SOCIETES = 8;
const CATEGORIES_FILTRE = ["Tous", "E", "D", "C", "A"];

/** Port de analyse_comparative() (comparative.py, Reflex). */
export function ComparativeTab() {
  const [societes, setSocietes] = useState<string[]>(["Groupama", "CNP Assurances"]);
  const [filtreCategorie, setFiltreCategorie] = useState("Tous");
  const [kpiGraphique, setKpiGraphique] = useState("ratio_scr");
  const [afficherMoyenne, setAfficherMoyenne] = useState(true);
  const [afficherMediane, setAfficherMediane] = useState(true);
  const [afficherSeuil, setAfficherSeuil] = useState(true);
  const [filtres, setFiltres] = useState<FiltresSocietes>(FILTRES_VIDES);

  const sfcrDisponibles = listeSfcrDisponibles();
  const idsFiltres = societesFiltrees(filtres);
  const disponiblesAAjouter = sfcrDisponibles.filter((s) => !societes.includes(s.id) && idsFiltres.includes(s.id));
  const avertissement = avertissementComparabilite(societes);
  const peutComparer = societes.length >= 2;
  const auMaximum = societes.length >= MAX_SOCIETES;

  const ajouter = (id: string) => {
    if (!id || societes.includes(id) || auMaximum) return;
    setSocietes((prev) => [...prev, id]);
  };
  const retirer = (soc: string) => setSocietes((prev) => prev.filter((s) => s !== soc));

  return (
    <div className="flex flex-col gap-4 w-full items-start">
      {/* Barre de sélection multi */}
      <div className="bg-surface border border-border rounded-[var(--radius-lg)] shadow-[var(--shadow-sm)] px-[1.2em] py-[1em] w-full">
        <div className="flex items-center gap-3 flex-wrap w-full">
          {societes.map((soc) => (
            <span
              key={soc}
              className="inline-flex items-center gap-2 pl-3.5 pr-2 py-1.5 rounded-full bg-accent-light text-accent text-sm font-medium"
            >
              {soc}
              <button onClick={() => retirer(soc)} title="Retirer">
                <X className="w-3.5 h-3.5" />
              </button>
            </span>
          ))}
          {!auMaximum && (
            <select
              value=""
              onChange={(e) => ajouter(e.target.value)}
              className="text-sm border border-border rounded-full px-3 py-1.5 bg-surface text-text-secondary font-body"
            >
              <option value="">
                {disponiblesAAjouter.length > 0 ? "+ Ajouter un assureur" : "Aucun assureur pour ces filtres"}
              </option>
              {disponiblesAAjouter.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          )}
          <span className="flex-1" />
          <span className="text-sm font-mono text-text-tertiary whitespace-nowrap">
            {societes.length}/{MAX_SOCIETES} assureurs sélectionnés
          </span>
        </div>
        <div className="mt-3 pt-3 border-t border-border">
          <FiltresSocietesBar
            filtres={filtres}
            onChange={setFiltres}
            resume={`${disponiblesAAjouter.length} assureur${disponiblesAAjouter.length > 1 ? "s" : ""} disponible${disponiblesAAjouter.length > 1 ? "s" : ""} à ajouter`}
          />
        </div>
      </div>

      {peutComparer && avertissement && (
        <div
          role="note"
          className="flex items-start gap-2 bg-warning-light border border-warning/30 rounded-[10px] px-4 py-2.5 w-full"
        >
          <TriangleAlert className="w-[15px] h-[15px] text-warning flex-shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-sm text-warning">{avertissement}</p>
        </div>
      )}

      {!peutComparer ? (
        <div className="flex flex-col items-center justify-center gap-2 w-full" style={{ minHeight: "30vh" }}>
          <Users className="w-8 h-8 text-text-tertiary" />
          <p className="text-base font-medium text-text-secondary mt-1.5">
            Sélectionnez au moins 2 assureurs pour comparer
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4 w-full items-start">
          <div className="flex items-center w-full">
            <span className="flex-1" />
            <button
              onClick={() => exporterCsvComparatif(societes)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] border border-border text-sm font-medium text-text-secondary hover:bg-surface-hover transition-colors"
            >
              <Download className="w-[15px] h-[15px]" />
              Exporter (CSV)
            </button>
          </div>

          <RadarComparatif societesComparees={societes} />
          <ComparisonBarChart societesComparees={societes} kpiId={kpiGraphique} onChangeKpi={setKpiGraphique} />

          {/* Filtre + options benchmark */}
          <div className="flex items-center gap-4 flex-wrap w-full">
            <select
              value={filtreCategorie}
              onChange={(e) => setFiltreCategorie(e.target.value)}
              className="text-sm border border-border rounded-[var(--radius-md)] px-2.5 py-1.5 bg-surface text-text-primary font-body"
            >
              {CATEGORIES_FILTRE.map((c) => (
                <option key={c} value={c}>
                  {CATEGORIE_LABELS[c]}
                </option>
              ))}
            </select>
            <span className="flex-1" />
            <label className="flex items-center gap-1.5 text-sm text-text-primary cursor-pointer">
              <input type="checkbox" checked={afficherMoyenne} onChange={() => setAfficherMoyenne((v) => !v)} />
              Moyenne
            </label>
            <label className="flex items-center gap-1.5 text-sm text-text-primary cursor-pointer">
              <input type="checkbox" checked={afficherMediane} onChange={() => setAfficherMediane((v) => !v)} />
              Médiane
            </label>
            <label className="flex items-center gap-1.5 text-sm text-text-primary cursor-pointer">
              <input type="checkbox" checked={afficherSeuil} onChange={() => setAfficherSeuil((v) => !v)} />
              Seuil réglementaire
            </label>
          </div>

          <ComparativeTable
            societesComparees={societes}
            filtreCategorie={filtreCategorie}
            afficherMoyenne={afficherMoyenne}
            afficherMediane={afficherMediane}
            afficherSeuil={afficherSeuil}
          />

          <AlertsPanel societesComparees={societes} />
        </div>
      )}
    </div>
  );
}
