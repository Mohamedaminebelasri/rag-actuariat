"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Maximize2, Minimize2 } from "lucide-react";
import { cn } from "@/lib/utils";

/** Éléments du document qui défilent (et peuvent donc faire défiler le fond). */
function ancetresDefilants(el: HTMLElement): HTMLElement[] {
  const resultat: HTMLElement[] = [];
  for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
    const oy = getComputedStyle(n).overflowY;
    if ((oy === "auto" || oy === "scroll") && n.scrollHeight > n.clientHeight) resultat.push(n);
  }
  return resultat;
}

/**
 * Carte d'outil agrandissable : titre + flèche « Agrandir » en haut à droite ;
 * agrandie, elle occupe presque tout l'écran (~96 vw × 94 vh, plein écran en
 * mobile) avec une flèche « Réduire », Échap et le clic sur le fond pour revenir.
 *
 * Le contenu n'est monté qu'UNE fois : la carte passe simplement en position
 * fixe (un emplacement de même hauteur garde la page en place), donc tout l'état
 * du contenu (KPI choisi, catégories ouvertes, filtre…) est conservé.
 * `children` reçoit `agrandi` pour adapter la mise en page, et `ouvrir`.
 */
export function CarteAgrandissable({
  titre,
  nom,
  actions,
  children,
  className,
}: {
  titre: string;
  /** Nom de l'outil pour les libellés accessibles (« le radar », « le tableau »…). */
  nom: string;
  /** Contrôles propres à l'outil, à gauche de la flèche (sélecteur, filtre…). */
  actions?: ReactNode;
  children: (etat: { agrandi: boolean; ouvrir: () => void }) => ReactNode;
  className?: string;
}) {
  const [agrandi, setAgrandi] = useState(false);
  const [hauteur, setHauteur] = useState<number | null>(null);
  const carteRef = useRef<HTMLDivElement>(null);
  const boutonRef = useRef<HTMLButtonElement>(null);

  const ouvrir = () => {
    setHauteur(carteRef.current?.getBoundingClientRect().height ?? null);
    setAgrandi(true);
  };
  const fermer = () => setAgrandi(false);

  // Agrandie : Échap ferme, focus piégé dans la carte, fond verrouillé (scroll
  // des conteneurs défilants gelé sans décaler la mise en page).
  useEffect(() => {
    if (!agrandi) return;
    const carte = carteRef.current;
    if (!carte) return;
    boutonRef.current?.focus();

    const verrous = ancetresDefilants(carte).map((n) => {
      const sauvegarde = { overflow: n.style.overflow, paddingRight: n.style.paddingRight };
      const barre = n.offsetWidth - n.clientWidth;
      if (barre > 0) n.style.paddingRight = `${parseFloat(getComputedStyle(n).paddingRight) + barre}px`;
      n.style.overflow = "hidden";
      return { n, sauvegarde };
    });
    const ancienBody = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const surClavier = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        // Une note d'avertissement ouverte se ferme d'abord.
        if (document.querySelector('[role="dialog"][aria-label="Valeur non comparable"]')) return;
        fermer();
        return;
      }
      if (e.key !== "Tab") return;
      const focalisables = Array.from(
        carte.querySelectorAll<HTMLElement>('button, [href], select, input, [tabindex]:not([tabindex="-1"])')
      ).filter((el) => !el.hasAttribute("disabled") && el.offsetParent !== null);
      if (focalisables.length === 0) return;
      const premier = focalisables[0];
      const dernier = focalisables[focalisables.length - 1];
      const courant = document.activeElement;
      if (!carte.contains(courant)) {
        e.preventDefault();
        premier.focus();
      } else if (e.shiftKey && courant === premier) {
        e.preventDefault();
        dernier.focus();
      } else if (!e.shiftKey && courant === dernier) {
        e.preventDefault();
        premier.focus();
      }
    };
    document.addEventListener("keydown", surClavier);
    return () => {
      document.removeEventListener("keydown", surClavier);
      document.body.style.overflow = ancienBody;
      verrous.forEach(({ n, sauvegarde }) => {
        n.style.overflow = sauvegarde.overflow;
        n.style.paddingRight = sauvegarde.paddingRight;
      });
    };
  }, [agrandi]);

  return (
    <div
      className={cn("w-full", className)}
      // Emplacement réservé : la page ne bouge pas quand la carte devient fixe.
      style={agrandi && hauteur ? { minHeight: hauteur } : undefined}
    >
      {agrandi && (
        <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={fermer} aria-hidden="true" />
      )}
      <div
        ref={carteRef}
        role={agrandi ? "dialog" : undefined}
        aria-modal={agrandi ? true : undefined}
        aria-label={agrandi ? `${titre} (agrandi)` : undefined}
        className={cn(
          "bg-surface border border-border flex flex-col",
          agrandi
            ? "fixed z-50 inset-0 sm:inset-x-[2vw] sm:inset-y-[3vh] sm:rounded-2xl shadow-2xl p-4 sm:p-5 overflow-hidden"
            : "rounded-[var(--radius-lg)] p-5 w-full"
        )}
      >
        <div className="flex items-center gap-3 flex-wrap mb-3 flex-shrink-0">
          <span className="font-body text-base font-medium text-text-primary">{titre}</span>
          <span className="flex-1" />
          {actions}
          <button
            ref={boutonRef}
            onClick={agrandi ? fermer : ouvrir}
            aria-label={agrandi ? `Réduire ${nom}` : `Agrandir ${nom}`}
            title={agrandi ? `Réduire ${nom}` : `Agrandir ${nom}`}
            className="w-8 h-8 flex-shrink-0 rounded-full flex items-center justify-center text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
          >
            {agrandi ? (
              <Minimize2 className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Maximize2 className="w-4 h-4" aria-hidden="true" />
            )}
          </button>
        </div>
        <div className={cn(agrandi && "flex-1 min-h-0 overflow-auto overscroll-contain")}>
          {children({ agrandi, ouvrir })}
        </div>
      </div>
    </div>
  );
}
