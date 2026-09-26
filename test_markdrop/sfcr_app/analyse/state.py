"""state.py — État Reflex pour l'onglet Analyse (2 sous-onglets)."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

import reflex as rx

from . import data

MAX_SOCIETES_COMPARAISON = 8


# Dataclasses (pas des dicts nus) pour les structures utilisées dans un
# rx.foreach IMBRIQUÉ (lignes -> cellules) : Reflex ne peut pas inférer le
# type d'un foreach interne sur un dict générique (list[dict] = Any),
# alors qu'un modèle typé permet l'indexation correcte à travers les 2
# niveaux — cf. https://reflex.dev/docs/library/dynamic-rendering/foreach/
@dataclass
class CelluleKPI:
    societe: str = ""
    valeur_str: str = ""
    rang: int = 0
    est_meilleur: bool = False
    est_pire: bool = False


@dataclass
class LigneKPI:
    kpi_id: str = ""
    kpi_label: str = ""
    unite: str = ""
    cellules: list[CelluleKPI] = field(default_factory=list)
    moyenne_str: str = ""
    mediane_str: str = ""
    seuil_str: str = ""
    a_seuil: bool = False

# Sens de "meilleure valeur" par KPI — utilisé UNIQUEMENT pour la mise en
# surbrillance meilleur/pire du tableau comparatif. Beaucoup de KPIs en
# montant absolu (SCR, fonds propres, primes...) dépendent avant tout de
# la taille de l'assureur : les qualifier de "meilleurs/pires" serait
# trompeur, donc ils restent "neutre" (affichés sans badge de classement).
# Seuls les ratios et le surplus (une mesure de marge de sécurité, encore
# imparfaite mais moins dépendante de la taille) sont classés.
SENS_KPI = {
    "ratio_scr": "higher", "ratio_mcr": "higher", "surplus_capital": "higher",
    "diversification": "lower",  # stocké négatif : plus négatif = plus de bénéfice
    "ratio_sp": "lower",
}

CATEGORIE_LABELS = {"Tous": "Tous", "E": "Capital", "D": "Valorisation", "C": "Risques", "A": "Activité"}


def _format_valeur(valeur: float, unite: str) -> str:
    if unite == "%":
        return f"{valeur:,.1f}".replace(",", " ").replace(".", ",") + " %"
    return f"{valeur:,.2f}".replace(",", " ").replace(".", ",") + " Md€"


def _couleur_seuil(kpi_id: str, valeur: float) -> str:
    """Couleur sémantique de la VALEUR principale — uniquement pour les 3
    KPIs avec un seuil réglementaire explicite (ratio_scr/mcr/sp, cf.
    data.py). Les autres KPIs utilisent une couleur neutre : leur "bon"
    niveau ne se juge pas dans l'absolu."""
    seuil = data.KPI_PAR_ID[kpi_id]["seuil_reglementaire"]
    if seuil is None:
        return "neutre"
    if kpi_id == "ratio_sp":  # plus bas = meilleur
        if valeur <= 95:
            return "success"
        if valeur <= 105:
            return "warning"
        return "danger"
    # ratio_scr / ratio_mcr : plus haut = meilleur
    if valeur >= 150:
        return "success"
    if valeur >= 100:
        return "warning"
    return "danger"


class AnalyseState(rx.State):
    # --- Navigation ---
    sous_onglet: str = "individuelle"

    # --- Sous-onglet 1 : analyse individuelle ---
    societe_selectionnee: str = ""

    # --- Sous-onglet 2 : analyse comparative ---
    societes_comparees: list[str] = ["Groupama", "AXA France"]
    filtre_categorie_comparaison: str = "Tous"
    kpi_graphique_selectionne: str = "ratio_scr"
    colonne_tri: str = ""
    tri_ascendant: bool = True
    afficher_moyenne: bool = True
    afficher_mediane: bool = True
    afficher_seuil: bool = True
    societes_radar_masquees: list[str] = []
    categories_repliees: list[str] = []

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------
    @rx.event
    def changer_sous_onglet(self, valeur: str):
        self.sous_onglet = valeur

    @rx.event
    def selectionner_societe(self, valeur: str):
        self.societe_selectionnee = valeur

    @rx.event
    def ajouter_societe_comparaison(self, valeur: str):
        if not valeur or valeur in self.societes_comparees:
            return
        if len(self.societes_comparees) >= MAX_SOCIETES_COMPARAISON:
            return
        self.societes_comparees = self.societes_comparees + [valeur]

    @rx.event
    def retirer_societe_comparaison(self, valeur: str):
        self.societes_comparees = [s for s in self.societes_comparees if s != valeur]
        self.societes_radar_masquees = [s for s in self.societes_radar_masquees if s != valeur]

    @rx.event
    def changer_filtre_categorie(self, valeur: str):
        self.filtre_categorie_comparaison = valeur

    @rx.event
    def changer_kpi_graphique(self, valeur: str):
        self.kpi_graphique_selectionne = valeur

    @rx.event
    def trier_par_colonne(self, colonne: str):
        if self.colonne_tri == colonne:
            self.tri_ascendant = not self.tri_ascendant
        else:
            self.colonne_tri = colonne
            self.tri_ascendant = False

    @rx.event
    def basculer_moyenne(self):
        self.afficher_moyenne = not self.afficher_moyenne

    @rx.event
    def basculer_mediane(self):
        self.afficher_mediane = not self.afficher_mediane

    @rx.event
    def basculer_seuil(self):
        self.afficher_seuil = not self.afficher_seuil

    @rx.event
    def basculer_categorie_repliee(self, code: str):
        if code in self.categories_repliees:
            self.categories_repliees = [c for c in self.categories_repliees if c != code]
        else:
            self.categories_repliees = self.categories_repliees + [code]

    @rx.event
    def exporter_csv(self):
        """Export CSV des 20 KPIs de la société sélectionnée (analyse
        individuelle) — génère le fichier côté serveur, télécharge côté
        client via rx.download."""
        if not self.societe_selectionnee:
            return
        kpis_bruts = data.kpis_societe(self.societe_selectionnee)
        lignes = ["categorie,code,label,valeur,unite,variation,confiance"]
        for kid, kdef in data.KPI_PAR_ID.items():
            brut = kpis_bruts.get(kid)
            if brut is None:
                continue
            variation = "" if brut["variation"] is None else str(brut["variation"])
            lignes.append(f"{kdef['categorie']},{kdef['code']},{kdef['label']},{brut['valeur']},{kdef['unite']},{variation},{brut['confiance']}")
        contenu = "\n".join(lignes)
        nom_fichier = f"analyse_{self.societe_selectionnee.replace(' ', '_')}.csv"
        return rx.download(data=contenu, filename=nom_fichier)

    @rx.event
    def exporter_comparatif_csv(self):
        """Export CSV du tableau comparatif (toutes les sociétés
        actuellement comparées, tous les KPIs)."""
        if len(self.societes_comparees) < 2:
            return
        entetes = ["categorie", "kpi", "unite"] + list(self.societes_comparees)
        lignes = [",".join(entetes)]
        for kid, kdef in data.KPI_PAR_ID.items():
            valeurs = []
            for soc in self.societes_comparees:
                brut = data.kpis_societe(soc).get(kid)
                valeurs.append(str(brut["valeur"]) if brut else "")
            lignes.append(",".join([kdef["categorie"], kdef["label"], kdef["unite"]] + valeurs))
        contenu = "\n".join(lignes)
        return rx.download(data=contenu, filename="analyse_comparative.csv")

    @rx.event
    def basculer_visibilite_radar(self, societe: str):
        if societe in self.societes_radar_masquees:
            self.societes_radar_masquees = [s for s in self.societes_radar_masquees if s != societe]
        else:
            self.societes_radar_masquees = self.societes_radar_masquees + [societe]

    # ------------------------------------------------------------------
    # Vars calculées — communes
    # ------------------------------------------------------------------
    @rx.var
    def sfcr_disponibles(self) -> list[dict]:
        return data.liste_sfcr_disponibles()

    # ------------------------------------------------------------------
    # Vars calculées — analyse individuelle
    # ------------------------------------------------------------------
    @rx.var
    def a_une_societe_selectionnee(self) -> bool:
        return bool(self.societe_selectionnee)

    @rx.var
    def label_societe_selectionnee(self) -> str:
        for s in self.sfcr_disponibles:
            if s["id"] == self.societe_selectionnee:
                return s["label"]
        return ""

    @rx.var
    def kpis_par_categorie(self) -> dict[str, list[dict]]:
        """Pour l'analyse individuelle : {code_categorie: [kpi enrichi]}."""
        kpis_bruts = data.kpis_societe(self.societe_selectionnee)
        resultat: dict[str, list[dict]] = {c["code"]: [] for c in data.CATEGORIES}
        for kid, kdef in data.KPI_PAR_ID.items():
            brut = kpis_bruts.get(kid)
            if brut is None:
                continue
            valeur = brut["valeur"]
            variation = brut["variation"]
            resultat[kdef["categorie"]].append({
                "id": kid, "code": kdef["code"], "label": kdef["label"],
                "description": kdef["description"], "unite": kdef["unite"],
                "valeur_str": _format_valeur(valeur, kdef["unite"]),
                "a_variation": variation is not None,
                "variation_str": (f"+{variation:.1f}" if variation is not None and variation >= 0 else f"{variation:.1f}") + f" {brut['variation_unit']}" if variation is not None else "",
                "variation_positive": bool(variation is not None and variation >= 0),
                "couleur_seuil": _couleur_seuil(kid, valeur),
                "confiance": brut["confiance"],
                "chapitre_source": brut["chapitre_source"],
                "page_source": brut["page_source"],
            })
        return resultat

    @rx.var
    def scr_decomposition(self) -> list[dict]:
        """Pour le graphique de décomposition du SCR (individuel)."""
        kpis_bruts = data.kpis_societe(self.societe_selectionnee)
        if not kpis_bruts:
            return []
        composantes = [
            ("SCR non-vie", "scr_nonvie"), ("SCR vie", "scr_vie"), ("SCR marché", "scr_marche"),
            ("SCR contrepartie", "scr_contrepartie"), ("SCR opérationnel", "scr_operationnel"),
        ]
        sortie = [{"module": label, "valeur": kpis_bruts[kid]["valeur"]} for label, kid in composantes if kid in kpis_bruts]
        if "diversification" in kpis_bruts:
            div_pct = kpis_bruts["diversification"]["valeur"]
            somme_brute = sum(c["valeur"] for c in sortie)
            sortie.append({"module": "Diversification", "valeur": round(somme_brute * div_pct / 100, 2)})
        return sortie

    # ------------------------------------------------------------------
    # Vars calculées — analyse comparative
    # ------------------------------------------------------------------
    @rx.var
    def nb_societes_comparees(self) -> int:
        return len(self.societes_comparees)

    @rx.var
    def peut_comparer(self) -> bool:
        return len(self.societes_comparees) >= 2

    @rx.var
    def au_maximum(self) -> bool:
        return len(self.societes_comparees) >= MAX_SOCIETES_COMPARAISON

    @rx.var
    def societes_disponibles_a_ajouter(self) -> list[dict]:
        return [s for s in self.sfcr_disponibles if s["id"] not in self.societes_comparees]

    @rx.var
    def categories_filtre(self) -> list[str]:
        return ["Tous"] + [c["code"] for c in data.CATEGORIES]

    def _kpis_filtres_ids(self) -> list[str]:
        if self.filtre_categorie_comparaison == "Tous":
            return [k["id"] for k in data.KPI_DEFINITIONS]
        return data.KPI_IDS_PAR_CATEGORIE.get(self.filtre_categorie_comparaison, [])

    @rx.var
    def tableau_comparatif(self) -> dict[str, list[LigneKPI]]:
        """{code_categorie: [LigneKPI]} — cf. modèles typés en tête de
        fichier (nécessaire pour le rx.foreach imbriqué lignes/cellules)."""
        if len(self.societes_comparees) < 2:
            return {}
        kpi_ids_filtres = set(self._kpis_filtres_ids())
        resultat: dict[str, list[LigneKPI]] = {c["code"]: [] for c in data.CATEGORIES}
        cles_tri: dict[str, list[float | None]] = {c["code"]: [] for c in data.CATEGORIES}

        for kid, kdef in data.KPI_PAR_ID.items():
            if kid not in kpi_ids_filtres:
                continue
            valeurs_par_societe = {}
            for soc in self.societes_comparees:
                brut = data.kpis_societe(soc).get(kid)
                if brut is not None:
                    valeurs_par_societe[soc] = brut["valeur"]
            if not valeurs_par_societe:
                continue

            sens = SENS_KPI.get(kid)
            valeurs_triees = sorted(valeurs_par_societe.values(), reverse=(sens == "higher")) if sens else []
            cellules = []
            for soc in self.societes_comparees:
                v = valeurs_par_societe.get(soc)
                if v is None:
                    cellules.append(CelluleKPI(societe=soc, valeur_str="—"))
                    continue
                rang = valeurs_triees.index(v) + 1 if sens else 0
                cellules.append(CelluleKPI(
                    societe=soc, valeur_str=_format_valeur(v, kdef["unite"]), rang=rang,
                    est_meilleur=bool(sens and rang == 1),
                    est_pire=bool(sens and rang == len(valeurs_triees) and len(valeurs_triees) > 1),
                ))

            vals = list(valeurs_par_societe.values())
            moyenne = statistics.mean(vals) if vals else 0.0
            mediane = statistics.median(vals) if vals else 0.0
            seuil = kdef["seuil_reglementaire"]
            resultat[kdef["categorie"]].append(LigneKPI(
                kpi_id=kid, kpi_label=kdef["label"], unite=kdef["unite"], cellules=cellules,
                moyenne_str=_format_valeur(moyenne, kdef["unite"]),
                mediane_str=_format_valeur(mediane, kdef["unite"]),
                seuil_str=_format_valeur(seuil, kdef["unite"]) if seuil is not None else "",
                a_seuil=seuil is not None,
            ))
            cles_tri[kdef["categorie"]].append(valeurs_par_societe.get(self.colonne_tri))

        if self.colonne_tri and self.colonne_tri in self.societes_comparees:
            for code in resultat:
                paires = sorted(
                    zip(resultat[code], cles_tri[code]),
                    key=lambda p: (p[1] is None, p[1] if p[1] is not None else 0),
                    reverse=not self.tri_ascendant,
                )
                resultat[code] = [ligne for ligne, _ in paires]
        return resultat

    @rx.var
    def radar_axes_labels(self) -> list[str]:
        return [data.KPI_PAR_ID[k]["label"].replace("SCR souscription ", "").replace("SCR risque de ", "").replace("SCR risque ", "") for k in data.AXES_RADAR]

    @rx.var
    def radar_data(self) -> list[dict]:
        """Format recharts : 1 ligne par axe, 1 colonne par société."""
        if not self.societes_comparees:
            return []
        lignes = []
        for axe_id, axe_label in zip(data.AXES_RADAR, self.radar_axes_labels):
            ligne = {"axe": axe_label}
            for soc in self.societes_comparees:
                brut = data.kpis_societe(soc).get(axe_id)
                ligne[soc] = brut["valeur"] if brut else 0
            lignes.append(ligne)
        return lignes

    @rx.var
    def couleurs_societes(self) -> dict[str, str]:
        palette = ["#2563eb", "#16a34a", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#db2777", "#65a30d"]
        return {soc: palette[i % len(palette)] for i, soc in enumerate(self.societes_comparees)}

    @rx.var
    def societes_radar_visibles(self) -> list[str]:
        return [s for s in self.societes_comparees if s not in self.societes_radar_masquees]

    @rx.var
    def label_kpi_graphique(self) -> str:
        return data.KPI_PAR_ID.get(self.kpi_graphique_selectionne, {}).get("label", "")

    @rx.var
    def unite_kpi_graphique(self) -> str:
        return data.KPI_PAR_ID.get(self.kpi_graphique_selectionne, {}).get("unite", "")

    @rx.var
    def seuil_kpi_graphique(self) -> int:
        """-1 = pas de seuil réglementaire pour ce KPI (sentinel plutôt que
        Optional : rx.recharts.reference_line exige y: str | int)."""
        seuil = data.KPI_PAR_ID.get(self.kpi_graphique_selectionne, {}).get("seuil_reglementaire")
        return int(seuil) if seuil is not None else -1

    @rx.var
    def bar_chart_data(self) -> list[dict]:
        sortie = []
        for soc in self.societes_comparees:
            brut = data.kpis_societe(soc).get(self.kpi_graphique_selectionne)
            sortie.append({"societe": soc, "valeur": brut["valeur"] if brut else 0})
        return sortie

    @rx.var
    def benchmark_moyenne_str(self) -> str:
        return ""  # affiché par ligne dans tableau_comparatif

    @rx.var
    def alertes(self) -> list[dict]:
        """Anomalies détectées automatiquement sur le panel comparé —
        règles simples et transparentes (pas de modèle statistique
        complexe) : variation négative significative, ou écart notable
        à la moyenne du panel sur un KPI à seuil."""
        if len(self.societes_comparees) < 2:
            return []
        resultat = []
        for soc in self.societes_comparees:
            kpis_soc = data.kpis_societe(soc)

            ratio_scr = kpis_soc.get("ratio_scr")
            if ratio_scr and ratio_scr["variation"] is not None and ratio_scr["variation"] <= -10:
                resultat.append({
                    "type": "attention", "icone": "triangle-alert",
                    "texte": f"{soc} : ratio SCR en baisse de {abs(ratio_scr['variation']):.0f} pts sur la période",
                })
            if ratio_scr and ratio_scr["valeur"] < 100:
                resultat.append({
                    "type": "critique", "icone": "circle-alert",
                    "texte": f"{soc} : ratio SCR sous le seuil réglementaire de 100 % ({ratio_scr['valeur']:.0f} %)",
                })

            div = kpis_soc.get("diversification")
            if div:
                valeurs_div = [data.kpis_societe(s).get("diversification", {}).get("valeur", 0) for s in self.societes_comparees]
                moyenne_div = statistics.mean(valeurs_div) if valeurs_div else 0
                if div["valeur"] > moyenne_div + 5:  # moins négatif que la moyenne = moins de bénéfice
                    resultat.append({
                        "type": "attention", "icone": "triangle-alert",
                        "texte": f"{soc} : effet de diversification inférieur à la moyenne du panel",
                    })

            ratio_sp = kpis_soc.get("ratio_sp")
            if ratio_sp and ratio_sp["valeur"] <= 90:
                resultat.append({
                    "type": "conforme", "icone": "circle-check",
                    "texte": f"{soc} : ratio S/P maîtrisé ({ratio_sp['valeur']:.0f} %)",
                })
        return resultat
