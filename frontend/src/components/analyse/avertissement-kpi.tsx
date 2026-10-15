"use client";

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { Scale, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/** Texte affiché quand le KPI porte `avertissement` sans `noteAvertissement`. */
export const NOTE_AVERTISSEMENT_DEFAUT =
  "Valeur calculée sur une base non directement comparable aux autres sociétés.";

const LARGEUR_MAX = 320;
const MARGE = 8;

/** Position « fixed » du panneau, calculée à l'ouverture : sous le bouton s'il
 * y a la place, sinon au-dessus. Le panneau est rendu dans un portail : ni le
 * conteneur `overflow-x-auto` du tableau ni une carte ne peuvent le couper. */
function positionPanneau(bouton: HTMLElement): CSSProperties {
  const r = bouton.getBoundingClientRect();
  const largeur = Math.min(LARGEUR_MAX, window.innerWidth - 2 * MARGE);
  const left = Math.max(MARGE, Math.min(r.left + r.width / 2 - largeur / 2, window.innerWidth - largeur - MARGE));
  const placeDessous = window.innerHeight - r.bottom - MARGE;
  const placeDessus = r.top - MARGE;
  if (placeDessous >= 180 || placeDessous >= placeDessus) {
    return { left, width: largeur, top: r.bottom + 6, maxHeight: Math.max(120, placeDessous - 6) };
  }
  return { left, width: largeur, bottom: window.innerHeight - r.top + 6, maxHeight: Math.max(120, placeDessus - 6) };
}

/** Marqueur « valeur non comparable » (champ `avertissement` d'un KPI) : petit
 * bouton-icône qui ouvre la note. Couleur d'accent — jamais celle du feu
 * tricolore (réservé aux ratios SCR/MCR) ni celle des alertes.
 *
 * `note` : noteAvertissement du KPI (texte par défaut si vide).
 * `titre` : ligne optionnelle au-dessus de la note (ex. modules concernés). */
export function AvertissementKpi({
  note,
  titre,
  className,
  icone: Icone = Scale,
  intitule = "Valeur non comparable",
  infobulle = "Valeur non comparable : cliquer pour lire la note",
  classeIcone = "text-accent",
}: {
  note?: string | null;
  titre?: string;
  className?: string;
  /** Icône du bouton (défaut : balance, valeur non comparable). */
  icone?: LucideIcon;
  /** Intitulé du panneau et nom accessible du bouton. */
  intitule?: string;
  infobulle?: string;
  /** Classe de couleur de l'icône (jamais celle du feu tricolore). */
  classeIcone?: string;
}) {
  const [ouvert, setOuvert] = useState(false);
  const [style, setStyle] = useState<CSSProperties>({});
  const boutonRef = useRef<HTMLButtonElement>(null);
  const panneauRef = useRef<HTMLDivElement>(null);
  const texte = note?.trim() ? note.trim() : NOTE_AVERTISSEMENT_DEFAUT;

  const fermer = useCallback((rendreFocus: boolean) => {
    setOuvert(false);
    if (rendreFocus) boutonRef.current?.focus();
  }, []);

  const basculer = () => {
    if (ouvert) {
      fermer(false);
      return;
    }
    if (boutonRef.current) setStyle(positionPanneau(boutonRef.current));
    setOuvert(true);
  };

  // Ouvert : Échap ferme (focus rendu au bouton), clic extérieur ferme, et le
  // panneau (position fixe) se ferme dès que la page défile ou se redimensionne.
  useEffect(() => {
    if (!ouvert) return;
    panneauRef.current?.focus();
    const surClavier = (e: KeyboardEvent) => {
      if (e.key === "Escape") fermer(true);
    };
    const surClic = (e: PointerEvent) => {
      const cible = e.target as Node;
      if (boutonRef.current?.contains(cible) || panneauRef.current?.contains(cible)) return;
      fermer(false);
    };
    const surDefilement = (e: Event) => {
      if (panneauRef.current?.contains(e.target as Node)) return;
      fermer(false);
    };
    const surRedim = () => fermer(false);
    document.addEventListener("keydown", surClavier);
    document.addEventListener("pointerdown", surClic);
    window.addEventListener("scroll", surDefilement, true);
    window.addEventListener("resize", surRedim);
    return () => {
      document.removeEventListener("keydown", surClavier);
      document.removeEventListener("pointerdown", surClic);
      window.removeEventListener("scroll", surDefilement, true);
      window.removeEventListener("resize", surRedim);
    };
  }, [ouvert, fermer]);

  return (
    <>
      <button
        ref={boutonRef}
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          basculer();
        }}
        aria-label={`${intitule} : voir la note`}
        aria-expanded={ouvert}
        aria-haspopup="dialog"
        title={infobulle}
        className={cn(
          "inline-flex items-center justify-center align-middle w-6 h-6 -my-1 rounded-full hover:bg-accent-light focus-visible:outline-2 focus-visible:outline-accent transition-colors",
          classeIcone,
          className
        )}
      >
        <Icone className="w-3.5 h-3.5" aria-hidden="true" />
      </button>

      {ouvert &&
        createPortal(
          <div
            ref={panneauRef}
            role="dialog"
            aria-label={intitule}
            tabIndex={-1}
            style={style}
            onKeyDown={(e) => {
              // Contenu textuel sans élément focusable : Tab quitte le panneau.
              if (e.key === "Tab") {
                e.preventDefault();
                fermer(true);
              }
            }}
            className="fixed z-[60] overflow-y-auto rounded-[var(--radius-md)] border border-border bg-surface p-3 shadow-[var(--shadow-lg)] text-left font-body outline-none"
          >
            <p className="flex items-center gap-1.5 text-xs font-medium text-text-primary">
              <Icone className={cn("w-3.5 h-3.5 flex-shrink-0", classeIcone)} aria-hidden="true" />
              {intitule}
            </p>
            {titre && <p className="mt-1.5 text-xs font-medium text-text-primary">{titre}</p>}
            <p className="mt-1.5 text-xs leading-relaxed text-text-secondary whitespace-pre-line">{texte}</p>
          </div>,
          document.body
        )}
    </>
  );
}
