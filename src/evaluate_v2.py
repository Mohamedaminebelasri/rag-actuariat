"""Évaluation golden set complet (25 questions), dense ou hybrid_rerank,
avec reprise sur incident 429 (quota Groq).

Écrit de façon incrémentale dans eval_{mode}_{date}.md : Q / R / S / PASS-FAIL,
un bloc par question, dès que la réponse arrive (pas à la fin).

Sur 429 en cours de route : écrit un marqueur STOP dans le fichier avec la
commande exacte pour reprendre, puis s'arrête (résultats déjà écrits conservés).

Usage :
    python evaluate_v2.py --mode dense
    python evaluate_v2.py --mode hybrid_rerank
    python evaluate_v2.py --mode dense --resume 15 --file eval_dense_2026-07-17.md
    (--file requis avec --resume ; sans --resume, reprise auto détectée si le
     fichier du jour existe déjà et contient des blocs Q déjà écrits)

NE PAS LANCER sans accord explicite — quota Groq partagé, étalé sur plusieurs
jours (cf. CLAUDE.md, section llama3.2:3b).
"""
import argparse, io, re, sys, unicodedata, contextlib
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from rag import client, poser_question
from golden_set import GOLDEN
from openai import RateLimitError

PING_MODEL = "llama-3.3-70b-versatile"


def _fold(text):
    """minuscule + accents retirés, pour un matching de mots-clés robuste."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def ping_quota():
    """Appel minuscule pour vérifier que le quota Groq est disponible AVANT
    de lancer la boucle. Retourne True si OK, False si 429."""
    try:
        client.chat.completions.create(
            model=PING_MODEL,
            messages=[{"role": "user", "content": "Réponds uniquement par: ok"}],
            temperature=0,
            max_tokens=5,
        )
        return True
    except RateLimitError as e:
        print(f"PING ECHOUE (429) : {e}", file=sys.stderr)
        return False


def count_done(path):
    """Nombre de blocs Q{i} déjà écrits dans le fichier (pour l'auto-resume)."""
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"^Q\d+:", text, re.MULTILINE))


def evaluate_one(c, mode, k=5):
    """Lance poser_question (même pipeline que la prod), calcule PASS/FAIL,
    extrait les sources affichées. Retourne (r, sources_str, ok)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = poser_question(c["q"], k=k, mode=mode, verbose=True)
    printed = buf.getvalue()

    sources = re.findall(r"\[\d+\]\s+(.+?)\s+p\.(\S+)", printed)
    sources_str = "; ".join(f"{n.strip()} p.{p}" for n, p in sources) if sources else "(aucune source affichée)"

    refus = r.strip().lower().startswith("je ne trouve pas")
    ok = refus if c["a"] == "REFUSE" else (not refus and any(_fold(m) in _fold(r) for m in (c["m"] or [])))
    return r, sources_str, ok


def write_block(path, i, c, r, sources_str, ok):
    status = "PASS" if ok else "FAIL"
    block = f"---\nQ{i}: {c['q']}\nR{i}: {r}\nS{i}: {sources_str}\nPASS-FAIL{i}: {status}\n\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(block)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dense", "hybrid_rerank"], required=True)
    parser.add_argument("--resume", type=int, default=None,
                         help="index (1-based) de la question par laquelle reprendre")
    parser.add_argument("--file", type=str, default=None,
                         help="fichier à reprendre (sinon auto-généré eval_{mode}_{date}.md)")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    today = date.today().isoformat()
    out_path = Path(args.file) if args.file else ROOT / f"eval_{args.mode}_{today}.md"

    if args.resume:
        if not out_path.exists():
            print(f"erreur: --resume {args.resume} demandé mais {out_path} n'existe pas", file=sys.stderr)
            sys.exit(1)
        start_index = args.resume
    else:
        done = count_done(out_path)
        start_index = done + 1
        if done:
            print(f"reprise auto détectée : {done} question(s) déjà présentes dans {out_path}", file=sys.stderr)

    if start_index > len(GOLDEN):
        print(f"rien à faire : {start_index - 1} questions déjà écrites sur {len(GOLDEN)}", file=sys.stderr)
        return

    if not ping_quota():
        print("ARRÊT : quota indisponible (ping 429). Aucune question lancée.", file=sys.stderr)
        sys.exit(1)

    if not out_path.exists():
        out_path.write_text("", encoding="utf-8")

    for i, c in enumerate(GOLDEN, 1):
        if i < start_index:
            continue
        try:
            r, sources_str, ok = evaluate_one(c, args.mode, k=args.k)
        except RateLimitError as e:
            with open(out_path, "a", encoding="utf-8") as f:
                f.write(
                    f"---\nSTOP: 429 à la question {i} ({c['q']})\n{e}\n"
                    f"Reprendre avec : python evaluate_v2.py --mode {args.mode} "
                    f"--resume {i} --file {out_path.name}\n---\n"
                )
            print(f"[{i}/{len(GOLDEN)}] 429 — arrêt. Q1-Q{i-1} conservées dans {out_path}.", file=sys.stderr)
            sys.exit(1)

        write_block(out_path, i, c, r, sources_str, ok)
        print(f"[{i}/{len(GOLDEN)}] {'PASS' if ok else 'FAIL'}", file=sys.stderr)

    with open(out_path, "a", encoding="utf-8") as f:
        f.write(f"TERMINÉ : {len(GOLDEN)}/{len(GOLDEN)} questions ({args.mode}).\n")
    print(f"done -> {out_path}")


if __name__ == "__main__":
    main()
