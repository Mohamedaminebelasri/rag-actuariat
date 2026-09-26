"use client";

import {
  ChevronRight,
  ChevronDown,
  FileText,
  Building2,
  FolderClosed,
  ArrowRight,
  ArrowLeft,
  Info,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import kpiSources from "@/data/kpi-sources.json";

// Un nœud "narrative" est une sous-section de chapitre SFCR (A.1, B.3,
// C.7, ...) dont le contenu textuel n'a jamais été extrait — seuls les
// KPIs des annexes QRT l'ont été. Un nœud "qrt" est le PDF QRT source,
// déjà exploitable. "chapter"/"company" sont des nœuds de regroupement
// sans contenu propre (dépliables uniquement).
type NodeType = "company" | "chapter" | "narrative" | "qrt";

type TreeNode = {
  label: string;
  type: NodeType;
  children?: TreeNode[];
  pageCount?: number;
};

const sfcrTree: TreeNode[] = [
  {
    label: "Groupama",
    type: "company",
    children: [
      {
        label: "A. Activité et résultats",
        type: "chapter",
        children: [
          { label: "A.1 Activité", type: "narrative" },
          { label: "A.2 Résultats de souscription", type: "narrative" },
          { label: "A.3 Résultats des investissements", type: "narrative" },
          { label: "A.4 Résultats des autres activités", type: "narrative" },
          { label: "A.5 Autres informations", type: "narrative" },
        ],
      },
      {
        label: "B. Système de gouvernance",
        type: "chapter",
        children: [
          { label: "B.1 Informations générales", type: "narrative" },
          { label: "B.2 Compétences et honorabilité", type: "narrative" },
          { label: "B.3 Système de gestion des risques", type: "narrative" },
          { label: "B.4 ORSA", type: "narrative" },
          { label: "B.5 Contrôle interne", type: "narrative" },
          { label: "B.6 Fonction d'audit interne", type: "narrative" },
          { label: "B.7 Fonction actuarielle", type: "narrative" },
          { label: "B.8 Sous-traitance", type: "narrative" },
        ],
      },
      {
        label: "C. Profil de risque",
        type: "chapter",
        children: [
          { label: "C.1 Risque de souscription", type: "narrative" },
          { label: "C.2 Risque de marché", type: "narrative" },
          { label: "C.3 Risque de crédit", type: "narrative" },
          { label: "C.4 Risque de liquidité", type: "narrative" },
          { label: "C.5 Risque opérationnel", type: "narrative" },
          { label: "C.6 Autres risques importants", type: "narrative" },
          { label: "C.7 Autres informations", type: "narrative" },
        ],
      },
      {
        label: "D. Valorisation à des fins de solvabilité",
        type: "chapter",
        children: [
          { label: "D.1 Actifs", type: "narrative" },
          { label: "D.2 Provisions techniques", type: "narrative" },
          { label: "D.3 Autres passifs", type: "narrative" },
          { label: "D.4 Méthodes de valorisation alternatives", type: "narrative" },
        ],
      },
      {
        label: "E. Gestion du capital",
        type: "chapter",
        children: [
          { label: "E.1 Fonds propres", type: "narrative" },
          { label: "E.2 SCR et MCR", type: "narrative" },
          { label: "E.3 Durée du modèle interne", type: "narrative" },
          { label: "E.4 Non-conformité", type: "narrative" },
        ],
      },
      { label: "Annexes QRT", type: "qrt", pageCount: 15 },
    ],
  },
];

// Association KPI -> libellé lisible, pour le message "vous cherchiez
// peut-être : ...". Tenue à part de kpi-sources.json (qui vient tel
// quel de kpis.db) pour ne pas mélanger données et présentation.
const KPI_LABELS: Record<string, string> = {
  ratio_scr: "Ratio SCR",
  ratio_mcr: "Ratio MCR",
  fonds_propres_eligibles: "Fonds propres éligibles",
  best_estimate: "Best Estimate",
  scr_total: "SCR total",
  mcr: "MCR",
};

type KpiSource = {
  value: number;
  unit: string;
  year: number;
  source_page: number | null;
  source_chapter: string | null;
};

type KpiSources = Record<string, Record<string, KpiSource>>;

const typedKpiSources = kpiSources as KpiSources;

type SelectedNode = {
  node: TreeNode;
  company: string;
  path: string[];
};

function findQrtNodeForCompany(company: string): TreeNode | null {
  const companyNode = sfcrTree.find((n) => n.label === company);
  const qrt = companyNode?.children?.find((n) => n.type === "qrt");
  return qrt ?? null;
}

function TreeItem({
  node,
  company,
  path,
  depth = 0,
  selectedPath,
  onSelect,
}: {
  node: TreeNode;
  company: string;
  path: string[];
  depth?: number;
  selectedPath: string[] | null;
  onSelect: (sel: SelectedNode) => void;
}) {
  const [isOpen, setIsOpen] = useState(depth < 2);
  const hasChildren = !!node.children && node.children.length > 0;
  const currentPath = [...path, node.label];
  const isSelected =
    !!selectedPath &&
    selectedPath.length === currentPath.length &&
    selectedPath.every((p, i) => p === currentPath[i]);

  const handleClick = () => {
    if (hasChildren) {
      setIsOpen(!isOpen);
    }
    if (node.type === "narrative" || node.type === "qrt") {
      onSelect({ node, company, path: currentPath });
    }
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-2 text-sm rounded-[var(--radius-sm)] hover:bg-surface-hover transition-colors text-left",
          depth === 0 && "font-medium text-text-primary",
          depth > 0 && "text-text-secondary",
          isSelected && "bg-accent-light text-accent font-medium"
        )}
        style={{ paddingLeft: `${depth * 16 + 12}px` }}
      >
        {hasChildren ? (
          isOpen ? (
            <ChevronDown className="w-3.5 h-3.5 text-text-tertiary flex-shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-text-tertiary flex-shrink-0" />
          )
        ) : node.type === "qrt" ? (
          <FolderClosed className="w-3.5 h-3.5 text-text-tertiary flex-shrink-0" />
        ) : (
          <FileText className="w-3.5 h-3.5 text-text-tertiary flex-shrink-0" />
        )}
        {depth === 0 && (
          <Building2 className="w-4 h-4 text-accent flex-shrink-0" />
        )}
        <span className="flex-1 truncate">{node.label}</span>
        {node.pageCount && (
          <span className="text-[10px] text-text-tertiary bg-surface-secondary px-1.5 py-0.5 rounded">
            {node.pageCount}p
          </span>
        )}
      </button>
      {hasChildren && isOpen && (
        <div>
          {node.children!.map((child, i) => (
            <TreeItem
              key={i}
              node={child}
              company={company}
              path={currentPath}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function NarrativeEmptyState({
  selected,
  onNavigateToQrt,
}: {
  selected: SelectedNode;
  onNavigateToQrt: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-96 text-center">
      <div className="w-14 h-14 rounded-2xl bg-surface-secondary flex items-center justify-center mb-4">
        <Info className="w-7 h-7 text-text-tertiary" />
      </div>
      <h3 className="font-heading text-xl text-text-primary mb-2">
        {selected.node.label}
      </h3>
      <p className="text-sm text-text-secondary max-w-sm mb-1">
        Cette section n&apos;est pas encore traitée.
      </p>
      <p className="text-xs text-text-tertiary max-w-sm mb-6">
        Le contenu narratif des chapitres SFCR (A à E) n&apos;a pas été
        extrait — seuls les KPIs des annexes QRT le sont, pour{" "}
        {selected.company}.
      </p>
      <button
        onClick={onNavigateToQrt}
        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-[var(--radius-md)] bg-accent text-accent-foreground text-sm font-medium hover:opacity-90 transition-opacity"
      >
        Voir les Annexes QRT
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}

function QrtView({
  selected,
  targetPage,
  targetKpi,
}: {
  selected: SelectedNode;
  targetPage: number | null;
  targetKpi: string | null;
}) {
  const kpiLabel = targetKpi ? KPI_LABELS[targetKpi] ?? targetKpi : null;
  return (
    <div className="flex flex-col items-center justify-center h-96 text-center">
      <div className="w-14 h-14 rounded-2xl bg-accent-light flex items-center justify-center mb-4">
        <FolderClosed className="w-7 h-7 text-accent" />
      </div>
      <h3 className="font-heading text-xl text-text-primary mb-2">
        {selected.node.label} — {selected.company}
      </h3>
      {targetPage ? (
        <p className="text-sm text-text-secondary max-w-md mb-1">
          {kpiLabel ? (
            <>
              Donnée recherchée : <strong>{kpiLabel}</strong> — page{" "}
              <strong>{targetPage}</strong> du PDF source.
            </>
          ) : (
            <>Page {targetPage} du PDF source.</>
          )}
        </p>
      ) : (
        <p className="text-sm text-text-secondary max-w-sm mb-1">
          {selected.node.pageCount} pages — tableaux QRT (S.02, S.05,
          S.23, S.25, S.28...) déjà extraits et vérifiés.
        </p>
      )}
      <p className="text-xs text-text-tertiary max-w-sm mt-4">
        Visualisation du PDF source à intégrer ici.
      </p>
    </div>
  );
}

export default function DocumentsPage() {
  const [selected, setSelected] = useState<SelectedNode | null>(null);
  const [targetPage, setTargetPage] = useState<number | null>(null);
  const [targetKpi, setTargetKpi] = useState<string | null>(null);

  // Arrivée depuis un autre onglet (ex. Analyse) avec ?company=...&kpi=...
  // -> saute directement sur le nœud Annexes QRT de la bonne entreprise,
  // à la bonne page si connue via kpis.db (source_page). Lu directement
  // depuis window.location plutôt que useSearchParams() : ce hook
  // nécessite un <Suspense>, et sur ce projet l'effet qui en dépend ne
  // se déclenchait pas de façon fiable au chargement direct de l'URL
  // (?company=...&kpi=...) — reproduit en dev, y compris après un vrai
  // F5, indépendamment du outil de navigation utilisé pour tester.
  // window.location.search en lecture directe est plus simple et fiable
  // ici, au prix de ne pas re-déclencher sur un changement de query
  // string SANS démontage du composant (cas marginal : navigation
  // client Documents -> Documents avec juste ?kpi= différent).
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const company = params.get("company");
    const kpi = params.get("kpi");
    if (!company) return;

    const qrtNode = findQrtNodeForCompany(company);
    if (!qrtNode) return;

    setSelected({ node: qrtNode, company, path: [company, qrtNode.label] });
    if (kpi) {
      setTargetKpi(kpi);
      const page = typedKpiSources[company]?.[kpi]?.source_page ?? null;
      setTargetPage(page);
    }
  }, []);

  const selectedPath = useMemo(() => selected?.path ?? null, [selected]);

  const handleSelect = (sel: SelectedNode) => {
    setSelected(sel);
    if (sel.node.type !== "qrt") {
      setTargetPage(null);
      setTargetKpi(null);
    }
  };

  const handleNavigateToQrt = () => {
    if (!selected) return;
    const qrtNode = findQrtNodeForCompany(selected.company);
    if (!qrtNode) return;
    setSelected({
      node: qrtNode,
      company: selected.company,
      path: [selected.company, qrtNode.label],
    });
    setTargetPage(null);
    setTargetKpi(null);
  };

  return (
    <div className="flex h-full">
      {/* Document tree sidebar */}
      <div
        className={`${selected ? "hidden md:block" : "block"} w-full md:w-80 md:flex-shrink-0 border-r border-border bg-surface overflow-auto`}
      >
        <div className="px-4 py-4 border-b border-border">
          <h3 className="font-heading text-lg text-text-primary">Documents</h3>
          <p className="text-xs text-text-tertiary mt-0.5">
            Navigation par chapitre SFCR
          </p>
        </div>
        <div className="py-2">
          {sfcrTree.map((node, i) => (
            <TreeItem
              key={i}
              node={node}
              company={node.label}
              path={[]}
              selectedPath={selectedPath}
              onSelect={handleSelect}
            />
          ))}
        </div>
      </div>

      {/* Document content viewer */}
      <div className={`${selected ? "block" : "hidden md:block"} flex-1 overflow-auto`}>
        <div className="max-w-4xl mx-auto px-4 sm:px-8 py-6 sm:py-8">
          {selected && (
            <button
              onClick={() => setSelected(null)}
              className="md:hidden mb-4 inline-flex items-center gap-1.5 text-sm text-accent hover:underline"
            >
              <ArrowLeft className="w-4 h-4" />
              Retour aux chapitres
            </button>
          )}
          {!selected && (
            <div className="flex flex-col items-center justify-center h-96 text-center">
              <div className="w-14 h-14 rounded-2xl bg-surface-secondary flex items-center justify-center mb-4">
                <FileText className="w-7 h-7 text-text-tertiary" />
              </div>
              <h3 className="font-heading text-xl text-text-primary mb-2">
                Sélectionnez un chapitre
              </h3>
              <p className="text-sm text-text-secondary max-w-sm">
                Choisissez un chapitre dans l&apos;arborescence pour afficher
                son contenu extrait avec les tableaux de données associés.
              </p>
            </div>
          )}
          {selected && selected.node.type === "narrative" && (
            <NarrativeEmptyState
              selected={selected}
              onNavigateToQrt={handleNavigateToQrt}
            />
          )}
          {selected && selected.node.type === "qrt" && (
            <QrtView
              selected={selected}
              targetPage={targetPage}
              targetKpi={targetKpi}
            />
          )}
        </div>
      </div>
    </div>
  );
}
