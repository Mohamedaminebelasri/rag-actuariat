import os
import sys

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

st.set_page_config(page_title="Assistant Solvabilité II", page_icon="⚖️")

REFORMULATION_PROMPT = """Voici l'historique récent d'une conversation sur Solvabilité II, suivi
d'une nouvelle question qui peut faire référence au contexte précédent.

HISTORIQUE :
{historique}

NOUVELLE QUESTION : {question}

Reformule cette nouvelle question sous une forme autonome et complète, qui a
du sens sans le contexte de la conversation. Si elle est déjà autonome,
renvoie-la telle quelle. Réponds uniquement avec la question reformulée,
rien d'autre."""


@st.cache_resource(show_spinner="Chargement du modèle BGE-M3 et de l'index...")
def charger_rag():
    import rag
    rag._get_embedding_model()  # force le chargement immédiat (pas paresseux) au démarrage
    return rag


def reformuler_question(rag_module, historique, question):
    if not historique:
        return question

    historique_texte = "\n".join(
        f"{'Utilisateur' if m['role'] == 'user' else 'Assistant'} : {m['content']}"
        for m in historique
    )
    prompt = REFORMULATION_PROMPT.format(historique=historique_texte, question=question)

    # appel_llm gère seul le fallback Gemini -> Mistral (Décision 009) ; verbose=False
    # pour ne rien afficher côté utilisateur, la bascule reste visible en mode dev.
    return rag_module.appel_llm(prompt, taille="long", verbose=False).strip()


def message_erreur_pour(exception):
    err = str(exception)
    if "429" in err or "401" in err or "402" in err:
        return "Les fournisseurs LLM (Gemini et Mistral) sont actuellement indisponibles. Réessayez dans quelques instants."
    return f"Une erreur est survenue lors de la génération de la réponse : {err}"


def afficher_articles(articles):
    if not articles:
        return
    with st.expander("Articles consultés"):
        for a in articles:
            st.markdown(f"- **[Article {a['numero_article']}]** — {a['titre']}")


def nouvelle_conversation():
    st.session_state.messages = []


def main():
    rag_module = charger_rag()

    st.title("Assistant Solvabilité II")
    st.caption("312 articles · directive 2009/138/CE · réponses citées")
    st.info("Ne constitue pas un avis actuariel", icon="ℹ️")

    with st.sidebar:
        st.button("Nouvelle conversation", on_click=nouvelle_conversation, use_container_width=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            afficher_articles(msg.get("articles"))

    question = st.chat_input("Posez votre question sur Solvabilité II...")

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Recherche en cours..."):
                # ne garde que les ~5 derniers échanges (10 messages) pour la reformulation,
                # afin de ne pas saturer le contexte envoyé au LLM
                historique_recent = st.session_state.messages[:-1][-10:]

                try:
                    question_reformulee = reformuler_question(rag_module, historique_recent, question)
                except Exception:
                    question_reformulee = question

                try:
                    resultat = rag_module.poser_question(
                        question_reformulee, k=5, verbose=False, clarify=True
                    )

                    if isinstance(resultat, dict) and resultat.get("type") == "clarification":
                        reponse = resultat["message"]
                        articles = []
                    else:
                        reponse = resultat
                        articles = rag_module._rechercher(
                            rag_module.expand_query(question_reformulee), 5
                        )

                    st.markdown(reponse)
                    afficher_articles(articles)

                    st.session_state.messages.append(
                        {"role": "assistant", "content": reponse, "articles": articles}
                    )
                except Exception as e:
                    erreur = message_erreur_pour(e)
                    st.error(erreur)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": erreur, "articles": []}
                    )

    st.markdown("---")
    st.caption("Prototype — Mohamed Amine Belasri · Iconcilio · 2026")


if __name__ == "__main__":
    main()
