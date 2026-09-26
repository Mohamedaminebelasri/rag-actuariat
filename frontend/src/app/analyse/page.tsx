"use client";

import { useState } from "react";
import { Columns3, FileBarChart, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { IndividualTab } from "@/components/analyse/individual-tab";
import { ComparativeTab } from "@/components/analyse/comparative-tab";

/** Port de page_analyse() (test_markdrop/sfcr_app/analyse/page.py, Reflex,
 * commit c83d3ef) — 2 sous-onglets (individuelle/comparative), design
 * "Ivory" repris des tokens globaux (globals.css). Données 100% mock
 * (analyse-demo.ts) tant que le backend réel (kpis.db) n'est pas branché
 * sur cette page — bandeau "Données de démonstration" ci-dessous. */
export default function AnalysePage() {
  const [sousOnglet, setSousOnglet] = useState<"individuelle" | "comparative">("individuelle");

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto px-6 py-8" style={{ width: "92%", maxWidth: "1500px" }}>
        <div className="flex items-center mb-2">
          <div>
            <p className="text-xs font-bold tracking-[0.12em] text-accent">SOLVABILITÉ II</p>
            <h2 className="font-heading italic text-3xl text-text-primary mt-0.5">Analyse</h2>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-warning-light border border-warning/30 rounded-[10px] px-4 py-2.5 w-full my-4">
          <Info className="w-[15px] h-[15px] text-warning flex-shrink-0" />
          <p className="text-sm font-medium text-warning">
            Données de démonstration — l&apos;onglet Analyse n&apos;est pas encore connecté au backend réel.
          </p>
        </div>

        <div className="inline-flex gap-1 p-1 bg-surface-secondary rounded-[12px] mb-6">
          <OngletNav
            label="Analyse individuelle"
            actif={sousOnglet === "individuelle"}
            icone={<FileBarChart className="w-[15px] h-[15px]" />}
            onClick={() => setSousOnglet("individuelle")}
          />
          <OngletNav
            label="Analyse comparative"
            actif={sousOnglet === "comparative"}
            icone={<Columns3 className="w-[15px] h-[15px]" />}
            onClick={() => setSousOnglet("comparative")}
          />
        </div>

        {sousOnglet === "individuelle" ? <IndividualTab /> : <ComparativeTab />}
      </div>
    </div>
  );
}

function OngletNav({
  label,
  actif,
  icone,
  onClick,
}: {
  label: string;
  actif: boolean;
  icone: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 px-[1.1em] py-[0.65em] rounded-[8px] text-sm font-medium transition-colors",
        actif ? "text-accent bg-accent-light" : "text-text-secondary hover:bg-surface-hover"
      )}
    >
      {icone}
      {label}
    </button>
  );
}
