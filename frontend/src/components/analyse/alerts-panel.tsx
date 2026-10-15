"use client";

import { useId, useState } from "react";
import { ChevronDown, CircleAlert, CircleCheck, Info, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { buildAlertes, type Alerte } from "@/lib/analyse-utils";

const ICONES: Record<Alerte["type"], React.ReactNode> = {
  critique: <CircleAlert className="w-4 h-4 text-danger flex-shrink-0" />,
  conforme: <CircleCheck className="w-4 h-4 text-success flex-shrink-0" />,
  attention: <TriangleAlert className="w-4 h-4 text-warning flex-shrink-0" />,
  // Niveau « info » : neutre (rouge/orange/vert restent réservés au feu tricolore).
  info: <Info className="w-4 h-4 text-text-tertiary flex-shrink-0" />,
};

// Gravité décroissante : critique, puis attention, puis info (conforme en dernier).
const GRAVITE: Record<Alerte["type"], number> = { critique: 0, attention: 1, info: 2, conforme: 3 };
const LIBELLE_NIVEAU: Record<Alerte["type"], (n: number) => string> = {
  critique: (n) => `${n} critique${n > 1 ? "s" : ""}`,
  attention: (n) => `${n} attention`,
  info: (n) => `${n} info`,
  conforme: (n) => `${n} conforme${n > 1 ? "s" : ""}`,
};

type GroupeSociete = { societe: string; principale: Alerte; autres: Alerte[] };

/** Message sans le préfixe « Société : » (le nom est déjà en en-tête), avec
 * majuscule initiale. */
function messageSansSociete(a: Alerte): string {
  const prefixe = `${a.societe} : `;
  const m = a.texte.startsWith(prefixe) ? a.texte.slice(prefixe.length) : a.texte;
  return m.charAt(0).toUpperCase() + m.slice(1);
}

/** Alertes de la sélection, regroupées par société : l'alerte la plus grave en
 * ligne, les autres dans un dépliant (« voir les autres alertes »). */
export function AlertsPanel({ societesComparees }: { societesComparees: string[] }) {
  const idBase = useId();
  // Dépliées par société (conservé quand la sélection change).
  const [depliees, setDepliees] = useState<Record<string, boolean>>({});
  const alertes = buildAlertes(societesComparees);
  if (alertes.length === 0) return null;

  // Regroupement : alertes triées par gravité (stable : ordre d'origine à
  // gravité égale) ; sociétés de l'alerte la plus sévère d'abord, puis ordre
  // de la sélection.
  const groupes: GroupeSociete[] = societesComparees
    .map((societe) => {
      const siennes = alertes
        .filter((a) => a.societe === societe)
        .map((a, i) => ({ a, i }))
        .sort((x, y) => GRAVITE[x.a.type] - GRAVITE[y.a.type] || x.i - y.i)
        .map(({ a }) => a);
      return { societe, principale: siennes[0], autres: siennes.slice(1) };
    })
    .filter((g) => g.principale !== undefined)
    .map((g, i) => ({ g, i }))
    .sort((x, y) => GRAVITE[x.g.principale.type] - GRAVITE[y.g.principale.type] || x.i - y.i)
    .map(({ g }) => g);
  const sansAlerte = societesComparees.filter((s) => !groupes.some((g) => g.societe === s));

  // Synthèse par niveau (uniquement ceux présents).
  const synthese = (["critique", "attention", "info", "conforme"] as const)
    .map((type) => ({ type, n: alertes.filter((a) => a.type === type).length }))
    .filter((x) => x.n > 0);

  const avecAutres = groupes.filter((g) => g.autres.length > 0);
  const toutesDepliees = avecAutres.length > 0 && avecAutres.every((g) => depliees[g.societe]);
  const basculer = (societe: string) => setDepliees((prev) => ({ ...prev, [societe]: !prev[societe] }));
  const toutBasculer = () =>
    setDepliees((prev) => ({ ...prev, ...Object.fromEntries(avecAutres.map((g) => [g.societe, !toutesDepliees])) }));

  return (
    <div className="bg-surface border border-border rounded-[var(--radius-lg)] p-5 w-full">
      <div className="flex items-center gap-x-4 gap-y-1 flex-wrap mb-3">
        <p className="font-heading italic text-lg text-text-primary">Alertes et points d&apos;attention</p>
        <span className="flex items-center gap-x-4 gap-y-1 flex-wrap text-xs text-text-secondary">
          {synthese.map((x) => (
            <span key={x.type} className="inline-flex items-center gap-1">
              {ICONES[x.type]}
              {LIBELLE_NIVEAU[x.type](x.n)}
            </span>
          ))}
        </span>
        <span className="flex-1" />
        {avecAutres.length >= 2 && (
          <button
            onClick={toutBasculer}
            className="text-xs text-accent hover:underline whitespace-nowrap"
          >
            {toutesDepliees ? "Tout replier" : "Tout déplier"}
          </button>
        )}
      </div>

      <ul className="flex flex-col">
        {groupes.map((g, i) => {
          const ouvert = !!depliees[g.societe];
          const n = g.autres.length;
          const idListe = `${idBase}-${i}`;
          const libelle = `Voir les ${n} autre${n > 1 ? "s" : ""} alerte${n > 1 ? "s" : ""}`.replace(
            "Voir les 1 autre alerte",
            "Voir l'autre alerte"
          );
          return (
            <li key={g.societe} className="py-2.5 border-b border-border last:border-0">
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-text-primary">{g.societe}</p>
                  <p className="mt-0.5 flex items-start gap-2 text-sm text-text-primary">
                    <span className="mt-0.5">{ICONES[g.principale.type]}</span>
                    <span>{messageSansSociete(g.principale)}</span>
                  </p>
                </div>
                {n > 0 && (
                  <button
                    onClick={() => basculer(g.societe)}
                    aria-expanded={ouvert}
                    aria-controls={idListe}
                    aria-label={ouvert ? `Masquer les autres alertes de ${g.societe}` : `${libelle} de ${g.societe}`}
                    className="flex items-center gap-1.5 flex-shrink-0 px-2 py-1 rounded-full text-xs text-text-secondary hover:bg-surface-hover transition-colors"
                  >
                    <span className="px-1.5 py-0.5 rounded-full bg-surface-secondary font-mono text-[11px] font-medium text-text-primary">
                      +{n}
                    </span>
                    <span className="hidden sm:inline">{ouvert ? "Masquer" : libelle}</span>
                    <ChevronDown
                      className={cn("w-3.5 h-3.5 transition-transform", ouvert && "rotate-180")}
                      aria-hidden="true"
                    />
                  </button>
                )}
              </div>
              {n > 0 && ouvert && (
                <ul id={idListe} className="mt-2 ml-6 flex flex-col gap-1.5 border-l border-border pl-3">
                  {g.autres.map((a, k) => (
                    <li key={k} className="flex items-start gap-2 text-sm text-text-secondary">
                      <span className="mt-0.5">{ICONES[a.type]}</span>
                      <span>{messageSansSociete(a)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ul>

      {sansAlerte.length > 0 && (
        <p className="mt-3 text-xs text-text-tertiary">Aucune alerte : {sansAlerte.join(", ")}</p>
      )}
    </div>
  );
}
