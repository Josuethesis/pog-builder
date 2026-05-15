
import streamlit as st
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple
import math, base64
from datetime import date

# ------------------------------------------------------------
# POG Builder Prototype
# Language: English
# Author workflow: Territory Manager creates a visual POG from modules,
# shelves, company allocations, and RJ brand load.
# ------------------------------------------------------------

st.set_page_config(page_title="POG Builder Prototype", layout="wide")

COMPANY_COLORS = {
    "PM": "#d9d9d9",
    "RJ": "#e8f4ff",
    "ITG": "#f3e5f5",
    "RC": "#fff3cd",
}

BRAND_STYLES = {
    "Newport": {"color": "#00843D", "text": "#FFFFFF", "pattern": "solid"},
    "Camel": {"color": "#0072CE", "text": "#FFFFFF", "pattern": "solid"},
    "NAS": {"color": "#FFD400", "text": "#111111", "pattern": "solid"},
    "Lucky Strike": {"color": "#FFFFFF", "text": "#111111", "pattern": "red_dot"},
    "Pall Mall Select": {"color": "#FFFFFF", "text": "#0033A0", "pattern": "diagonal_blue"},
}

VALID_WIDTHS_FT = [2, 3, 4, 5, 6, 7, 8]

def facings_for_width(width_ft: int) -> int:
    # Current rule from TM notes: 1 ft = 5 facings, 2 ft = 9 facings.
    # For wider modules, estimate by adding 4 facings per additional foot.
    # This can be replaced later with an exact corporate table.
    if width_ft == 1:
        return 5
    return 5 + (width_ft - 1) * 4

@dataclass
class Module:
    index: int
    width_ft: int
    shelves: int

@dataclass
class CompanyAllocation:
    company: str
    feet: float

@dataclass
class BrandLoad:
    brand: str
    feet: float

def feet_to_facings(feet: float) -> int:
    # Convert feet to approximate cigarette facing count.
    # 1 ft=5, 2 ft=9, then +4 per ft.
    # For fractions, linear interpolation.
    if feet <= 0:
        return 0
    whole = int(math.floor(feet))
    frac = feet - whole
    return int(round(facings_for_width(max(1, whole)) + frac * 4)) if whole >= 1 else int(round(frac * 5))

def build_svg(
    title: str,
    retailer: str,
    effective_date: str,
    modules: List[Module],
    allocations: List[CompanyAllocation],
    brand_loads: List[BrandLoad],
    notes: str = ""
) -> str:
    total_width_ft = sum(m.width_ft for m in modules)
    max_shelves = max(m.shelves for m in modules) if modules else 1
    px_per_ft = 95
    shelf_h = 70
    module_gap = 16
    margin = 40
    header_h = 90
    footer_h = 45

    width = int(margin * 2 + total_width_ft * px_per_ft + module_gap * (len(modules) - 1))
    height = int(header_h + max_shelves * shelf_h + footer_h + margin)

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg.append('<rect width="100%" height="100%" fill="white"/>')
    svg.append(f'<rect x="10" y="10" width="{width-20}" height="{height-20}" fill="none" stroke="#111" stroke-width="1"/>')

    svg.append(f'<text x="{margin}" y="38" font-family="Arial" font-size="22" font-weight="700">{escape(title)}</text>')
    svg.append(f'<text x="{margin}" y="64" font-family="Arial" font-size="14">Retailer: {escape(retailer)} | Effective: {escape(effective_date)}</text>')
    svg.append(f'<text x="{width-margin}" y="38" font-family="Arial" font-size="14" text-anchor="end">Modules: {len(modules)} | Total: {total_width_ft} ft</text>')

    x = margin
    y0 = header_h

    # Company allocation bar
    bar_y = header_h - 18
    bar_x = margin
    for a in allocations:
        alloc_w = a.feet * px_per_ft
        svg.append(f'<rect x="{bar_x}" y="{bar_y}" width="{alloc_w}" height="14" fill="{COMPANY_COLORS.get(a.company, "#eee")}" stroke="#333" stroke-width="0.5"/>')
        svg.append(f'<text x="{bar_x + alloc_w/2}" y="{bar_y+11}" font-family="Arial" font-size="10" text-anchor="middle">{a.company} {a.feet:g}ft</text>')
        bar_x += alloc_w

    # Modules and shelves
    for m in modules:
        mw = m.width_ft * px_per_ft
        mh = m.shelves * shelf_h
        svg.append(f'<rect x="{x}" y="{y0}" width="{mw}" height="{mh}" fill="#d8d2b8" stroke="#333" stroke-width="1.5"/>')
        svg.append(f'<text x="{x+mw/2}" y="{y0-6}" font-family="Arial" font-size="12" text-anchor="middle">Module {m.index}: {m.width_ft} ft / {m.shelves} shelves</text>')

        for s in range(m.shelves):
            sy = y0 + s * shelf_h
            svg.append(f'<line x1="{x}" y1="{sy+shelf_h}" x2="{x+mw}" y2="{sy+shelf_h}" stroke="#333" stroke-width="2"/>')
            svg.append(f'<text x="{x+4}" y="{sy+14}" font-family="Arial" font-size="10" fill="#444">Shelf {s+1}</text>')

            facings = facings_for_width(m.width_ft)
            facing_w = mw / facings
            for f in range(facings):
                fx = x + f * facing_w
                svg.append(f'<rect x="{fx+1}" y="{sy+20}" width="{facing_w-2}" height="{shelf_h-26}" fill="#f8f8f8" stroke="#aaa" stroke-width="0.4"/>')

        x += mw + module_gap

    # RJ brand load overlay: rough engine places RJ blocks from bottom shelf upward.
    # 4 ft means 2 ft stacked over 2 ft, per TM rule.
    rj_alloc = next((a.feet for a in allocations if a.company == "RJ"), 0)
    if rj_alloc > 0 and brand_loads:
        overlay_y = y0 + max_shelves * shelf_h + 8
        svg.append(f'<text x="{margin}" y="{overlay_y}" font-family="Arial" font-size="13" font-weight="700">RJ Brand Load Summary</text>')
        bx = margin
        by = overlay_y + 10
        for b in brand_loads:
            style = BRAND_STYLES.get(b.brand, {"color": "#eee", "text": "#000", "pattern": "solid"})
            block_w = max(55, b.feet * 38)
            block_h = 24
            svg.append(f'<rect x="{bx}" y="{by}" width="{block_w}" height="{block_h}" fill="{style["color"]}" stroke="#222" stroke-width="1"/>')
            if style["pattern"] == "red_dot":
                svg.append(f'<circle cx="{bx+block_w/2}" cy="{by+block_h/2}" r="7" fill="#D71920"/>')
            if style["pattern"] == "diagonal_blue":
                svg.append(f'<polygon points="{bx},{by+block_h} {bx+block_w},{by} {bx+block_w},{by+block_h}" fill="#0033A0" opacity="0.85"/>')
            svg.append(f'<text x="{bx+block_w/2}" y="{by+16}" font-family="Arial" font-size="10" text-anchor="middle" fill="{style["text"]}" font-weight="700">{escape(b.brand)} {b.feet:g}ft</text>')
            bx += block_w + 8

    if notes:
        svg.append(f'<text x="{margin}" y="{height-22}" font-family="Arial" font-size="11">Notes: {escape(notes)}</text>')

    svg.append('</svg>')
    return "\n".join(svg)

def escape(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def svg_download_link(svg: str, filename: str) -> str:
    b64 = base64.b64encode(svg.encode("utf-8")).decode()
    return f'<a href="data:image/svg+xml;base64,{b64}" download="{filename}">Download SVG</a>'

st.title("POG Builder Prototype")
st.caption("Initial prototype for Tobacco Fixture Planograms: modules, shelves, company space, RJ brand load, visual preview, and export.")

with st.sidebar:
    st.header("POG Setup")
    title = st.text_input("POG Title", "CIGARETTES 4FT STD 6 SHELVES 1 BAY")
    retailer = st.text_input("Retailer / Account", "Store / Account Name")
    effective = st.date_input("Effective Date", value=date.today())
    notes = st.text_area("Planogram Notes", "")

    st.divider()
    module_count = st.number_input("How many modules in this POG?", min_value=1, max_value=8, value=1, step=1)

modules = []
st.subheader("1. Fixture Configuration")
cols = st.columns(int(module_count))
for i in range(int(module_count)):
    with cols[i]:
        width = st.selectbox(f"Module {i+1} width (ft)", VALID_WIDTHS_FT, index=2 if i == 0 else 0)
        shelves = st.number_input(f"Module {i+1} shelves", min_value=1, max_value=30, value=6, step=1)
        modules.append(Module(i+1, width, int(shelves)))

total_width = sum(m.width_ft for m in modules)
total_capacity_ft = sum(m.width_ft * m.shelves for m in modules)
st.info(f"Fixture width: {total_width} ft | Vertical shelf capacity: {total_capacity_ft} shelf-feet")

st.subheader("2. Companies in the POG")
selected_companies = st.multiselect("Select companies", ["PM", "RJ", "ITG", "RC"], default=["PM", "RJ"])

allocations = []
alloc_cols = st.columns(max(1, len(selected_companies)))
for idx, company in enumerate(selected_companies):
    with alloc_cols[idx]:
        ft = st.number_input(f"{company} space (ft)", min_value=0.0, max_value=float(total_capacity_ft), value=0.0, step=0.5)
        allocations.append(CompanyAllocation(company, ft))

allocated_total = sum(a.feet for a in allocations)
if allocated_total > total_capacity_ft:
    st.error(f"Not enough space. Requested {allocated_total:g} shelf-feet but fixture capacity is {total_capacity_ft:g} shelf-feet.")
else:
    st.success(f"Allocated {allocated_total:g} of {total_capacity_ft:g} shelf-feet.")

st.subheader("3. RJ Brand Load")
brand_loads = []
rj_space = next((a.feet for a in allocations if a.company == "RJ"), 0)

if "RJ" in selected_companies and rj_space > 0:
    brand_cols = st.columns(5)
    for idx, brand in enumerate(BRAND_STYLES.keys()):
        with brand_cols[idx]:
            ft = st.number_input(f"{brand} feet", min_value=0.0, max_value=float(rj_space), value=0.0, step=0.5)
            if ft > 0:
                brand_loads.append(BrandLoad(brand, ft))

    brand_total = sum(b.feet for b in brand_loads)
    if brand_total > rj_space:
        st.error(f"RJ brand load exceeds RJ space. Requested {brand_total:g} ft but RJ has {rj_space:g} ft.")
    else:
        st.success(f"RJ brand load: {brand_total:g} of {rj_space:g} ft.")
else:
    st.warning("Select RJ and assign RJ space to configure RJ brand load.")

st.subheader("4. Visual Preview")
svg = build_svg(title, retailer, str(effective), modules, allocations, brand_loads, notes)
st.components.v1.html(svg, height=760, scrolling=True)

st.markdown(svg_download_link(svg, "pog_preview.svg"), unsafe_allow_html=True)

st.subheader("5. Current Data")
st.json({
    "title": title,
    "retailer": retailer,
    "effective_date": str(effective),
    "modules": [asdict(m) for m in modules],
    "total_width_ft": total_width,
    "total_capacity_shelf_feet": total_capacity_ft,
    "company_allocations": [asdict(a) for a in allocations],
    "rj_brand_load": [asdict(b) for b in brand_loads],
})
