"""
Export blog-ready figure copies directly from the formal research report SVGs.

This script does not redraw charts from blog-specific plotting code. Instead, it
uses the committed formal-report SVGs as the authoritative visual source and
derives blog copies that only differ in:
  1. visible in-figure title text
  2. figure numbering for the blog sequence

The chart body, axes, legends, paths, and annotations remain unchanged.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
DC_NS = "http://purl.org/dc/elements/1.1/"
CC_NS = "http://creativecommons.org/ns#"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("cc", CC_NS)
ET.register_namespace("rdf", RDF_NS)

SVG = f"{{{SVG_NS}}}"

REPO_ROOT = Path(__file__).resolve().parents[1]
FORMAL_DIR = REPO_ROOT / "docs" / "assets" / "formal_research_report"
DEFAULT_OUT = Path(__file__).resolve().parent / "blog_figure_export"

XML_DECL = '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n'
SVG_DOCTYPE = (
    '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n'
    '  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
)


@dataclass(frozen=True)
class ExportSpec:
    source_name: str
    output_name: str
    title: str
    font_size: float = 13.0
    title_y: float = 17.5


EXPORT_SPECS: tuple[ExportSpec, ...] = (
    ExportSpec(
        "figure_01_causal_loop.svg",
        "fig-causal-loop.svg",
        "Figure 1. The Feedback Loops Driving the Convenience Paradox",
    ),
    ExportSpec(
        "figure_04_horizon_panel.svg",
        "fig-horizon-panel.svg",
        "Figure 2. Type A and Type B Remain Structurally Different Across Longer Horizons",
    ),
    ExportSpec(
        "figure_10_available_time_density.svg",
        "fig-available-time-density.svg",
        "Figure 3. Available Time Distribution at Final Step",
    ),
    ExportSpec(
        "figure_06_phase_atlas.svg",
        "fig-phase-atlas.svg",
        "Figure 4. Delegation-Task Load Phase Atlas: Backlog Emergence",
    ),
    ExportSpec(
        "figure_08_story_timeseries.svg",
        "fig-story-timeseries.svg",
        "Figure 5. System Dynamics: Four Story Cases from Relief to Overload",
    ),
    ExportSpec(
        "figure_09_labor_decomposition.svg",
        "fig-labor-decomposition.svg",
        "Figure 6. Labor Composition: Convenience Reshapes Before It Overloads",
    ),
    ExportSpec(
        "figure_13_cost_sensitivity.svg",
        "fig-cost-sensitivity.svg",
        "Figure 7. Service Cost Is Conditional: Relief at Low Load, Amplification Near Threshold",
    ),
    ExportSpec(
        "figure_11_mixed_heatmap.svg",
        "fig-mixed-stability.svg",
        "Figure 8a. Mixed-System Stability: Dispersion Remains Modest",
    ),
    ExportSpec(
        "figure_12_mixed_scatter.svg",
        "fig-mixed-stability-scatter.svg",
        "Figure 8b. Mixed-System Stability: Outcomes Stay Close to Initial Values",
    ),
)


def _parse_viewbox_width(root: ET.Element) -> float:
    view_box = root.attrib.get("viewBox", "").strip()
    if not view_box:
        raise ValueError("SVG root is missing viewBox")
    _, _, width, _ = [float(part) for part in view_box.split()]
    return width


def _is_comment(element: ET.Element) -> bool:
    return element.tag is ET.Comment


def _find_figure_group(root: ET.Element) -> ET.Element:
    figure = root.find(f"{SVG}g[@id='figure_1']")
    if figure is None:
        raise ValueError("Could not find figure_1 group in SVG")
    return figure


def _find_title_group(figure: ET.Element) -> ET.Element:
    for child in list(figure):
        if child.tag != f"{SVG}g":
            continue
        for sub in list(child):
            if _is_comment(sub) and "Figure " in (sub.text or ""):
                return child
    raise ValueError("Could not find visible title group in formal-report SVG")


def _make_blog_title_group(width: float, spec: ExportSpec) -> ET.Element:
    group = ET.Element(f"{SVG}g", {"id": "blog_title"})
    group.append(ET.Comment(f" {spec.title} "))
    text = ET.SubElement(
        group,
        f"{SVG}text",
        {
            "x": f"{width / 2:.3f}",
            "y": f"{spec.title_y:.3f}",
            "text-anchor": "middle",
            "font-family": "DejaVu Serif, Georgia, serif",
            "font-size": f"{spec.font_size:.1f}px",
            "font-weight": "700",
            "fill": "#2d2d2d",
        },
    )
    text.text = spec.title
    return group


def export_one(spec: ExportSpec, output_dir: Path) -> Path:
    source_path = FORMAL_DIR / spec.source_name
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(source_path, parser=parser)
    root = tree.getroot()
    figure = _find_figure_group(root)
    title_group = _find_title_group(figure)
    width = _parse_viewbox_width(root)

    figure.remove(title_group)
    figure.append(_make_blog_title_group(width, spec))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / spec.output_name
    xml_body = ET.tostring(root, encoding="unicode")
    output_path.write_text(XML_DECL + SVG_DOCTYPE + xml_body, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export blog-ready figure copies from formal-report SVGs."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUT,
        help="Directory to write blog figure SVGs into.",
    )
    args = parser.parse_args()

    print(f"Formal source: {FORMAL_DIR}")
    print(f"Output directory: {args.output_dir}")
    for spec in EXPORT_SPECS:
        output_path = export_one(spec, args.output_dir)
        print(f"  exported {spec.source_name} -> {output_path.name}")


if __name__ == "__main__":
    main()
