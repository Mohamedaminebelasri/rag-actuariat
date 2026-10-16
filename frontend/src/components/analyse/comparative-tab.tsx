"use client";

import { useState } from "react";
import { Info, RotateCcw, TriangleAlert, Users, X } from "lucide-react";
import {
  FILTRES_VIDES,
  avertissementComparabilite,
  societesFiltrees,
  type FiltresSocietes,
} from "@/lib/analyse-utils";
import { listeSfcrDisponibles } from "@/data/analyse-demo";
import { ComparativeTable } from "./comparative-table";
import { RadarComparatif } from "./radar-chart";
import { TiersComparatif } from "./tiers-comparatif";
import { TreemapPanel } from "./treemap-panel";
import { GroupeFiliales } from "./groupe-filiales";
import { ComparisonBarChart } from "./comparison-bar-chart";
import { AlertsPanel } from "./alerts-panel";
import { FiltresSocietesBar } from "./filtres-societes";
import { groupePairsCommun, groupePairsDe } from "@/lib/comparabilite";
// import { exporterCsvComparatif } from "@/lib/csv-export"; // masqué : export CSV à refaire plus tard (marqueur valeur non comparable, séparateur ; + BOM UTF-8, colonnes confiance/variation)
import { SEUIL_VERT_SCR_DEFAUT } from "@/lib/seuils-config";

const MAX_SOCIETES = 8;

/** Port de analyse_comparative() (comparative.py, Reflex). */
export function ComparativeTab({ seuilVertScr = SEUIL_VERT_SCR_DEFAUT }: { seuilVertScr?: number }) {
  const [societes, setSocietes] = useState<string[]>([]);
  const [filtreCategorie, setFiltreCategorie] = useState("Tous");
  const [kpiGraphique, setKpiGraphique] = useState("ratio_scr");
  const [filtres, setFiltres] = useState<FiltresSocietes>(FILTRES_VIDES);

  const sfcrDisponibles = listeSfcrDisponibles();
  const idsFiltres = societesFiltrees(filtres);
  const disponiblesAAjouter = sfcrDisponibles.filter((s) => !societes.includes(s.id) && idsFiltres.includes(s.id));
  const avertissement = avertissementComparabilite(societes);
  const peutComparer = societes.length >= 2;
  const auMaximum = societes.length >= MAX_SOCIETES;

  // Groupe de pairs (activité · modèle · périmètre) de la société de référence
  // = la première sélectionnée. Le comparatif est limité à MAX_SOCIETES colonnes.
  const reference = societes[0];
  const pairsReference = reference ? groupePairsDe(reference) : null;
  const pairsSelection = groupePairsCommun(societes);
  const comparerAuxPairs = () => {
    if (!reference || !pairsReference) return;
    const membres = [reference, ...pairsReference.societes.filter((s) => s !== reference)];
    setSocietes(membres.slice(0, MAX_SOCIETES));
  };

  const ajouter = (id: string) => {
    if (!id || societes.includes(id) || auMaximum) return;
    setSocietes((prev) => [...prev, id]);
  };
  const retirer = (soc: string) => setSocietes((prev) => prev.filter((s) => s !== soc));
  const reinitialiser = () => setSocietes([]);

  return (
    <div className="flex flex-col gap-4 w-full items-start">
      {/* Barre de sélection multi */}
      {/* Filtres activité / modèle */}
      <div className="bg-surface border border-border rounded-[var(--radius-lg)] shadow-[var(--shadow-sm)] px-[1.2em] py-[1em] w-full">
        <FiltresSocietesBar
          filtres={filtres}
          onChange={setFiltres}
          resume={`${disponiblesAAjouter.length} assureur${disponiblesAAjouter.length > 1 ? "s" : ""} disponible${disponiblesAAjouter.length > 1 ? "s" : ""} à ajouter`}
        />
      </div>

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
          <button
            onClick={comparerAuxPairs}
            disabled={!pairsReference || pairsReference.n < 2}
            title={
              !reference
                ? "Sélectionnez d'abord un assureur (le premier sert de référence)"
                : !pairsReference || pairsReference.n < 2
                  ? "Aucun pair dans le panel pour cet assureur"
                  : `Sélectionne les pairs de ${reference} : ${pairsReference.id}`
            }
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border text-sm text-text-secondary hover:bg-surface-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
          >
            <Users className="w-3.5 h-3.5" aria-hidden="true" />
            Comparer à ses pairs
          </button>
          {societes.length > 0 && (
            <button
              onClick={reinitialiser}
              title="Retirer toutes les sociétés sélectionnées"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-danger/40 bg-danger-light text-sm font-medium text-danger hover:border-danger transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
              Réinitialiser
            </button>
          )}
          <span className="text-sm font-mono text-text-tertiary whitespace-nowrap">
            {societes.length}/{MAX_SOCIETES} assureurs sélectionnés
          </span>
        </div>
        {pairsSelection && (
          <p role="note" className="mt-2.5 flex items-start gap-1.5 text-xs leading-relaxed text-text-secondary">
            <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-text-tertiary" aria-hidden="true" />
            <span>
              Groupe de pairs : <span className="font-medium text-text-primary">{pairsSelection.id}</span> —{" "}
              {societes.length} sur {pairsSelection.n} société{pairsSelection.n > 1 ? "s" : ""} du groupe
              {pairsSelection.n > MAX_SOCIETES && ` (comparatif limité à ${MAX_SOCIETES} colonnes)`}.
              {pairsSelection.petitEchantillon &&
                ` Échantillon de ${pairsSelection.n} société${pairsSelection.n > 1 ? "s" : ""} : moyenne peu fiable.`}
            </span>
          </p>
        )}
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
          {/* masqué : export CSV à refaire plus tard (marqueur valeur non comparable, séparateur ; + BOM UTF-8, colonnes confiance/variation)
          <button
            onClick={() => exporterCsvComparatif(societes)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] border border-border text-sm font-medium text-text-secondary hover:bg-surface-hover transition-colors"
          >
            <Download className="w-[15px] h-[15px]" />
            Exporter (CSV)
          </button> */}

          <RadarComparatif societesComparees={societes} />
          <TiersComparatif societesComparees={societes} />
          <TreemapPanel societesFiltrees={idsFiltres} societesSelectionnees={societes} seuilVertScr={seuilVertScr} />
          <GroupeFiliales societesSelectionnees={societes} seuilVertScr={seuilVertScr} />
          <ComparisonBarChart societesComparees={societes} kpiId={kpiGraphique} onChangeKpi={setKpiGraphique} />

          <ComparativeTable
            societesComparees={societes}
            filtreCategorie={filtreCategorie}
            onChangeFiltre={setFiltreCategorie}
            seuilVertScr={seuilVertScr}
          />

          <AlertsPanel societesComparees={societes} />
        </div>
      )}
    </div>
  );
}
