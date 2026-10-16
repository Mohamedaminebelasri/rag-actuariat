"use client";

import { cn } from "@/lib/utils";
import { kpisSociete } from "@/data/analyse-demo";
import { couleurSeuil, valeurDisponible } from "@/lib/analyse-utils";
import { DONNEES_EXTRAITES } from "@/lib/donnees-extraites-utils";
import { SEUIL_LEGAL, SEUIL_VERT_SCR_DEFAUT } from "@/lib/seuils-config";
import { AvertissementKpi } from "./avertissement-kpi";
import { CarteAgrandissable } from "./carte-agrandissable";

const COULEUR_POINT: Record<string, string> = {
  success: "var(--success)",
  warning: "var(--warning)",
  danger: "var(--danger)",
  neutre: "var(--text-tertiary)",
};
const NOM_ZONE: Record<string, string> = { success: "vert", warning: "orange", danger: "rouge" };
const IDS_KPI = ["ratio_scr", "ratio_scr_sans_mesures_lt", "impact_va", "impact_transitoires"];

/** Nombre signé en points (« −90 », « +3 », « −0,3 ») : entier dès que |v| ≥ 1. */
function pts(v: number): string {
  const abs = Math.abs(v);
  const texte = abs >= 1 ? Math.round(abs).toString() : abs.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  return `${v < 0 ? "−" : "+"}${texte}`;
}
function pctFr(v: number): string {
  return `${v.toLocaleString("fr-FR", { minimumFractionDigits: 0, maximumFractionDigits: 1 })} %`;
}

type LigneMesures = {
  societe: string;
  etat: "halteres" | "aucune-mesure" | "sans-mesures-indisponible" | "indisponible";
  publie: number | null;
  sans: number | null;
  va: number | null;
  transitoire: number | null;
  avert: { note: string } | null;
};

function ligneMesures(societe: string): LigneMesures {
  const kpis = kpisSociete(societe);
  const ind = DONNEES_EXTRAITES.indicateursParSociete[societe];
  const publie = valeurDisponible(kpis, "ratio_scr");
  const sans = valeurDisponible(kpis, "ratio_scr_sans_mesures_lt");
  const va = valeurDisponible(kpis, "impact_va");
  const transitoire = valeurDisponible(kpis, "impact_transitoires");
  const concernes = IDS_KPI.filter((id) => kpis[id]?.avertissement);
  const avert = concernes.length > 0
    ? { note: Array.from(new Set(concernes.map((id) => kpis[id].noteAvertissement ?? "").filter((n) => n !== ""))).join("\n\n") }
    : null;
  // « Pas de mesure » = la société n'utilise ni la VA ni de mesure transitoire
  // (donnée explicite) ; une donnée absente n'est jamais lue comme « aucune ».
  const aucuneMesure = ind?.utilise_va === false && ind?.mesure_transitoire !== true;
  let etat: LigneMesures["etat"];
  if (publie === null) etat = "indisponible";
  else if (aucuneMesure) etat = "aucune-mesure";
  else if (sans === null) etat = "sans-mesures-indisponible";
  else etat = "halteres";
  return { societe, etat, publie, sans, va, transitoire, avert };
}

/** Dépendance du ratio SCR aux mesures de long terme (correction pour volatilité
 * et mesures transitoires) : un « haltère » par société sélectionnée — point
 * plein = ratio publié, point creux = ratio sans ces mesures — sur un axe commun
 * en %. Ordre = ordre de la sélection (ni tri, ni rang). */
export function MesuresLongTerme({
  societesComparees,
  seuilVertScr = SEUIL_VERT_SCR_DEFAUT,
}: {
  societesComparees: string[];
  seuilVertScr?: number;
}) {
  const lignes = societesComparees.map(ligneMesures);

  // Axe commun : borne basse ≤ 100 %, borne haute = plus grand ratio arrondi.
  const valeurs = lignes.flatMap((l) => [l.publie, l.sans]).filter((v): v is number => v !== null);
  const min = Math.min(SEUIL_LEGAL, ...valeurs);
  const max = Math.max(SEUIL_VERT_SCR_DEFAUT, ...valeurs);
  const bas = Math.floor((min - 10) / 50) * 50;
  const haut = Math.ceil((max + 10) / 50) * 50;
  const etendue = haut - bas > 0 ? haut - bas : 1;
  const pos = (v: number) => `${((v - bas) / etendue) * 100}%`;
  const repere = [SEUIL_LEGAL, seuilVertScr].filter((v) => v > bas && v < haut);
  // Bornes de l'axe étiquetées seulement si elles ne se superposent pas à un repère.
  const procheRepere = (v: number) => repere.some((r) => Math.abs(r - v) / etendue < 0.14);

  return (
    <CarteAgrandissable titre="Dépendance aux mesures de long terme" nom="le graphique des mesures de long terme">
      {({ agrandi }) => (
        <>
          <p className="text-xs text-text-tertiary mb-3">
            Écart entre le ratio publié et le ratio sans correction pour volatilité ni mesures transitoires : plus il est
            grand, plus le ratio dépend de ces mesures réglementaires.
          </p>
          <ul className="flex flex-wrap gap-x-5 gap-y-1 mb-4 text-xs text-text-secondary" aria-label="Légende">
            <li className="inline-flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 rounded-full bg-text-secondary" aria-hidden="true" />
              ratio SCR publié
            </li>
            <li className="inline-flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 rounded-full border-2 border-text-secondary bg-surface" aria-hidden="true" />
              ratio sans correction pour volatilité ni mesures transitoires
            </li>
            <li className="text-text-tertiary">Couleur des points = zone du ratio SCR</li>
          </ul>

          <ul className="flex flex-col gap-3">
            {lignes.map((l) => {
              const couleurPub = l.publie === null ? "neutre" : couleurSeuil("ratio_scr", l.publie, seuilVertScr);
              const couleurSans = l.sans === null ? "neutre" : couleurSeuil("ratio_scr", l.sans, seuilVertScr);
              const haltere = l.etat === "halteres" && l.publie !== null && l.sans !== null;
              const ecart = haltere ? (l.sans as number) - (l.publie as number) : null;
              const parts: string[] = [];
              if (haltere) {
                if (l.va !== null) parts.push(`VA ${pts(l.va)}`);
                if (l.transitoire !== null) parts.push(`transitoire ${pts(l.transitoire)}`);
              }
              const changeZone = haltere && couleurPub !== couleurSans && NOM_ZONE[couleurPub] && NOM_ZONE[couleurSans];
              const resume =
                l.etat === "indisponible"
                  ? "ratio SCR non disponible"
                  : `ratio publié ${pctFr(l.publie as number)}${l.sans !== null && haltere ? `, sans mesures ${pctFr(l.sans)}` : ""}`;
              return (
                <li
                  key={l.societe}
                  className="flex flex-col gap-1 sm:grid sm:grid-cols-[minmax(8rem,11rem)_1fr_minmax(11rem,16rem)] sm:items-center sm:gap-4"
                >
                  <span className="min-w-0 flex items-center">
                    <span className={cn("font-medium text-text-primary truncate", agrandi ? "text-base" : "text-sm")}>
                      {l.societe}
                    </span>
                    {l.avert && (
                      <AvertissementKpi note={l.avert.note} titre={`Ratio SCR — ${l.societe}`} className="ml-1" />
                    )}
                  </span>

                  <div
                    role="img"
                    aria-label={`${l.societe} : ${resume}`}
                    className={cn("relative", agrandi ? "h-8" : "h-6")}
                  >
                    {repere.map((v) => (
                      <span
                        key={v}
                        className="absolute top-0 bottom-0 border-l border-dashed border-border-hover"
                        style={{ left: pos(v) }}
                        aria-hidden="true"
                      />
                    ))}
                    {haltere && (
                      <span
                        className="absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full bg-text-tertiary"
                        style={{
                          left: pos(Math.min(l.publie as number, l.sans as number)),
                          width: `${(Math.abs((l.publie as number) - (l.sans as number)) / etendue) * 100}%`,
                        }}
                        aria-hidden="true"
                      />
                    )}
                    {haltere && (
                      <span
                        className="absolute top-1/2 w-3.5 h-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 bg-surface"
                        style={{ left: pos(l.sans as number), borderColor: COULEUR_POINT[couleurSans] }}
                        title={`Sans mesures : ${pctFr(l.sans as number)}`}
                      />
                    )}
                    {l.publie !== null && (
                      <span
                        className="absolute top-1/2 w-3.5 h-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface"
                        style={{ left: pos(l.publie), background: COULEUR_POINT[couleurPub] }}
                        title={`Ratio publié : ${pctFr(l.publie)}`}
                      />
                    )}
                  </div>

                  <div className="text-xs text-text-secondary leading-snug">
                    {l.etat === "indisponible" && <span className="text-text-tertiary">non disponible</span>}
                    {l.etat === "aucune-mesure" && <span>aucune mesure · {pctFr(l.publie as number)}</span>}
                    {l.etat === "sans-mesures-indisponible" && (
                      <span className="text-text-tertiary">ratio sans mesures non disponible</span>
                    )}
                    {haltere && (
                      <>
                        <span className="font-mono text-text-primary">
                          {pctFr(l.publie as number)} → {pctFr(l.sans as number)}
                        </span>
                        <br />
                        <span>
                          {ecart !== null && Math.abs(ecart) < 0.05 ? "aucun écart" : `${pts(ecart as number)} pts`}
                          {parts.length > 0 && ` : ${parts.join(", ")}`}
                        </span>
                        {changeZone && (
                          <>
                            <br />
                            <span className="text-text-tertiary">
                              change de zone : {NOM_ZONE[couleurPub]} → {NOM_ZONE[couleurSans]}
                            </span>
                          </>
                        )}
                      </>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>

          {/* Axe commun */}
          <div className="mt-3 sm:grid sm:grid-cols-[minmax(8rem,11rem)_1fr_minmax(11rem,16rem)] sm:gap-4" aria-hidden="true">
            <span className="hidden sm:block" />
            <div className="relative h-4 text-[10px] font-mono text-text-tertiary">
              {!procheRepere(bas) && <span className="absolute left-0">{bas} %</span>}
              {repere.map((v) => (
                <span key={v} className="absolute -translate-x-1/2" style={{ left: pos(v) }}>
                  {v} %
                </span>
              ))}
              {!procheRepere(haut) && <span className="absolute right-0">{haut} %</span>}
            </div>
          </div>
        </>
      )}
    </CarteAgrandissable>
  );
}
