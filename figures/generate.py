#!/usr/bin/env python3
"""
effector-bench figure generator.

Reads results/{latest.json} and tier-b/results/{latest.json},
produces publication-quality figures in figures/out/.

Color palette aligned to brand-kit/colors.md:
  Primary:   Claw Red #E03E3E — all effector data
  Secondary: Signal Orange #F27A3A — positive delta labels, ≥85% bars
  Neutral:   Ash #9CA3AF — baseline data
  Warning:   Amber #F59E0B — <85% bars, caution

Usage:
    python3 figures/generate.py            # generate all
    python3 figures/generate.py --dpi 200  # custom DPI
"""

import json
import os
import sys
import argparse
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

# ── Paths ────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIER_A_JSON = os.path.join(ROOT, "results", "latest.json")
TIER_B_JSON = os.path.join(ROOT, "tier-b", "results", "latest.json")
OUT_DIR = os.path.join(ROOT, "figures", "out")

# ── Brand palette (from brand-kit/colors.md) ─────────────────────────
CLAW_RED      = "#E03E3E"   # Primary — marks things that matter
SIGNAL_ORANGE = "#F27A3A"   # Secondary — interaction, progress
CHARCOAL      = "#1A1A1A"   # Primary dark background
SLATE         = "#6B7280"   # Secondary text
ASH           = "#9CA3AF"   # Muted / disabled / baseline
STONE         = "#D1D5DB"   # Light borders
BONE          = "#F5F0EB"   # Light background
AMBER         = "#F59E0B"   # Semantic: warning
CLAW_RED_DARK = "#B91C1C"   # Error bar whisker color

# Custom sequential colormap: Bone → Signal Orange → Claw Red
BRAND_CMAP = LinearSegmentedColormap.from_list(
    "effector",
    [BONE, "#F9D4B0", SIGNAL_ORANGE, "#E85A3A", CLAW_RED, "#A02020"],
    N=256,
)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.15,
})


def load_json(path):
    with open(path) as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════
# Figure 1: Tier A — Category Score Breakdown (horizontal bar)
# ═══════════════════════════════════════════════════════════════════════
def fig_tier_a_categories(a, dpi):
    cats = a["categories"]
    names  = [c["label"] for c in cats]
    scores = [c["score"] for c in cats]
    counts = [f'{c["passed"]}/{c["cases"]}' for c in cats]

    fig, ax = plt.subplots(figsize=(7.5, 3.2))

    y = np.arange(len(names))
    # Brand: Claw Red for 100%, Signal Orange for ≥85%, Amber for <85%
    colors = [CLAW_RED if s == 100 else (AMBER if s < 85 else SIGNAL_ORANGE) for s in scores]

    bars = ax.barh(y, scores, height=0.55, color=colors, edgecolor="white", linewidth=0.5)

    for i, (bar, s, ct) in enumerate(zip(bars, scores, counts)):
        if s > 30:
            ax.text(s - 1.5, i, f"{s}%", ha="right", va="center",
                    color="white", fontweight="bold", fontsize=10)
        else:
            ax.text(s + 1, i, f"{s}%", ha="left", va="center",
                    color=colors[i], fontweight="bold", fontsize=10)
        ax.text(101, i, ct, ha="left", va="center", color=SLATE, fontsize=9)

    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlim(0, 115)
    ax.set_xlabel("Accuracy (%)")
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(mticker.MultipleLocator(25))
    ax.axvline(x=100, color=BONE, linewidth=0.8, zorder=0)

    overall = a["score"]
    ax.set_title(f"Tier A \u2014 Toolchain Accuracy    overall {overall}%  ({a['totalPassed']}/{a['totalCases']} cases)",
                 loc="left", pad=10)

    legend_elems = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor=CLAW_RED, markersize=8, label="100%"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=SIGNAL_ORANGE, markersize=8, label="\u226585%"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=AMBER, markersize=8, label="<85%"),
    ]
    ax.legend(handles=legend_elems, loc="lower right", frameon=False, fontsize=9)

    fig.savefig(os.path.join(OUT_DIR, "tier-a-categories.png"), dpi=dpi)
    plt.close(fig)
    print("  \u2713 tier-a-categories.png")


# ═══════════════════════════════════════════════════════════════════════
# Figure 2: Tier B — Dimension Comparison (grouped bar)
# ═══════════════════════════════════════════════════════════════════════
def fig_tier_b_dimensions(b, dpi):
    dim_keys = [
        ("functionSelection",   "D1\nFunction\nSelection"),
        ("parameterExtraction", "D2\nParameter\nExtraction"),
        ("compositionSafety",   "D3\nComposition\nSafety"),
        ("safetyPermissions",   "D4\nSafety &\nPermissions"),
        ("schemaCompleteness",  "D5\nSchema\nCompleteness"),
    ]

    dim_class = ["comparable", "comparable", "differential", "differential", "comparable"]

    agg = b["aggregated"]
    baseline_vals = [agg[k]["baseline"]["mean"] for k, _ in dim_keys]
    effector_vals = [agg[k]["effector"]["mean"] for k, _ in dim_keys]
    baseline_std  = [agg[k]["baseline"]["stdDev"] for k, _ in dim_keys]
    effector_std  = [agg[k]["effector"]["stdDev"] for k, _ in dim_keys]

    fig, ax = plt.subplots(figsize=(8.5, 4.5))

    x = np.arange(len(dim_keys))
    w = 0.32

    ax.bar(x - w/2, baseline_vals, w, label="Baseline MCP",
           color=ASH, edgecolor="white", linewidth=0.5,
           yerr=baseline_std, capsize=3, error_kw={"linewidth": 1, "color": SLATE})
    ax.bar(x + w/2, effector_vals, w, label="effector",
           color=CLAW_RED, edgecolor="white", linewidth=0.5,
           yerr=effector_std, capsize=3, error_kw={"linewidth": 1, "color": CLAW_RED_DARK})

    # Delta labels — Signal Orange for positive
    for i, (bv, ev) in enumerate(zip(baseline_vals, effector_vals)):
        delta = ev - bv
        sign = "+" if delta >= 0 else ""
        color = SIGNAL_ORANGE if delta > 0 else CLAW_RED
        ax.text(x[i] + w/2, ev + effector_std[i] + 3, f"{sign}{delta}",
                ha="center", va="bottom", fontsize=9, fontweight="bold", color=color)

    # Shade differential dimensions
    for i, cls in enumerate(dim_class):
        if cls == "differential":
            ax.axvspan(i - 0.45, i + 0.45, alpha=0.06, color=CLAW_RED, zorder=0)

    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in dim_keys], fontsize=9)
    ax.set_ylabel("Score (0\u2013100)")
    ax.set_ylim(0, 115)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(25))
    ax.legend(loc="upper left", frameon=False)

    ax.text(3, 108, "shaded = differential (effector-only capabilities)",
            fontsize=8, color=SLATE, ha="center", style="italic")

    ax.set_title("Tier B \u2014 Schema Quality: Baseline MCP vs effector (n = 10 tools)",
                 loc="left", pad=10)

    fig.savefig(os.path.join(OUT_DIR, "tier-b-dimensions.png"), dpi=dpi)
    plt.close(fig)
    print("  \u2713 tier-b-dimensions.png")


# ═══════════════════════════════════════════════════════════════════════
# Figure 3: Tier B — Per-Tool Delta Heatmap (brand colormap)
# ═══════════════════════════════════════════════════════════════════════
def fig_tier_b_heatmap(b, dpi):
    tools = b["tools"]
    dim_keys = ["functionSelection", "parameterExtraction", "compositionSafety",
                "safetyPermissions", "schemaCompleteness"]
    dim_short = ["D1: Func\nSelect", "D2: Param\nExtract", "D3: Comp\nSafety",
                 "D4: Safety\nPerms", "D5: Schema\nComplete"]

    tool_names = [t["id"] for t in tools]
    matrix = np.zeros((len(tools), len(dim_keys)))
    for i, t in enumerate(tools):
        for j, dk in enumerate(dim_keys):
            matrix[i, j] = t["effector"][dk] - t["baseline"][dk]

    fig, ax = plt.subplots(figsize=(7.5, 5.5))

    vmin, vmax = matrix.min(), matrix.max()
    if vmin < 0:
        from matplotlib.colors import TwoSlopeNorm
        norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
        cmap = "RdBu_r"
    else:
        norm = None
        cmap = BRAND_CMAP

    im = ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto",
                   vmin=max(vmin, 0), vmax=vmax)

    for i in range(len(tools)):
        for j in range(len(dim_keys)):
            val = int(matrix[i, j])
            color = "white" if val > 45 else CHARCOAL
            sign = "+" if val > 0 else ""
            ax.text(j, i, f"{sign}{val}", ha="center", va="center",
                    fontsize=9, color=color, fontweight="bold" if val > 30 else "normal")

    ax.set_xticks(np.arange(len(dim_keys)))
    ax.set_xticklabels(dim_short, fontsize=9)
    ax.set_yticks(np.arange(len(tools)))
    ax.set_yticklabels(tool_names, fontsize=9)

    ax.set_title("Tier B \u2014 Per-Tool Score Delta (effector \u2212 baseline)", loc="left", pad=10)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("\u0394 Score", fontsize=10)

    fig.savefig(os.path.join(OUT_DIR, "tier-b-heatmap.png"), dpi=dpi)
    plt.close(fig)
    print("  \u2713 tier-b-heatmap.png")


# ═══════════════════════════════════════════════════════════════════════
# Figure 4: Tier B — Comparable vs Differential Summary
# ═══════════════════════════════════════════════════════════════════════
def fig_tier_b_summary(b, dpi):
    agg = b["aggregated"]

    fig, axes = plt.subplots(1, 3, figsize=(9, 3.5))

    groups = [
        ("Comparable\n(D1, D2, D5)", "comparableAvg"),
        ("Differential\n(D3, D4)", "differentialAvg"),
        ("Combined\nOverall", "overall"),
    ]

    for ax, (label, key) in zip(axes, groups):
        bm = agg[key]["baseline"]["mean"]
        em = agg[key]["effector"]["mean"]
        delta = em - bm

        bars = ax.bar(["Baseline", "effector"], [bm, em],
                      color=[ASH, CLAW_RED], width=0.5,
                      edgecolor="white", linewidth=0.5)

        for bar, val in zip(bars, [bm, em]):
            ax.text(bar.get_x() + bar.get_width()/2, val + 2,
                    str(val), ha="center", va="bottom", fontweight="bold", fontsize=12)

        # Delta label — Signal Orange
        sign = "+" if delta > 0 else ""
        ax.annotate(f"{sign}{delta}", xy=(1, em + 8),
                    fontsize=14, fontweight="bold", ha="center",
                    color=SIGNAL_ORANGE)

        ax.set_ylim(0, 100)
        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.yaxis.set_major_locator(mticker.MultipleLocator(25))
        ax.spines["left"].set_visible(True)

    fig.suptitle("Tier B \u2014 Aggregate Deltas by Metric Class", fontsize=13,
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "tier-b-summary.png"), dpi=dpi)
    plt.close(fig)
    print("  \u2713 tier-b-summary.png")


# ═══════════════════════════════════════════════════════════════════════
# Figure 5: Tier B — D2 Parameter Extraction Detail (dumbbell chart)
# ═══════════════════════════════════════════════════════════════════════
def fig_tier_b_d2_detail(b, dpi):
    tools = b["tools"]
    dim_key = "parameterExtraction"

    tool_names = [t["id"] for t in tools]
    baseline   = [t["baseline"][dim_key] for t in tools]
    effector   = [t["effector"][dim_key] for t in tools]
    deltas     = [e - bl for bl, e in zip(baseline, effector)]

    # Sort by delta descending
    order = np.argsort(deltas)[::-1]
    tool_names = [tool_names[i] for i in order]
    baseline   = [baseline[i] for i in order]
    effector   = [effector[i] for i in order]
    deltas     = [deltas[i] for i in order]

    fig, ax = plt.subplots(figsize=(7.5, 4))

    y = np.arange(len(tool_names))
    for i in range(len(tool_names)):
        # Brand: Claw Red for improvement, Amber for regression
        color = CLAW_RED if deltas[i] > 0 else AMBER
        ax.plot([baseline[i], effector[i]], [i, i], color=color, linewidth=2, zorder=1)
        ax.scatter(baseline[i], i, color=ASH, s=60, zorder=2, edgecolors="white", linewidths=0.5)
        ax.scatter(effector[i], i, color=color, s=60, zorder=2, edgecolors="white", linewidths=0.5)

        sign = "+" if deltas[i] >= 0 else ""
        ax.text(max(baseline[i], effector[i]) + 3, i,
                f"{sign}{deltas[i]}", va="center", fontsize=9,
                color=SIGNAL_ORANGE, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(tool_names, fontsize=9)
    ax.set_xlabel("D2: Parameter Extraction Score")
    ax.set_xlim(-5, 110)
    ax.invert_yaxis()

    legend_elems = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ASH, markersize=8, label="Baseline MCP"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=CLAW_RED, markersize=8, label="effector"),
    ]
    ax.legend(handles=legend_elems, loc="lower right", frameon=False, fontsize=9)

    agg_delta = b["aggregated"][dim_key]["delta"]
    ax.set_title(f"D2 Parameter Extraction \u2014 type catalog expansion (\u0394+{agg_delta} avg)",
                 loc="left", pad=10)

    ax.text(0.02, -0.10,
            "Grounded in: BFCL + API-Bank (Li et al., ACL 2023)\n"
            "Compiler expands interface input types into JSON Schema properties via type catalog.",
            transform=ax.transAxes, fontsize=8, color=SLATE, va="top")

    fig.savefig(os.path.join(OUT_DIR, "tier-b-d2-detail.png"), dpi=dpi)
    plt.close(fig)
    print("  \u2713 tier-b-d2-detail.png")


# ═══════════════════════════════════════════════════════════════════════
# Figure 6: Combined overview (compact, for org README)
# ═══════════════════════════════════════════════════════════════════════
def fig_overview_compact(a, b, dpi):
    """A single compact figure showing both tiers side-by-side."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8),
                                    gridspec_kw={"width_ratios": [1, 1.2]})

    # ── Left: Tier A horizontal bars ──
    cats = a["categories"]
    names  = [c["label"] for c in cats]
    scores = [c["score"] for c in cats]

    y = np.arange(len(names))
    colors = [CLAW_RED if s == 100 else (AMBER if s < 85 else SIGNAL_ORANGE) for s in scores]
    bars = ax1.barh(y, scores, height=0.5, color=colors, edgecolor="white", linewidth=0.5)

    for i, (bar, s) in enumerate(zip(bars, scores)):
        ax1.text(s - 1.5 if s > 30 else s + 1, i,
                 f"{s}%", ha="right" if s > 30 else "left", va="center",
                 color="white" if s > 30 else colors[i], fontweight="bold", fontsize=10)

    ax1.set_yticks(y)
    ax1.set_yticklabels(names, fontsize=9)
    ax1.set_xlim(0, 105)
    ax1.invert_yaxis()
    ax1.set_title(f"Tier A \u2014 {a['score']}% ({a['totalPassed']}/{a['totalCases']})",
                  loc="left", fontsize=11)
    ax1.xaxis.set_visible(False)

    # ── Right: Tier B grouped bars ──
    dim_keys = [
        ("functionSelection",   "D1"),
        ("parameterExtraction", "D2"),
        ("compositionSafety",   "D3"),
        ("safetyPermissions",   "D4"),
        ("schemaCompleteness",  "D5"),
    ]
    agg = b["aggregated"]
    bvals = [agg[k]["baseline"]["mean"] for k, _ in dim_keys]
    evals = [agg[k]["effector"]["mean"] for k, _ in dim_keys]

    x = np.arange(len(dim_keys))
    w = 0.3
    ax2.bar(x - w/2, bvals, w, color=ASH, label="Baseline", edgecolor="white")
    ax2.bar(x + w/2, evals, w, color=CLAW_RED, label="effector", edgecolor="white")

    for i, (bv, ev) in enumerate(zip(bvals, evals)):
        d = ev - bv
        sign = "+" if d >= 0 else ""
        ax2.text(x[i] + w/2, ev + 3, f"{sign}{d}", ha="center", fontsize=8,
                 fontweight="bold", color=SIGNAL_ORANGE)

    ax2.set_xticks(x)
    ax2.set_xticklabels([l for _, l in dim_keys], fontsize=10)
    ax2.set_ylim(0, 110)
    ax2.set_title(f"Tier B \u2014 \u0394{b['aggregated']['overall']['delta']} overall (n=10)",
                  loc="left", fontsize=11)
    ax2.legend(loc="upper left", frameon=False, fontsize=9)
    ax2.yaxis.set_major_locator(mticker.MultipleLocator(25))

    fig.suptitle("effector-bench v2.0 \u2014 deterministic, no LLM, <10ms",
                 fontsize=12, fontweight="bold", color=CHARCOAL, y=1.01)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "overview-compact.png"), dpi=dpi)
    plt.close(fig)
    print("  \u2713 overview-compact.png")


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Generate effector-bench figures")
    parser.add_argument("--dpi", type=int, default=150, help="Output DPI (default: 150)")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    a = load_json(TIER_A_JSON)
    b = load_json(TIER_B_JSON)

    print(f"Generating figures (DPI={args.dpi})...")
    fig_tier_a_categories(a, args.dpi)
    fig_tier_b_dimensions(b, args.dpi)
    fig_tier_b_heatmap(b, args.dpi)
    fig_tier_b_summary(b, args.dpi)
    fig_tier_b_d2_detail(b, args.dpi)
    fig_overview_compact(a, b, args.dpi)
    print(f"\nDone \u2014 {len(os.listdir(OUT_DIR))} figures in figures/out/")


if __name__ == "__main__":
    main()
