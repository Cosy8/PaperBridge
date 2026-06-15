"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CitationGraph } from "../components/CitationGraph";
import { Search, Network, ExternalLink, X } from "lucide-react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Article {
  article_id: string;
  title: string;
  abstract?: string;
  authors: string[];
  keywords: string[];
  year?: number;
  venue?: string;
  citations: number;
  url?: string;
  score: number;
  method: string;
}

const METHODS = [
  { value: "hybrid", label: "Hybrid" },
  { value: "semantic", label: "Semantic" },
  { value: "keyword", label: "Keyword" },
] as const;

async function fetchRecommendations(query: string, method: string): Promise<Article[]> {
  const { data } = await axios.post(
    `${API_URL}/api/v1/recommendations/`,
    { query_text: query },
    { params: { method, top_k: 15 } },
  );
  return data;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [method, setMethod] = useState("hybrid");
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  const { data: recommendations, isLoading, isError } = useQuery({
    queryKey: ["recommendations", submitted, method],
    queryFn: () => fetchRecommendations(submitted, method),
    enabled: !!submitted,
  });

  const graphNodes = recommendations
    ? [
        { id: "query", title: submitted, score: 1, citations: 0 },
        ...recommendations.map((r) => ({
          id: r.article_id,
          title: r.title,
          score: r.score,
          citations: r.citations,
          year: r.year,
        })),
      ]
    : [];

  const graphLinks = recommendations
    ? recommendations.map((r) => ({ source: "query", target: r.article_id, weight: r.score }))
    : [];

  return (
    <main className="min-h-screen bg-bg text-ink">
      <header className="sticky top-0 z-[100] border-b border-border bg-bg/85 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center gap-2.5 px-6 py-4">
          <span className="grid h-8 w-8 place-items-center rounded-sm bg-accent-soft text-accent-ink">
            <Network size={18} aria-hidden />
          </span>
          <span className="text-lg font-semibold tracking-tight">PaperBridge</span>
          <span className="hidden text-sm text-muted sm:inline">Related research, ranked</span>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-6 py-12">
        <section className="mx-auto max-w-2xl text-center">
          <h1 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Discover related research
          </h1>
          <p className="mx-auto mt-3 max-w-prose text-pretty text-muted">
            Enter a paper title or topic. PaperBridge blends semantic and keyword
            ranking to surface the work most relevant to it.
          </p>

          <form
            className="mt-8"
            onSubmit={(e) => {
              e.preventDefault();
              if (query.trim()) setSubmitted(query.trim());
            }}
          >
            <label htmlFor="query" className="sr-only">
              Search query
            </label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="relative flex-1">
                <Search
                  className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-faint"
                  size={18}
                  aria-hidden
                />
                <input
                  id="query"
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. attention mechanism transformer"
                  className="w-full rounded-sm border border-border bg-surface py-3 pl-11 pr-4 text-ink shadow-sm transition-colors placeholder:text-faint focus:border-accent focus:outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={!query.trim()}
                className="rounded-sm bg-accent px-6 py-3 font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-45"
              >
                Search
              </button>
            </div>

            <fieldset className="mt-4 flex items-center justify-center gap-1.5">
              <legend className="sr-only">Ranking method</legend>
              <span className="mr-1 text-sm text-muted">Method</span>
              <div className="inline-flex rounded-sm border border-border bg-surface p-0.5">
                {METHODS.map((m) => {
                  const active = method === m.value;
                  return (
                    <button
                      key={m.value}
                      type="button"
                      aria-pressed={active}
                      onClick={() => setMethod(m.value)}
                      className={`rounded-[6px] px-3.5 py-1.5 text-sm font-medium transition-colors ${
                        active
                          ? "bg-accent-soft text-accent-ink"
                          : "text-muted hover:text-ink"
                      }`}
                    >
                      {m.label}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          </form>
        </section>

        <div className="mt-12">
          {!submitted && <EmptyState />}

          {isLoading && <ResultsSkeleton />}

          {isError && (
            <p className="text-center text-muted" role="alert">
              Something went wrong fetching recommendations. Please try again.
            </p>
          )}

          {recommendations && recommendations.length === 0 && (
            <p className="text-center text-muted">
              No related papers found for <span className="text-ink">“{submitted}”</span>.
            </p>
          )}

          {selectedArticle && (
            <article className="mb-8 rounded border border-border bg-surface p-6 shadow-card">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h3 className="text-lg font-semibold leading-snug">{selectedArticle.title}</h3>
                  <p className="mt-1 text-sm text-muted">
                    {selectedArticle.authors.join(", ")}
                    {selectedArticle.year && ` · ${selectedArticle.year}`}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedArticle(null)}
                  aria-label="Close details"
                  className="shrink-0 rounded-sm p-1 text-faint transition-colors hover:bg-surface-2 hover:text-ink"
                >
                  <X size={18} aria-hidden />
                </button>
              </div>
              {selectedArticle.abstract && (
                <p className="mt-4 max-w-prose text-pretty leading-relaxed text-ink/90">
                  {selectedArticle.abstract}
                </p>
              )}
              <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted">
                {selectedArticle.url && (
                  <a
                    href={selectedArticle.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 font-medium text-accent-ink hover:underline"
                  >
                    View paper <ExternalLink size={14} aria-hidden />
                  </a>
                )}
                <span>Score {selectedArticle.score.toFixed(4)}</span>
                <span className="capitalize">Method · {selectedArticle.method}</span>
                <span>{selectedArticle.citations.toLocaleString()} citations</span>
              </div>
            </article>
          )}

          {recommendations && recommendations.length > 0 && (
            <div className="grid grid-cols-1 gap-8 lg:h-[600px] lg:grid-cols-[1fr_1.1fr]">
              <section aria-label="Citation graph" className="flex min-h-0 flex-col">
                <h2 className="mb-3 text-sm font-medium text-muted">Citation graph</h2>
                <div className="h-[440px] lg:h-auto lg:flex-1 lg:min-h-0">
                  <CitationGraph
                    nodes={graphNodes}
                    links={graphLinks}
                    centerNodeId="query"
                    selectedId={selectedArticle?.article_id}
                    onNodeClick={(node) => {
                      const article = recommendations.find((r) => r.article_id === node.id);
                      if (article) setSelectedArticle(article);
                    }}
                  />
                </div>
              </section>

              <section aria-label="Recommendations" className="flex min-h-0 flex-col">
                <h2 className="mb-3 text-sm font-medium text-muted" aria-live="polite">
                  {recommendations.length} recommendations
                </h2>
                <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
                  {recommendations.map((article, i) => {
                    const selected = selectedArticle?.article_id === article.article_id;
                    return (
                      <li key={article.article_id}>
                        <button
                          onClick={() => setSelectedArticle(article)}
                          aria-pressed={selected}
                          className={`w-full rounded text-left transition-colors ${
                            selected
                              ? "border border-accent bg-accent-soft"
                              : "border border-border bg-surface hover:border-border-strong"
                          } p-4`}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                              <p className="flex gap-2 text-[15px] font-medium leading-snug">
                                <span className="text-faint tabular-nums">{i + 1}.</span>
                                <span className="line-clamp-2">{article.title}</span>
                              </p>
                              <p className="mt-1 truncate text-sm text-muted">
                                {article.authors.slice(0, 2).join(", ")}
                                {article.authors.length > 2 && " et al."}
                                {article.year && ` · ${article.year}`}
                                {article.venue && ` · ${article.venue}`}
                              </p>
                              {article.keywords.length > 0 && (
                                <div className="mt-2 flex flex-wrap gap-1.5">
                                  {article.keywords.slice(0, 3).map((kw) => (
                                    <span
                                      key={kw}
                                      className="rounded-[6px] bg-surface-2 px-2 py-0.5 text-xs text-muted"
                                    >
                                      {kw}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="shrink-0 text-right">
                              <div className="font-semibold text-accent-ink tabular-nums">
                                {(article.score * 100).toFixed(0)}%
                              </div>
                              <div className="text-xs text-faint tabular-nums">
                                {article.citations.toLocaleString()} cited
                              </div>
                            </div>
                          </div>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function EmptyState() {
  const examples = ["contrastive learning", "diffusion models", "graph neural networks"];
  return (
    <div className="mx-auto max-w-md rounded border border-dashed border-border bg-surface-2 p-8 text-center">
      <span className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-accent-soft text-accent-ink">
        <Network size={20} aria-hidden />
      </span>
      <p className="mt-4 font-medium">Start with a topic or paper</p>
      <p className="mx-auto mt-1 max-w-prose text-sm text-muted">
        Results show a ranked list alongside a citation graph you can explore.
      </p>
      <div className="mt-4 flex flex-wrap justify-center gap-1.5 text-sm text-muted">
        <span>Try:</span>
        {examples.map((ex) => (
          <span key={ex} className="text-accent-ink">
            {ex}
          </span>
        ))}
      </div>
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_1.1fr]" aria-hidden>
      <div className="h-[500px] animate-pulse rounded border border-border bg-surface-2" />
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-[88px] animate-pulse rounded border border-border bg-surface-2"
          />
        ))}
      </div>
    </div>
  );
}
