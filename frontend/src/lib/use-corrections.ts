"use client";

import { useCallback, useEffect, useState } from "react";

export type Correction = {
  valeurCorrigee: string;
  commentaire: string | null;
  date: string;
};

/** Map clé = "societe::kpiId" → Correction */
export type CorrectionsMap = Record<string, Correction>;

/**
 * Hook qui charge les corrections KPI depuis l'API (/api/kpi/correct GET)
 * et fournit un moyen de soumettre de nouvelles corrections.
 *
 * Retourne :
 * - corrections : la map des corrections chargées
 * - getCorrection(societe, kpiId) : récupère une correction si elle existe
 * - soumettre(societe, kpiId, valeur, commentaire) : envoie une correction
 * - recharger() : recharge depuis l'API
 */
export function useCorrections() {
  const [corrections, setCorrections] = useState<CorrectionsMap>({});

  const charger = useCallback(async () => {
    try {
      const res = await fetch("/api/kpi/correct");
      if (res.ok) {
        const data = await res.json();
        setCorrections(data.corrections ?? {});
      }
    } catch {
      // silently ignore — corrections are optional UX enhancement
    }
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  const getCorrection = useCallback(
    (societe: string, kpiId: string): Correction | null => {
      return corrections[`${societe}::${kpiId}`] ?? null;
    },
    [corrections]
  );

  const soumettre = useCallback(
    async (
      societe: string,
      kpiId: string,
      valeurCorrigee: string,
      commentaire: string | null
    ): Promise<boolean> => {
      try {
        const res = await fetch("/api/kpi/correct", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ societe, kpiId, valeurCorrigee, commentaire }),
        });
        if (res.ok) {
          // Mettre à jour localement sans re-fetch
          setCorrections((prev) => ({
            ...prev,
            [`${societe}::${kpiId}`]: {
              valeurCorrigee,
              commentaire,
              date: new Date().toISOString(),
            },
          }));
          return true;
        }
        return false;
      } catch {
        return false;
      }
    },
    []
  );

  return { corrections, getCorrection, soumettre, recharger: charger };
}
