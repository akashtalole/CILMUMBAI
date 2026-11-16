import { useState } from "react";
import { api, type GraphNode, type SourcePage } from "../api";
import { useLang } from "../lang";

/** A small "source" chip under a fact. Opens to show the quote, the document and its tier (constitution C3). */
export function Source({ node }: { node: GraphNode | null | undefined }) {
  const { t } = useLang();
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState<SourcePage | null>(null);
  if (!node?.source || !node.page) return null;
  const toggle = () => {
    setOpen(!open);
    if (!page && node.source && node.page) api.source(node.source, node.page).then(setPage).catch(() => undefined);
  };
  return (
    <span className="source">
      <button type="button" className="source-chip" onClick={toggle} aria-expanded={open}>
        <span className={`tier-dot tier-${node.tier ?? "reported"}`} aria-hidden />
        {t.source}
      </button>
      {open && (
        <span className="source-card" role="note">
          {node.quote && (
            <>
              <span className="source-label">{t.quote}</span>
              <q>{node.quote}</q>
            </>
          )}
          <span className="source-meta">
            {page ? t.sourceOf(page.publisher, node.page) : `${node.source.slice(0, 12)}…, p. ${node.page}`}
            {" · "}
            {t.tier[node.tier ?? "reported"] ?? node.tier}
          </span>
          {page?.licence && <span className="source-meta subtle">{page.licence}</span>}
        </span>
      )}
    </span>
  );
}
