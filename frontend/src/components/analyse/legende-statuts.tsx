import { Lock } from "lucide-react";

/** Légende de lecture des couleurs du feu tricolore (ratio SCR / ratio MCR
 * uniquement). Rouge = seuil légal Solvabilité II (verrouillé). Vert =
 * repère conventionnel de marché, modifiable via le panneau Seuils. */
function Point({ classe, label, verrouille }: { classe: string; label: string; verrouille?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`w-2 h-2 rounded-full ${classe}`} aria-hidden="true" />
      {label}
      {verrouille && <Lock className="w-3 h-3 text-text-tertiary" aria-label="Seuil légal, verrouillé" />}
    </span>
  );
}

export function LegendeStatuts({ seuilVertScr }: { seuilVertScr: number }) {
  return (
    <div
      role="note"
      className="flex flex-wrap items-center gap-x-5 gap-y-1.5 w-full text-xs text-text-secondary bg-surface-secondary rounded-[var(--radius-md)] px-4 py-2.5 mb-6"
    >
      <span className="font-medium text-text-primary">Lecture des couleurs (ratio SCR)</span>
      <Point classe="bg-danger" label="< 100 % (légal)" verrouille />
      <Point classe="bg-warning" label={`100–${seuilVertScr} % (vigilance)`} />
      <Point classe="bg-success" label={`≥ ${seuilVertScr} % (conventionnel)`} />
      <span className="text-text-tertiary">Ratio MCR : rouge si &lt; 100 % (légal), vert sinon — pas de zone orange.</span>
      <span className="flex-1" />
      <span className="text-text-tertiary">
        Flèche de tendance : « — » tant qu&apos;un seul exercice (2025) est disponible.
      </span>
    </div>
  );
}
