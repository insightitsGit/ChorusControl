/** Interactive SVG visuals driven by /api/v1/pipelines/live data.
 *  Palette is read from CSS custom properties so visuals follow the
 *  light/dark theme. Motion is decorative-but-meaningful: packets travel
 *  in the direction of data flow; pulses mark live nodes.
 */
(function (global) {
  const REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function palette() {
    const s = getComputedStyle(document.documentElement);
    const v = (name, fb) => (s.getPropertyValue(name) || "").trim() || fb;
    return {
      ok: v("--ok", "#1a7a4c"),
      bad: v("--bad", "#b42318"),
      active: v("--accent", "#0b6e6a"),
      accent2: v("--accent-2", "#1a8f88"),
      idle: v("--viz-idle", "#9aa3b2"),
      ink: v("--ink", "#14181f"),
      muted: v("--muted", "#6b7585"),
      line: v("--viz-line", "#c5ceda"),
      paper: v("--surface", "#ffffff"),
      soft: v("--accent-soft", "#e8f3f2"),
      GREEN: v("--green", "#1a7a4c"),
      BLUE: v("--blue", "#1f5f8a"),
      ORANGE: v("--orange", "#9a5b12"),
    };
  }

  let uid = 0;

  function el(tag, attrs = {}, children = []) {
    const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    children.forEach((c) => n.appendChild(typeof c === "string" ? document.createTextNode(c) : c));
    return n;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  /** Shared defs: flow gradient + soft glow filter. Returns ids. */
  function makeDefs(svg, C) {
    const id = ++uid;
    const gradId = `ccflow${id}`;
    const glowId = `ccglow${id}`;
    const grad = el("linearGradient", { id: gradId, x1: "0%", y1: "0%", x2: "100%", y2: "0%" }, [
      el("stop", { offset: "0%", "stop-color": C.active, "stop-opacity": "0.35" }),
      el("stop", { offset: "50%", "stop-color": C.accent2, "stop-opacity": "1" }),
      el("stop", { offset: "100%", "stop-color": C.active, "stop-opacity": "0.35" }),
    ]);
    const glow = el("filter", { id: glowId, x: "-60%", y: "-60%", width: "220%", height: "220%" }, [
      el("feGaussianBlur", { stdDeviation: "2.4", result: "b" }),
      el("feMerge", {}, [el("feMergeNode", { in: "b" }), el("feMergeNode", { in: "SourceGraphic" })]),
    ]);
    svg.appendChild(el("defs", {}, [grad, glow]));
    return { gradId, glowId };
  }

  /** Traveling packet dots along an SVG path (direction = data flow). */
  function addPackets(svg, pathD, C, glowId, { count = 3, dur = 2.6, r = 3 } = {}) {
    if (REDUCED) return;
    for (let i = 0; i < count; i++) {
      const dot = el("circle", {
        r: String(r),
        fill: C.accent2,
        opacity: "0.9",
        filter: `url(#${glowId})`,
      });
      const anim = el("animateMotion", {
        dur: `${dur}s`,
        repeatCount: "indefinite",
        begin: `${(dur / count) * i}s`,
        path: pathD,
        rotate: "auto",
      });
      dot.appendChild(anim);
      svg.appendChild(dot);
    }
  }

  /** Horizontal execution pipeline: Guard → Ledger → Shine */
  function renderExecutionPipeline(container, execution, opts = {}) {
    clear(container);
    const C = palette();
    const stages = execution?.stages || [];
    const w = container.clientWidth || opts.width || 640;
    const h = opts.height || 140;
    const pad = 28;
    const svg = el("svg", {
      viewBox: `0 0 ${w} ${h}`,
      width: "100%",
      height: String(h),
      class: "viz-svg",
      role: "img",
      "aria-label": "Execution pipeline Guard to Ledger to Shine",
    });

    if (!stages.length) {
      svg.appendChild(
        el("text", { x: w / 2, y: h / 2, "text-anchor": "middle", fill: C.muted, "font-size": "13" }, [
          "No pipeline data yet — seed a trace",
        ])
      );
      container.appendChild(svg);
      return svg;
    }

    const { gradId, glowId } = makeDefs(svg, C);
    const gap = (w - pad * 2) / Math.max(stages.length - 1, 1);
    const cy = h / 2;
    const nodes = stages.map((s, i) => ({ ...s, x: pad + i * gap, y: cy }));

    const pathD = nodes.map((n, i) => `${i ? "L" : "M"} ${n.x} ${n.y}`).join(" ");
    svg.appendChild(
      el("path", {
        d: pathD,
        fill: "none",
        stroke: C.line,
        "stroke-width": "3",
        "stroke-linecap": "round",
      })
    );
    svg.appendChild(
      el("path", {
        d: pathD,
        fill: "none",
        stroke: `url(#${gradId})`,
        "stroke-width": "3",
        "stroke-linecap": "round",
        class: "viz-flow-stroke",
        "stroke-dasharray": "10 14",
      })
    );
    addPackets(svg, pathD, C, glowId, { count: Math.min(4, nodes.length), dur: 3 });

    nodes.forEach((n, i) => {
      const status = n.status || "idle";
      const fill =
        status === "ok" ? C.ok : status === "bad" ? C.bad : status === "active" ? C.active : C.idle;
      const selectable = typeof opts.onSelect === "function";
      const g = el("g", {
        class: "viz-node" + (selectable ? " is-interactive" : ""),
        style: selectable ? "cursor:pointer" : "cursor:default",
        "data-id": n.id || "",
      });
      g.appendChild(
        el("circle", { cx: n.x, cy: n.y, r: "18", fill: C.paper, stroke: fill, "stroke-width": "3" })
      );
      g.appendChild(
        el("circle", { cx: n.x, cy: n.y, r: "6", fill: fill, class: status === "active" ? "viz-pulse" : "" })
      );
      g.appendChild(
        el(
          "text",
          {
            x: n.x,
            y: n.y - 28,
            "text-anchor": "middle",
            fill: C.ink,
            "font-size": "13",
            "font-weight": "700",
            "font-family": "Syne, DM Sans, sans-serif",
          },
          [n.label || n.id]
        )
      );
      const detail = n.decision || n.gate || "";
      if (detail) {
        g.appendChild(
          el(
            "text",
            {
              x: n.x,
              y: n.y + 36,
              "text-anchor": "middle",
              fill: C.muted,
              "font-size": "11",
              "font-family": "DM Sans, sans-serif",
            },
            [String(detail).slice(0, 22)]
          )
        );
      }
      if (selectable) {
        g.addEventListener("click", () => {
          opts.onSelect(n, i);
          container.querySelectorAll(".viz-node").forEach((x) => x.classList.remove("is-selected"));
          g.classList.add("is-selected");
        });
      }
      svg.appendChild(g);
    });

    container.appendChild(svg);
    return svg;
  }

  /** Fleet topology — mother hub with orbit ring + heartbeat links */
  function renderFleetTopology(container, fleet, opts = {}) {
    clear(container);
    const C = palette();
    const items = fleet || [];
    const w = container.clientWidth || opts.width || 640;
    const h = opts.height || 220;
    const svg = el("svg", {
      viewBox: `0 0 ${w} ${h}`,
      width: "100%",
      height: String(h),
      class: "viz-svg",
      "aria-label": "Fleet topology",
    });
    const { glowId } = makeDefs(svg, C);

    const hx = w / 2;
    const hy = h / 2;
    const radius = Math.min(w, h) * 0.34;

    // orbit ring (decorative, marks the agent belt)
    svg.appendChild(
      el("circle", {
        cx: hx,
        cy: hy,
        r: String(radius),
        fill: "none",
        stroke: C.line,
        "stroke-width": "1",
        "stroke-dasharray": "3 7",
        class: "viz-orbit",
        opacity: "0.8",
      })
    );

    // mother hub — clickable when onSelectMother provided
    const motherSelectable = typeof opts.onSelectMother === "function";
    const motherG = el("g", {
      class: "viz-node" + (motherSelectable ? " is-interactive" : ""),
      style: motherSelectable ? "cursor:pointer" : "cursor:default",
    });
    motherG.appendChild(
      el("circle", {
        cx: hx,
        cy: hy,
        r: "34",
        fill: C.soft,
        stroke: C.active,
        "stroke-width": "2",
        filter: `url(#${glowId})`,
      })
    );
    motherG.appendChild(
      el(
        "text",
        { x: hx, y: hy + 4, "text-anchor": "middle", fill: C.active, "font-size": "11", "font-weight": "700" },
        ["Mother"]
      )
    );
    if (motherSelectable) {
      motherG.addEventListener("click", () => opts.onSelectMother({ kind: "mother", label: "Mother" }));
    }
    svg.appendChild(motherG);

    if (!items.length) {
      svg.appendChild(
        el("text", { x: hx, y: hy + 58, "text-anchor": "middle", fill: C.muted, "font-size": "12" }, [
          "No agents — enroll from Admin",
        ])
      );
      container.appendChild(svg);
      return svg;
    }

    items.forEach((n, i) => {
      const angle = (Math.PI * 2 * i) / items.length - Math.PI / 2;
      const x = hx + Math.cos(angle) * radius;
      const y = hy + Math.sin(angle) * radius;
      const color = C[n.color] || C.GREEN;
      svg.appendChild(
        el("line", {
          x1: hx,
          y1: hy,
          x2: x,
          y2: y,
          stroke: n.online ? color : C.line,
          "stroke-width": n.online ? "2" : "1.5",
          "stroke-dasharray": n.online ? "0" : "4 4",
          class: n.online ? "viz-link-live" : "",
        })
      );
      // heartbeat packet: node → mother (telemetry direction)
      if (n.online) {
        addPackets(svg, `M ${x} ${y} L ${hx} ${hy}`, { ...C, accent2: color }, glowId, {
          count: 1,
          dur: 2 + (i % 3) * 0.6,
          r: 2.5,
        });
      }

      const selectable = typeof opts.onSelect === "function";
      const g = el("g", {
        class: "viz-node" + (selectable ? " is-interactive" : ""),
        style: selectable ? "cursor:pointer" : "cursor:default",
      });
      g.appendChild(
        el("circle", { cx: x, cy: y, r: "16", fill: C.paper, stroke: color, "stroke-width": "2.5" })
      );
      if (n.online) g.appendChild(el("circle", { cx: x + 11, cy: y - 11, r: "4", fill: color, class: "viz-pulse" }));
      g.appendChild(
        el(
          "text",
          { x: x, y: y + 32, "text-anchor": "middle", fill: C.ink, "font-size": "11", "font-weight": "600" },
          [String(n.label || n.id).slice(0, 14)]
        )
      );
      g.appendChild(
        el("text", { x: x, y: y + 44, "text-anchor": "middle", fill: C.muted, "font-size": "10" }, [
          n.role || "worker",
        ])
      );
      if (selectable) g.addEventListener("click", () => opts.onSelect(n));
      svg.appendChild(g);
    });

    container.appendChild(svg);
    return svg;
  }

  /** Force-ish asset graph (deterministic layout from data) */
  function renderAssetGraph(container, graph, opts = {}) {
    clear(container);
    const C = palette();
    const nodes = graph?.nodes || [];
    const edges = graph?.edges || [];
    const w = container.clientWidth || opts.width || 640;
    const h = opts.height || 280;
    const svg = el("svg", {
      viewBox: `0 0 ${w} ${h}`,
      width: "100%",
      height: String(h),
      class: "viz-svg",
      "aria-label": "Asset graph",
    });

    if (!nodes.length) {
      svg.appendChild(
        el("text", { x: w / 2, y: h / 2, "text-anchor": "middle", fill: C.muted, "font-size": "13" }, [
          "Asset graph empty — join agents to sync",
        ])
      );
      container.appendChild(svg);
      return svg;
    }

    const kinds = [...new Set(nodes.map((n) => n.kind))];
    const pos = {};
    nodes.forEach((n) => {
      const ki = kinds.indexOf(n.kind);
      const col = kinds.length ? ki : 0;
      const inKind = nodes.filter((x) => x.kind === n.kind);
      const row = inKind.indexOf(n);
      const x = 60 + (col + 0.5) * ((w - 80) / Math.max(kinds.length, 1));
      const y = 40 + row * Math.min(48, (h - 60) / Math.max(inKind.length, 1));
      pos[n.id] = { x, y, ...n };
    });

    edges.forEach((e) => {
      const a = pos[e.source];
      const b = pos[e.target];
      if (!a || !b) return;
      svg.appendChild(
        el("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: C.line, "stroke-width": "1.5" })
      );
    });

    Object.values(pos).forEach((n) => {
      const selectable = typeof opts.onSelect === "function";
      const g = el("g", {
        class: "viz-node" + (selectable ? " is-interactive" : ""),
        style: selectable ? "cursor:pointer" : "cursor:default",
      });
      const fill =
        n.kind === "organization"
          ? C.active
          : n.kind === "agent"
            ? C.BLUE
            : n.kind === "policy"
              ? C.ORANGE
              : C.ok;
      g.appendChild(el("circle", { cx: n.x, cy: n.y, r: "10", fill: fill, opacity: "0.9" }));
      g.appendChild(
        el("text", { x: n.x + 14, y: n.y + 4, fill: C.ink, "font-size": "11", "font-weight": "600" }, [
          String(n.label).slice(0, 18),
        ])
      );
      if (selectable) g.addEventListener("click", () => opts.onSelect(n));
      svg.appendChild(g);
    });

    container.appendChild(svg);
    return svg;
  }

  /** Cascade step pipeline */
  function renderCascade(container, cascade, opts = {}) {
    if (!cascade) {
      clear(container);
      const C = palette();
      const w = container.clientWidth || 640;
      const svg = el("svg", { viewBox: `0 0 ${w} 80`, width: "100%", height: "80" });
      svg.appendChild(
        el("text", { x: w / 2, y: 42, "text-anchor": "middle", fill: C.muted, "font-size": "12" }, [
          "No correction cascade yet — resolve a memory conflict",
        ])
      );
      container.appendChild(svg);
      return;
    }
    renderExecutionPipeline(
      container,
      {
        stages: (cascade.steps || []).map((s) => ({
          id: s.id,
          label: s.label,
          decision: cascade.state,
          status: s.status === "ok" || s.status === "done" ? "ok" : "active",
        })),
      },
      { ...opts, height: 120 }
    );
  }

  global.CCViz = {
    renderExecutionPipeline,
    renderFleetTopology,
    renderAssetGraph,
    renderCascade,
  };
})(window);
