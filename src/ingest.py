import json
import re

import requests

EURLEX_URL = "http://publications.europa.eu/resource/uriserv/OJ.L_.2009.335.01.0001.01.FRA.xhtml"
EURLEX_HEADERS = {"Accept": "application/xhtml+xml"}
OUTPUT_PATH = "data/articles.jsonl"
SOURCE_LABEL = "directive 2009/138/CE (version 2009)"

TAG_RE = re.compile(r"<[^>]+>")
ARTICLE_START_RE = re.compile(r'<div class="eli-subdivision" id="art_\d+">')
NUMERO_RE = re.compile(r'id="art_(\d+)"')
TITRE_RE = re.compile(r'class="oj-sti-art">([^<]*)<')
ELI_TITLE_DIV_RE = re.compile(r'<div class="eli-title"[\s\S]*?</div>')
TI_ART_PARAGRAPH_RE = re.compile(r'<p[^>]*class="oj-ti-art"[^>]*>.*?</p>')


def fetch_html():
    response = requests.get(EURLEX_URL, headers=EURLEX_HEADERS, timeout=60)
    response.raise_for_status()
    return response.text


def strip_tags(html):
    text = TAG_RE.sub(" ", html)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_articles(html):
    starts = [m.start() for m in ARTICLE_START_RE.finditer(html)]
    starts.append(len(html))

    articles = []
    for i in range(len(starts) - 1):
        block = html[starts[i]:starts[i + 1]]

        numero = int(NUMERO_RE.search(block).group(1))

        titre_m = TITRE_RE.search(block)
        titre = titre_m.group(1).strip() if titre_m else ""

        corps_html = ELI_TITLE_DIV_RE.sub("", block, count=1)
        corps_html = TI_ART_PARAGRAPH_RE.sub("", corps_html, count=1)
        texte = strip_tags(corps_html)

        articles.append({"numero_article": numero, "titre": titre, "texte": texte})

    return articles


def save_articles(articles, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        for a in articles:
            record = {
                "numero_article": a["numero_article"],
                "titre": a["titre"],
                "texte": a["texte"],
                "source": SOURCE_LABEL,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


STOPWORDS_SHORT = {
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "ou", "en", "ne",
    "se", "ce", "on", "il", "ma", "ta", "sa", "mon", "ton", "son", "nos",
    "vos", "ses", "aux", "au", "y", "ni", "or", "où", "si", "tu", "tes",
    "mes", "ces", "est", "sont", "ont", "a", "par", "sur", "eux", "lui",
    "qui", "que", "qu", "dont", "dans", "sous", "vers", "chez", "car",
    "mais", "donc", "es", "ai", "as", "va", "vu", "à", "non", "pas", "vie",
    "fin", "an", "ans", "eu", "été", "dit", "dès", "tel", "sien",
}
BROKEN_WORD_RE = re.compile(
    r"\b([a-zàâäçéèêëîïôöùûüÿœ]{3,})\s([a-zàâäçéèêëîïôöùûüÿœ]{1,3})(?!['’ʼ])\b"
)
FOOTER_SIGNATURE_RE = re.compile(r"Journal officiel de l.Union européenne\s+\d{1,2}\.\d{1,2}\.\d{4}")


def broken_words(text):
    found = []
    for m in BROKEN_WORD_RE.finditer(text):
        a, b = m.group(1), m.group(2)
        if a.lower() in STOPWORDS_SHORT or b.lower() in STOPWORDS_SHORT:
            continue
        found.append(f"{a} {b}")
    return found


def reread_and_verify(output_path):
    articles = []
    with open(output_path, "r", encoding="utf-8") as f:
        for line in f:
            articles.append(json.loads(line))

    print(f"=== Nombre d'articles relus : {len(articles)} (cible 312) ===")

    titres_casses = [a["numero_article"] for a in articles if broken_words(a["titre"])]
    print(f"\nTitres avec espace parasite (\"techniqu es\") : {len(titres_casses)}")
    if titres_casses:
        print(f"  Numéros : {titres_casses}")

    naive_journal = [a["numero_article"] for a in articles if "Journal officiel" in a["texte"]]
    footer_signature = [a["numero_article"] for a in articles if FOOTER_SIGNATURE_RE.search(a["texte"])]
    print(f"\nMentions brutes de \"Journal officiel\" dans le corps : {len(naive_journal)} {naive_journal}")
    print("  (à vérifier : mention légitime dans le texte de loi, ou vrai pied de page collé ?)")
    print(f"Vrais pieds de page (motif \"Journal officiel ... JJ.MM.AAAA\" collé, comme dans le PDF) : {len(footer_signature)}")

    print("\n=== Exemples ===")
    for n in [45, 47, 77, 129]:
        a = next((x for x in articles if x["numero_article"] == n), None)
        if a is None:
            print(f"Article {n} : ABSENT")
            continue
        print(f"\nArticle {a['numero_article']} — titre = \"{a['titre']}\"")
        print(f"  corps (150 premiers caractères) : {a['texte'][:150]}")


def main():
    html = fetch_html()
    articles = parse_articles(html)
    print(f"=== Articles extraits du HTML EUR-Lex : {len(articles)} ===")

    save_articles(articles, OUTPUT_PATH)
    print(f"=== Écriture terminée dans {OUTPUT_PATH} ===\n")

    reread_and_verify(OUTPUT_PATH)


if __name__ == "__main__":
    main()
