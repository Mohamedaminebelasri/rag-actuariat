"use client";

import { ShieldCheck, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

/** Port de badge_confiance() (individuelle.py, Reflex). */
export function ConfidenceBadge({
  confiance,
  chapitre,
  page,
}: {
  confiance: "verified" | "extracted";
  chapitre: string;
  page: number | null;
}) {
  const estVerifie = confiance === "verified";
  const titre = page != null ? `Source : chapitre ${chapitre}, page ${page}` : `Source : chapitre ${chapitre}`;

  return (
    <span
      title={titre}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium w-fit",
        estVerifie ? "text-success bg-success-light" : "text-warning bg-warning-light"
      )}
    >
      {estVerifie ? <ShieldCheck className="w-3 h-3" /> : <Sparkles className="w-3 h-3" />}
      {estVerifie ? "Vérifié" : "Extrait par IA"}
    </span>
  );
}
