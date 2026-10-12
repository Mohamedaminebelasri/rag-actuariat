"use client";

import { useState } from "react";
import { Lock, RotateCcw, SlidersHorizontal } from "lucide-react";
import { SEUIL_LEGAL, SEUIL_VERT_SCR_DEFAUT } from "@/lib/seuils-config";

/** Panneau de réglage du seuil vert (conventionnel, modifiable) du ratio
 * SCR. Le seuil rouge (100 %, légal) n'est jamais réglable ici. */
export function SeuilsPanel({
  seuilVertScr,
  onChange,
  onReset,
}: {
  seuilVertScr: number;
  onChange: (valeur: number) => void;
  onReset: () => void;
}) {
  const [ouvert, setOuvert] = useState(false);
  const [brouillon, setBrouillon] = useState(String(seuilVertScr));

  const appliquer = () => {
    const v = Number(brouillon.replace(",", "."));
    if (Number.isFinite(v) && v > SEUIL_LEGAL) onChange(v);
    else setBrouillon(String(seuilVertScr));
  };

  const reinitialiser = () => {
    onReset();
    setBrouillon(String(SEUIL_VERT_SCR_DEFAUT));
  };

  return (
    <div className="bg-surface border border-border rounded-[var(--radius-lg)] shadow-[var(--shadow-sm)] w-full mb-4">
      <button
        onClick={() => setOuvert((v) => !v)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-text-primary"
      >
        <SlidersHorizontal className="w-[15px] h-[15px] text-text-secondary" aria-hidden="true" />
        Seuils
        <span className="text-text-tertiary font-normal">
          (vert ratio SCR : {seuilVertScr} %)
        </span>
        <span className="flex-1" />
        <span className="text-xs text-text-tertiary">{ouvert ? "Masquer" : "Modifier"}</span>
      </button>

      {ouvert && (
        <div className="px-4 pb-4 flex flex-col gap-3 border-t border-border pt-3">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="inline-flex items-center gap-1.5 text-sm text-text-secondary">
              <Lock className="w-3.5 h-3.5" aria-hidden="true" />
              Seuil rouge (légal, Solvabilité II) : <span className="font-mono font-medium">{SEUIL_LEGAL} %</span>
            </span>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <label htmlFor="seuil-vert-scr" className="text-sm text-text-secondary">
              Seuil vert (conventionnel, ratio SCR)
            </label>
            <input
              id="seuil-vert-scr"
              type="number"
              min={SEUIL_LEGAL + 1}
              step={1}
              value={brouillon}
              onChange={(e) => setBrouillon(e.target.value)}
              onBlur={appliquer}
              onKeyDown={(e) => e.key === "Enter" && appliquer()}
              className="w-24 text-sm font-mono border border-border rounded-[var(--radius-md)] px-2.5 py-1.5 bg-surface text-text-primary"
            />
            <span className="text-sm text-text-secondary">%</span>
            <button
              onClick={reinitialiser}
              className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary px-2.5 py-1.5 rounded-[var(--radius-md)] border border-border hover:bg-surface-hover transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
              Réinitialiser ({SEUIL_VERT_SCR_DEFAUT} %)
            </button>
          </div>
          <p className="text-xs text-text-tertiary">
            Le seuil vert doit rester strictement supérieur au seuil légal ({SEUIL_LEGAL} %). Mémorisé dans ce
            navigateur uniquement.
          </p>
        </div>
      )}
    </div>
  );
}
