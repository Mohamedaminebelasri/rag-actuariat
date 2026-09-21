# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier vérifie que les tableaux réglementaires ont été lus dans le
# bon ordre de colonnes, pour éviter que des chiffres se retrouvent
# décalés d'une colonne.
# ------------------------------------------------------------------
"""Check de détection de décalage de colonne ("column shift") sur une
extraction QRT structurée (Gemini ou autre).

Principe : on ne peut pas savoir, à partir du seul dictionnaire EIOPA,
QUELLES cellules doivent être remplies pour une ligne donnée (ça dépend
des données réelles de l'assureur, pas du template). Le seul signal
purement structurel et généralisable, sans vérité terrain par ligne, est
la CONTIGUÏTÉ : dans ces templates, une ligne qui a des valeurs les a
normalement dans des colonnes contiguës.

CORRECTION (après test sur S.05.01.02.01, 17 colonnes) : la contiguïté
n'a de sens qu'À L'INTÉRIEUR d'un même groupe de colonnes (ligne 5 du
fichier EIOPA, ex. "Line of Business for: non-life insurance..." vs
"...accepted non-proportional reinsurance" vs "Total") — PAS sur toute
la largeur du tableau. Sur un tableau large à plusieurs groupes, une
ligne peut légitimement être remplie dans un groupe et vide dans un
autre (l'entité n'a simplement pas cette activité) ; ce n'est pas un
trou suspect. Sans cette correction, ce cas générait des dizaines de
faux positifs (24 sur S.05.01.02.01).

Ne corrige rien : signale uniquement, avec un flag "à vérifier
manuellement" — une correction automatique masquerait les cas où la
valeur est réellement, légitimement, dans la colonne "isolée".

DÉCISION DOCUMENTÉE (2026-07-30) — S.23.01.22 et S.25.05.22 : PAS de
règle officielle EIOPA équivalente disponible pour ces deux templates.
Vérifié dans EIOPA_SolvencyII_Validations_2.8.2_Published.xlsx :
- Feuille "Business Validation 2.8.2" (les vraies règles de calcul) :
  0 règle pour S.23.01.22 et pour S.25.05.22 (suffixe groupe ".22") —
  ce fichier ne couvre que les templates SOLO (S.23.01.07, S.25.05.01/
  04/21...) sur ces deux familles. Seul S.05.01.02 (même code aux deux
  niveaux) y est couvert, cf. check_bv_rules_S05.py.
- Feuille "Identical datapoints 2.8.2" : S.23.01.22/S.25.05.22 y
  apparaissent, mais uniquement pour de la cohérence INTER-templates
  (même cellule R/C doit avoir la même valeur dans S.25.05.01,
  S.25.05.04, S.25.05.21, S.25.05.22, S.26.08.01, S.26.08.04...) —
  jamais de relation entre colonnes DIFFÉRENTES d'un même template. Ne
  répond donc pas à la question posée (relation entre C0010/C0070/
  C0090/C0120 sur S.25.05.22).
DÉCISION RETENUE : option 2 — accepter la limite. Pour ces deux
templates, le check de contiguïté par groupe (ci-dessus) reste le seul
signal automatique disponible, avec ses faux négatifs connus (colonnes
mutuellement exclusives sans groupe partagé, cf. S.25.05.22.01 où
chaque colonne a son propre groupe individuel — R0310/R0400 ne seraient
plus détectés). Vérification manuelle nécessaire sur ces templates tant
qu'aucune règle officielle exploitable n'est trouvée.
"""

import re
from collections import defaultdict


def _col_sort_key(code):
    m = re.match(r"C(\d+)", code)
    return int(m.group(1)) if m else code


def detect_column_shifts(lignes, col_groups):
    """lignes : liste de dicts {"code": "R0310", "C0010": ..., "C0070": ..., ...}
    col_groups : {code_colonne: libellé_de_groupe} (dictionnaire EIOPA,
    ligne 5) — la contiguïté n'est vérifiée qu'entre colonnes partageant
    le même libellé de groupe. Retourne une liste de signalements (liste
    vide si rien de suspect)."""
    groupes = defaultdict(list)
    for code, groupe in col_groups.items():
        groupes[groupe].append(code)
    for groupe in groupes:
        groupes[groupe].sort(key=_col_sort_key)

    signalements = []

    for ligne in lignes:
        code = ligne.get("code")
        for groupe, colonnes_ord in groupes.items():
            if len(colonnes_ord) < 2:
                continue  # groupe à 1 seule colonne : pas de "trou" possible

            remplissage = [ligne.get(c) is not None for c in colonnes_ord]
            indices_remplis = [i for i, r in enumerate(remplissage) if r]
            if len(indices_remplis) < 2:
                continue  # pas assez de valeurs DANS CE GROUPE pour qu'un trou ait un sens

            lo, hi = min(indices_remplis), max(indices_remplis)
            trous = [i for i in range(lo, hi + 1) if not remplissage[i]]
            for i in trous:
                col_vide = colonnes_ord[i]
                voisins_remplis = [colonnes_ord[j] for j in indices_remplis]
                signalements.append({
                    "code_ligne": code,
                    "groupe_colonnes": groupe,
                    "colonne_vide_encadree": col_vide,
                    "colonnes_remplies_sur_la_ligne": voisins_remplis,
                    "flag": "SUSPICION DÉCALAGE DE COLONNE — à vérifier manuellement",
                    "detail": (f"{code} : {col_vide} est vide mais encadrée, DANS LE MÊME GROUPE "
                               f"« {groupe} », par des colonnes remplies "
                               f"({', '.join(voisins_remplis)}) — une des valeurs voisines "
                               f"pourrait appartenir à {col_vide}."),
                })

    return signalements


def print_report(signalements, n_lignes_total):
    print(f"=== Check décalage de colonne ({n_lignes_total} lignes analysées) ===")
    if not signalements:
        print("OK — aucun trou de colonne suspect détecté.")
        return
    print(f"{len(signalements)} signalement(s) :")
    for s in signalements:
        print(f"  [SUSPICION] {s['detail']}")
