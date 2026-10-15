"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Info, Scale, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { KPI_DEFINITIONS } from "@/data/analyse-demo";
import { STATS_GLOBALES } from "@/lib/donnees-extraites-utils";
import { SEUIL_LEGAL, SEUIL_VERT_SCR_DEFAUT } from "@/lib/seuils-config";

type SousOnglet = "individuelle" | "comparative";

function Point({ classe }: { classe: string }) {
  return <span className={cn("inline-block w-2 h-2 rounded-full mr-1.5", classe)} aria-hidden="true" />;
}

function Section({ titre, defaultOpen, children }: { titre: string; defaultOpen: boolean; children: React.ReactNode }) {
  const [ouvert, setOuvert] = useState(defaultOpen);
  return (
    <section className="border border-border rounded-[var(--radius-md)]">
      <button
        onClick={() => setOuvert((v) => !v)}
        aria-expanded={ouvert}
        className="w-full flex items-center gap-2 px-3.5 py-2.5 text-sm font-medium text-text-primary text-left"
      >
        <span className="flex-1">{titre}</span>
        <ChevronDown className={cn("w-4 h-4 text-text-tertiary transition-transform", ouvert && "rotate-180")} aria-hidden="true" />
      </button>
      {ouvert && (
        <div className="px-3.5 pb-3.5 pt-0.5 flex flex-col gap-2 text-sm text-text-secondary leading-relaxed">{children}</div>
      )}
    </section>
  );
}

/** Bouton « i » fixe (bas droite) + panneau latéral d'aide à la lecture.
 * Remplace la légende des couleurs et le panneau Seuils, qui étaient inline
 * dans la page. Seuil vert fixé (seuils-config.ts) — plus de réglage. */
export function AidePanel({ sousOnglet }: { sousOnglet: SousOnglet }) {
  const [ouvert, setOuvert] = useState(false);
  const fermerRef = useRef<HTMLButtonElement>(null);
  const declencheurRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!ouvert) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOuvert(false);
        declencheurRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    fermerRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [ouvert]);

  const fermer = () => {
    setOuvert(false);
    declencheurRef.current?.focus();
  };

  const individuelle = (
    <Section key={`ind-${sousOnglet}`} titre="Analyse individuelle" defaultOpen={sousOnglet === "individuelle"}>
      <p>
        Chaque carte affiche un indicateur tel qu&apos;écrit dans le rapport SFCR (valeur brute du PDF quand elle est
        disponible), avec sa définition. Seuls les ratios SCR et MCR portent une pastille de statut.
      </p>
      <p>
        <span className="font-medium text-text-primary">Décomposition du SCR :</span> une barre par module de risque
        (non-vie, santé, vie, marché, contrepartie), la diversification (hachurée, montant négatif), le SCR
        opérationnel et le SCR total.
      </p>
      <p>
        La ligne hachurée « Absorption des pertes et autres ajustements (calculé) » est obtenue par différence
        (SCR total − somme des modules, diversification et opérationnel) ; elle n&apos;est pas extraite du PDF et
        n&apos;apparaît que si tous les modules sont extraits et que l&apos;écart atteint 1 % du SCR total.
      </p>
      <p>« n/d » signale un module non extrait du rapport.</p>
    </Section>
  );

  const comparative = (
    <Section key={`cmp-${sousOnglet}`} titre="Analyse comparative" defaultOpen={sousOnglet === "comparative"}>
      <p>
        <span className="font-medium text-text-primary">Sélection :</span> de 2 à 8 assureurs, filtrables par type
        d&apos;activité et modèle de capital. Un avertissement apparaît quand modèles de capital ou activités vie /
        non-vie sont mélangés.
      </p>
      <p>
        <span className="font-medium text-text-primary">Compteur de couleurs :</span> répartition du ratio SCR de la
        sélection (vertes / orange / rouges).
      </p>
      <p>
        <span className="font-medium text-text-primary">Profil de risque (radar) :</span> parts de chaque module de base
        (non-vie, vie, santé, marché, contrepartie) dans la somme des modules, sur une échelle commune de 0 au plus
        grand pourcentage de la sélection : il compare le profil de risque, pas la taille. Les valeurs sont dans la
        table sous le graphique. Les sociétés en modèle interne ne sont pas dessinées (parts non comparables à la
        formule standard) ; un groupe ne se compare qu&apos;à d&apos;autres groupes (si solo et groupes sont mélangés,
        seul le périmètre majoritaire est dessiné). Cliquer sur un assureur dans la légende le masque ou l&apos;affiche.
      </p>
      <p>
        <span className="font-medium text-text-primary">Comparaison par KPI :</span> barres pour l&apos;indicateur
        choisi, en M€ ou en % ; une valeur absente s&apos;affiche « n/d », sans barre ; une ligne pointillée
        « Seuil réglementaire » apparaît pour les ratios SCR et MCR ({SEUIL_LEGAL} %).
      </p>
      <p>
        <span className="font-medium text-text-primary">Tableau :</span> sections par catégorie repliables, tri en
        cliquant sur la colonne d&apos;un assureur, filtre de catégorie, colonnes Moyenne, Médiane et Seuil
        (« Afficher les seuils »). Un rang (#1…) est affiché pour le ratio SCR, le ratio MCR et la diversification ;
        pour la diversification, le meilleur et le pire sont en gras.
      </p>
      <p>
        <span className="font-medium text-text-primary">Alertes</span> (par ordre de gravité : critique, attention,
        information) : ratio SCR sous {SEUIL_LEGAL} %, y compris sans correction pour volatilité ni mesure
        transitoire ; ratio SCR très dépendant des mesures de long terme ; mesure transitoire en cours ; fonds propres
        de niveau 2 et 3 au plafond d&apos;éligibilité de 50 % du SCR ; sinistres / primes très élevé en non-vie ; MCR
        collé au plancher absolu. Aucune alerte n&apos;est déclenchée sur une valeur non comparable.
      </p>
    </Section>
  );

  return (
    <>
      <button
        ref={declencheurRef}
        onClick={() => setOuvert(true)}
        aria-label="Aide à la lecture"
        aria-haspopup="dialog"
        title="Aide à la lecture"
        className="fixed right-4 bottom-[calc(4.75rem+env(safe-area-inset-bottom))] md:right-6 md:bottom-6 z-40 w-11 h-11 rounded-full bg-surface border border-border text-accent shadow-[var(--shadow-md)] hover:bg-surface-hover transition-colors flex items-center justify-center"
      >
        <Info className="w-5 h-5" aria-hidden="true" />
      </button>

      {ouvert && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/30" onClick={fermer} aria-hidden="true" />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Aide à la lecture"
            className="relative h-full w-full sm:w-[420px] sm:max-w-[90vw] bg-surface border-l border-border shadow-[var(--shadow-lg)] flex flex-col"
          >
            <header className="flex items-center gap-2 px-5 py-4 border-b border-border flex-shrink-0">
              <h2 className="font-heading italic text-xl text-text-primary flex-1">Aide à la lecture</h2>
              <button
                ref={fermerRef}
                onClick={fermer}
                aria-label="Fermer l'aide"
                className="w-8 h-8 rounded-full flex items-center justify-center text-text-secondary hover:bg-surface-hover"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            </header>

            <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4 flex flex-col gap-3 pb-[calc(1rem+env(safe-area-inset-bottom))]">
              <Section titre="Données" defaultOpen>
                <p>
                  {STATS_GLOBALES.nbSocietes} sociétés, {KPI_DEFINITIONS.length} indicateurs extraits des rapports
                  SFCR. Valeurs en M€, exercice 2025.
                </p>
              </Section>

              <Section titre="Couleurs des ratios" defaultOpen>
                <p>
                  <span className="font-medium text-text-primary">Ratio SCR</span>
                </p>
                <p>
                  <Point classe="bg-danger" />
                  Rouge : sous {SEUIL_LEGAL} % — seuil légal Solvabilité II.
                </p>
                <p>
                  <Point classe="bg-warning" />
                  Orange : de {SEUIL_LEGAL} % à {SEUIL_VERT_SCR_DEFAUT} % — couvre l&apos;exigence légale, sous le
                  repère de marché.
                </p>
                <p>
                  <Point classe="bg-success" />
                  Vert : {SEUIL_VERT_SCR_DEFAUT} % ou plus — repère de marché conventionnel, pas une règle légale.
                </p>
                <p>
                  <span className="font-medium text-text-primary">Ratio MCR :</span> rouge si sous {SEUIL_LEGAL} %
                  (légal), vert sinon ; pas de zone orange.
                </p>
                <p>Les montants (M€) restent sans couleur : un montant n&apos;est ni bon ni mauvais en soi.</p>
                <p>
                  <span className="font-medium text-text-primary">Tendance « — » :</span> un seul exercice (2025) est
                  disponible, donc aucune variation à afficher.
                </p>
              </Section>

              <Section titre="Valeurs non comparables" defaultOpen>
                <p>
                  <Scale className="inline w-3.5 h-3.5 text-accent align-text-bottom mr-1" aria-hidden="true" />
                  Le symbole signale un chiffre calculé sur une base non directement comparable (ex. modèle
                  interne). Cliquer pour lire la note. Ces valeurs sont exclues des moyennes, médianes et
                  classements.
                </p>
                <p>
                  <span className="font-medium text-text-primary">Comparabilité :</span> selon la sélection, une ligne
                  grisée signale un KPI non comparable (activité, modèle de capital, périmètre ou forme juridique
                  différents), une icône « i » une comparaison avec réserve ; la note en donne la raison. Les moyennes
                  et médianes excluent les sociétés déjà consolidées dans un groupe sélectionné et ne mélangent pas
                  solo et groupe. « Comparer à ses pairs » sélectionne les sociétés de même activité, modèle et
                  périmètre que la première sélectionnée.
                </p>
              </Section>

              {sousOnglet === "individuelle" ? (
                <>
                  {individuelle}
                  {comparative}
                </>
              ) : (
                <>
                  {comparative}
                  {individuelle}
                </>
              )}
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
