
import streamlit as st
from dataclasses import dataclass, asdict
from datetime import date
import base64
import math

st.set_page_config(page_title="POG Builder v0.3", layout="wide")

COMPANY_COLORS = {
    "PM": {"fill": "#C9C9C9", "text": "#111"},
    "RJ": {"fill": "#D9ECFF", "text": "#111"},
    "ITG": {"fill": "#E7D8FF", "text": "#111"},
    "RC": {"fill": "#FFE6A6", "text": "#111"},
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
    return str(x).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def facings_for_width(width_ft):
    # Working rule: 1 ft = 5 facings, 2 ft = 9 facings.
    # Temporary wider rule until exact table is confirmed.
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
    shelf_feet: float

@dataclass
class Brand:
    name: str
    shelf_feet: float

def build_slots(modules):
    """
    Creates shelf-foot slots from bottom shelf upward, left to right.
    Each 1-foot slot becomes a placement unit.
    """
    slots = []
    for m in modules:
        for shelf in range(m.shelves, 0, -1):  # bottom to top
            for ft in range(1, m.width_ft + 1):
                slots.append({
                    "module": m.index,
                    "shelf": shelf,
                    "ft": ft,
                    "key": f"M{m.index}-S{shelf}-F{ft}",
                    "company": None,
                    "brand": None,
                })
    return slots

def split_brand_segments(name, feet):
    """
    RJ rule: 4 ft should become 2 ft over 2 ft, not 4 linear.
    This function breaks any RJ brand into max 2-ft segments.
    """
    segs = []
    remaining = feet
    while remaining > 0:
        seg = min(2, remaining)
        segs.append({"name": name, "feet": seg})
        remaining -= seg
    return segs

def assign_layout(modules, allocations, brands, fill_direction):
    slots = build_slots(modules)
    slot_index = 0

    # Company assignment into fixture
    for alloc in allocations:
        needed = int(round(alloc.shelf_feet))
        for _ in range(needed):
            if slot_index < len(slots):
                slots[slot_index]["company"] = alloc.company
                slot_index += 1

    # RJ brand assignment only into RJ slots
    rj_slots = [s for s in slots if s["company"] == "RJ"]
    rj_i = 0
    for b in brands:
        for seg in split_brand_segments(b.name, b.shelf_feet):
            needed = int(round(seg["feet"]))
            for _ in range(needed):
                if rj_i < len(rj_slots):
                    rj_slots[rj_i]["brand"] = b.name
                    rj_i += 1

    return slots

def slot_lookup(slots):
    return {(s["module"], s["shelf"], s["ft"]): s for s in slots}

def draw_brand_rect(svg, x, y, w, h, brand_name):
    style = RJ_BRANDS.get(brand_name)
    if not style:
        return
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{style["fill"]}" stroke="#111" stroke-width="1.2" rx="3"/>')
    if style["kind"] == "red_dot":
        svg.append(f'<circle cx="{x+w/2}" cy="{y+h/2}" r="{min(w,h)*0.18}" fill="#D71920"/>')
    elif style["kind"] == "diagonal":
        svg.append(f'<polygon points="{x},{y+h} {x+w},{y} {x+w},{y+h}" fill="#0033A0" opacity="0.85"/>')
    label = brand_name.replace("Pall Mall Select", "Pall Mall")
    svg.append(f'<text x="{x+w/2}" y="{y+h/2+4}" font-family="Arial" font-size="11" text-anchor="middle" fill="{style["text"]}" font-weight="700">{esc(label)}</text>')

def build_svg(title, account, effective, pog_type, modules, allocations, brands, notes, show_facing_numbers):
    total_width_ft = sum(m.width_ft for m in modules)
    max_shelves = max([m.shelves for m in modules] or [1])
    slots = assign_layout(modules, allocations, brands, "bottom_up")
    lookup = slot_lookup(slots)

    px_per_ft = 110
    shelf_h = 76
    margin = 38
    module_gap = 18
    top_h = 108
    bottom_h = 75

    fixture_w = total_width_ft * px_per_ft + (len(modules)-1)*module_gap
    svg_w = int(fixture_w + margin*2)
    svg_h = int(top_h + max_shelves*shelf_h + bottom_h)

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">')
    svg.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    svg.append(f'<rect x="8" y="8" width="{svg_w-16}" height="{svg_h-16}" fill="none" stroke="#111" stroke-width="1"/>')

    # Header similar to corporate POG
    svg.append(f'<text x="{margin}" y="34" font-family="Arial" font-size="22" font-weight="700">{esc(title)}</text>')
    svg.append(f'<text x="{margin}" y="58" font-family="Arial" font-size="13">Account: {esc(account)} | Type: {esc(pog_type)} | Effective: {esc(effective)}</text>')
    svg.append(f'<text x="{svg_w-margin}" y="34" font-family="Arial" font-size="12" text-anchor="end">Total Width: {total_width_ft} ft</text>')

    # Legend
    lx = margin
    ly = 76
    for name, style in RJ_BRANDS.items():
        svg.append(f'<rect x="{lx}" y="{ly}" width="18" height="12" fill="{style["fill"]}" stroke="#111" stroke-width="0.7"/>')
        if style["kind"] == "red_dot":
            svg.append(f'<circle cx="{lx+9}" cy="{ly+6}" r="3" fill="#D71920"/>')
        if style["kind"] == "diagonal":
            svg.append(f'<polygon points="{lx},{ly+12} {lx+18},{ly} {lx+18},{ly+12}" fill="#0033A0" opacity="0.85"/>')
        svg.append(f'<text x="{lx+24}" y="{ly+10}" font-family="Arial" font-size="10">{esc(name)}</text>')
        lx += 115

    x = margin
    y0 = top_h

    # Draw each module
    for m in modules:
        mw = m.width_ft * px_per_ft
        module_h = m.shelves * shelf_h

        svg.append(f'<rect x="{x}" y="{y0-26}" width="{mw}" height="24" fill="#202020" stroke="#111"/>')
        svg.append(f'<text x="{x+mw/2}" y="{y0-9}" font-family="Arial" font-size="12" fill="#fff" font-weight="700" text-anchor="middle">MODULE {m.index} — {m.width_ft} FT</text>')
        svg.append(f'<rect x="{x}" y="{y0}" width="{mw}" height="{module_h}" fill="#D8C895" stroke="#111" stroke-width="2"/>')

        for shelf_visual in range(1, m.shelves+1):
            sy = y0 + (shelf_visual-1)*shelf_h
            shelf_num = shelf_visual  # top-to-bottom visually

            svg.append(f'<rect x="{x}" y="{sy}" width="{mw}" height="{shelf_h}" fill="#E7D7A5" stroke="#333" stroke-width="1"/>')
            svg.append(f'<text x="{x+5}" y="{sy+14}" font-family="Arial" font-size="10" fill="#111">Shelf {shelf_num}</text>')

            # feet slots across shelf
            for ft in range(1, m.width_ft+1):
                slot = lookup.get((m.index, shelf_num, ft))
                fx = x + (ft-1)*px_per_ft
                fw = px_per_ft
                fy = sy + 18
                fh = shelf_h - 29

                company = slot["company"] if slot else None
                brand = slot["brand"] if slot else None

                if brand:
                    draw_brand_rect(svg, fx+3, fy, fw-6, fh, brand)
                elif company:
                    style = COMPANY_COLORS.get(company, {"fill":"#F5F5F5","text":"#111"})
                    svg.append(f'<rect x="{fx+3}" y="{fy}" width="{fw-6}" height="{fh}" fill="{style["fill"]}" stroke="#111" stroke-width="1" rx="3"/>')
                    svg.append(f'<text x="{fx+fw/2}" y="{fy+fh/2+4}" font-family="Arial" font-size="12" text-anchor="middle" fill="{style["text"]}" font-weight="700">{company}</text>')
                else:
                    svg.append(f'<rect x="{fx+3}" y="{fy}" width="{fw-6}" height="{fh}" fill="#FAFAFA" stroke="#999" stroke-width="0.7" rx="3"/>')
                    svg.append(f'<text x="{fx+fw/2}" y="{fy+fh/2+4}" font-family="Arial" font-size="10" text-anchor="middle" fill="#999">OPEN</text>')

                # small facings within each foot
                facings = 5 if ft == 1 else 4
                mini_w = (fw-10)/facings
                for f in range(facings):
                    mx = fx+5+f*mini_w
                    my = sy+shelf_h-11
                    svg.append(f'<rect x="{mx}" y="{my}" width="{mini_w-1}" height="7" fill="#fefefe" stroke="#777" stroke-width="0.35"/>')
                    if show_facing_numbers:
                        svg.append(f'<text x="{mx+mini_w/2}" y="{my+6}" font-family="Arial" font-size="5" text-anchor="middle" fill="#555">{f+1}</text>')

            svg.append(f'<rect x="{x}" y="{sy+shelf_h-8}" width="{mw}" height="8" fill="#6F6F6F" stroke="#333" stroke-width="0.5"/>')

        x += mw + module_gap

    # Footer summary
    alloc_txt = " | ".join([f"{a.company}: {a.shelf_feet:g} shelf-ft" for a in allocations]) or "No company allocation"
    brand_txt = " | ".join([f"{b.name}: {b.shelf_feet:g}" for b in brands]) or "No RJ brand load"
    fy = svg_h - 45
    svg.append(f'<text x="{margin}" y="{fy}" font-family="Arial" font-size="11" font-weight="700">Company Allocation:</text>')
    svg.append(f'<text x="{margin+115}" y="{fy}" font-family="Arial" font-size="11">{esc(alloc_txt)}</text>')
    svg.append(f'<text x="{margin}" y="{fy+18}" font-family="Arial" font-size="11" font-weight="700">RJ Brand Load:</text>')
    svg.append(f'<text x="{margin+115}" y="{fy+18}" font-family="Arial" font-size="11">{esc(brand_txt)}</text>')

    if notes:
        svg.append(f'<text x="{margin}" y="{svg_h-10}" font-family="Arial" font-size="10">Notes: {esc(notes)}</text>')

    svg.append('</svg>')
    return "\n".join(svg)

st.title("POG Builder v0.3")
st.caption("This version places company and RJ brand blocks inside the fixture shelves.")

with st.sidebar:
    st.header("POG Information")
    title = st.text_input("POG Title", "CIGARETTES 4FT STD 6 SHELVES 1 BAY")
    account = st.text_input("Account / Store", "Account Name")
    pog_type = st.selectbox("POG Type", ["CFM / Cigarettes", "Vapor", "TO / Moist", "NMO / Pouches", "Mixed Fixture"])
    effective = st.date_input("Effective Date", value=date.today())
    notes = st.text_area("Notes", "")
    show_facing_numbers = st.checkbox("Show facing numbers", value=False)

    st.divider()
    module_count = st.number_input("How many modules in this POG?", min_value=1, max_value=8, value=1, step=1)

st.subheader("1. Fixture Configuration")
modules = []
cols = st.columns(int(module_count))
for i in range(int(module_count)):
    with cols[i]:
        width = st.selectbox(f"Module {i+1} Width (ft)", WIDTH_OPTIONS, index=2 if i == 0 else 0, key=f"w{i}")
        shelves = st.number_input(f"Module {i+1} Shelves", min_value=1, max_value=30, value=6, step=1, key=f"s{i}")
        modules.append(Module(i+1, int(width), int(shelves)))
        st.caption(f"Approx. facings per shelf: {facings_for_width(int(width))}")

capacity = sum(m.width_ft*m.shelves for m in modules)
st.info(f"Available capacity: {capacity:g} shelf-feet")

st.subheader("2. Company Allocation")
selected = st.multiselect("Companies in this POG", ["PM", "RJ", "ITG", "RC"], default=["PM", "RJ"])
allocations = []
if selected:
    ccols = st.columns(len(selected))
    for i, company in enumerate(selected):
        with ccols[i]:
            feet = st.number_input(f"{company} shelf-feet", min_value=0.0, max_value=float(capacity), value=0.0, step=1.0, key=f"a{company}")
            if feet > 0:
                allocations.append(Allocation(company, float(feet)))

alloc_total = sum(a.shelf_feet for a in allocations)
if alloc_total > capacity:
    st.error(f"Not enough space: requested {alloc_total:g} shelf-feet, capacity is {capacity:g}.")
else:
    st.success(f"Allocated {alloc_total:g} of {capacity:g} shelf-feet.")

st.subheader("3. RJ Brand Load")
rj_space = sum(a.shelf_feet for a in allocations if a.company == "RJ")
brands = []
if rj_space > 0:
    bcols = st.columns(5)
    for i, brand in enumerate(RJ_BRANDS.keys()):
        with bcols[i]:
            val = st.number_input(f"{brand}", min_value=0.0, max_value=float(rj_space), value=0.0, step=1.0, key=f"b{brand}")
            if val > 0:
                brands.append(Brand(brand, float(val)))
    brand_total = sum(b.shelf_feet for b in brands)
    if brand_total > rj_space:
        st.error(f"RJ brand load exceeds RJ allocation: {brand_total:g} > {rj_space:g}.")
    else:
        st.success(f"RJ brand load: {brand_total:g} of {rj_space:g} shelf-feet.")
else:
    st.warning("Assign shelf-feet to RJ to enter RJ brand load.")

st.subheader("4. Generated Planogram")
svg = build_svg(title, account, str(effective), pog_type, modules, allocations, brands, notes, show_facing_numbers)

st.markdown(f'<div style="overflow:auto;border:1px solid #ccc;padding:8px;background:white;">{svg}</div>', unsafe_allow_html=True)

st.download_button("Download POG SVG", data=svg.encode("utf-8"), file_name="generated_pog_v03.svg", mime="image/svg+xml")

st.subheader("Layout Data")
st.json({
    "capacity_shelf_feet": capacity,
    "modules": [asdict(m) for m in modules],
    "company_allocation": [asdict(a) for a in allocations],
    "rj_brand_load": [asdict(b) for b in brands],
})
