import json
import re
import sys
import time

sys.path.insert(0, "src")
from rag import poser_question, _rechercher, expand_query  # noqa: E402

GOLDEN_PATH = "data/golden_set.jsonl"
OUTPUT_PATH = "data/eval_final_50.md"
K = 5
MODE = "dense"

CITATION_RE = re.compile(r"\[Article\s*(\d+)")


def load_golden_set():
    items = []
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        for line in f:
            items.append(json.loads(line))
    return items


def rang_retrieval(question, attendu, k):
    # même expansion d'acronymes que poser_question, pour mesurer le retrieval
    # tel qu'il est réellement utilisé (pas la requête brute)
    articles = _rechercher(expand_query(question), k)
    numeros = [a["numero_article"] for a in articles]
    if attendu in numeros:
        return numeros.index(attendu) + 1
    return None


def articles_cites(reponse):
    return [int(n) for n in CITATION_RE.findall(reponse)]


def poser_question_avec_retry(question, k, max_retries=3, base_wait=20):
    # poser_question -> appel_llm gère déjà le fallback Gemini->Mistral->Groq
    # en interne ; ce wrapper ne retente que si LA CHAÎNE ENTIÈRE a échoué.
    for tentative in range(max_retries):
        try:
            return poser_question(question, k=k, verbose=False, mode=MODE)
        except Exception as e:
            if tentative == max_retries - 1:
                raise
            attente = base_wait * (tentative + 1)
            print(f"  Chaîne de fallback épuisée (tentative {tentative + 1}/{max_retries}), attente {attente}s...")
            time.sleep(attente)


def main():
    golden = load_golden_set()
    print(f"Questions du golden set : {len(golden)}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("# Évaluation finale du système RAG complet (50 questions)\n\n")
        f.write(
            f"Golden set : `{GOLDEN_PATH}` ({len(golden)} questions). "
            f"Retrieval BGE-M3 mode=\"{MODE}\", k={K}. "
            f"Génération avec fallback Gemini -> Mistral -> Groq (Décision 012).\n\n"
        )
        f.write("## Résultats question par question\n\n")
        f.write("| id | question (30c) | attendu | rang retrieval | cité ? |\n")
        f.write("|---|---|---|---|---|\n")
        f.flush()

        resultats = []
        derniere_id_traitee = None

        for item in golden:
            qid = item["id"]
            question = item["question"]
            attendu = item["article_attendu"]

            try:
                rang = rang_retrieval(question, attendu, K)
                reponse = poser_question_avec_retry(question, K)
                cites = articles_cites(reponse)
                cite_ok = attendu in cites
                time.sleep(2)  # espacer les appels, limiter les 429
            except Exception as e:
                f.write(f"\n**INTERROMPU à la question id={qid}** : {e}\n")
                f.write(f"\nReprendre à partir de l'id {qid} (dernière id traitée avec succès : {derniere_id_traitee}).\n")
                f.flush()
                print(f"ERREUR à la question id={qid} : {e}")
                print(f"Reprendre à partir de l'id {qid}.")
                ecrire_metriques(f, resultats, len(golden), interrompu=True)
                return

            resultats.append({
                "id": qid, "question": question, "attendu": attendu,
                "rang": rang, "cite_ok": cite_ok, "cites": cites,
            })
            derniere_id_traitee = qid

            q30 = question[:30].replace("|", "-")
            rang_str = str(rang) if rang else "absent"
            cite_str = "Oui" if cite_ok else "Non"
            f.write(f"| {qid} | {q30} | {attendu} | {rang_str} | {cite_str} |\n")
            f.flush()

            print(f"id {qid} : rang={rang_str}, cité={cite_str}")

        ecrire_metriques(f, resultats, len(golden), interrompu=False)

    print(f"\nRésultat écrit dans {OUTPUT_PATH}")


def ecrire_metriques(f, resultats, n_total, interrompu):
    n = len(resultats)
    if n == 0:
        return

    recall_k = sum(1 for r in resultats if r["rang"] is not None)
    citation_ok = sum(1 for r in resultats if r["cite_ok"])
    mrr = sum((1 / r["rang"]) if r["rang"] else 0 for r in resultats) / n

    f.write(f"\n## Métriques finales ({'PARTIEL — ' if interrompu else ''}{n}/{n_total} questions traitées)\n\n")
    f.write("| Métrique | Valeur |\n")
    f.write("|---|---|\n")
    f.write(f"| Recall@{K} (retrieval) | {recall_k}/{n} ({recall_k/n:.3f}) |\n")
    f.write(f"| Citation correcte (génération) | {citation_ok}/{n} ({citation_ok/n:.3f}) |\n")
    f.write(f"| MRR (retrieval) | {mrr:.4f} |\n")

    echecs = [r for r in resultats if not r["cite_ok"]]
    f.write(f"\n## Échecs — article attendu non cité ({len(echecs)})\n\n")
    if echecs:
        for r in echecs:
            rang_str = str(r["rang"]) if r["rang"] else "absent"
            f.write(f"- id {r['id']} : \"{r['question']}\" (attendu Art. {r['attendu']}, "
                    f"rang retrieval : {rang_str}, articles cités dans la réponse : {r['cites']})\n")
    else:
        f.write("Aucun — toutes les réponses citent l'article attendu.\n")
    f.flush()

    print(f"\n=== MÉTRIQUES ({n}/{n_total} questions) ===")
    print(f"Recall@{K} retrieval : {recall_k}/{n} ({recall_k/n:.3f})")
    print(f"Citation correcte    : {citation_ok}/{n} ({citation_ok/n:.3f})")
    print(f"MRR retrieval         : {mrr:.4f}")
    print(f"\nÉchecs ({len(echecs)}) :")
    for r in echecs:
        rang_str = str(r["rang"]) if r["rang"] else "absent"
        print(f"  id {r['id']} : \"{r['question']}\" (attendu {r['attendu']}, rang {rang_str}, cités {r['cites']})")


if __name__ == "__main__":
    main()
