/** Légende de lecture des couleurs (idée 1). Seuils indicatifs de démonstration. */
function Point({ classe, label }: { classe: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`w-2 h-2 rounded-full ${classe}`} aria-hidden="true" />
      {label}
    </span>
  );
}

export function LegendeStatuts() {
  return (
    <div
      role="note"
      className="flex flex-wrap items-center gap-x-5 gap-y-1.5 w-full text-xs text-text-secondary bg-surface-secondary rounded-[var(--radius-md)] px-4 py-2.5 mb-6"
    >
      <span className="font-medium text-text-primary">Lecture des couleurs</span>
      <Point classe="bg-success" label="Solide (ratios SCR/MCR ≥ 150 %)" />
      <Point classe="bg-warning" label="Vigilance (100 à 150 %)" />
      <Point classe="bg-danger" label="Sous le seuil (< 100 %)" />
      <span>
        Flèche : <span className="text-success font-medium">amélioration</span> ·{" "}
        <span className="text-danger font-medium">dégradation</span> · grise si le sens n&apos;est pas jugeable
      </span>
      <span className="text-text-tertiary">
        Ratio S/P : ≤ 95 % maîtrisé, ≤ 105 % vigilance. Seuils indicatifs de démonstration.
      </span>
    </div>
  );
}
