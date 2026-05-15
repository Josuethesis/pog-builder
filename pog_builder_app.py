import streamlit as st
from dataclasses import dataclass, asdict
from datetime import date
import base64
import math

st.set_page_config(page_title="POG Builder Prototype v0.2", layout="wide")

COMPANY_COLORS = {
    "PM": "#BDBDBD",
    "RJ": "#D7ECFF",
    "ITG": "#E9D5FF",
    "RC": "#FFE6A7",
}

RJ_BRANDS = {
    "Newport": {"fill": "#00843D", "text": "#FFFFFF", "kind": "solid"},
    "Camel": {"fill": "#0072CE", "text": "#FFFFFF", "kind": "solid"},
    "NAS": {"fill": "#FFD400", "text": "#111111", "kind": "solid"},
    "Lucky Strike": {"fill": "#FFFFFF", "text": "#111111", "kind": "red_dot"},
    "Pall Mall Select": {"fill": "#FFFFFF", "text": "#0033A0", "kind": "diagonal"},
}

WIDTH_OPTIONS = [2, 3, 4, 5, 6, 7, 8]

def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def facings_for_width(width_ft):
    # Current working rule from Josue:
    # 2 ft = 9 facings, 1 ft = 5 facings.
    # Temporary scale for wider modules until exact table is confirmed.
    if width_ft <= 1:
        return 5
    return 5 + (width_ft - 1) * 4

@dataclass
class Module:
    index: int
    width_ft: int
    shelves: int

@dataclass
class Allocation:
    company: str
    feet: float

@dataclass
class Brand:
    name: str
    feet: float

def split_brand_into_segments(feet):
    """
    Josue rule:
    Any RJ brand requested as 4 ft should be arranged 2 ft over 2 ft,
    not 4 linear ft.
    For now, all brand blocks above 2 ft are split into 2-ft rows.
    """
    segments = []
    remaining = feet
    while remaining > 0:
        seg = min(2, remaining)
        segments.append(seg)
        remaining -= seg
    return segments

def build_pog_svg(title, account, effective, modules, allocations, brands, pog_type, notes):
    total_width_ft = sum(m.width_ft for m in modules)
    max_shelves = max([m.shelves for m in modules] or [1])

    px_per_ft = 120
    shelf_h = 82
    margin = 40
    module_gap = 18
    top_h = 130
    bottom_h = 115

    fixture_w = total_width_ft * px_per_ft + (len(modules)-1) * module_gap
    svg_w = int(fixture_w + margin * 2)
    svg_h = int(top_h + max_shelves * shelf_h + bottom_h)

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">')
    svg.append('<rect width="100%" height="100%" fill="#FFFFFF"/>')
    svg.append(f'<rect x="8" y="8" width="{svg_w-16}" height="{svg_h-16}" fill="none" stroke="#111" stroke-width="1"/>')

    # Header
    svg.append(f'<text x="{margin}" y="36" font-family="Arial" font-size="24" font-weight="700">{esc(title)}</text>')
    svg.append(f'<text x="{margin}" y="62" font-family="Arial" font-size="14">Account: {esc(account)} | Type: {esc(pog_type)} | Effective: {esc(effective)}</text>')
    svg.append(f'<text x="{svg_w-margin}" y="36" font-family="Arial" font-size="13" text-anchor="end">Total Width: {total_width_ft} ft | Modules: {len(modules)}</text>')

    # Company allocation bar
    bar_x = margin
    bar_y = 84
    total_alloc = sum(a.feet for a in allocations)
    cap = sum(m.width_ft * m.shelves for m in modules)
    svg.append(f'<text x="{margin}" y="{bar_y-8}" font-family="Arial" font-size="12" font-weight="700">Company Space Allocation</text>')
    if total_alloc > 0:
        for a in allocations:
            w = max(1, (a.feet / max(total_alloc, 1)) * fixture_w)
            color = COMPANY_COLORS.get(a.company, "#EEEEEE")
            svg.append(f'<rect x="{bar_x}" y="{bar_y}" width="{w}" height="22" fill="{color}" stroke="#333" stroke-width="1"/>')
            svg.append(f'<text x="{bar_x+w/2}" y="{bar_y+15}" font-family="Arial" font-size="11" text-anchor="middle" font-weight="700">{a.company} {a.feet:g} ft</text>')
            bar_x += w
    else:
        svg.append(f'<rect x="{margin}" y="{bar_y}" width="{fixture_w}" height="22" fill="#F8F8F8" stroke="#333" stroke-width="1"/>')
        svg.append(f'<text x="{margin+fixture_w/2}" y="{bar_y+15}" font-family="Arial" font-size="11" text-anchor="middle">No company allocation entered yet</text>')

    # Fixture modules
    x = margin
    y0 = top_h
    shelf_global_num = 1

    for m in modules:
        mw = m.width_ft * px_per_ft
        module_h = m.shelves * shelf_h

        svg.append(f'<rect x="{x}" y="{y0}" width="{mw}" height="{module_h}" fill="#E6D8A8" stroke="#111" stroke-width="2"/>')
        svg.append(f'<rect x="{x}" y="{y0-26}" width="{mw}" height="24" fill="#252525" stroke="#111" stroke-width="1"/>')
        svg.append(f'<text x="{x+mw/2}" y="{y0-9}" font-family="Arial" font-size="12" fill="#fff" text-anchor="middle" font-weight="700">MODULE {m.index} — {m.width_ft} FT</text>')

        facings = facings_for_width(m.width_ft)
        facing_w = mw / facings

        for s in range(m.shelves):
            sy = y0 + s * shelf_h
            # shelf strip
            svg.append(f'<rect x="{x}" y="{sy}" width="{mw}" height="{shelf_h}" fill="#F2E5B8" stroke="#333" stroke-width="1"/>')
            svg.append(f'<rect x="{x}" y="{sy+shelf_h-10}" width="{mw}" height="10" fill="#777" stroke="#333" stroke-width="0.5"/>')
            svg.append(f'<text x="{x+5}" y="{sy+14}" font-family="Arial" font-size="10" fill="#111">Shelf {s+1}</text>')

            for f in range(facings):
                fx = x + f * facing_w + 2
                fy = sy + 20
                fh = shelf_h - 34
                fw = facing_w - 4
                svg.append(f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="#FFFFFF" stroke="#777" stroke-width="0.5" rx="2"/>')
                svg.append(f'<text x="{fx+fw/2}" y="{fy+fh/2+4}" font-family="Arial" font-size="9" text-anchor="middle" fill="#666">{f+1}</text>')

            shelf_global_num += 1

        x += mw + module_gap

    # RJ Brand visual block, with stacked 2-ft logic
    rj_y = top_h + max_shelves * shelf_h + 38
    svg.append(f'<text x="{margin}" y="{rj_y-14}" font-family="Arial" font-size="14" font-weight="700">RJ Brand Load Visual</text>')

    if brands:
        bx = margin
        by = rj_y
        row_h = 34
        for b in brands:
            style = RJ_BRANDS[b.name]
            segments = split_brand_into_segments(b.feet)
            for seg_idx, seg in enumerate(segments):
                bw = seg * px_per_ft
                fill = style["fill"]
                text = style["text"]
                svg.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{row_h}" fill="{fill}" stroke="#111" stroke-width="1.2" rx="3"/>')
                if style["kind"] == "red_dot":
                    svg.append(f'<circle cx="{bx+bw/2}" cy="{by+row_h/2}" r="10" fill="#D71920"/>')
                if style["kind"] == "diagonal":
                    svg.append(f'<polygon points="{bx},{by+row_h} {bx+bw},{by} {bx+bw},{by+row_h}" fill="#0033A0" opacity="0.85"/>')
                svg.append(f'<text x="{bx+bw/2}" y="{by+21}" font-family="Arial" font-size="12" text-anchor="middle" fill="{text}" font-weight="700">{esc(b.name)} {seg:g} ft</text>')
                by += row_h + 4
            bx += 16
            by = rj_y
    else:
        svg.append(f'<rect x="{margin}" y="{rj_y}" width="{fixture_w}" height="34" fill="#F7F7F7" stroke="#999" stroke-width="1"/>')
        svg.append(f'<text x="{margin+fixture_w/2}" y="{rj_y+22}" font-family="Arial" font-size="12" text-anchor="middle">Enter RJ brand load to draw brand blocks</text>')

    if notes:
        svg.append(f'<text x="{margin}" y="{svg_h-26}" font-family="Arial" font-size="11">Notes: {esc(notes)}</text>')

    svg.append('</svg>')
    return "\n".join(svg)

def svg_data_url(svg):
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"

st.title("POG Builder Prototype v0.2")
st.caption("This version actually draws the POG preview based on the TM inputs.")

with st.sidebar:
    st.header("POG Inputs")
    title = st.text_input("POG Title", "CIGARETTES 4FT STD 6 SHELVES 1 BAY")
    account = st.text_input("Account / Store", "Circle K / Store")
    pog_type = st.selectbox("POG Type", ["CFM / Cigarettes", "Vapor", "TO / Moist", "NMO / Pouches", "Mixed Fixture"])
    effective = st.date_input("Effective Date", value=date.today())
    notes = st.text_area("Notes", "")

    st.divider()
    module_count = st.number_input("How many modules in the POG?", min_value=1, max_value=8, value=1, step=1)

modules = []
st.subheader("1. Fixture Configuration")
module_cols = st.columns(int(module_count))
for i in range(int(module_count)):
    with module_cols[i]:
        width = st.selectbox(f"Module {i+1} Width", WIDTH_OPTIONS, index=2 if i == 0 else 0, key=f"width_{i}")
        shelves = st.number_input(f"Module {i+1} Shelves", min_value=1, max_value=30, value=6, step=1, key=f"shelves_{i}")
        modules.append(Module(i+1, int(width), int(shelves)))
        st.caption(f"{facings_for_width(int(width))} facings per shelf")

total_width = sum(m.width_ft for m in modules)
capacity = sum(m.width_ft * m.shelves for m in modules)
st.info(f"Fixture total width: {total_width} ft | Total shelf-feet capacity: {capacity:g}")

st.subheader("2. Companies")
selected_companies = st.multiselect("Companies in this POG", ["PM", "RJ", "ITG", "RC"], default=["PM", "RJ"])
allocations = []
if selected_companies:
    cols = st.columns(len(selected_companies))
    for i, c in enumerate(selected_companies):
        with cols[i]:
            val = st.number_input(f"{c} shelf-feet", min_value=0.0, max_value=float(capacity), value=0.0, step=0.5, key=f"alloc_{c}")
            allocations.append(Allocation(c, float(val)))

alloc_total = sum(a.feet for a in allocations)
if alloc_total > capacity:
    st.error(f"ERROR: Not enough space. You requested {alloc_total:g} shelf-feet but the fixture only has {capacity:g}.")
else:
    st.success(f"Allocated {alloc_total:g} of {capacity:g} shelf-feet.")

st.subheader("3. RJ Brand Load")
brands = []
rj_space = next((a.feet for a in allocations if a.company == "RJ"), 0)

if "RJ" in selected_companies and rj_space > 0:
    cols = st.columns(5)
    for i, brand_name in enumerate(RJ_BRANDS.keys()):
        with cols[i]:
            val = st.number_input(f"{brand_name}", min_value=0.0, max_value=float(rj_space), value=0.0, step=0.5, key=f"brand_{brand_name}")
            if val > 0:
                brands.append(Brand(brand_name, float(val)))

    brand_total = sum(b.feet for b in brands)
    if brand_total > rj_space:
        st.error(f"ERROR: RJ brand load is too large. RJ has {rj_space:g} shelf-feet, but brands total {brand_total:g}.")
    else:
        st.success(f"RJ brands total {brand_total:g} of {rj_space:g} shelf-feet.")
else:
    st.warning("Select RJ and give RJ some shelf-feet to enter RJ brand load.")

st.subheader("4. Generated POG Preview")

svg = build_pog_svg(
    title=title,
    account=account,
    effective=str(effective),
    modules=modules,
    allocations=allocations,
    brands=brands,
    pog_type=pog_type,
    notes=notes,
)

# Render SVG visibly in browser
st.markdown(
    f"""
    <div style="border:1px solid #ccc; padding:10px; overflow:auto; background:white;">
        {svg}
    </div>
    """,
    unsafe_allow_html=True,
)

st.download_button(
    label="Download POG as SVG",
    data=svg.encode("utf-8"),
    file_name="generated_pog.svg",
    mime="image/svg+xml",
)

st.subheader("5. Debug Data")
st.json({
    "modules": [asdict(m) for m in modules],
    "capacity_shelf_feet": capacity,
    "allocations": [asdict(a) for a in allocations],
    "rj_brand_load": [asdict(b) for b in brands],
})
