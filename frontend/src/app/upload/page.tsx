"use client";

import { useCallback, useRef, useState } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Pencil,
} from "lucide-react";
import { cn } from "@/lib/utils";

type Etape = "depot" | "confirmation" | "envoi" | "succes" | "erreur";

type SuggestionApi = {
  suggestion: string;
  titreExtrait: string | null;
  nomNettoye: string;
  tailleOctets: number;
};

/**
 * Onglet "Ajouter un PDF" — étape 1 du circuit d'ingestion : le fondateur
 * dépose un PDF, on lui propose un titre (extrait de la page 1, ou à
 * défaut le nom de fichier nettoyé), il confirme ou renomme, puis le PDF
 * est enregistré dans data/ sous ce titre.
 *
 * L'extraction des KPIs par le modèle est une étape séparée, volontairement
 * pas déclenchée ici — voir la note en bas de page.
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
  const [messageErreur, setMessageErreur] = useState("");
  const [nomEnregistre, setNomEnregistre] = useState("");
  const [glisseActif, setGlisseActif] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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
    if (!fichier || titre.trim().length < 3) return;
    setEtape("envoi");
    try {
      const forme = new FormData();
      forme.append("pdf", fichier);
      forme.append("titre", titre.trim());
      const reponse = await fetch("/api/upload-pdf", { method: "POST", body: forme });
      const donnees = await reponse.json();
      if (!reponse.ok || !donnees.ok) throw new Error(donnees.erreur ?? "Échec de l'enregistrement.");
      setNomEnregistre(donnees.nomFichier);
      setEtape("succes");
    } catch (err) {
      setMessageErreur(err instanceof Error ? err.message : "Échec de l'enregistrement.");
      setEtape("erreur");
    }
  }, [fichier, titre]);

  const reinitialiser = () => {
    setEtape("depot");
    setFichier(null);
    setSuggestion(null);
    setTitre("");
    setEnRenommage(false);
    setMessageErreur("");
    setNomEnregistre("");
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
          Déposez un rapport SFCR : nous proposons un titre à partir du document, vous confirmez ou renommez,
          puis il est enregistré dans notre base. L&apos;extraction des chiffres KPI se fera dans une étape séparée, plus tard.
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

            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={confirmer}
                disabled={titre.trim().length < 3}
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

        {/* Succès */}
        {etape === "succes" && (
          <div className="flex flex-col items-center justify-center gap-3 border border-success/30 bg-success-light rounded-[var(--radius-lg)] px-6 py-16">
            <CheckCircle2 className="w-10 h-10 text-success" />
            <p className="text-sm font-medium text-success text-center">
              PDF enregistré sous « {nomEnregistre} »
            </p>
            <button
              onClick={reinitialiser}
              className="mt-2 px-4 py-2 rounded-[var(--radius-md)] bg-accent text-accent-foreground text-sm font-medium hover:bg-accent-hover transition-colors"
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
            Fonctionne uniquement en local (le PDF est écrit sur le disque du PC) — pas sur la version en ligne.
            Étape suivante, séparée et pas encore construite : l&apos;extraction automatique des chiffres KPI par le modèle.
          </p>
        </div>
      </div>
    </div>
  );
}
