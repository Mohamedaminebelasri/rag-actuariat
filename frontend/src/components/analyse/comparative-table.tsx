"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, ArrowUpDown, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { CATEGORIES } from "@/data/analyse-demo";
import {
  buildTableauComparatif,
  couleurSeuil,
  statutKpi,
  texteInfobulleSeuil,
  trierLignes,
  type LigneKpi,
} from "@/lib/analyse-utils";
import { COULEUR_VALEUR, ICONE_STATUT } from "./kpi-card";
import { SEUIL_LEGAL, SEUIL_VERT_SCR_DEFAUT } from "@/lib/seuils-config";

// KPIs avec seuil réglementaire : couleur par seuil (couleurSeuil), jamais par
// rang — un rang #1 rouge reste un rang #1 rouge si sous le seuil légal.
const KPIS_AVEC_SEUIL = new Set(["ratio_scr", "ratio_mcr"]);

/** Port de tableau_comparatif_ui() + en_tete_categorie()/ligne_kpi()
 * (comparative.py, Reflex) — sections repliables, tri par colonne,
 * classement meilleur/pire, benchmark moyenne/médiane/seuil. ratio_scr et
 * ratio_mcr sont coloriés par couleurSeuil() (même logique que les cartes
 * KPI de l'onglet individuel), pas par rang. */
export function ComparativeTable({
  societesComparees,
  filtreCategorie,
  afficherMoyenne,
  afficherMediane,
  afficherSeuil,
  seuilVertScr = SEUIL_VERT_SCR_DEFAUT,
}: {
  societesComparees: string[];
  filtreCategorie: string;
  afficherMoyenne: boolean;
  afficherMediane: boolean;
  afficherSeuil: boolean;
  seuilVertScr?: number;
}) {
  const [categoriesRepliees, setCategoriesRepliees] = useState<string[]>([]);
  const [colonneTri, setColonneTri] = useState("");
  const [triAscendant, setTriAscendant] = useState(true);

  const tableau = useMemo(
    () => buildTableauComparatif(societesComparees, filtreCategorie),
    [societesComparees, filtreCategorie]
  );

  const basculerCategorie = (code: string) =>
    setCategoriesRepliees((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));

  const trierParColonne = (soc: string) => {
    if (colonneTri === soc) {
      setTriAscendant((a) => !a);
    } else {
      setColonneTri(soc);
      setTriAscendant(false);
    }
  };

  return (
    <div className="bg-surface border border-border rounded-[var(--radius-lg)] overflow-x-auto w-full">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left px-4 py-2.5 text-[11px] font-bold uppercase tracking-wide text-text-tertiary">
              KPI
            </th>
            {societesComparees.map((soc) => (
              <th
                key={soc}
                onClick={() => trierParColonne(soc)}
                className="text-right px-4 py-2.5 text-[11px] font-bold uppercase tracking-wide text-text-tertiary cursor-pointer select-none hover:text-text-primary"
              >
                <span className="inline-flex items-center gap-1 justify-end w-full">
                  {soc}
                  <ArrowUpDown className="w-2.5 h-2.5" />
                </span>
              </th>
            ))}
            {afficherMoyenne && (
              <th className="text-right px-4 py-2.5 text-[11px] font-bold uppercase tracking-wide text-text-tertiary">
                Moyenne
              </th>
            )}
            {afficherMediane && (
              <th className="text-right px-4 py-2.5 text-[11px] font-bold uppercase tracking-wide text-text-tertiary">
                Médiane
              </th>
            )}
            {afficherSeuil && (
              <th className="text-right px-4 py-2.5 text-[11px] font-bold uppercase tracking-wide text-text-tertiary whitespace-nowrap min-w-[8rem]">
                Seuil
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {CATEGORIES.map((c) => {
            const repliee = categoriesRepliees.includes(c.code);
            const lignes = colonneTri && societesComparees.includes(colonneTri)
              ? trierLignes(tableau[c.code] ?? [], colonneTri, triAscendant)
              : tableau[c.code] ?? [];
            const nColonnes = 1 + societesComparees.length + Number(afficherMoyenne) + Number(afficherMediane) + Number(afficherSeuil);
            return (
              <SectionCategorie
                key={c.code}
                code={c.code}
                label={c.label}
                repliee={repliee}
                onToggle={() => basculerCategorie(c.code)}
                nColonnes={nColonnes}
                lignes={lignes}
                societesComparees={societesComparees}
                afficherMoyenne={afficherMoyenne}
                afficherMediane={afficherMediane}
                afficherSeuil={afficherSeuil}
                seuilVertScr={seuilVertScr}
              />
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SectionCategorie({
  code,
  label,
  repliee,
  onToggle,
  nColonnes,
  lignes,
  societesComparees,
  afficherMoyenne,
  afficherMediane,
  afficherSeuil,
  seuilVertScr,
}: {
  code: string;
  label: string;
  repliee: boolean;
  onToggle: () => void;
  nColonnes: number;
  lignes: LigneKpi[];
  societesComparees: string[];
  afficherMoyenne: boolean;
  afficherMediane: boolean;
  afficherSeuil: boolean;
  seuilVertScr: number;
}) {
  if (lignes.length === 0) return null;
  return (
    <>
      <tr className="bg-surface-secondary">
        <td
          colSpan={nColonnes}
          onClick={onToggle}
          className="px-4 py-2 cursor-pointer select-none"
        >
          <span className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-wide text-text-secondary">
            {repliee ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            {code} — {label}
          </span>
        </td>
      </tr>
      {!repliee &&
        lignes.map((ligne) => {
          const aSeuilReglementaire = KPIS_AVEC_SEUIL.has(ligne.kpiId);
          return (
            <tr key={ligne.kpiId} className="border-b border-border last:border-0 hover:bg-surface-hover">
              <td className="px-4 py-2.5 font-medium text-text-primary">{ligne.kpiLabel}</td>
              {societesComparees.map((soc) => {
                const cellule = ligne.cellules.find((c) => c.societe === soc);
                if (!cellule) return <td key={soc} className="px-4 py-2.5 text-right text-text-tertiary">—</td>;

                if (aSeuilReglementaire) {
                  const valeur = ligne.valeursParSociete[soc];
                  const couleur = couleurSeuil(ligne.kpiId, valeur, seuilVertScr);
                  const statut = statutKpi(ligne.kpiId, valeur, seuilVertScr);
                  const infobulle = statut ? texteInfobulleSeuil(ligne.kpiId, couleur, seuilVertScr) : undefined;
                  const IconeStatut = statut ? ICONE_STATUT[statut.couleur] : null;
                  return (
                    <td key={soc} className="px-4 py-2.5 text-right font-mono">
                      <span
                        className={cn("inline-flex items-center gap-1 justify-end", COULEUR_VALEUR[couleur])}
                        title={infobulle}
                      >
                        {IconeStatut && <IconeStatut className="w-3 h-3" aria-hidden="true" />}
                        {cellule.valeurStr}
                      </span>
                      {cellule.rang > 0 && (
                        <span className="ml-1.5 text-[11px] font-bold text-text-tertiary">#{cellule.rang}</span>
                      )}
                    </td>
                  );
                }

                const couleurRang = cellule.estMeilleur ? "text-success" : cellule.estPire ? "text-danger" : "text-text-primary";
                return (
                  <td key={soc} className="px-4 py-2.5 text-right font-mono">
                    <span className={cn(couleurRang, (cellule.estMeilleur || cellule.estPire) && "font-bold")}>
                      {cellule.valeurStr}
                    </span>
                    {cellule.rang > 0 && (
                      <span className="ml-1.5 text-[11px] font-bold text-text-tertiary">#{cellule.rang}</span>
                    )}
                  </td>
                );
              })}
              {afficherMoyenne && (
                <td className="px-4 py-2.5 text-right font-mono text-text-secondary">{ligne.moyenneStr}</td>
              )}
              {afficherMediane && (
                <td className="px-4 py-2.5 text-right font-mono text-text-secondary">{ligne.medianeStr}</td>
              )}
              {afficherSeuil && (
                <td className="px-4 py-2.5 text-right font-mono whitespace-nowrap">
                  {ligne.kpiId === "ratio_scr" ? (
                    <span className="inline-flex items-center gap-1 justify-end text-text-secondary">
                      <Lock className="w-3 h-3 text-text-tertiary" aria-label="Seuil légal, verrouillé" />
                      {SEUIL_LEGAL} % · {seuilVertScr} %
                    </span>
                  ) : ligne.kpiId === "ratio_mcr" ? (
                    <span className="inline-flex items-center gap-1 justify-end text-text-secondary">
                      <Lock className="w-3 h-3 text-text-tertiary" aria-label="Seuil légal, verrouillé" />
                      {SEUIL_LEGAL} %
                    </span>
                  ) : (
                    <span className="text-text-tertiary">—</span>
                  )}
                </td>
              )}
            </tr>
          );
        })}
    </>
  );
}
