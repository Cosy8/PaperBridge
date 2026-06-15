"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";

interface Node {
  id: string;
  title: string;
  score: number;
  citations: number;
  year?: number;
}

interface Link {
  source: string;
  target: string;
  weight: number;
}

interface CitationGraphProps {
  nodes: Node[];
  links: Link[];
  centerNodeId: string;
  selectedId?: string;
  onNodeClick?: (node: Node) => void;
}

// Resolve a CSS custom property to a concrete color for SVG attributes.
function cssVar(name: string, fallback: string) {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export function CitationGraph({
  nodes,
  links,
  centerNodeId,
  selectedId,
  onNodeClick,
}: CitationGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const el = svgRef.current;
    if (!el || nodes.length === 0) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const accent = cssVar("--accent", "#2f9e6e");
    const accentInk = cssVar("--accent-ink", "#2a8862");
    const center = cssVar("--ink", "#2a2f38");
    const linkColor = cssVar("--border-strong", "#cfd4da");
    const labelColor = cssVar("--muted", "#5b626c");
    const surface = cssVar("--surface", "#ffffff");

    const width = el.clientWidth;
    const height = el.clientHeight;
    const pad = 24;

    d3.select(el).selectAll("*").remove();
    const svg = d3.select(el).attr("viewBox", `0 0 ${width} ${height}`);

    // Single zoom/pan layer so the whole graph stays reachable.
    const root = svg.append("g");

    const radius = (d: any) =>
      d.id === centerNodeId ? 20 : 9 + Math.sqrt(d.citations || 0) * 0.4;

    const link = root
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", linkColor)
      .attr("stroke-opacity", 0.9)
      .attr("stroke-width", (d: any) => 1 + Math.sqrt(d.weight) * 1.4);

    const node = root
      .append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .attr("tabindex", 0)
      .attr("role", "button")
      .attr("aria-label", (d: any) => d.title)
      .on("click", (_event, d) => onNodeClick?.(d))
      .on("keydown", (event: any, d) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onNodeClick?.(d);
        }
      });

    node
      .append("circle")
      .attr("r", radius)
      .attr("fill", (d: any) =>
        d.id === centerNodeId ? center : d.id === selectedId ? accentInk : accent,
      )
      .attr("fill-opacity", (d: any) =>
        d.id === centerNodeId ? 1 : 0.4 + d.score * 0.55,
      )
      .attr("stroke", surface)
      .attr("stroke-width", (d: any) => (d.id === selectedId ? 3 : 1.5));

    node
      .append("text")
      .attr("dy", (d: any) => radius(d) + 13)
      .attr("text-anchor", "middle")
      .attr("fill", labelColor)
      .attr("font-size", "10.5px")
      .attr("pointer-events", "none")
      .text((d: any) => (d.title.length > 22 ? d.title.slice(0, 22) + "…" : d.title));

    // Keep every node inside the visible frame so the graph never drifts off-canvas.
    const clamp = (d: any) => {
      const r = radius(d) + pad;
      d.x = Math.max(r, Math.min(width - r, d.x));
      d.y = Math.max(r, Math.min(height - r, d.y));
    };

    const simulation = d3
      .forceSimulation(nodes as any)
      .velocityDecay(0.55) // strong friction → no perpetual jitter
      .alphaDecay(0.06) // cools and stops quickly
      .force(
        "link",
        d3
          .forceLink(links)
          .id((d: any) => d.id)
          .distance(Math.min(width, height) / 3.2)
          .strength(0.8),
      )
      .force("charge", d3.forceManyBody().strength(-180).distanceMax(280))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((d: any) => radius(d) + 14).strength(0.9));

    // Drag: pin while held, release back to the simulation.
    node.call(
      d3
        .drag<any, any>()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.2).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = Math.max(0, Math.min(width, event.x));
          d.fy = Math.max(0, Math.min(height, event.y));
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }),
    );

    // Node visual size scales gently with zoom (k^0.45), decoupled from the
    // pan/zoom transform. Counter-scaling by 1/k keeps positions driven by the
    // root transform while each node grows when zoomed in and stays legible
    // when zoomed out. Labels live inside the group, so they scale too.
    let k = 1;
    const nodeScale = () => Math.pow(k, 0.45) / k;
    const placeNodes = () =>
      node.attr("transform", (d: any) => `translate(${d.x},${d.y}) scale(${nodeScale()})`);

    const ticked = () => {
      nodes.forEach(clamp);
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);
      placeNodes();
    };
    simulation.on("tick", ticked);

    if (reduceMotion) {
      // Settle instantly instead of animating into place.
      simulation.alpha(1).stop();
      for (let i = 0; i < 200; i++) simulation.tick();
      ticked();
    }

    // Pan + zoom so a dense graph is fully traversable.
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.4, 4])
      .on("zoom", (event) => {
        k = event.transform.k;
        root.attr("transform", event.transform.toString());
        placeNodes();
      });
    svg.call(zoom).on("dblclick.zoom", null);

    return () => {
      simulation.stop();
      svg.on(".zoom", null);
    };
  }, [nodes, links, centerNodeId, selectedId, onNodeClick]);

  return (
    <div className="relative h-full overflow-hidden rounded border border-border bg-surface">
      <svg
        ref={svgRef}
        role="img"
        aria-label="Force-directed citation graph of recommended papers. Drag to pan, scroll to zoom."
        className="h-full w-full touch-none"
      />
      <p className="pointer-events-none absolute bottom-2 right-3 text-xs text-faint">
        Scroll to zoom · drag to move
      </p>
    </div>
  );
}
