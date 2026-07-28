# Expérimentation abandonnée (migration Hugging Face Spaces / ZeroGPU non
# retenue, on est passé à un déploiement VM Oracle Cloud) — app.py (Streamlit)
# est la version active. Conservé pour historique, requirements.txt ne le
# supporte plus (gradio/spaces retirés).

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import gradio as gr
import spaces

import rag  # rag.py inchangé : BGE-M3 dense, FAISS, expand_query, clarifier,
            # fallback Gemini->Mistral->Groq (voir Décisions 001-015)

# Chargement du modèle d'embedding UNE SEULE FOIS, au niveau module, avant
# toute fonction décorée @spaces.GPU. Requis par ZeroGPU : les modèles
# doivent être placés sur cuda au chargement, pas paresseusement à l'intérieur
# d'une fonction @spaces.GPU (voir doc HF ZeroGPU, section "Model loading").
rag._get_embedding_model()

REFORMULATION_PROMPT = """Voici l'historique récent d'une conversation sur Solvabilité II, suivi
d'une nouvelle question qui peut faire référence au contexte précédent.

HISTORIQUE :
{historique}

NOUVELLE QUESTION : {question}

Reformule cette nouvelle question sous une forme autonome et complète, qui a
du sens sans le contexte de la conversation. Si elle est déjà autonome,
renvoie-la telle quelle. Réponds uniquement avec la question reformulée,
rien d'autre."""

EXEMPLES = [
    "Comment calcule-t-on le MCR ?",
    "Qu'est-ce que l'ORSA ?",
    "Comment sont calculées les provisions techniques ?",
    "En quoi consiste l'audit interne ?",
]


def reformuler_question(historique_texte, question):
    if not historique_texte:
        return question
    prompt = REFORMULATION_PROMPT.format(historique=historique_texte, question=question)
    try:
        # appel_llm gère seul le fallback Gemini -> Mistral -> Groq (Décision 012),
        # aucun besoin de GPU ici (juste des appels API texte).
        return rag.appel_llm(prompt, taille="long", verbose=False).strip()
    except Exception:
        return question


@spaces.GPU(duration=90)
def _repondre_gpu(question_reformulee, k):
    # Regroupé dans une seule fonction @spaces.GPU pour ne consommer qu'un
    # seul créneau ZeroGPU par tour de conversation (retrieval + génération).
    resultat = rag.poser_question(question_reformulee, k=k, verbose=False, clarify=True)

    if isinstance(resultat, dict) and resultat.get("type") == "clarification":
        return resultat["message"], []

    articles = rag._rechercher(rag.expand_query(question_reformulee), k)
    return resultat, articles


def message_erreur_pour(exception):
    err = str(exception)
    if any(code in err for code in ("429", "401", "402", "400", "403")):
        return "Les fournisseurs LLM (Gemini, Mistral, Groq) sont actuellement indisponibles. Réessayez dans quelques instants."
    return f"Une erreur est survenue lors de la génération de la réponse : {err}"


def repondre(message, historique_precedent):
    # historique_precedent : liste de {"role": "user"|"assistant", "content": str},
    # SANS le message qu'on est en train de traiter (cf. on_submit).
    historique_texte = "\n".join(
        f"{'Utilisateur' if m['role'] == 'user' else 'Assistant'} : {m['content']}"
        for m in historique_precedent[-10:]  # ~5 derniers échanges, comme app.py
    )

    try:
        question_reformulee = reformuler_question(historique_texte, message)
    except Exception:
        question_reformulee = message

    try:
        reponse, articles = _repondre_gpu(question_reformulee, 5)
    except Exception as e:
        return message_erreur_pour(e)

    if articles:
        sources_md = "\n".join(
            f"- **[Article {a['numero_article']}]** — {a['titre']}" for a in articles
        )
        reponse = f"{reponse}\n\n<details><summary>📚 Articles consultés</summary>\n\n{sources_md}\n\n</details>"

    return reponse


def on_submit(message, historique):
    if not message or not message.strip():
        return historique, ""
    historique_avant = historique
    reponse = repondre(message, historique_avant)
    nouvel_historique = historique_avant + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reponse},
    ]
    return nouvel_historique, ""


def nouvelle_conversation():
    return [], ""


with gr.Blocks(title="Assistant Solvabilité II") as demo:
    gr.Markdown("# Assistant Solvabilité II")
    gr.Markdown("312 articles · directive 2009/138/CE · réponses citées")
    gr.Markdown("> ℹ️ Ne constitue pas un avis actuariel")

    chatbot = gr.Chatbot(height=500, label=None, show_label=False)

    with gr.Row():
        msg = gr.Textbox(
            placeholder="Posez votre question sur Solvabilité II...",
            show_label=False,
            scale=8,
        )
        envoyer_btn = gr.Button("Envoyer 📤", scale=1)

    with gr.Row():
        nouvelle_btn = gr.Button("🔄 Nouvelle conversation")

    gr.Examples(examples=EXEMPLES, inputs=msg)

    # Entrée (PC) et clic sur le bouton (utile sur mobile, sans touche Entrée
    # dédiée) appellent tous deux on_submit, pour ne pas dupliquer la logique.
    msg.submit(on_submit, [msg, chatbot], [chatbot, msg], api_name="chat")
    envoyer_btn.click(on_submit, [msg, chatbot], [chatbot, msg])
    nouvelle_btn.click(nouvelle_conversation, None, [chatbot, msg])

    gr.Markdown("---")
    gr.Markdown("Prototype — Mohamed Amine Belasri · Iconcilio · 2026")


if __name__ == "__main__":
    demo.launch()
