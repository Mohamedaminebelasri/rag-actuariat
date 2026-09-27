"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Pencil,
  Sparkles,
  ShieldAlert,
} from "lucide-react";
import { cn } from "@/lib/utils";

type Etape = "depot" | "confirmation" | "envoi" | "extraction" | "resultats" | "erreur";

type SuggestionApi = {
  suggestion: string;
  titreExtrait: string | null;
  nomNettoye: string;
  tailleOctets: number;
};

type KpiExtrait = {
  kpi_name: string;
  value: number;
  unit: string;
  category: string;
  source_page: number;
  source_chapter: string;
  validated: boolean;
};

type EtatJob = {
  ok: boolean;
  statut?: "en_cours" | "termine" | "erreur";
  etape?: string;
  message?: string | null;
  societe?: string;
  annee?: number;
  kpis?: KpiExtrait[];
  erreur?: string | null;
};

const LIBELLES_ETAPES: Record<string, string> = {
  demarrage: "Lancement de l'extraction…",
  extraction_pdf: "Lecture du PDF (Docling)…",
  appel_modele: "Appel du modèle d'extraction…",
  validation: "Validation des chiffres extraits…",
  ecriture_db: "Enregistrement des résultats…",
};

/**
 * Onglet "Ajouter un PDF" — circuit complet : le fondateur dépose un PDF,
 * on lui propose un titre (extrait de la page 1, ou à défaut le nom de
 * fichier nettoyé), il confirme ou renomme, précise la société et l'année
 * du rapport. Le PDF est alors enregistré dans data/, puis l'extraction
 * des KPIs est déclenchée en arrière-plan (script Python côté backend) et
 * suivie ici par polling jusqu'au résultat.
 *
 * Société + année sont saisies à la main (plutôt que devinées) pour
 * fiabiliser l'extraction sur un PDF inconnu du système. Les KPIs obtenus
 * restent marqués "à vérifier" tant qu'ils n'ont pas de validation
 * manuelle (validated=false côté kpis.db).
 *
 * Ne fonctionne qu'en local (npm run dev / next start sur le PC) : l'API
 * d'enregistrement écrit sur le disque, ce qui n'est pas possible sur le
 * déploiement en ligne (Vercel, sans stockage persistant).
 */
export default function UploadPage() {
  const [etape, setEtape] = useState<Etape>("depot");
  const [fichier, setFichier] = useState<File | null>(null);
  const [suggestion, setSuggestion] = useState<SuggestionApi | null>(null);
  const [titre, setTitre] = useState("");
  const [enRenommage, setEnRenommage] = useState(false);
  const [societe, setSociete] = useState("");
  const [annee, setAnnee] = useState("");
  const [messageErreur, setMessageErreur] = useState("");
  const [nomEnregistre, setNomEnregistre] = useState("");
  const [glisseActif, setGlisseActif] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [etapeExtraction, setEtapeExtraction] = useState("");
  const [kpisExtraits, setKpisExtraits] = useState<KpiExtrait[]>([]);
  const [societeResultat, setSocieteResultat] = useState("");
  const [anneeResultat, setAnneeResultat] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const minuteur = useRef<ReturnType<typeof setTimeout> | null>(null);

  const anneeValide = /^(19|20)\d{2}$/.test(annee.trim());
  const formulaireValide = titre.trim().length >= 3 && societe.trim().length >= 2 && anneeValide;

  const analyserFichier = useCallback(async (f: File) => {
    if (!f.name.toLowerCase().endsWith(".pdf") && f.type !== "application/pdf") {
      setMessageErreur("Ce fichier n'est pas un PDF.");
      setEtape("erreur");
      return;
    }
    setFichier(f);
    setEtape("envoi");
    try {
      const forme = new FormData();
      forme.append("pdf", f);
      const reponse = await fetch("/api/pdf-titre", { method: "POST", body: forme });
      const donnees = await reponse.json();
      if (!reponse.ok) throw new Error(donnees.erreur ?? "Échec de l'analyse du PDF.");
      setSuggestion(donnees as SuggestionApi);
      setTitre((donnees as SuggestionApi).suggestion);
      setEtape("confirmation");
    } catch (err) {
      setMessageErreur(err instanceof Error ? err.message : "Échec de l'analyse du PDF.");
      setEtape("erreur");
    }
  }, []);

  const confirmer = useCallback(async () => {
    if (!fichier || !formulaireValide) return;
    setEtape("envoi");
    try {
      const forme = new FormData();
      forme.append("pdf", fichier);
      forme.append("titre", titre.trim());
      forme.append("societe", societe.trim());
      forme.append("annee", annee.trim());
      const reponse = await fetch("/api/upload-pdf", { method: "POST", body: forme });
      const donnees = await reponse.json();
      if (!reponse.ok || !donnees.ok) throw new Error(donnees.erreur ?? "Échec de l'enregistrement.");
      setNomEnregistre(donnees.nomFichier);

      // Le PDF est enregistré : on enchaîne aussitôt sur le déclenchement de
      // l'extraction (en arrière-plan, suivi ensuite par polling).
      const reponseExtraction = await fetch("/api/lancer-extraction", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chemin: donnees.chemin,
          nomFichier: donnees.nomFichier,
          societe: donnees.societe,
          annee: donnees.annee,
        }),
      });
      const donneesExtraction = await reponseExtraction.json();
      if (!reponseExtraction.ok || !donneesExtraction.ok) {
        throw new Error(
          donneesExtraction.erreur ?? "Le PDF est enregistré, mais l'extraction n'a pas pu démarrer."
        );
      }
      setJobId(donneesExtraction.jobId);
      setEtapeExtraction("demarrage");
      setEtape("extraction");
    } catch (err) {
      setMessageErreur(err instanceof Error ? err.message : "Échec de l'enregistrement.");
      setEtape("erreur");
    }
  }, [fichier, titre, societe, annee, formulaireValide]);

  // Suivi de l'extraction en cours : on relit le statut du job toutes les
  // 2,5s tant qu'il n'est pas terminé (ou en erreur).
  useEffect(() => {
    if (etape !== "extraction" || !jobId) return;
    let annule = false;

    const interroger = async () => {
      try {
        const reponse = await fetch(`/api/extraction-statut/${jobId}`);
        const donnees = (await reponse.json()) as EtatJob;
        if (annule) return;

        if (!reponse.ok || !donnees.ok) {
          setMessageErreur(donnees.erreur ?? "Suivi de l'extraction impossible.");
          setEtape("erreur");
          return;
        }
        setEtapeExtraction(donnees.etape ?? "");

        if (donnees.statut === "termine") {
          setKpisExtraits(donnees.kpis ?? []);
          setSocieteResultat(donnees.societe ?? societe);
          setAnneeResultat(donnees.annee ?? Number(annee));
          setEtape("resultats");
          return;
        }
        if (donnees.statut === "erreur") {
          setMessageErreur(donnees.erreur ?? "L'extraction a échoué.");
          setEtape("erreur");
          return;
        }
        minuteur.current = setTimeout(interroger, 2500);
      } catch (err) {
        if (annule) return;
        setMessageErreur(err instanceof Error ? err.message : "Suivi de l'extraction impossible.");
        setEtape("erreur");
      }
    };

    interroger();
    return () => {
      annule = true;
      if (minuteur.current) clearTimeout(minuteur.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etape, jobId]);

  const reinitialiser = () => {
    setEtape("depot");
    setFichier(null);
    setSuggestion(null);
    setTitre("");
    setEnRenommage(false);
    setSociete("");
    setAnnee("");
    setMessageErreur("");
    setNomEnregistre("");
    setJobId(null);
    setEtapeExtraction("");
    setKpisExtraits([]);
    setSocieteResultat("");
    setAnneeResultat(null);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setGlisseActif(false);
    const f = e.dataTransfer.files?.[0];
    if (f) analyserFichier(f);
  };

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto px-4 sm:px-6 py-6 sm:py-8" style={{ width: "92%", maxWidth: "900px" }}>
        <div className="flex items-center mb-2">
          <div>
            <p className="text-xs font-bold tracking-[0.12em] text-accent">SOLVABILITÉ II</p>
            <h2 className="font-heading italic text-3xl text-text-primary mt-0.5">Ajouter un PDF</h2>
          </div>
        </div>
        <p className="text-sm text-text-secondary mb-6">
          Déposez un rapport SFCR : nous proposons un titre à partir du document, vous confirmez ou renommez et
          précisez la société et l&apos;année, puis le modèle extrait automatiquement les KPIs.
        </p>

        {/* Étape 1 : dépôt */}
        {etape === "depot" && (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setGlisseActif(true);
            }}
            onDragLeave={() => setGlisseActif(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className={cn(
              "flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-[var(--radius-lg)] px-6 py-16 cursor-pointer transition-colors bg-surface",
              glisseActif ? "border-accent bg-accent-light" : "border-border hover:border-border-hover"
            )}
          >
            <UploadCloud className="w-10 h-10 text-text-tertiary" />
            <p className="text-sm font-medium text-text-primary">
              Glissez un PDF ici, ou cliquez pour en choisir un
            </p>
            <p className="text-xs text-text-tertiary">Fichier PDF uniquement</p>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) analyserFichier(f);
              }}
            />
          </div>
        )}

        {/* Chargement (analyse ou envoi) */}
        {etape === "envoi" && (
          <div className="flex flex-col items-center justify-center gap-3 border border-border rounded-[var(--radius-lg)] px-6 py-16 bg-surface">
            <Loader2 className="w-8 h-8 text-accent animate-spin" />
            <p className="text-sm text-text-secondary">
              {fichier && !suggestion ? "Analyse du PDF en cours…" : "Enregistrement en cours…"}
            </p>
          </div>
        )}

        {/* Étape 2 : confirmation / renommage */}
        {etape === "confirmation" && fichier && suggestion && (
          <div className="border border-border rounded-[var(--radius-lg)] bg-surface p-6">
            <div className="flex items-start gap-3 mb-5">
              <FileText className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">{fichier.name}</p>
                <p className="text-xs text-text-tertiary">{(fichier.size / 1024 / 1024).toFixed(2)} Mo</p>
              </div>
            </div>

            <p className="text-xs font-medium text-text-secondary mb-2">
              {suggestion.titreExtrait
                ? "Titre détecté sur la première page du document :"
                : "Aucun titre détecté sur la première page — nom de fichier proposé :"}
            </p>

            {!enRenommage ? (
              <div className="flex items-center gap-2 bg-surface-secondary border border-border rounded-[var(--radius-md)] px-4 py-3">
                <span className="flex-1 text-sm font-medium text-text-primary">{titre}</span>
                <button
                  onClick={() => setEnRenommage(true)}
                  className="flex items-center gap-1 text-xs text-accent hover:underline flex-shrink-0"
                >
                  <Pencil className="w-3 h-3" /> Renommer
                </button>
              </div>
            ) : (
              <input
                autoFocus
                value={titre}
                onChange={(e) => setTitre(e.target.value)}
                className="w-full text-sm font-medium text-text-primary bg-surface-secondary border border-accent rounded-[var(--radius-md)] px-4 py-3 outline-none"
                placeholder="Titre du document"
              />
            )}

            <div className="grid grid-cols-2 gap-4 mt-5">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1.5">Société</label>
                <input
                  value={societe}
                  onChange={(e) => setSociete(e.target.value)}
                  placeholder="Ex. Groupama"
                  className="w-full text-sm text-text-primary bg-surface-secondary border border-border rounded-[var(--radius-md)] px-3 py-2.5 outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1.5">Année du rapport</label>
                <input
                  value={annee}
                  onChange={(e) => setAnnee(e.target.value.replace(/[^\d]/g, "").slice(0, 4))}
                  placeholder="Ex. 2025"
                  inputMode="numeric"
                  className="w-full text-sm text-text-primary bg-surface-secondary border border-border rounded-[var(--radius-md)] px-3 py-2.5 outline-none focus:border-accent"
                />
              </div>
            </div>
            {(societe.trim().length > 0 && societe.trim().length < 2) ||
            (annee.trim().length === 4 && !anneeValide) ? (
              <p className="text-xs text-danger mt-2">Vérifiez le nom de la société et l&apos;année (ex. 2025).</p>
            ) : null}

            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={confirmer}
                disabled={!formulaireValide}
                className="px-4 py-2 rounded-[var(--radius-md)] bg-accent text-accent-foreground text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-accent-hover transition-colors"
              >
                Confirmer et enregistrer
              </button>
              <button
                onClick={reinitialiser}
                className="px-4 py-2 rounded-[var(--radius-md)] text-sm text-text-secondary hover:bg-surface-hover transition-colors"
              >
                Annuler
              </button>
            </div>
          </div>
        )}

        {/* Extraction en cours */}
        {etape === "extraction" && (
          <div className="flex flex-col items-center justify-center gap-3 border border-border rounded-[var(--radius-lg)] px-6 py-16 bg-surface">
            <Loader2 className="w-8 h-8 text-accent animate-spin" />
            <p className="text-sm font-medium text-text-primary">
              {LIBELLES_ETAPES[etapeExtraction] ?? "Extraction en cours…"}
            </p>
            <p className="text-xs text-text-tertiary">
              PDF enregistré sous « {nomEnregistre} » — le modèle traite le document, ça peut prendre quelques minutes.
            </p>
          </div>
        )}

        {/* Résultats de l'extraction */}
        {etape === "resultats" && (
          <div className="border border-border rounded-[var(--radius-lg)] bg-surface p-6">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0" />
                <p className="text-sm font-medium text-text-primary">
                  {societeResultat} {anneeResultat ? `— ${anneeResultat}` : ""}
                </p>
                <span className="text-[10px] font-bold uppercase tracking-wide text-accent bg-accent-light px-1.5 py-0.5 rounded">
                  Nouveau
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2 bg-warning-light border border-warning/30 rounded-[10px] px-3 py-2 mb-4">
              <ShieldAlert className="w-[15px] h-[15px] text-warning flex-shrink-0 mt-0.5" />
              <p className="text-xs text-warning">
                Extraction automatique — ces chiffres n&apos;ont pas encore été vérifiés manuellement.
              </p>
            </div>

            {kpisExtraits.length === 0 ? (
              <p className="text-sm text-text-secondary">Aucun KPI n&apos;a pu être extrait de ce document.</p>
            ) : (
              <div className="space-y-2">
                {kpisExtraits.map((kpi) => (
                  <div
                    key={kpi.kpi_name}
                    className="flex items-center justify-between gap-3 bg-surface-secondary border border-border rounded-[var(--radius-md)] px-3 py-2.5"
                  >
                    <div className="min-w-0">
                      <p className="text-sm text-text-primary truncate">{kpi.kpi_name}</p>
                      <p className="text-[11px] text-text-tertiary">
                        page {kpi.source_page} · chapitre {kpi.source_chapter}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="font-mono text-sm text-text-primary">
                        {kpi.value} {kpi.unit}
                      </span>
                      {!kpi.validated && (
                        <span className="flex items-center gap-1 text-[10px] text-warning bg-warning-light px-1.5 py-0.5 rounded">
                          <Sparkles className="w-3 h-3" /> à vérifier
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={reinitialiser}
              className="mt-6 px-4 py-2 rounded-[var(--radius-md)] bg-accent text-accent-foreground text-sm font-medium hover:bg-accent-hover transition-colors"
            >
              Ajouter un autre PDF
            </button>
          </div>
        )}

        {/* Erreur */}
        {etape === "erreur" && (
          <div className="flex flex-col items-center justify-center gap-3 border border-danger/30 bg-danger-light rounded-[var(--radius-lg)] px-6 py-16">
            <AlertTriangle className="w-10 h-10 text-danger" />
            <p className="text-sm font-medium text-danger text-center">{messageErreur}</p>
            <button
              onClick={reinitialiser}
              className="mt-2 px-4 py-2 rounded-[var(--radius-md)] text-sm text-text-secondary hover:bg-surface-hover transition-colors"
            >
              Réessayer
            </button>
          </div>
        )}

        <div className="flex items-start gap-2 bg-warning-light border border-warning/30 rounded-[10px] px-4 py-2.5 w-full mt-8">
          <AlertTriangle className="w-[15px] h-[15px] text-warning flex-shrink-0 mt-0.5" />
          <p className="text-xs text-warning">
            Fonctionne uniquement en local (le PDF est écrit sur le disque du PC, et le modèle d&apos;extraction y
            tourne aussi) — pas sur la version en ligne. Les résultats d&apos;une extraction automatique restent
            « à vérifier » tant qu&apos;ils n&apos;ont pas été validés manuellement.
          </p>
        </div>
      </div>
    </div>
  );
}
