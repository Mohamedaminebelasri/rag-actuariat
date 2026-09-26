"use client";

import { Filter, X } from "lucide-react";
import { MODELES_CAPITAL, TYPES_SOCIETE, type ModeleCapital, type TypeSociete } from "@/data/analyse-demo";
import { FILTRES_VIDES, type FiltresSocietes } from "@/lib/analyse-utils";

const CLASSE_SELECT =
  "text-sm border border-border rounded-[var(--radius-md)] px-2.5 py-1.5 bg-surface text-text-primary font-body";

/** Idée 3 : filtres par type d'activité et par modèle de capital. */
export function FiltresSocietesBar({
  filtres,
  onChange,
  resume,
}: {
  filtres: FiltresSocietes;
  onChange: (f: FiltresSocietes) => void;
  resume?: string;
}) {
  const actif = filtres.type !== FILTRES_VIDES.type || filtres.modele !== FILTRES_VIDES.modele;

  return (
    <div className="flex items-center gap-3 flex-wrap w-full">
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary">
        <Filter className="w-3.5 h-3.5" aria-hidden="true" />
        Filtres
      </span>
      <select
        aria-label="Filtrer par type d'activité"
        value={filtres.type}
        onChange={(e) => onChange({ ...filtres, type: e.target.value as TypeSociete | "Tous" })}
        className={CLASSE_SELECT}
      >
        <option value="Tous">Toutes les activités</option>
        {TYPES_SOCIETE.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
      <select
        aria-label="Filtrer par modèle de capital"
        value={filtres.modele}
        onChange={(e) => onChange({ ...filtres, modele: e.target.value as ModeleCapital | "Tous" })}
        className={CLASSE_SELECT}
      >
        <option value="Tous">Tous les modèles</option>
        {MODELES_CAPITAL.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
      {actif && (
        <button
          onClick={() => onChange(FILTRES_VIDES)}
          className="inline-flex items-center gap-1 text-xs text-accent hover:underline"
        >
          <X className="w-3 h-3" aria-hidden="true" />
          Réinitialiser
        </button>
      )}
      {resume && <span className="text-xs text-text-tertiary ml-auto">{resume}</span>}
    </div>
  );
}
