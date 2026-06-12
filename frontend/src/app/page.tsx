"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CitationGraph } from "../components/CitationGraph";
import { Search, BookOpen, Network, Zap } from "lucide-react";
import axios from "axios";
import React from "react";

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

async function fetchRecommendations(query: string, method: string): Promise<Article[]> {
  const { data } = await axios.post(`${API_URL}/api/v1/recommendations/`, { query_text: query }, {
    params: { method, top_k: 15 },
  });
  return data;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [method, setMethod] = useState("hybrid");
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  const { data: recommendations, isLoading, error } = useQuery({
    queryKey: ["recommendations", submitted, method],
    queryFn: () => fetchRecommendations(submitted, method),
    enabled: !!submitted,
  });

  const graphNodes = recommendations ? [
    { id: "query", title: submitted, score: 1, citations: 0 },
    ...recommendations.map(r => ({
      id: r.article_id, title: r.title, score: r.score, citations: r.citations, year: r.year,
    })),
  ] : [];

  const graphLinks = recommendations ? recommendations.map(r => ({
    source: "query", target: r.article_id, weight: r.score,
  })) : [];

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 font-mono">
      <header className="border-b border-slate-800 px-8 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Network className="text-emerald-400" size={24} />
          <span className="text-xl font-bold tracking-tight text-emerald-400">PaperBridge</span>
          <span className="text-slate-500 text-sm">/ ranked paper recommendations</span>
        </div>
        <div className="flex gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1"><Zap size={12} /> FAISS ANN</span>
          <span className="flex items-center gap-1"><BookOpen size={12} /> Elasticsearch</span>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-8 py-10">
        <div className="mb-10">
          <h1 className="text-3xl font-bold mb-2 text-white">
            Discover Related Research
          </h1>
          <p className="text-slate-400 mb-6 text-sm">
            Semantic + keyword hybrid ranking using sentence-transformers and Elasticsearch
          </p>

          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && setSubmitted(query)}
                placeholder="e.g. attention mechanism transformer NLP..."
                className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-12 pr-4 py-3 text-sm
                           focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500
                           placeholder:text-slate-600 transition-colors"
              />
            </div>
            <select
              value={method}
              onChange={e => setMethod(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm
                         focus:outline-none focus:border-emerald-500 text-slate-300"
            >
              <option value="hybrid">Hybrid (RRF)</option>
              <option value="semantic">Semantic only</option>
              <option value="keyword">Keyword only</option>
            </select>
            <button
              onClick={() => setSubmitted(query)}
              disabled={!query.trim()}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed
                         text-white px-6 py-3 rounded-lg text-sm font-semibold transition-colors"
            >
              Search
            </button>
          </div>
        </div>

        {isLoading && (
          <div className="text-center py-20 text-slate-500">
            <div className="inline-block w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm">Running semantic search...</p>
          </div>
        )}

        {recommendations && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
            <div>
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Citation Graph
              </h2>
              <CitationGraph
                nodes={graphNodes}
                links={graphLinks}
                centerNodeId="query"
                onNodeClick={node => {
                  const article = recommendations.find(r => r.article_id === node.id);
                  if (article) setSelectedArticle(article);
                }}
              />
            </div>

            <div>
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Top {recommendations.length} Recommendations
              </h2>
              <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                {recommendations.map((article, i) => (
                  <div
                    key={article.article_id}
                    onClick={() => setSelectedArticle(article)}
                    className={`p-4 rounded-lg border cursor-pointer transition-all
                                ${selectedArticle?.article_id === article.article_id
                                  ? "border-emerald-500 bg-slate-800"
                                  : "border-slate-800 bg-slate-900 hover:border-slate-600"
                                }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white leading-snug mb-1 line-clamp-2">
                          {i + 1}. {article.title}
                        </p>
                        <p className="text-xs text-slate-500">
                          {article.authors.slice(0, 2).join(", ")}
                          {article.authors.length > 2 && " et al."}
                          {article.year && ` · ${article.year}`}
                          {article.venue && ` · ${article.venue}`}
                        </p>
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {article.keywords.slice(0, 3).map(kw => (
                            <span key={kw} className="text-xs bg-slate-800 text-emerald-400 px-2 py-0.5 rounded border border-slate-700">
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-emerald-400 font-bold text-sm">{(article.score * 100).toFixed(0)}%</div>
                        <div className="text-xs text-slate-600">{article.citations} cited</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {selectedArticle && (
          <div className="mt-8 p-6 bg-slate-900 border border-emerald-500/30 rounded-xl">
            <h3 className="font-bold text-white text-lg mb-2">{selectedArticle.title}</h3>
            {selectedArticle.abstract && (
              <p className="text-slate-400 text-sm leading-relaxed mb-4 line-clamp-4">
                {selectedArticle.abstract}
              </p>
            )}
            <div className="flex gap-4 text-xs text-slate-500">
              {selectedArticle.url && (
                <a href={selectedArticle.url} target="_blank" rel="noopener noreferrer"
                   className="text-emerald-400 hover:underline">View paper →</a>
              )}
              <span>Score: {selectedArticle.score.toFixed(4)}</span>
              <span>Method: {selectedArticle.method}</span>
              <span>{selectedArticle.citations} citations</span>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
