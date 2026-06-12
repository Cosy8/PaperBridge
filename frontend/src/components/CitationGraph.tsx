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
  onNodeClick?: (node: Node) => void;
}

export function CitationGraph({ nodes, links, centerNodeId, onNodeClick }: CitationGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
      .attr("viewBox", `0 0 ${width} ${height}`);

    const defs = svg.append("defs");
    const gradient = defs.append("radialGradient").attr("id", "node-gradient");
    gradient.append("stop").attr("offset", "0%").attr("stop-color", "#6ee7b7");
    gradient.append("stop").attr("offset", "100%").attr("stop-color", "#059669");

    const centerGradient = defs.append("radialGradient").attr("id", "center-gradient");
    centerGradient.append("stop").attr("offset", "0%").attr("stop-color", "#fbbf24");
    centerGradient.append("stop").attr("offset", "100%").attr("stop-color", "#d97706");

    const simulation = d3.forceSimulation(nodes as any)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(120).strength(0.5))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(40));

    const link = svg.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#334155")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", (d: any) => Math.sqrt(d.weight) * 2);

    const node = svg.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .on("click", (event, d) => onNodeClick?.(d))
      .call(d3.drag<any, any>()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      );

    node.append("circle")
      .attr("r", (d: any) => d.id === centerNodeId ? 28 : 18 + Math.sqrt(d.citations || 0) * 0.5)
      .attr("fill", (d: any) => d.id === centerNodeId ? "url(#center-gradient)" : "url(#node-gradient)")
      .attr("stroke", (d: any) => d.id === centerNodeId ? "#fbbf24" : "#6ee7b7")
      .attr("stroke-width", 2)
      .attr("filter", "drop-shadow(0 2px 8px rgba(0,0,0,0.4))");

    node.filter((d: any) => d.id !== centerNodeId)
      .append("circle")
      .attr("r", (d: any) => 18 + Math.sqrt(d.citations || 0) * 0.5 + 4)
      .attr("fill", "none")
      .attr("stroke", "#6ee7b7")
      .attr("stroke-width", 1)
      .attr("stroke-opacity", (d: any) => d.score);

    node.append("text")
      .attr("dy", (d: any) => (d.id === centerNodeId ? 44 : 34))
      .attr("text-anchor", "middle")
      .attr("fill", "#e2e8f0")
      .attr("font-size", "11px")
      .attr("font-family", "monospace")
      .text((d: any) => d.title.length > 28 ? d.title.slice(0, 28) + "…" : d.title);

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);
      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [nodes, links, centerNodeId, onNodeClick]);

  return (
    <svg
      ref={svgRef}
      className="w-full h-full bg-slate-900 rounded-xl"
      style={{ minHeight: "500px" }}
    />
  );
}
