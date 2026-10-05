"use client";

import { useCallback, useEffect, useState } from "react";

export type ValidationHumaine = {
  par: string;
  date: string;
};

/** Map clé = "societe::kpiId" → ValidationHumaine */
export type ValidationsMap = Record<string, ValidationHumaine>;

/**
 * Hook qui charge les validations humaines depuis /api/kpi/validate
 * et fournit un moyen de marquer un KPI comme traité.
 */
export function useValidationsHumaines() {
  const [validations, setValidations] = useState<ValidationsMap>({});

  const charger = useCallback(async () => {
    try {
      const res = await fetch("/api/kpi/validate");
      if (res.ok) {
        const data = await res.json();
        setValidations(data.validations ?? {});
      }
    } catch {
      // silently ignore
    }
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  const estValideParHumain = useCallback(
    (societe: string, kpiId: string): ValidationHumaine | null => {
      return validations[`${societe}::${kpiId}`] ?? null;
    },
    [validations]
  );

  const valider = useCallback(
    async (societe: string, kpiId: string, par?: string): Promise<boolean> => {
      try {
        const res = await fetch("/api/kpi/validate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ societe, kpiId, par: par || "Analyste" }),
        });
        if (res.ok) {
          setValidations((prev) => ({
            ...prev,
            [`${societe}::${kpiId}`]: {
              par: par || "Analyste",
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

  const retirer = useCallback(
    async (societe: string, kpiId: string): Promise<boolean> => {
      try {
        const cle = `${societe}::${kpiId}`;
        const res = await fetch(`/api/kpi/validate?cle=${encodeURIComponent(cle)}`, {
          method: "DELETE",
        });
        if (res.ok) {
          setValidations((prev) => {
            const next = { ...prev };
            delete next[cle];
            return next;
          });
          return true;
        }
        return false;
      } catch {
        return false;
      }
    },
    []
  );

  return { validations, estValideParHumain, valider, retirer, recharger: charger };
}
