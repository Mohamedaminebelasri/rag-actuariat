"use client";

import { useMemo, useState } from "react";
import { useCorrections } from "@/lib/use-corrections";
import { Database, Download, Search, ShieldCheck, Clock, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { KpiLigne } from "@/components/donnees/kpi-ligne";
import { KpiPdfModal } from "@/components/donnees/kpi-pdf-modal";
import {
  CATEGORIES_REELLES,
  DONNEES_EXTRAITES,
  GROUPE_TOUS,
  KPI_LABELS_REELS,
  STATS_GLOBALES,
  couvertureKpis,
  estNouvelleSociete,
  exporterCsvSociete,
  groupesDisponibles,
  kpisDe,
  societesFiltrees,
  type Societe,
} from "@/lib/donnees-extraites-utils";

/**
 * Onglet "Base de données" — liste, société par société, tous les KPIs
 * réellement extraits de kpis.db (contrairement à l'onglet Analyse, qui
 * reste sur des données de démonstration). Deux filtres : groupe (les
 * sociétés qui appartiennent à un même groupe, ex. Aéma Groupe, ont
 * plusieurs SFCR) puis document/SFCR (la société elle-même).
 *
 * Prochaine itération (pas dans ce lot) : cliquer sur une valeur pour voir
 * un aperçu de la page PDF source avec le chiffre surligné — nécessite
 * d'étendre l'arborescence Documents à toutes les sociétés (aujourd'hui
 * limitée à Groupama) et un visualiseur PDF. Voir la note en bas de page.
 */
export default function BaseDonneesPage() {
  const [groupe, setGroupe] = useState<string>(GROUPE_TOUS);
  const [recherche, setRecherche] = useState("");
  const [societeSelectionnee, setSocieteSelectionnee] = useState<string | null>(null);

  const { getCorrection, soumettre: soumettreCorrection } = useCorrections();

  const groupes = useMemo(() => groupesDisponibles(), []);
  const documents = useMemo(() => societesFiltrees(groupe, recherche), [groupe, recherche]);
  const societe = documents.find((s) => s.name === societeSelectionnee) ?? null;

  const dateSnapshot = useMemo(() => {
    try {
      return new Date(DONNEES_EXTRAITES.genereLe).toLocaleString("fr-FR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return DONNEES_EXTRAITES.genereLe;
    }
  }, []);

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto px-4 sm:px-6 py-6 sm:py-8" style={{ width: "92%", maxWidth: "1500px" }}>
        <div className="flex items-center mb-2">
          <div>
            <p className="text-xs font-bold tracking-[0.12em] text-accent">SOLVABILITÉ II</p>
            <h2 className="font-heading italic text-3xl text-text-primary mt-0.5">Base de données</h2>
          </div>
        </div>

        <div className="flex items-start gap-2 bg-success-light border border-success/30 rounded-[10px] px-4 py-2.5 w-full my-4">
          <ShieldCheck className="w-[15px] h-[15px] text-success flex-shrink-0 mt-0.5" />
          <p className="text-sm font-medium text-success">
            Données réelles extraites de kpis.db — {STATS_GLOBALES.nbSocietes} sociétés, {STATS_GLOBALES.nbKpis} KPIs.
            Snapshot du {dateSnapshot} (pas une connexion live : à régénérer après chaque mise à jour de la base).
          </p>
        </div>

        {/* Aperçu global */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <StatTile label="Sociétés / SFCR" valeur={STATS_GLOBALES.nbSocietes} />
          <StatTile label="KPIs extraits" valeur={STATS_GLOBALES.nbKpis} />
          <StatTile label="Groupes suivis" valeur={STATS_GLOBALES.nbGroupes} />
        </div>

        {/* Filtres */}
        <div className="bg-surface border border-border rounded-[var(--radius-lg)] p-4 mb-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-text-secondary">Groupe</label>
              <select
                value={groupe}
                onChange={(e) => {
                  setGroupe(e.target.value);
                  setSocieteSelectionnee(null);
                }}
                className="text-sm border border-border rounded-[var(--radius-md)] px-2.5 py-2 bg-surface text-text-primary font-body min-w-0"
              >
                <option value={GROUPE_TOUS}>Toutes les sociétés ({STATS_GLOBALES.nbSocietes})</option>
                {groupes.map((g) => (
                  <option key={g.valeur} value={g.valeur}>
                    {g.label} ({g.nb})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-text-secondary">Rechercher une société</label>
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-text-tertiary absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  value={recherche}
                  onChange={(e) => setRecherche(e.target.value)}
                  placeholder="Ex. Macif, Allianz..."
                  className="w-full text-sm border border-border rounded-[var(--radius-md)] pl-8 pr-2.5 py-2 bg-surface text-text-primary font-body"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-text-secondary">
                Document / SFCR {groupe !== GROUPE_TOUS ? `(${documents.length})` : ""}
              </label>
              <select
                value={societeSelectionnee ?? ""}
                onChange={(e) => setSocieteSelectionnee(e.target.value || null)}
                className="text-sm border border-border rounded-[var(--radius-md)] px-2.5 py-2 bg-surface text-text-primary font-body min-w-0"
              >
                <option value="">Sélectionnez un document SFCR...</option>
                {documents.map((s) => {
                  const nouvelle = estNouvelleSociete(s.name);
                  const suffixeGroupe = groupe === GROUPE_TOUS && s.groupe ? ` (${s.groupe})` : "";
                  const suffixeNouveau = nouvelle ? " — Nouveau" : "";
                  return (
                    <option key={s.id} value={s.name}>
                      {s.name}{suffixeGroupe}{suffixeNouveau}
                    </option>
                  );
                })}
              </select>
              {documents.length === 0 && (
                <p className="text-xs text-warning mt-0.5">Aucune société ne correspond à ces filtres.</p>
              )}
            </div>
          </div>
        </div>

        {societe ? (
          <DetailSociete societe={societe} getCorrection={getCorrection} soumettreCorrection={soumettreCorrection} />
        ) : (
          <div className="flex flex-col items-center justify-center h-72 text-center">
            <div className="w-14 h-14 rounded-2xl bg-surface-secondary flex items-center justify-center mb-4">
              <Database className="w-7 h-7 text-text-tertiary" />
            </div>
            <h3 className="font-heading text-xl text-text-primary mb-2">Sélectionnez un document</h3>
            <p className="text-sm text-text-secondary max-w-sm">
              Choisissez un groupe puis un document SFCR pour afficher tous les KPIs extraits, avec leur page et
              chapitre source.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function StatTile({ label, valeur }: { label: string; valeur: number }) {
  return (
    <div className="bg-surface border border-border rounded-[var(--radius-lg)] px-4 py-3">
      <p className="font-mono text-2xl font-bold text-text-primary leading-none">{valeur}</p>
      <p className="text-xs text-text-secondary mt-1">{label}</p>
    </div>
  );
}

function DetailSociete({
  societe,
  getCorrection,
  soumettreCorrection,
}: {
  societe: Societe;
  getCorrection: (s: string, k: string) => import("@/lib/use-corrections").Correction | null;
  soumettreCorrection: (s: string, k: string, v: string, c: string | null) => Promise<boolean>;
}) {
  const [kpiModal, setKpiModal] = useState<string | null>(null);
  const kpis = kpisDe(societe.name);
  const couverture = couvertureKpis(societe.name);
  const annee = Object.values(kpis)[0]?.annee;
  const nouvelle = estNouvelleSociete(societe.name);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-heading text-2xl text-text-primary">{societe.name}</h3>
            {nouvelle && (
              <span
                title="Société ajoutée à chaud via l'onglet Upload — aucun KPI n'a encore été vérifié manuellement."
                className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-warning-light text-warning"
              >
                <Sparkles className="w-3 h-3" /> Nouveau
              </span>
            )}
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-surface-secondary text-text-secondary capitalize">
              {societe.type}
            </span>
            {societe.groupe && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-accent-light text-accent">
                {societe.groupe}
              </span>
            )}
          </div>
          <p className="text-xs text-text-tertiary mt-1">
            {societe.country}
            {annee ? ` · SFCR exercice ${annee}` : ""} ·{" "}
            <span
              className={cn(
                nouvelle
                  ? "text-warning"
                  : couverture.valides === couverture.total
                    ? "text-success"
                    : "text-text-tertiary"
              )}
            >
              {couverture.extraits}/{couverture.total} KPIs extraits
              {nouvelle ? " — aucun vérifié" : `, ${couverture.valides} vérifiés`}
            </span>
          </p>
        </div>
        <button
          onClick={() => exporterCsvSociete(societe.name)}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-[var(--radius-md)] text-sm font-medium text-text-secondary border border-border hover:bg-surface-hover transition-colors flex-shrink-0"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {nouvelle && (
        <div className="flex items-start gap-2 bg-warning-light border border-warning/30 rounded-[10px] px-4 py-2.5 mb-4">
          <Sparkles className="w-[15px] h-[15px] text-warning flex-shrink-0 mt-0.5" />
          <p className="text-sm text-warning">
            Extraction automatique, non vérifiée — chaque chiffre doit être recoupé avec le PDF source avant utilisation.
          </p>
        </div>
      )}

      {couverture.extraits === 0 ? (
        <p className="text-sm text-text-secondary">Aucun KPI extrait pour cette société pour le moment.</p>
      ) : (
        <div className="space-y-6">
          {CATEGORIES_REELLES.map((cat) => {
            const idsDeCat = Object.entries(KPI_LABELS_REELS).filter(
              ([id]) => kpis[id]?.categorie === cat.code
            );
            if (idsDeCat.length === 0) return null;
            return (
              <div key={cat.code}>
                <h4 className="text-xs font-bold tracking-[0.08em] text-text-tertiary uppercase mb-2.5">
                  {cat.label}
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {idsDeCat.map(([id, label]) => (
                    <KpiLigne key={id} id={id} label={label} kpi={kpis[id]} societe={societe.name} onSelect={setKpiModal} correction={getCorrection(societe.name, id)} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="flex items-start gap-2 border border-dashed border-border rounded-[10px] px-4 py-3 mt-8 text-text-tertiary">
        <Clock className="w-[15px] h-[15px] flex-shrink-0 mt-0.5" />
        <p className="text-xs">
          Cliquez sur une valeur pour afficher le PDF source à la bonne page et vérifier le chiffre extrait.
        </p>
      </div>

      {kpiModal && kpis[kpiModal] && (
        <KpiPdfModal
          kpiId={kpiModal}
          label={KPI_LABELS_REELS[kpiModal] ?? kpiModal}
          kpi={kpis[kpiModal]}
          societe={societe.name}
          onClose={() => setKpiModal(null)}
          onCorrection={soumettreCorrection}
        />
      )}
    </div>
  );
}
