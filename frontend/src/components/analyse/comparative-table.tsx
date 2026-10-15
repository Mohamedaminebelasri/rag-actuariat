"use client";

import { useMemo, useState } from "react";
import { Ban, ChevronDown, ChevronRight, ArrowUpDown, Info, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { CATEGORIES, kpisSociete } from "@/data/analyse-demo";
import {
  CATEGORIE_LABELS,
  buildTableauComparatif,
  couleurSeuil,
  statutKpi,
  texteInfobulleSeuil,
  trierLignes,
  type LigneKpi,
} from "@/lib/analyse-utils";
import { COULEUR_VALEUR, ICONE_STATUT } from "./kpi-card";
import { AvertissementKpi } from "./avertissement-kpi";
import { CarteAgrandissable } from "./carte-agrandissable";
import { compatibiliteKpi, texteNotesCompat } from "@/lib/comparabilite";
import { SEUIL_LEGAL, SEUIL_VERT_SCR_DEFAUT } from "@/lib/seuils-config";

// KPIs avec seuil réglementaire : couleur par seuil (couleurSeuil), jamais par
// rang — un rang #1 rouge reste un rang #1 rouge si sous le seuil légal.
const KPIS_AVEC_SEUIL = new Set(["ratio_scr", "ratio_mcr"]);

const CATEGORIES_FILTRE = ["Tous", "E", "D", "C", "A"];

/** Port de tableau_comparatif_ui() + en_tete_categorie()/ligne_kpi()
 * (comparative.py, Reflex) — sections repliables (fermées à l'ouverture), tri
 * par colonne, classement meilleur/pire, colonne Moyenne. ratio_scr et
 * ratio_mcr sont coloriés par couleurSeuil() (même logique que les cartes
 * KPI de l'onglet individuel), pas par rang. Carte agrandissable : le filtre
 * de catégorie est dans son en-tête (état conservé à l'agrandissement). */
export function ComparativeTable({
  societesComparees,
  filtreCategorie,
  onChangeFiltre,
  seuilVertScr = SEUIL_VERT_SCR_DEFAUT,
}: {
  societesComparees: string[];
  filtreCategorie: string;
  onChangeFiltre: (categorie: string) => void;
  seuilVertScr?: number;
}) {
  // Les 4 catégories sont fermées à l'ouverture ; l'utilisateur les ouvre.
  const [categoriesRepliees, setCategoriesRepliees] = useState<string[]>(CATEGORIES.map((c) => c.code));
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
    <CarteAgrandissable
      titre="Tableau comparatif"
      nom="le tableau comparatif"
      actions={
        <select
          value={filtreCategorie}
          onChange={(e) => onChangeFiltre(e.target.value)}
          aria-label="Filtrer par catégorie de KPI"
          className="text-sm border border-border rounded-[var(--radius-md)] px-2.5 py-1.5 bg-surface text-text-primary font-body"
        >
          {CATEGORIES_FILTRE.map((c) => (
            <option key={c} value={c}>
              {CATEGORIE_LABELS[c]}
            </option>
          ))}
        </select>
      }
    >
      {({ agrandi }) => {
        // En-têtes de colonnes collés en haut quand le tableau défile (vue agrandie).
        const cellEntete = cn(
          "px-4 py-2.5 text-[11px] font-bold uppercase tracking-wide text-text-tertiary",
          agrandi && "sticky top-0 z-10 bg-surface"
        );
        return (
          <div className={cn("border border-border rounded-[var(--radius-md)]", !agrandi && "overflow-x-auto")}>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className={cn("text-left", cellEntete)}>KPI</th>
                  {societesComparees.map((soc) => (
                    <th
                      key={soc}
                      onClick={() => trierParColonne(soc)}
                      className={cn("text-right cursor-pointer select-none hover:text-text-primary", cellEntete)}
                    >
                      <span className="inline-flex items-center gap-1 justify-end w-full">
                        {soc}
                        <ArrowUpDown className="w-2.5 h-2.5" />
                      </span>
                    </th>
                  ))}
                  <th className={cn("text-right", cellEntete)}>Moyenne</th>
                </tr>
              </thead>
              <tbody>
                {CATEGORIES.map((c) => {
                  // Une catégorie choisie dans le filtre s'affiche ouverte.
                  const repliee = filtreCategorie === "Tous" && categoriesRepliees.includes(c.code);
                  const lignes =
                    colonneTri && societesComparees.includes(colonneTri)
                      ? trierLignes(tableau[c.code] ?? [], colonneTri, triAscendant)
                      : tableau[c.code] ?? [];
                  return (
                    <SectionCategorie
                      key={c.code}
                      code={c.code}
                      label={c.label}
                      repliee={repliee}
                      onToggle={() => basculerCategorie(c.code)}
                      nColonnes={2 + societesComparees.length}
                      lignes={lignes}
                      societesComparees={societesComparees}
                      seuilVertScr={seuilVertScr}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      }}
    </CarteAgrandissable>
  );
}

/** Infobulle (+ soulignement pointillé) d'une moyenne calculée hors
 * valeurs non comparables, sociétés déjà consolidées et autre périmètre ;
 * rien s'il n'y a aucune exclusion. */
function infobulleExclues(note: string | null) {
  if (!note) return {};
  return {
    title: note,
    className: "underline decoration-dotted underline-offset-4 cursor-help",
  };
}

function SectionCategorie({
  code,
  label,
  repliee,
  onToggle,
  nColonnes,
  lignes,
  societesComparees,
  seuilVertScr,
}: {
  code: string;
  label: string;
  repliee: boolean;
  onToggle: () => void;
  nColonnes: number;
  lignes: LigneKpi[];
  societesComparees: string[];
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
            <span className="font-medium normal-case tracking-normal text-text-tertiary">
              · {lignes.length} KPI{lignes.length > 1 ? "s" : ""}
            </span>
          </span>
        </td>
      </tr>
      {!repliee &&
        lignes.map((ligne) => {
          const aSeuilReglementaire = KPIS_AVEC_SEUIL.has(ligne.kpiId);
          // Compatibilité du KPI pour la sélection : N = grisé + note, R =
          // marqueur + note, NA = « sans objet » pour les zéros. Couleurs
          // neutres (rouge/orange/vert restent réservés au feu tricolore).
          const compat = compatibiliteKpi(ligne.kpiId, societesComparees);
          const grise = compat.verdict === "N";
          const noteCompat = texteNotesCompat(compat.notes);
          const grisee = grise ? "opacity-50" : undefined;
          // Libellé propre aux groupes (ex. « SCR minimal consolidé du groupe ») :
          // en titre de ligne s'il est commun, sinon en légende de la cellule.
          const libelles = societesComparees
            .map((s) => kpisSociete(s)[ligne.kpiId])
            .filter((k) => k !== undefined)
            .map((k) => k.libelle ?? null);
          const libelleCommun =
            libelles.length > 0 && libelles[0] && libelles.every((l) => l === libelles[0]) ? libelles[0] : null;
          return (
            <tr
              key={ligne.kpiId}
              className="border-b border-border last:border-0 hover:bg-surface-hover"
              title={grise ? `Non comparable — ${noteCompat}` : undefined}
            >
              <td className={cn("px-4 py-2.5 font-medium", grise ? "text-text-tertiary" : "text-text-primary")}>
                {libelleCommun ?? ligne.kpiLabel}
                {/* Seuils (légal verrouillé ; vert = repère de marché, seuilVertScr) */}
                {ligne.kpiId === "ratio_scr" && (
                  <span className="mt-0.5 flex items-center gap-1 text-[11px] font-normal text-text-tertiary">
                    <Lock className="w-3 h-3" aria-label="Seuil légal, verrouillé" />
                    seuil légal {SEUIL_LEGAL} % · vert {seuilVertScr} %
                  </span>
                )}
                {ligne.kpiId === "ratio_mcr" && (
                  <span className="mt-0.5 flex items-center gap-1 text-[11px] font-normal text-text-tertiary">
                    <Lock className="w-3 h-3" aria-label="Seuil légal, verrouillé" />
                    seuil légal {SEUIL_LEGAL} %
                  </span>
                )}
                {(compat.verdict === "N" || compat.verdict === "R") && noteCompat && (
                  <AvertissementKpi
                    note={noteCompat}
                    titre={ligne.kpiLabel}
                    className="ml-1"
                    icone={compat.verdict === "N" ? Ban : Info}
                    intitule={compat.verdict === "N" ? "Non comparable" : "À comparer avec réserve"}
                    infobulle={
                      compat.verdict === "N"
                        ? "Non comparable pour cette sélection : cliquer pour lire la note"
                        : "À comparer avec réserve : cliquer pour lire la note"
                    }
                    classeIcone="text-text-secondary"
                  />
                )}
              </td>
              {societesComparees.map((soc) => {
                const cellule = ligne.cellules.find((c) => c.societe === soc);
                if (!cellule) return <td key={soc} className="px-4 py-2.5 text-right text-text-tertiary">—</td>;
                const sansObjet = compat.sansObjet && ligne.valeursParSociete[soc] === 0;
                const valeurStr = sansObjet ? "sans objet" : cellule.valeurStr;
                const legende = libelleCommun ? null : kpisSociete(soc)[ligne.kpiId]?.libelle ?? null;

                if (aSeuilReglementaire) {
                  const valeur = ligne.valeursParSociete[soc];
                  const couleur = couleurSeuil(ligne.kpiId, valeur, seuilVertScr);
                  const statut = statutKpi(ligne.kpiId, valeur, seuilVertScr);
                  const infobulle = statut ? texteInfobulleSeuil(ligne.kpiId, couleur, seuilVertScr) : undefined;
                  const IconeStatut = statut ? ICONE_STATUT[statut.couleur] : null;
                  return (
                    <td key={soc} className={cn("px-4 py-2.5 text-right font-mono", grisee)}>
                      {cellule.avertissement && <AvertissementKpi note={cellule.noteAvertissement} className="mr-1" />}
                      <span
                        className={cn("inline-flex items-center gap-1 justify-end", COULEUR_VALEUR[couleur])}
                        title={infobulle}
                      >
                        {IconeStatut && <IconeStatut className="w-3 h-3" aria-hidden="true" />}
                        {valeurStr}
                      </span>
                      {cellule.rang > 0 && (
                        <span className="ml-1.5 text-[11px] font-bold text-text-tertiary">#{cellule.rang}</span>
                      )}
                      {legende && (
                        <span className="block text-[10px] font-body leading-tight text-text-tertiary">{legende}</span>
                      )}
                    </td>
                  );
                }

                const couleurRang = cellule.estMeilleur ? "text-success" : cellule.estPire ? "text-danger" : "text-text-primary";
                return (
                  <td key={soc} className={cn("px-4 py-2.5 text-right font-mono", grisee)}>
                    {cellule.avertissement && <AvertissementKpi note={cellule.noteAvertissement} className="mr-1" />}
                    <span
                      className={cn(
                        couleurRang,
                        (cellule.estMeilleur || cellule.estPire) && "font-bold",
                        sansObjet && "italic font-body text-text-tertiary"
                      )}
                    >
                      {valeurStr}
                    </span>
                    {cellule.rang > 0 && (
                      <span className="ml-1.5 text-[11px] font-bold text-text-tertiary">#{cellule.rang}</span>
                    )}
                    {legende && (
                      <span className="block text-[10px] font-body leading-tight text-text-tertiary">{legende}</span>
                    )}
                  </td>
                );
              })}
              <td className={cn("px-4 py-2.5 text-right font-mono text-text-secondary", grisee)}>
                <span {...infobulleExclues(ligne.noteAgregat)}>{ligne.moyenneStr}</span>
              </td>
            </tr>
          );
        })}
    </>
  );
}
