"""PDF generation service for antenna spec sheets using ReportLab."""
import io
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# Color palette matching the app
CYAN = colors.HexColor("#00BCD4")
GREEN = colors.HexColor("#4CAF50")
ORANGE = colors.HexColor("#FF9800")
RED = colors.HexColor("#f44336")
BLUE = colors.HexColor("#2196F3")
PURPLE = colors.HexColor("#9C27B0")
PINK = colors.HexColor("#E91E63")
DEEP_ORANGE = colors.HexColor("#FF5722")
LIME = colors.HexColor("#8BC34A")
DARK_BG = colors.HexColor("#1a1a1a")
DARKER_BG = colors.HexColor("#111111")
MID_GRAY = colors.HexColor("#333333")
LIGHT_GRAY = colors.HexColor("#888888")
WHITE = colors.white


def _style(name, **kw):
    defaults = dict(fontName="Helvetica", fontSize=9, textColor=WHITE, leading=12)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


STYLES = {
    "title": _style("title", fontSize=16, fontName="Helvetica-Bold", textColor=CYAN, leading=20),
    "subtitle": _style("subtitle", fontSize=10, textColor=LIGHT_GRAY),
    "section": _style("section", fontSize=11, fontName="Helvetica-Bold", leading=14),
    "label": _style("label", fontSize=8, textColor=LIGHT_GRAY),
    "value": _style("value", fontSize=8, textColor=WHITE),
    "value_bold": _style("value_bold", fontSize=8, fontName="Helvetica-Bold", textColor=WHITE),
    "hero_num": _style("hero_num", fontSize=20, fontName="Helvetica-Bold", alignment=TA_CENTER, leading=24),
    "hero_label": _style("hero_label", fontSize=7, textColor=LIGHT_GRAY, alignment=TA_CENTER),
    "note": _style("note", fontSize=7, textColor=LIGHT_GRAY, leading=10),
    "footer": _style("footer", fontSize=7, textColor=colors.HexColor("#444444"), alignment=TA_CENTER),
}


def _section_header(text, color):
    """Create a colored section header."""
    return Paragraph(f'<font color="{color.hexval()}">{text.upper()}</font>', STYLES["section"])


def _spec_rows(pairs, accent_keys=None):
    """Build a table of label-value rows."""
    accent_keys = accent_keys or {}
    data = []
    for label, value in pairs:
        tc = accent_keys.get(label, WHITE)
        if isinstance(tc, str):
            tc = colors.HexColor(tc)
        style = _style("tmp", fontSize=8, fontName="Helvetica-Bold" if label in accent_keys else "Helvetica", textColor=tc)
        data.append([
            Paragraph(label, STYLES["label"]),
            Paragraph(str(value), style),
        ])
    if not data:
        return Spacer(1, 0)
    t = Table(data, colWidths=[2.8 * inch, 4 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BG),
        ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, MID_GRAY),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def _element_table(elements):
    """Build element dimensions table."""
    header = ["#", "Type", "Length", "Diameter", "Position"]
    data = [header]
    for i, e in enumerate(elements):
        data.append([
            str(i + 1),
            e.get("element_type", "").capitalize(),
            f'{e.get("length", "-")}"',
            f'{e.get("diameter", "-")}"',
            f'{e.get("position", "-")}"',
        ])
    t = Table(data, colWidths=[0.4 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
    styles = [
        ("BACKGROUND", (0, 0), (-1, 0), MID_GRAY),
        ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), LIGHT_GRAY),
        ("TEXTCOLOR", (0, 1), (-1, -1), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, MID_GRAY),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]
    # Color-code element types
    type_colors = {"reflector": RED, "driven": ORANGE, "director": GREEN}
    for i, e in enumerate(elements):
        c = type_colors.get(e.get("element_type", ""), WHITE)
        styles.append(("TEXTCOLOR", (1, i + 1), (1, i + 1), c))
    t.setStyle(TableStyle(styles))
    return t


def _hero_card(value, label, color):
    """Single hero metric card."""
    data = [
        [Paragraph(f'<font color="{color.hexval()}">{value}</font>', STYLES["hero_num"])],
        [Paragraph(label, STYLES["hero_label"])],
    ]
    t = Table(data, colWidths=[1.8 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BG),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (0, 0), 8),
        ("BOTTOMPADDING", (0, -1), (0, -1), 6),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return t


def _hero_row(results):
    """Top hero metrics row."""
    swr = results.get("swr", 0)
    swr_color = GREEN if swr <= 1.5 else (ORANGE if swr <= 2.0 else RED)
    cards = [
        _hero_card(str(results.get("gain_dbi", "-")), "GAIN (dBi)", GREEN),
        _hero_card(f"{swr:.3f}", "SWR", swr_color),
        _hero_card(str(results.get("fb_ratio", "-")), "F/B (dB)", BLUE),
    ]
    row = Table([cards], colWidths=[2.2 * inch] * 3)
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return row


def _hero_row2(results):
    """Second hero metrics row."""
    cards = [
        _hero_card(f"{results.get('multiplication_factor', '-')}x", "POWER MULT", ORANGE),
        _hero_card(f"{results.get('antenna_efficiency', '-')}%", "EFFICIENCY", PINK),
        _hero_card(f"{results.get('takeoff_angle', '-')}°", "TAKEOFF", PURPLE),
    ]
    row = Table([cards], colWidths=[2.2 * inch] * 3)
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return row


def _power_table(results):
    """Power analysis table."""
    data = [
        ["", "@ 100W", "@ 1kW"],
        ["Forward", f"{results.get('forward_power_100w', '-')}W", f"{results.get('forward_power_1kw', '-')}W"],
        ["Reflected", f"{results.get('reflected_power_100w', '-')}W", f"{results.get('reflected_power_1kw', '-')}W"],
    ]
    t = Table(data, colWidths=[2 * inch, 2 * inch, 2 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MID_GRAY),
        ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), LIGHT_GRAY),
        ("TEXTCOLOR", (0, 1), (0, 1), GREEN),
        ("TEXTCOLOR", (0, 2), (0, 2), RED),
        ("TEXTCOLOR", (1, 1), (-1, -1), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, MID_GRAY),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def _wind_table(wind_load):
    """Wind force by speed table."""
    data = [["MPH", "Force (lbs)", "Torque (ft-lbs)"]]
    ratings = wind_load.get("wind_ratings", {})
    for mph in ["50", "70", "80", "90", "100", "120"]:
        r = ratings.get(mph)
        if r:
            data.append([mph, str(r.get("force_lbs", "-")), str(r.get("torque_ft_lbs", "-"))])
    if len(data) == 1:
        return Spacer(1, 0)
    t = Table(data, colWidths=[1.5 * inch, 2 * inch, 2 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MID_GRAY),
        ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), LIGHT_GRAY),
        ("TEXTCOLOR", (0, 1), (-1, -1), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, MID_GRAY),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def generate_spec_sheet_pdf(inputs: dict, results: dict, user_email: str = "guest", gain_mode: str = "realworld") -> bytes:
    """Generate a professional antenna spec sheet PDF. Returns PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
    )

    story = []
    sp = Spacer(1, 8)
    sp_sm = Spacer(1, 4)

    orientation = inputs.get("antenna_orientation", "horizontal")
    is_dual = orientation == "dual"
    pol_label = "Dual Polarity" if is_dual else ("Horizontal" if orientation == "horizontal" else ("Vertical" if orientation == "vertical" else "45° Slant"))
    feed_label = {"gamma": "Gamma Match", "hairpin": "Hairpin Match"}.get(inputs.get("feed_type", ""), "Direct Feed")
    num_el = inputs.get("num_elements", 2)

    # Title
    story.append(Paragraph(f"{num_el}-Element {pol_label} Yagi Antenna Spec Sheet", STYLES["title"]))
    band_name = results.get("band_info", {}).get("name", inputs.get("band", ""))
    story.append(Paragraph(f"{band_name} | {inputs.get('frequency_mhz', '')} MHz | {feed_label}", STYLES["subtitle"]))
    if results.get("dual_polarity_info"):
        story.append(Paragraph(results["dual_polarity_info"].get("description", ""), _style("dp", fontSize=9, textColor=ORANGE)))
    story.append(sp)

    # Hero metrics
    story.append(_hero_row(results))
    story.append(sp_sm)
    story.append(_hero_row2(results))
    story.append(sp)

    # Configuration
    story.append(_section_header("Configuration", CYAN))
    story.append(sp_sm)
    el_count = f"{num_el} per pol ({num_el * 2} total)" if is_dual else str(num_el)
    mount_label = {"bonded": "Bonded (Elements to Boom)", "insulated": "Insulated (Sleeves)"}.get(inputs.get("boom_mount", ""), "Non-Conductive Boom")
    story.append(_spec_rows([
        ("Band", band_name),
        ("Center Frequency", f"{inputs.get('frequency_mhz', '')} MHz"),
        ("Polarization", pol_label),
        ("Feed System", feed_label),
        ("Elements", el_count),
        ("Height", f"{inputs.get('height_from_ground', '')} {inputs.get('height_unit', 'ft')}"),
        ("Boom", f"{inputs.get('boom_diameter', '')} {inputs.get('boom_unit', 'inches')} OD"),
        ("Boom Mount", mount_label),
        ("Gain Mode", "Real World" if gain_mode == "realworld" else "Free Space"),
    ]))
    story.append(sp)

    # Element Dimensions
    elements = inputs.get("elements", [])
    if elements:
        story.append(_section_header("Element Dimensions", ORANGE))
        story.append(sp_sm)
        story.append(_element_table(elements))
        story.append(sp)

    # Signal Performance
    story.append(_section_header("Signal Performance", GREEN))
    story.append(sp_sm)
    signal_rows = [
        ("Gain", f"{results.get('gain_dbi', '-')} dBi"),
        ("Base Free-Space Gain", f"{results.get('base_gain_dbi', '-')} dBi"),
        ("Multiplication Factor", f"{results.get('multiplication_factor', '-')}x"),
        ("Efficiency", f"{results.get('antenna_efficiency', '-')}%"),
    ]
    accents = {"Gain": GREEN, "Multiplication Factor": ORANGE}
    gb = results.get("gain_breakdown")
    if gb:
        signal_rows.append(("Element Lookup", f"{gb.get('standard_gain', '-')} dBi"))
        adj = gb.get("boom_adj", 0)
        signal_rows.append(("Boom Adjustment", f"{'+' if adj >= 0 else ''}{adj} dB"))
        if gb.get("taper_bonus", 0) > 0:
            signal_rows.append(("Taper Bonus", f"+{gb['taper_bonus']} dB"))
        if gb.get("height_bonus", 0) > 0:
            signal_rows.append(("Height/Ground", f"+{gb['height_bonus']} dB"))
        if gb.get("boom_bonus", 0) > 0:
            signal_rows.append(("Boom Bonus", f"+{gb['boom_bonus']} dB"))
        if gb.get("ground_type"):
            signal_rows.append(("Ground Type", f"{gb['ground_type']} ({gb.get('ground_scale', '-')}x)"))
        if gb.get("dual_active_bonus", 0) > 0:
            signal_rows.append(("H+V Active Bonus", f"+{gb['dual_active_bonus']} dB"))
            accents["H+V Active Bonus"] = ORANGE
        signal_rows.append(("Final Gain", f"{gb.get('final_gain', results.get('gain_dbi', '-'))} dBi"))
        accents["Final Gain"] = GREEN
    story.append(_spec_rows(signal_rows, accents))
    story.append(sp)

    # SWR & Impedance
    story.append(_section_header("SWR & Impedance", RED))
    story.append(sp_sm)
    swr = results.get("swr", 0)
    swr_color = GREEN if swr <= 1.5 else (ORANGE if swr <= 2.0 else RED)
    swr_rows = [
        ("SWR", f"{swr:.3f}:1"),
        ("SWR Rating", results.get("swr_description", "-")),
    ]
    swr_accents = {"SWR": swr_color}
    mi = results.get("matching_info")
    if mi and results.get("feed_type", "direct") != "direct":
        swr_rows.append(("Match Type", mi.get("type", "-").upper()))
        swr_rows.append(("Before Match", f"{mi.get('original_swr', '-')}:1"))
        swr_rows.append(("After Match", f"{mi.get('matched_swr', '-')}:1"))
        swr_accents["After Match"] = GREEN
        swr_rows.append(("Bandwidth Effect", mi.get("bandwidth_effect", "-")))
    swr_rows.extend([
        ("Impedance Range", f"{results.get('impedance_low', '-')} - {results.get('impedance_high', '-')} \u03a9"),
        ("Return Loss", f"{results.get('return_loss_db', '-')} dB"),
        ("Mismatch Loss", f"{results.get('mismatch_loss_db', '-')} dB"),
    ])
    story.append(_spec_rows(swr_rows, swr_accents))
    story.append(sp)

    # Radiation Pattern
    story.append(_section_header("Radiation Pattern", BLUE))
    story.append(sp_sm)
    story.append(_spec_rows([
        ("F/B Ratio", f"{results.get('fb_ratio', '-')} dB"),
        ("F/S Ratio", f"{results.get('fs_ratio', '-')} dB"),
        ("Horizontal Beamwidth", f"{results.get('beamwidth_h', '-')}°"),
        ("Vertical Beamwidth", f"{results.get('beamwidth_v', '-')}°"),
    ], {"F/B Ratio": BLUE}))
    story.append(sp)

    # Propagation
    story.append(_section_header("Propagation", PURPLE))
    story.append(sp_sm)
    story.append(_spec_rows([
        ("Take-off Angle", f"{results.get('takeoff_angle', '-')}°"),
        ("Rating", results.get("takeoff_angle_description", "-")),
        ("Height Performance", results.get("height_performance", "-")),
        ("Noise Level", results.get("noise_level", "-")),
    ], {"Take-off Angle": PURPLE}))
    if results.get("noise_description"):
        story.append(Paragraph(results["noise_description"], STYLES["note"]))
    story.append(sp)

    # Bandwidth
    bw_title = "Bandwidth (per beam)" if results.get("dual_polarity_info") else "Bandwidth"
    story.append(_section_header(bw_title, ORANGE))
    story.append(sp_sm)
    bw_label = "Bandwidth per Beam" if results.get("dual_polarity_info") else "Total Bandwidth"
    story.append(_spec_rows([
        (bw_label, f"{results.get('bandwidth', '-')} MHz"),
        ("Usable @ 1.5:1 SWR", f"{results.get('usable_bandwidth_1_5', '-')} MHz"),
        ("Usable @ 2.0:1 SWR", f"{results.get('usable_bandwidth_2_0', '-')} MHz"),
    ], {bw_label: ORANGE}))
    story.append(sp)

    # Dual Polarity (conditional)
    dpi = results.get("dual_polarity_info")
    if dpi:
        story.append(_section_header("Dual Polarity", ORANGE))
        story.append(sp_sm)
        story.append(_spec_rows([
            ("Configuration", dpi.get("description", "-")),
            ("Gain per Polarization", f"{dpi.get('gain_per_polarization_dbi', '-')} dBi"),
            ("Cross-Coupling Bonus", f"+{dpi.get('coupling_bonus_db', '-')} dB"),
            ("F/B Improvement", f"+{dpi.get('fb_bonus_db', '-')} dB"),
        ], {"Cross-Coupling Bonus": GREEN, "F/B Improvement": BLUE}))
        story.append(sp)

    # Stacking (conditional)
    si = results.get("stacking_info")
    if results.get("stacking_enabled") and si:
        story.append(_section_header("Stacking", PINK))
        story.append(sp_sm)
        layout_desc = f"{si.get('num_antennas', '')} in 2x2 Quad (H-Frame)" if si.get("layout") == "quad" else f"{si.get('num_antennas', '')} stacked {si.get('orientation', '')}"
        stacking_rows = [
            ("Antennas", layout_desc),
            ("Spacing", f"{si.get('spacing', '')} {si.get('spacing_unit', '')} ({si.get('spacing_wavelengths', 0):.2f}\u03bb)"),
            ("Spacing Status", si.get("spacing_status", "-")),
            ("Isolation", f"~{si.get('isolation_db', '-')}dB"),
            ("Gain Increase", f"+{si.get('gain_increase_db', '-')} dB"),
            ("Stacked Gain", f"{results.get('stacked_gain_dbi', '-')} dBi"),
            ("Optimal Spacing", f"{si.get('optimal_spacing_ft', '-')}'"),
            ("Min Spacing", f"{si.get('min_spacing_ft', '-')}'"),
        ]
        status = si.get("spacing_status", "")
        status_color = GREEN if status == "Optimal" else (ORANGE if status == "Good" else RED)
        stacking_accents = {"Gain Increase": GREEN, "Stacked Gain": PINK, "Spacing Status": status_color}
        story.append(_spec_rows(stacking_rows, stacking_accents))

        ps = si.get("power_splitter")
        if ps:
            story.append(sp_sm)
            story.append(Paragraph('<font color="#888888">POWER SPLITTER</font>', _style("ps_hdr", fontSize=8, fontName="Helvetica-Bold", textColor=LIGHT_GRAY)))
            story.append(sp_sm)
            story.append(_spec_rows([
                ("Type", ps.get("type", "-")),
                ("Input Impedance", ps.get("input_impedance", "-")),
                ("Combined Load", ps.get("combined_load", "-")),
                ("Matching Method", ps.get("matching_method", "-")),
                ("Quarter-Wave Line", f"{ps.get('quarter_wave_ft', '-')}' ({ps.get('quarter_wave_in', '-')}\")"),
                ("Power @ 100W", f"{ps.get('power_per_antenna_100w', '-')}W each"),
                ("Power @ 1kW", f"{ps.get('power_per_antenna_1kw', '-')}W each"),
                ("Min Rating", ps.get("min_power_rating", "-")),
            ]))
        story.append(sp)

    # Taper (conditional)
    ti = results.get("taper_info")
    if ti and ti.get("enabled"):
        story.append(_section_header("Element Taper", CYAN))
        story.append(sp_sm)
        story.append(_spec_rows([
            ("Taper Steps", str(ti.get("num_tapers", "-"))),
            ("Gain Bonus", f"+{ti.get('gain_bonus', '-')} dB"),
            ("Bandwidth Improvement", ti.get("bandwidth_improvement", "-")),
        ], {"Gain Bonus": GREEN}))
        story.append(sp)

    # Corona Balls (conditional)
    ci = results.get("corona_info")
    if ci and ci.get("enabled"):
        story.append(_section_header("Corona Ball Tips", DEEP_ORANGE))
        story.append(sp_sm)
        story.append(_spec_rows([
            ("Diameter", f'{ci.get("diameter", "-")}"'),
            ("Corona Reduction", f"{ci.get('corona_reduction', '-')}%"),
            ("Bandwidth Effect", f"x{ci.get('bandwidth_effect', '-')}"),
        ], {"Corona Reduction": GREEN}))
        story.append(sp)

    # Power Analysis (conditional)
    if results.get("forward_power_100w"):
        story.append(_section_header("Power Analysis", RED))
        story.append(sp_sm)
        story.append(_power_table(results))
        story.append(sp)

    # Ground Radials (conditional)
    gri = results.get("ground_radials_info")
    if gri:
        story.append(_section_header("Ground Radial System", LIME))
        story.append(sp_sm)
        impr = gri.get("estimated_improvements", {})
        story.append(_spec_rows([
            ("Ground Type", gri.get("ground_type", "-")),
            ("Number of Radials", str(gri.get("num_radials", "-"))),
            ("Radial Length", f"{gri.get('radial_length_ft', '-')}' ({gri.get('radial_length_in', '-')}\")"),
            ("Total Wire", f"{gri.get('total_wire_length_ft', '-')}'"),
            ("SWR Improvement", impr.get("swr_improvement", "-")),
            ("Efficiency Bonus", f"+{impr.get('efficiency_bonus_percent', '-')}%"),
        ], {"Efficiency Bonus": LIME}))
        story.append(sp)

    # Boom Correction (conditional)
    bci = results.get("boom_correction_info")
    if bci:
        mt = bci.get("boom_mount", "bonded")
        mt_label = {"bonded": "Bonded", "insulated": "Insulated", "nonconductive": "Non-Conductive"}.get(mt, mt)
        mt_color = {"bonded": ORANGE, "insulated": BLUE}.get(mt, GREEN)
        story.append(_section_header(f"Boom Correction: {mt_label}", mt_color))
        story.append(sp_sm)
        boom_rows = [("Mount Type", {"bonded": "Elements Bonded to Metal Boom", "insulated": "Insulated on Metal Boom"}.get(mt, "Non-Conductive Boom"))]
        if bci.get("enabled"):
            boom_rows.extend([
                ("Correction", f"{(bci.get('correction_multiplier', 0) * 100):.0f}% of full DL6WU"),
                ("Boom/Element Ratio", f"{bci.get('boom_to_element_ratio', '-')}:1"),
                ("Shorten Each Element", f'{bci.get("correction_total_in", "-")}" total'),
                ("Per Side", f'{bci.get("correction_per_side_in", "-")}"'),
                ("Gain Effect", f"{bci.get('gain_adj_db', '-')} dB"),
                ("F/B Effect", f"{bci.get('fb_adj_db', '-')} dB"),
                ("Impedance Shift", f"{bci.get('impedance_shift_ohm', '-')} ohm"),
            ])
        story.append(_spec_rows(boom_rows, {"Mount Type": mt_color, "Shorten Each Element": ORANGE}))

        # Corrected cut list
        corrected = bci.get("corrected_elements", [])
        if corrected:
            story.append(sp_sm)
            story.append(Paragraph('<font color="#4CAF50">CORRECTED CUT LIST</font>', _style("cl", fontSize=8, fontName="Helvetica-Bold", textColor=GREEN)))
            story.append(sp_sm)
            cut_data = [["Element", "Original", "Cut To"]]
            for el in corrected:
                etype = el.get("type", "")
                cut_data.append([etype.capitalize(), f'{el.get("original_length", "-")}"', f'{el.get("corrected_length", "-")}"'])
            ct = Table(cut_data, colWidths=[2 * inch, 2 * inch, 2 * inch])
            ct.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), MID_GRAY),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#1a2a1a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), LIGHT_GRAY),
                ("TEXTCOLOR", (0, 1), (-1, -1), WHITE),
                ("TEXTCOLOR", (-1, 1), (-1, -1), GREEN),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (-1, 1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, MID_GRAY),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]))
            story.append(ct)

        if bci.get("description"):
            story.append(sp_sm)
            story.append(Paragraph(bci["description"], STYLES["note"]))
        story.append(sp)

    # Wind Load (conditional)
    wl = results.get("wind_load")
    if wl:
        story.append(_section_header("Wind Load & Mechanical", DEEP_ORANGE))
        story.append(sp_sm)
        surv = wl.get("survival_mph", 0)
        surv_color = GREEN if surv >= 90 else (ORANGE if surv >= 70 else RED)
        wind_rows = [
            ("Total Wind Area", f"{wl.get('total_area_sqft', '-')} sq ft"),
            ("Total Weight", f"{wl.get('total_weight_lbs', '-')} lbs"),
            ("Elements", f"{wl.get('element_weight_lbs', '-')} lbs"),
            (f"Boom ({wl.get('boom_length_ft', '-')}ft)", f"{wl.get('boom_weight_lbs', '-')} lbs"),
            ("Hardware/Truss", f"{wl.get('hardware_weight_lbs', '-')} lbs"),
            ("Turn Radius", f"{wl.get('turn_radius_ft', '-')}' ({wl.get('turn_radius_in', '-')}\")"),
            ("Survival Rating", f"{surv} mph"),
        ]
        story.append(_spec_rows(wind_rows, {"Total Weight": DEEP_ORANGE, "Survival Rating": surv_color}))
        story.append(sp_sm)
        story.append(Paragraph("WIND FORCE BY SPEED", _style("wf", fontSize=8, fontName="Helvetica-Bold", textColor=LIGHT_GRAY)))
        story.append(sp_sm)
        story.append(_wind_table(wl))
        story.append(sp)

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(sp_sm)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Generated {now} | {user_email} | SMA Antenna Calculator", STYLES["footer"]))

    # Build with dark background
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(DARKER_BG)
        canvas.rect(0, 0, letter[0], letter[1], fill=1, stroke=0)
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
