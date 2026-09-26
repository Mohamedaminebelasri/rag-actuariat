/**
 * csv-export.ts — Port de exporter_csv()/exporter_comparatif_csv()
 * (state.py, Reflex) : génère un CSV côté client et déclenche le
 * téléchargement (équivalent de rx.download côté navigateur).
 */

import { KPI_PAR_ID, kpisSociete } from "@/data/analyse-demo";

function telecharger(contenu: string, nomFichier: string) {
  const blob = new Blob([contenu], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nomFichier;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exporterCsvIndividuel(societe: string) {
  const kpisBruts = kpisSociete(societe);
  const lignes = ["categorie,code,label,valeur,unite,variation,confiance"];
  for (const [kid, kdef] of Object.entries(KPI_PAR_ID)) {
    const brut = kpisBruts[kid];
    if (!brut) continue;
    const variation = brut.variation === null ? "" : String(brut.variation);
    lignes.push(`${kdef.categorie},${kdef.code},${kdef.label},${brut.valeur},${kdef.unite},${variation},${brut.confiance}`);
  }
  telecharger(lignes.join("\n"), `analyse_${societe.replace(/ /g, "_")}.csv`);
}

export function exporterCsvComparatif(societes: string[]) {
  if (societes.length < 2) return;
  const entetes = ["categorie", "kpi", "unite", ...societes];
  const lignes = [entetes.join(",")];
  for (const [kid, kdef] of Object.entries(KPI_PAR_ID)) {
    const valeurs = societes.map((soc) => {
      const brut = kpisSociete(soc)[kid];
      return brut ? String(brut.valeur) : "";
    });
    lignes.push([kdef.categorie, kdef.label, kdef.unite, ...valeurs].join(","));
  }
  telecharger(lignes.join("\n"), "analyse_comparative.csv");
}
