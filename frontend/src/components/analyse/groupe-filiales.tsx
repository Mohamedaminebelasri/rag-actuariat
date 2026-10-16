"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { kpisSociete } from "@/data/analyse-demo";
import { couleurSeuil, statutKpi, valeurDisponible } from "@/lib/analyse-utils";
import { DONNEES_EXTRAITES } from "@/lib/donnees-extraites-utils";
import { SEUIL_VERT_SCR_DEFAUT } from "@/lib/seuils-config";
import { AvertissementKpi } from "./avertissement-kpi";
import { CarteAgrandissable } from "./carte-agrandissable";
import { COULEUR_VALEUR, ICONE_STATUT } from "./kpi-card";

type DonneesLigne = {
  nom: string;
  ratio: number | null;
  primes: number | null;
  /** Note d'avertissement du ratio SCR (undefined = aucun avertissement). */
  avert: string | null | undefined;
};

function donneesLigne(nom: string): DonneesLigne {
  const kpis = kpisSociete(nom);
  return {
    nom,
    ratio: valeurDisponible(kpis, "ratio_scr"),
    primes: valeurDisponible(kpis, "primes_acquises_brutes"),
    avert: kpis["ratio_scr"]?.avertissement ? (kpis["ratio_scr"].noteAvertissement ?? null) : undefined,
  };
}

function fmt(v: number, d: number): string {
  return v.toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
}

/** Groupes du panel qui ont au moins une filiale (consolideDans = ce groupe),
 * par ordre alphabétique, avec leurs filiales (alphabétique aussi). */
function groupesAvecFiliales(): { groupe: string; filiales: string[] }[] {
  const tri = (a: string, b: string) => a.localeCompare(b, "fr");
  const filialesDe = new Map<string, string[]>();
  for (const s of DONNEES_EXTRAITES.societes) {
    if (s.consolideDans && s.consolideDans !== s.name) {
      filialesDe.set(s.consolideDans, [...(filialesDe.get(s.consolideDans) ?? []), s.name]);
    }
  }
  return DONNEES_EXTRAITES.societes
    .filter((s) => s.perimetre === "groupe" && (filialesDe.get(s.name)?.length ?? 0) > 0)
    .map((s) => s.name)
    .sort(tri)
    .map((groupe) => ({ groupe, filiales: [...(filialesDe.get(groupe) ?? [])].sort(tri) }));
}

/** Ratio SCR coloré par le feu tricolore (couleurSeuil/statutKpi en lecture
 * seule) avec son icône : la couleur n'est jamais seule. */
function RatioSCR({ ratio, seuilVertScr }: { ratio: number | null; seuilVertScr: number }) {
  if (ratio === null) {
    return <span className="text-xs text-text-tertiary whitespace-nowrap">non disponible</span>;
  }
  const couleur = couleurSeuil("ratio_scr", ratio, seuilVertScr);
  const statut = statutKpi("ratio_scr", ratio, seuilVertScr);
  const Icone = statut ? ICONE_STATUT[statut.couleur] : null;
  return (
    <span
      className={cn("inline-flex items-center gap-1 font-mono text-sm font-medium whitespace-nowrap", COULEUR_VALEUR[couleur])}
      title={statut ? `Ratio SCR — ${statut.libelle}` : undefined}
    >
      {Icone && <Icone className="w-3.5 h-3.5" aria-hidden="true" />}
      {fmt(ratio, 0)} %
    </span>
  );
}

function LigneArbre({
  donnees,
  groupe,
  selectionnee,
  seuilVertScr,
}: {
  donnees: DonneesLigne;
  groupe?: boolean;
  selectionnee: boolean;
  seuilVertScr: number;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-3 gap-y-0.5 rounded-[var(--radius-md)] px-3 py-2",
        groupe && "bg-surface-secondary"
      )}
      // Société sélectionnée dans le comparatif : contour --text-primary.
      style={selectionnee ? { boxShadow: "0 0 0 2px var(--text-primary)" } : undefined}
    >
      <span className={cn("min-w-0 basis-full sm:basis-0 sm:flex-1 text-sm text-text-primary", groupe && "font-semibold")}>
        {donnees.nom}
      </span>
      {donnees.primes !== null && (
        <span className="text-xs text-text-secondary whitespace-nowrap">primes {fmt(donnees.primes, 1)} M€</span>
      )}
      <span className="inline-flex items-center gap-1 ml-auto">
        <RatioSCR ratio={donnees.ratio} seuilVertScr={seuilVertScr} />
        {donnees.avert !== undefined && (
          <AvertissementKpi note={donnees.avert} titre={`Ratio SCR — ${donnees.nom}`} />
        )}
      </span>
    </div>
  );
}

/** Arbre « Groupe → filiales » : le ratio SCR du groupe, puis une ligne par
 * filiale (ratio coloré par le feu tricolore, primes en texte neutre).
 * Volontairement sans rang, sans « meilleur/pire », sans moyenne ni somme des
 * filiales : le ratio d'un groupe n'est pas la moyenne de ses filiales
 * (éliminations de consolidation, diversification entre entités).
 *
 * Intégration (Analyse comparative) :
 *   <GroupeFiliales societesSelectionnees={societes} seuilVertScr={seuilVertScr} /> */
export function GroupeFiliales({
  societesSelectionnees = [],
  seuilVertScr = SEUIL_VERT_SCR_DEFAUT,
}: {
  /** Sociétés sélectionnées dans le comparatif : ouvrent leur groupe par défaut
   * et sont mises en évidence (contour). */
  societesSelectionnees?: string[];
  seuilVertScr?: number;
}) {
  const groupes = useMemo(groupesAvecFiliales, []);
  const [choisi, setChoisi] = useState<string | null>(null);
  if (groupes.length === 0) return null;

  // Groupe par défaut : celui d'une société sélectionnée (le groupe lui-même ou
  // une de ses filiales), sinon le premier par ordre alphabétique.
  const defaut =
    societesSelectionnees
      .map((s) => groupes.find((g) => g.groupe === s || g.filiales.includes(s))?.groupe)
      .find((g) => g !== undefined) ?? groupes[0].groupe;
  const courant = groupes.find((g) => g.groupe === choisi) ?? groupes.find((g) => g.groupe === defaut) ?? groupes[0];
  const selection = new Set(societesSelectionnees);

  return (
    <CarteAgrandissable
      titre="Groupe et filiales"
      nom="l'arbre groupe et filiales"
      actions={
        <div role="group" aria-label="Groupe affiché" className="flex flex-wrap gap-1">
          {groupes.map((g) => (
            <button
              key={g.groupe}
              onClick={() => setChoisi(g.groupe)}
              aria-pressed={courant.groupe === g.groupe}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-medium border transition-colors",
                courant.groupe === g.groupe
                  ? "bg-accent-light text-accent border-accent/30"
                  : "text-text-secondary border-border hover:bg-surface-hover"
              )}
            >
              {g.groupe}
            </button>
          ))}
        </div>
      }
    >
      {() => (
        <>
          <div className="flex flex-col gap-1">
            <LigneArbre
              donnees={donneesLigne(courant.groupe)}
              groupe
              selectionnee={selection.has(courant.groupe)}
              seuilVertScr={seuilVertScr}
            />
            <p className="px-3 pt-1 text-xs text-text-tertiary">
              {courant.filiales.length} filiale{courant.filiales.length > 1 ? "s" : ""} dans le panel
            </p>
            <ul className="ml-4 flex flex-col gap-0.5 border-l border-border-hover pl-3">
              {courant.filiales.map((nom) => (
                <li key={nom}>
                  <LigneArbre donnees={donneesLigne(nom)} selectionnee={selection.has(nom)} seuilVertScr={seuilVertScr} />
                </li>
              ))}
            </ul>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-text-tertiary">
            Le ratio du groupe n&apos;est pas la moyenne de ses filiales. Covéa et Groupama n&apos;ont pas de filiale
            dans le panel.
          </p>
        </>
      )}
    </CarteAgrandissable>
  );
}
