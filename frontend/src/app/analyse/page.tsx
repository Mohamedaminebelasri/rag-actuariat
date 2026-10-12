"use client";

import { useEffect, useState } from "react";
import { Columns3, FileBarChart, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { IndividualTab } from "@/components/analyse/individual-tab";
import { ComparativeTab } from "@/components/analyse/comparative-tab";
import { LegendeStatuts } from "@/components/analyse/legende-statuts";
import { SeuilsPanel } from "@/components/analyse/seuils-panel";
import { KPI_DEFINITIONS } from "@/data/analyse-demo";
import { STATS_GLOBALES } from "@/lib/donnees-extraites-utils";
import {
  SEUIL_VERT_SCR_DEFAUT,
  ecrireSeuilVertStocke,
  lireSeuilVertStocke,
  reinitialiserSeuilVertStocke,
} from "@/lib/seuils-config";

/** Port de page_analyse() (test_markdrop/sfcr_app/analyse/page.py, Reflex,
 * commit c83d3ef) — 2 sous-onglets (individuelle/comparative), design
 * "Ivory" repris des tokens globaux (globals.css). Données réelles issues de kpis.db via donnees-extraites.json
 * (analyse-demo.ts). Nombre de sociétés/KPIs lu dynamiquement (STATS_GLOBALES,
 * KPI_DEFINITIONS) — jamais codé en dur, pour ne pas se figer après ajout de sociétés. */
export default function AnalysePage() {
  const [sousOnglet, setSousOnglet] = useState<"individuelle" | "comparative">("individuelle");
  const [seuilVertScr, setSeuilVertScr] = useState(SEUIL_VERT_SCR_DEFAUT);

  // Lu après montage uniquement (localStorage indisponible côté serveur,
  // évite un mismatch d'hydratation) ; try/catch déjà géré dans la lib.
  useEffect(() => {
    setSeuilVertScr(lireSeuilVertStocke());
  }, []);

  const changerSeuilVert = (valeur: number) => {
    setSeuilVertScr(valeur);
    ecrireSeuilVertStocke(valeur);
  };
  const reinitialiserSeuilVert = () => {
    reinitialiserSeuilVertStocke();
    setSeuilVertScr(SEUIL_VERT_SCR_DEFAUT);
  };

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto px-4 sm:px-6 py-6 sm:py-8" style={{ width: "92%", maxWidth: "1500px" }}>
        <div className="flex items-center mb-2">
          <div>
            <p className="text-xs font-bold tracking-[0.12em] text-accent">SOLVABILITÉ II</p>
            <h2 className="font-heading italic text-3xl text-text-primary mt-0.5">Analyse</h2>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-300/40 rounded-[10px] px-4 py-2.5 w-full my-4 dark:bg-emerald-950/30 dark:border-emerald-500/20">
          <Info className="w-[15px] h-[15px] text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
          <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
            Données réelles — {STATS_GLOBALES.nbSocietes} sociétés, {KPI_DEFINITIONS.length} indicateurs extraits des rapports SFCR.
          </p>
        </div>

        <div className="flex sm:inline-flex gap-1 p-1 bg-surface-secondary rounded-[12px] mb-6 w-full sm:w-auto">
          <OngletNav
            label="Analyse individuelle"
            court="Individuelle"
            actif={sousOnglet === "individuelle"}
            icone={<FileBarChart className="w-[15px] h-[15px]" />}
            onClick={() => setSousOnglet("individuelle")}
          />
          <OngletNav
            label="Analyse comparative"
            court="Comparative"
            actif={sousOnglet === "comparative"}
            icone={<Columns3 className="w-[15px] h-[15px]" />}
            onClick={() => setSousOnglet("comparative")}
          />
        </div>

        <LegendeStatuts seuilVertScr={seuilVertScr} />
        <SeuilsPanel seuilVertScr={seuilVertScr} onChange={changerSeuilVert} onReset={reinitialiserSeuilVert} />

        {sousOnglet === "individuelle" ? (
          <IndividualTab seuilVertScr={seuilVertScr} />
        ) : (
          <ComparativeTab seuilVertScr={seuilVertScr} />
        )}
      </div>
    </div>
  );
}

function OngletNav({
  label,
  court,
  actif,
  icone,
  onClick,
}: {
  label: string;
  court: string;
  actif: boolean;
  icone: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex flex-1 sm:flex-none items-center justify-center gap-2 px-3 sm:px-[1.1em] py-[0.65em] rounded-[8px] text-sm font-medium transition-colors",
        actif ? "text-accent bg-accent-light" : "text-text-secondary hover:bg-surface-hover"
      )}
    >
      {icone}
      <span className="sm:hidden">{court}</span>
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}
