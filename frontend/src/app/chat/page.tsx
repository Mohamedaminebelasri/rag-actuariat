"use client";

import { MessageSquare, Send, ShieldAlert, Sparkles } from "lucide-react";
import { useState } from "react";

const suggestions = [
  "Quel est le ratio de solvabilité SCR de Groupama en 2024 ?",
  "Comment les fonds propres éligibles ont-ils évolué ?",
  "Quels sont les principaux risques identifiés dans le SFCR ?",
  "Résumez la politique de gestion des risques de Groupama.",
];

export default function ChatPage() {
  const [query, setQuery] = useState("");

  return (
    <div className="flex flex-col h-full">
      {/* Bannière maintenance */}
      <div className="mx-4 mt-4 flex items-center gap-3 rounded-[10px] border border-red-300 bg-red-50 px-4 py-3 dark:border-red-500/30 dark:bg-red-950/40">
        <ShieldAlert className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
        <p className="text-sm font-medium text-red-700 dark:text-red-300">
          Fonctionnalité en cours de développement — le chat RAG n&apos;est pas encore opérationnel.
        </p>
      </div>

      {/* Empty state */}
      <div className="flex-1 flex items-center justify-center">
        <div className="max-w-xl w-full px-6 text-center">
          <div className="w-14 h-14 rounded-2xl bg-accent-light flex items-center justify-center mx-auto mb-6">
            <MessageSquare className="w-7 h-7 text-accent" />
          </div>
          <h2 className="font-heading text-3xl text-text-primary mb-2">
            Interrogez les rapports SFCR
          </h2>
          <p className="text-text-secondary text-sm mb-8">
            Posez vos questions sur les rapports de solvabilité. Les réponses
            sont sourcées et vérifiables.
          </p>

          {/* Suggestion chips */}
          <div className="flex flex-wrap gap-2 justify-center">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => setQuery(s)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full
                  text-xs text-text-secondary bg-surface border border-border
                  hover:border-accent hover:text-accent hover:bg-accent-light
                  transition-colors cursor-pointer"
              >
                <Sparkles className="w-3 h-3" />
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Input bar */}
      <div className="border-t border-border bg-surface px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-3 bg-background border border-border rounded-[var(--radius-lg)] px-4 py-3 focus-within:border-accent focus-within:shadow-[0_0_0_3px_rgba(37,99,235,0.1)] transition-all">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Posez votre question sur les rapports SFCR..."
              className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-tertiary outline-none"
            />
            <button
              className="w-8 h-8 rounded-[var(--radius-md)] bg-accent hover:bg-accent-hover text-accent-foreground
                flex items-center justify-center transition-colors disabled:opacity-40"
              disabled={!query.trim()}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="text-[10px] text-text-tertiary mt-2 text-center">
            Les réponses sont générées par IA à partir des documents SFCR
            indexés. Vérifiez toujours les sources.
          </p>
        </div>
      </div>
    </div>
  );
}
