# -*- coding: utf-8 -*-
"""aema_entites.py — Décision 083 : intégration multi-entités du document
combiné "Aéma Groupe" (621 pages, 13 entités juridiques) dans le pipeline
KPI. Le document est 100% image (confirmé par test automatisé, cf.
POINT_ETAPE_PAUSE.md) — chaque entité nécessite une lecture manuelle
sur rendu PNG avec recoupement interne entre pages indépendantes du
même bloc, comme pour Generali Iard/Vie (Décision 080) et MACIF SAM
(Décision 081).

Généralisation : `extraire_entite()` dans test_markdrop/ingest.py isole
n'importe quel bloc [page_debut, page_fin] en sous-PDF autonome via
fitz.insert_pdf — technique réutilisable pour d'autres documents
combinés futurs, pas seulement Aéma.

État (voir DECISIONS.md, Décision 083 pour le détail complet) :
2 des 13 entités sont complètes et vérifiées (MACIF SAM, Aéma Groupe),
11 restent à faire — bornes de pages déjà connues ci-dessous, prêtes à
être traitées avec la même méthode dès qu'une session aura le temps.
"""

AEMA_SOURCE = "data/Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf"

# Bornes de pages (1-indexées, inclusives) des 13 entités dans le
# document original — vérifiées via les en-têtes "Entité : ..." /
# noms affichés sur chaque bloc (Décision 083).
ENTITES_BORNES = {
    "Aema Groupe": (439, 451),
    "MACIF SAM": (452, 467),
    "Macif Vie": (468, 478),
    "Macif Sante Prevoyance": (479, 493),
    "Themis": (494, 507),
    "Macifilia": (508, 522),
    "Aesio Mutuelle": (523, 538),
    "MNPAF": (539, 550),
    "MMJ": (551, 563),
    "Nuoma": (564, 576),
    "Abeille Vie": (577, 592),
    "Abeille Epargne Retraite": (593, 602),
    "Abeille IARD Sante": (603, 621),
}

# Valeurs en K€ BRUT (telles que lues sur la page, devise "KEUR" —
# converties en M€ uniquement au moment de l'insertion en base, cf.
# `inserer_entite_en_base`, pour rester auditable contre le PDF).
# ratio_scr/ratio_mcr sont déjà en points de pourcentage (ex. 212 pour
# 212%), pas de conversion.
ENTITES_KPIS = {
    "MACIF SAM": {
        "best_estimate": (5969795.0, 453, "S.02.01.02.01 Bilan, somme 5 segments Meilleure estimation"),
        "marge_risque": (341059.0, 453, "S.02.01.02.01 Bilan, somme 5 segments Marge de risque"),
        "primes_acquises_brutes": (4854620.0, 455, "S.05.01.02.01+.02, R0210+R0220+R0230 (non-vie) + R1510 (vie), colonne Total"),
        "charge_sinistres": (3429372.0, 455, "S.05.01.02.01+.02, R0310+R0320+R0330 (non-vie) + R1610 (vie), colonne Total"),
        "fonds_propres_eligibles": (9443143.0, 463, "S.23.01.01.01/R0540/Total"),
        "fonds_propres_t1_nr": (7872072.0, 463, "S.23.01.01.01/R0540/Niveau1 non restreint"),
        "fonds_propres_t1_r": (374465.0, 463, "S.23.01.01.01/R0540/Niveau1 restreint"),
        "fonds_propres_t2": (751973.0, 463, "S.23.01.01.01/R0540/Niveau2"),
        "fonds_propres_t3": (444633.0, 463, "S.23.01.01.01/R0540/Niveau3"),
        "scr_total": (2964220.0, 463, "S.23.01.01.01/R0580 — confirmé p.464 (S.25.01.21.02/R0220) et p.467 (S.28.01.01.05/R0310)"),
        "mcr": (746130.0, 463, "S.23.01.01.01/R0600 — confirmé p.467 (S.28.01.01.05/R0400)"),
        "ratio_scr": (319.0, 463, "S.23.01.01.01/R0620"),
        "ratio_mcr": (1125.0, 463, "S.23.01.01.01/R0640"),
        "scr_marche": (2713693.0, 464, "S.25.01.21.01/R0010"),
        "scr_contrepartie": (63361.0, 464, "S.25.01.21.01/R0020"),
        "scr_souscription_vie": (40522.0, 464, "S.25.01.21.01/R0030"),
        "scr_souscription_sante": (235321.0, 464, "S.25.01.21.01/R0040"),
        "scr_souscription_nonvie": (1464010.0, 464, "S.25.01.21.01/R0050"),
        "scr_diversification": (-1035321.0, 464, "S.25.01.21.01/R0060"),
        "scr_operationnel": (148152.0, 465, "S.25.01.21.02/R0130"),
    },
    "Aema Groupe": {
        "best_estimate": (105865186.0, 440, "S.02.01.02.01 Bilan, somme 5 segments Meilleure estimation"),
        "marge_risque": (2260715.0, 440, "S.02.01.02.01 Bilan, somme 5 segments Marge de risque"),
        "primes_acquises_brutes": (18552020.0, 442, "S.05.01.02.01+.02, R0210+R0220+R0230 (non-vie) + R1510 (vie), colonne Total"),
        "charge_sinistres": (15035231.0, 442, "S.05.01.02.01+.02, R0310+R0320+R0330 (non-vie) + R1610 (vie), colonne Total"),
        "fonds_propres_eligibles": (12860966.0, 446, "S.23.01.22.01/R0660/Total (y compris autres secteurs financiers)"),
        "fonds_propres_t1_nr": (10741242.0, 446, "S.23.01.22.01/R0660/Niveau1 non restreint"),
        "fonds_propres_t1_r": (374466.0, 446, "S.23.01.22.01/R0660/Niveau1 restreint"),
        "fonds_propres_t2": (1259990.0, 446, "S.23.01.22.01/R0660/Niveau2"),
        "fonds_propres_t3": (485268.0, 446, "S.23.01.22.01/R0660/Niveau3"),
        "scr_total": (6063105.0, 446, "S.23.01.22.01/R0680 — confirmé p.444 (S.22.01.22.01/R0090) et p.448 (S.25.01.22.02/R0220 et R0570)"),
        "mcr": (2836823.0, 446, "S.23.01.22.01/R0610 — confirmé p.448 (S.25.01.22.02/R0470)"),
        "ratio_scr": (212.0, 446, "S.23.01.22.01/R0690"),
        "ratio_mcr": (390.0, 446, "S.23.01.22.01/R0650"),
        "scr_marche": (10837399.0, 448, "S.25.01.22.01/R0010"),
        "scr_contrepartie": (264007.0, 448, "S.25.01.22.01/R0020"),
        "scr_souscription_vie": (6245084.0, 448, "S.25.01.22.01/R0030"),
        "scr_souscription_sante": (590138.0, 448, "S.25.01.22.01/R0040"),
        "scr_souscription_nonvie": (1706195.0, 448, "S.25.01.22.01/R0050"),
        "scr_diversification": (-5127701.0, 448, "S.25.01.22.01/R0060"),
        "scr_operationnel": (586048.0, 448, "S.25.01.22.02/R0130"),
    },
    "Macif Vie": {
        # Pages 468-478 (Décision 085). Entité 100% vie (S.05.01.02.02
        # seul, pas de S.05.01.02.01 non-vie) — primes/sinistres = R1510/
        # R1610 seuls. 4 recoupements arithmétiques exacts vérifiés :
        # R1000(p469)=R0700(p475)=1 674 024 ; R0580(p475)=R0220(p476)=
        # 814 179 ; R0100(p476)=somme(R0010..R0070)=3 963 973 ;
        # R0100+R0130+R0140+R0150=R0220=814 179.
        "best_estimate": (25497971.0, 468, "S.02.01.02.01 Bilan, somme 5 lignes Meilleure estimation (R0540+R0580+R0630+R0670+R0710)"),
        "marge_risque": (274339.0, 468, "S.02.01.02.01 Bilan, somme 5 lignes Marge de risque (R0550+R0590+R0640+R0680+R0720)"),
        "primes_acquises_brutes": (2278966.0, 471, "S.05.01.02.02 (vie seule), R1510/Total"),
        "charge_sinistres": (1844429.0, 471, "S.05.01.02.02 (vie seule), R1610/Total"),
        "fonds_propres_eligibles": (1801400.0, 475, "S.23.01.01.01/R0540/Total"),
        "fonds_propres_t1_nr": (1663589.0, 475, "S.23.01.01.01/R0540/Niveau1 non restreint"),
        "fonds_propres_t1_r": (0.0, 475, "S.23.01.01.01/R0540/Niveau1 restreint"),
        "fonds_propres_t2": (137811.0, 475, "S.23.01.01.01/R0540/Niveau2"),
        "fonds_propres_t3": (0.0, 475, "S.23.01.01.01/R0540/Niveau3"),
        "scr_total": (814179.0, 475, "S.23.01.01.01/R0580 — confirmé p.476 (S.25.01.21.02/R0220)"),
        "mcr": (366381.0, 475, "S.23.01.01.01/R0600"),
        "ratio_scr": (221.0, 475, "S.23.01.01.01/R0620"),
        "ratio_mcr": (474.0, 475, "S.23.01.01.01/R0640"),
        "scr_marche": (2982426.0, 476, "S.25.01.21.01/R0010"),
        "scr_contrepartie": (8505.0, 476, "S.25.01.21.01/R0020"),
        "scr_souscription_vie": (1952263.0, 476, "S.25.01.21.01/R0030"),
        "scr_souscription_sante": (29818.0, 476, "S.25.01.21.01/R0040"),
        "scr_souscription_nonvie": (0.0, 476, "S.25.01.21.01/R0050"),
        "scr_diversification": (-1009039.0, 476, "S.25.01.21.01/R0060"),
        "scr_operationnel": (113265.0, 476, "S.25.01.21.02/R0130"),
    },
    "Macif Sante Prevoyance": {
        # Pages 479-493 (Décision 085). Entité mixte vie+non-vie —
        # primes/sinistres = somme S.05.01.02.01(non-vie,p.481-482,
        # R0210/R0310 Total C0200) + S.05.01.02.02(vie,p.483,R1510/R1610
        # Total C0300). Recoupements exacts : R1000(p480)=R0700(p490)=
        # 948 561 ; provisions_techniques=best_estimate+marge_risque=
        # R0510+R0600+R0690(p480)=650 734 ; R0100(p491)=somme(R0010..
        # R0070)=332 593 ; R0220=R0100+R0130+R0140+R0150=366 181=R0580(p490).
        "best_estimate": (592695.0, 480, "S.02.01.02.01 Bilan, somme 4 lignes non-nulles Meilleure estimation (R0580+R0630+R0670)"),
        "marge_risque": (58039.0, 480, "S.02.01.02.01 Bilan, somme 3 lignes Marge de risque (R0590+R0640+R0680)"),
        "primes_acquises_brutes": (1181586.0, 481, "S.05.01.02.01(non-vie,R0210/Total=896062,p.482)+S.05.01.02.02(vie,R1510/Total=285524,p.483)"),
        "charge_sinistres": (777528.0, 481, "S.05.01.02.01(non-vie,R0310/Total=656058,p.482)+S.05.01.02.02(vie,R1610/Total=121470,p.483)"),
        "fonds_propres_eligibles": (948561.0, 490, "S.23.01.01.01/R0540/Total"),
        "fonds_propres_t1_nr": (948561.0, 490, "S.23.01.01.01/R0540/Niveau1 non restreint"),
        "fonds_propres_t1_r": (0.0, 490, "S.23.01.01.01/R0540/Niveau1 restreint"),
        "fonds_propres_t2": (0.0, 490, "S.23.01.01.01/R0540/Niveau2"),
        "fonds_propres_t3": (0.0, 490, "S.23.01.01.01/R0540/Niveau3"),
        "scr_total": (366181.0, 490, "S.23.01.01.01/R0580 — confirmé p.491 (S.25.01.21.02/R0220)"),
        "mcr": (92022.0, 490, "S.23.01.01.01/R0600"),
        "ratio_scr": (259.0, 490, "S.23.01.01.01/R0620"),
        "ratio_mcr": (1031.0, 490, "S.23.01.01.01/R0640"),
        "scr_marche": (183553.0, 491, "S.25.01.21.01/R0010"),
        "scr_contrepartie": (12382.0, 491, "S.25.01.21.01/R0020"),
        "scr_souscription_vie": (61988.0, 491, "S.25.01.21.01/R0030"),
        "scr_souscription_sante": (199866.0, 491, "S.25.01.21.01/R0040"),
        "scr_souscription_nonvie": (0.0, 491, "S.25.01.21.01/R0050"),
        "scr_diversification": (-125196.0, 491, "S.25.01.21.01/R0060"),
        "scr_operationnel": (38266.0, 491, "S.25.01.21.02/R0130"),
    },
    "Themis": {
        # Pages 494-507 (Décision 085). Entité 100% non-vie (page vie
        # S.05.01.02.02 entièrement à 0, confirmé visuellement). Petite
        # entité : MCR (2 700) > SCR (1 055) — plancher absolu du MCR,
        # cas légitime (pas une erreur), cf. ratio_mcr(349%) < ratio_scr
        # (894%) cohérent avec fonds_propres(9428)/MCR=349%. Recoupements
        # exacts : R1000(p495)=R0700(p503)=9 428 ; R0220(p504)=R0100+
        # R0130+R0140+R0150=1025+58+0-28=1055=R0580(p503). R0100(p504)=
        # somme(R0010..R0070)=1026 vs imprimé 1025 (écart d'arrondi ±1,
        # source, pas une erreur de lecture).
        "best_estimate": (1218.0, 495, "S.02.01.02.01 Bilan, R0540 seul (100% non-vie hors santé)"),
        "marge_risque": (78.0, 495, "S.02.01.02.01 Bilan, R0550 seul"),
        "primes_acquises_brutes": (1899.0, 497, "S.05.01.02.01 (non-vie, seule activité), R0210/Total"),
        "charge_sinistres": (1920.0, 497, "S.05.01.02.01 (non-vie, seule activité), R0310/Total"),
        "fonds_propres_eligibles": (9428.0, 503, "S.23.01.01.01/R0540/Total"),
        "fonds_propres_t1_nr": (9428.0, 503, "S.23.01.01.01/R0540/Niveau1 non restreint"),
        "fonds_propres_t1_r": (0.0, 503, "S.23.01.01.01/R0540/Niveau1 restreint"),
        "fonds_propres_t2": (0.0, 503, "S.23.01.01.01/R0540/Niveau2"),
        "fonds_propres_t3": (0.0, 503, "S.23.01.01.01/R0540/Niveau3"),
        "scr_total": (1055.0, 503, "S.23.01.01.01/R0580 — confirmé p.504 (S.25.01.21.02/R0220)"),
        "mcr": (2700.0, 503, "S.23.01.01.01/R0600 — plancher absolu MCR (> SCR), cas légitime pour petite entité"),
        "ratio_scr": (894.0, 503, "S.23.01.01.01/R0620"),
        "ratio_mcr": (349.0, 503, "S.23.01.01.01/R0640"),
        "scr_marche": (599.0, 504, "S.25.01.21.01/R0010"),
        "scr_contrepartie": (35.0, 504, "S.25.01.21.01/R0020"),
        "scr_souscription_vie": (0.0, 504, "S.25.01.21.01/R0030"),
        "scr_souscription_sante": (0.0, 504, "S.25.01.21.01/R0040"),
        "scr_souscription_nonvie": (675.0, 504, "S.25.01.21.01/R0050"),
        "scr_diversification": (-283.0, 504, "S.25.01.21.01/R0060"),
        "scr_operationnel": (58.0, 504, "S.25.01.21.02/R0130"),
    },
    "Macifilia": {
        # Pages 508-522 (Décision 085). Pas de S.05.01.02.02 (vie) dans
        # ce bloc bien que le bilan porte une petite composante vie
        # (R0670/R0680) — provisions sans primes cette année (portefeuille
        # en run-off), cohérent, pas une anomalie. charge_sinistres brute
        # = -939 552 K€ (NÉGATIF, vérifié : Part réassureurs=0 donc Net=
        # Brut, valeur source, pas une erreur de lecture) — probable
        # reprise de provision importante sur ce petit véhicule technique.
        # MCR(4000)>SCR(1932) — plancher absolu, comme Thémis. Recoupements
        # exacts : R1000(p509)=R0700(p518)=18 411 ; provisions_techniques=
        # best_estimate+marge_risque=R0510+R0600(p509)=11 474 ; R0100(p519)
        # =somme(R0010..R0070)=1632 ; R0220=R0100+R0130=1932=R0580(p518).
        "best_estimate": (11424.0, 509, "S.02.01.02.01 Bilan, somme 2 lignes non-nulles BE (R0540 non-vie + R0670 vie, sans primes cette année)"),
        "marge_risque": (50.0, 509, "S.02.01.02.01 Bilan, somme 2 lignes MR (R0550+R0680)"),
        "primes_acquises_brutes": (5554.0, 511, "S.05.01.02.01 (non-vie, seule activité avec primes), R0210/Total"),
        "charge_sinistres": (-939552.0, 511, "S.05.01.02.01, R0310/Total — NÉGATIF, vérifié (reprise de provision probable, pas une erreur)"),
        "fonds_propres_eligibles": (18411.0, 518, "S.23.01.01.01/R0540/Total"),
        "fonds_propres_t1_nr": (18411.0, 518, "S.23.01.01.01/R0540/Niveau1 non restreint"),
        "fonds_propres_t1_r": (0.0, 518, "S.23.01.01.01/R0540/Niveau1 restreint"),
        "fonds_propres_t2": (0.0, 518, "S.23.01.01.01/R0540/Niveau2"),
        "fonds_propres_t3": (0.0, 518, "S.23.01.01.01/R0540/Niveau3"),
        "scr_total": (1932.0, 518, "S.23.01.01.01/R0580 — confirmé p.519 (S.25.01.21.02/R0220)"),
        "mcr": (4000.0, 518, "S.23.01.01.01/R0600 — plancher absolu MCR (> SCR), cas légitime pour petite entité"),
        "ratio_scr": (953.0, 518, "S.23.01.01.01/R0620"),
        "ratio_mcr": (460.0, 518, "S.23.01.01.01/R0640"),
        "scr_marche": (1596.0, 519, "S.25.01.21.01/R0010"),
        "scr_contrepartie": (38.0, 519, "S.25.01.21.01/R0020"),
        "scr_souscription_vie": (0.0, 519, "S.25.01.21.01/R0030"),
        "scr_souscription_sante": (0.0, 519, "S.25.01.21.01/R0040"),
        "scr_souscription_nonvie": (91.0, 519, "S.25.01.21.01/R0050"),
        "scr_diversification": (-93.0, 519, "S.25.01.21.01/R0060"),
        "scr_operationnel": (300.0, 519, "S.25.01.21.02/R0130"),
    },
    "Aesio Mutuelle": {
        # Pages 523-538 (Décision 085). Plus grande entité traitée à ce
        # jour après Aéma Groupe/MACIF SAM. Mixte vie+non-vie+santé,
        # utilise le "Simplifications - life catastrophe risk" sur R0030
        # (formule standard simplifiée, pas un modèle interne). Recoupements
        # exacts : R1000(p524)=R0700(p534)=1 840 228 925 ; provisions_
        # techniques=best_estimate+marge_risque=R0510+R0600(p524)=
        # 601 102 714 (±1 arrondi) ; R0100(p535)=somme(R0010..R0070)=
        # 618 525 459 ; R0220=R0100+R0130+R0140=680 657 827≈R0580(p534,
        # ±1 arrondi).
        "best_estimate": (534971909.0, 524, "S.02.01.02.01 Bilan, somme 3 lignes BE (R0580+R0630+R0670)"),
        "marge_risque": (66130806.0, 524, "S.02.01.02.01 Bilan, somme 3 lignes MR (R0590+R0640+R0680)"),
        "primes_acquises_brutes": (1773403021.0, 526, "S.05.01.02.01(non-vie,R0210/Total=1707564110,p.526)+S.05.01.02.02(vie,R1510/Total=65838911,p.527)"),
        "charge_sinistres": (1325929044.0, 526, "S.05.01.02.01(non-vie,R0310/Total=1289307027,p.526)+S.05.01.02.02(vie,R1610/Total=36622017,p.527)"),
        "fonds_propres_eligibles": (1840228925.0, 534, "S.23.01.01.01/R0540/Total"),
        "fonds_propres_t1_nr": (1840228925.0, 534, "S.23.01.01.01/R0540/Niveau1 non restreint"),
        "fonds_propres_t1_r": (0.0, 534, "S.23.01.01.01/R0540/Niveau1 restreint"),
        "fonds_propres_t2": (0.0, 534, "S.23.01.01.01/R0540/Niveau2"),
        "fonds_propres_t3": (0.0, 534, "S.23.01.01.01/R0540/Niveau3"),
        "scr_total": (680657826.0, 534, "S.23.01.01.01/R0580 — confirmé p.535 (S.25.01.21.02/R0220, ±1 arrondi)"),
        "mcr": (170164457.0, 534, "S.23.01.01.01/R0600"),
        "ratio_scr": (270.0, 534, "S.23.01.01.01/R0620"),
        "ratio_mcr": (1081.0, 534, "S.23.01.01.01/R0640"),
        "scr_marche": (308698424.0, 535, "S.25.01.21.01/R0010"),
        "scr_contrepartie": (57851994.0, 535, "S.25.01.21.01/R0020"),
        "scr_souscription_vie": (30920506.0, 535, "S.25.01.21.01/R0030 (Simplification life catastrophe risk)"),
        "scr_souscription_sante": (428129823.0, 535, "S.25.01.21.01/R0040"),
        "scr_souscription_nonvie": (0.0, 535, "S.25.01.21.01/R0050"),
        "scr_diversification": (-207075288.0, 535, "S.25.01.21.01/R0060"),
        "scr_operationnel": (63580291.0, 535, "S.25.01.21.02/R0130"),
    },
    "MNPAF": {
        # Pages 539-550 (Décision 085). Entité 100% non-vie/santé (pas de
        # S.05.01.02.02 vie, BE/MR entièrement dans la branche santé
        # similaire non-vie R0580/R0590). Recoupements exacts : R1000
        # (p540)=R0700(p547)=97 481 243 ; R0510(p540)=R0580+R0590=
        # 6 589 213 ; R0100(p548)=somme(R0010..R0070)=30 660 653 ;
        # R0220=R0100+R0130=34 398 840≈R0580(p547, ±1 arrondi).
        "best_estimate": (4848587.0, 540, "S.02.01.02.01 Bilan, R0580 seul (santé similaire non-vie)"),
        "marge_risque": (1740626.0, 540, "S.02.01.02.01 Bilan, R0590 seul"),
        "primes_acquises_brutes": (124606250.0, 542, "S.05.01.02.01 (non-vie, seule activité), R0210/Total"),
        "charge_sinistres": (110861791.0, 542, "S.05.01.02.01 (non-vie, seule activité), R0310/Total"),
        "fonds_propres_eligibles": (97481243.0, 547, "S.23.01.01.01/R0540/Total"),
        "fonds_propres_t1_nr": (97481243.0, 547, "S.23.01.01.01/R0540/Niveau1 non restreint"),
        "fonds_propres_t1_r": (0.0, 547, "S.23.01.01.01/R0540/Niveau1 restreint"),
        "fonds_propres_t2": (0.0, 547, "S.23.01.01.01/R0540/Niveau2"),
        "fonds_propres_t3": (0.0, 547, "S.23.01.01.01/R0540/Niveau3"),
        "scr_total": (34398841.0, 547, "S.23.01.01.01/R0580 — confirmé p.548 (S.25.01.21.02/R0220, ±1 arrondi)"),
        "mcr": (8599710.0, 547, "S.23.01.01.01/R0600"),
        "ratio_scr": (283.0, 547, "S.23.01.01.01/R0620"),
        "ratio_mcr": (1134.0, 547, "S.23.01.01.01/R0640"),
        "scr_marche": (13467991.0, 548, "S.25.01.21.01/R0010"),
        "scr_contrepartie": (2485410.0, 548, "S.25.01.21.01/R0020"),
        "scr_souscription_vie": (0.0, 548, "S.25.01.21.01/R0030"),
        "scr_souscription_sante": (23428466.0, 548, "S.25.01.21.01/R0040"),
        "scr_souscription_nonvie": (0.0, 548, "S.25.01.21.01/R0050"),
        "scr_diversification": (-8721214.0, 548, "S.25.01.21.01/R0060"),
        "scr_operationnel": (3738187.0, 548, "S.25.01.21.02/R0130"),
    },
    # 5 entités restantes : bornes connues (ENTITES_BORNES ci-dessus),
    # extraction manuelle pas encore faite. Ne PAS deviner de valeurs —
    # absence délibérée de ces clés, traitée comme "non traité" par
    # calculer_score() ci-dessous, jamais comme un score de 0/20 (ce qui
    # laisserait croire à un vrai échec d'extraction plutôt qu'à un
    # travail non fait).
}

KPIS_IRREDUCTIBLES = set()  # aucun, les 2 entités faites utilisent la formule standard (aucune fusion)


def calculer_score(nom_entite):
    """Retourne (kpis_ok, total, statut) pour une entité. statut :
    'fait' si présente dans ENTITES_KPIS, 'non_traite' sinon. total=20 :
    les 20 KPIs lus manuellement (provisions_techniques calculé et
    resultat_technique NULL sont ajoutés automatiquement à l'insertion,
    cf. inserer_entite_en_base, pas comptés comme "lus" ici)."""
    if nom_entite not in ENTITES_KPIS:
        return None, None, "non_traite"
    kpis = ENTITES_KPIS[nom_entite]
    return len(kpis), 20, "fait"


def afficher_scores():
    print("=" * 90)
    print(f"{'Entité':28} {'Pages (orig.)':15} {'Score':8} {'Statut'}")
    print("=" * 90)
    for nom, (pd, pf) in ENTITES_BORNES.items():
        ok, total, statut = calculer_score(nom)
        score_str = f"{ok}/{total}" if statut == "fait" else "—"
        libelle_statut = "Fait (vérifié)" if statut == "fait" else "Non traité (bornes connues, à faire)"
        print(f"{nom:28} {f'{pd}-{pf}':15} {score_str:8} {libelle_statut}")
    print("=" * 90)
    n_fait = sum(1 for n in ENTITES_BORNES if n in ENTITES_KPIS)
    print(f"\n{n_fait}/13 entités traitées et vérifiées.")


def inserer_entite_en_base(nom_entite, db_path="kpis.db", year=2025, company_type="mutuelle (Aéma Groupe)"):
    """Insère une entité comme société séparée dans kpis.db, avec une
    note dans source_chapter indiquant sa provenance (document combiné
    Aéma Groupe + pages d'origine). Convertit K€ -> M€ (÷1000) pour les
    montants, laisse les ratios (déjà en points de %) inchangés — même
    convention que extract_kpis.py (cf. Décision 083)."""
    import sqlite3
    from kpi_definitions import KPI_DEFINITIONS

    if nom_entite not in ENTITES_KPIS:
        raise ValueError(f"{nom_entite!r} pas encore traitée (voir ENTITES_KPIS) — rien à insérer")

    pd, pf = ENTITES_BORNES[nom_entite]
    note_origine = (f"Document combiné 'Aéma Groupe RAPPORT UNIQUE...' (621p), "
                     f"entité isolée pages {pd}-{pf} (extraction manuelle sur rendu image, cf. Décision 083)")
    defs_par_nom = {d["kpi_name"]: d for d in KPI_DEFINITIONS}

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    row = conn.execute("SELECT id FROM companies WHERE name = ?", (nom_entite,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO companies (name, type, country) VALUES (?, ?, ?)",
                      (nom_entite, company_type, "France"))
        company_id = conn.execute("SELECT id FROM companies WHERE name = ?", (nom_entite,)).fetchone()[0]
    else:
        company_id = row[0]

    kpis_entite = dict(ENTITES_KPIS[nom_entite])
    # Complète les 22 KPIs (Décision 085) : les 20 déjà présents dans
    # ENTITES_KPIS ne couvrent pas provisions_techniques (calculable,
    # jamais lu directement sur une page) ni resultat_technique (NULL
    # par construction, cf. Décision 051) — les 2 manquaient pour
    # MACIF SAM/Aéma Groupe (Décision 083), corrigé ici pour toute
    # entité, rétroactivement incluses (ON CONFLICT DO UPDATE, idempotent).
    if "best_estimate" in kpis_entite and "marge_risque" in kpis_entite:
        be, page_be, _ = kpis_entite["best_estimate"]
        rm, _, _ = kpis_entite["marge_risque"]
        kpis_entite["provisions_techniques"] = (be + rm, page_be, "best_estimate + marge_risque")
    kpis_entite["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec Groupama/CNP)")

    lignes = []
    for kpi_name, (valeur_brute, source_page, note) in kpis_entite.items():
        d = defs_par_nom[kpi_name]
        if valeur_brute is None:
            valeur = None
        else:
            valeur = valeur_brute if d["unit"] == "pct" else valeur_brute / 1000.0
        conn.execute(
            """INSERT INTO kpis (company_id, year, category, kpi_name, value, unit, source_page, source_chapter, validated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
               ON CONFLICT(company_id, year, kpi_name) DO UPDATE SET
                 value=excluded.value, unit=excluded.unit,
                 source_page=excluded.source_page, source_chapter=excluded.source_chapter""",
            (company_id, year, d["category"], kpi_name, valeur, d["unit"], source_page,
             f"{note_origine} — {note}"),
        )
        lignes.append((kpi_name, valeur, d["unit"]))
    conn.commit()
    conn.close()
    return lignes


if __name__ == "__main__":
    afficher_scores()
