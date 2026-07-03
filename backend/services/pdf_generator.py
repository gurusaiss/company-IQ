from io import BytesIO
from typing import Any, Dict, List, Optional
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.pdfgen import canvas as pdfcanvas

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#0A1628")
NAVY_MID  = colors.HexColor("#0D2137")
GOLD      = colors.HexColor("#C9A84C")
GOLD_L    = colors.HexColor("#E8C56E")
GOLD_BG   = colors.HexColor("#F5EDD8")
WHITE     = colors.white
LIGHT     = colors.HexColor("#EEF0F3")
RED_SOFT  = colors.HexColor("#FEE2E2")
RED_DARK  = colors.HexColor("#DC2626")
GREEN_BG  = colors.HexColor("#D1FAE5")
GREEN     = colors.HexColor("#059669")
TEXT      = colors.HexColor("#1A1A2E")
TEXT_MED  = colors.HexColor("#4A5568")
TEXT_LITE = colors.HexColor("#718096")

PAGE_W, PAGE_H = A4
MARGIN     = 1.8 * cm
CONTENT_W  = PAGE_W - 2 * MARGIN

# ── Section catalogue (for TOC) ───────────────────────────────────────────────
SECTIONS = [
    ("01", "Company Overview"),
    ("02", "Founders & Leadership"),
    ("03", "Origin Story & Growth Timeline"),
    ("04", "Past Challenges & Resolutions"),
    ("05", "Current Projects & Products"),
    ("06", "Future Roadmap"),
    ("07", "Competitive Landscape"),
    ("08", "Struggles Turned Into Success"),
    ("09", "Interview Preparation"),
    ("10", "Culture & Work Environment"),
    ("11", "Red Flags & Due Diligence"),
    ("12", "Application Strategy & Insider Tips"),
    ("13", "Candidate Fit Analysis"),
]


# ── Page footer/header callback ────────────────────────────────────────────────
class _PageDecorator:
    def __init__(self, company: str):
        self.company = company

    def __call__(self, canv: pdfcanvas.Canvas, doc) -> None:
        canv.saveState()
        # Footer rule
        canv.setStrokeColor(GOLD)
        canv.setLineWidth(0.5)
        canv.line(MARGIN, 22, PAGE_W - MARGIN, 22)
        # Footer text
        canv.setFont("Helvetica", 7)
        canv.setFillColor(TEXT_LITE)
        canv.drawString(MARGIN, 13, f"CompanyIQ — {self.company} Intelligence Report — Confidential")
        canv.drawRightString(PAGE_W - MARGIN, 13, f"Page {canv.getPageNumber()}")
        canv.restoreState()


# ── Style factory ─────────────────────────────────────────────────────────────
def _S() -> Dict[str, ParagraphStyle]:
    def p(name, **kw) -> ParagraphStyle:
        return ParagraphStyle(name, **kw)

    return {
        "cov_name": p("cov_name", fontName="Helvetica-Bold", fontSize=36, textColor=WHITE,
                       alignment=TA_CENTER, leading=42, spaceAfter=6),
        "cov_tag":  p("cov_tag",  fontName="Helvetica-Oblique", fontSize=13, textColor=GOLD_L,
                       alignment=TA_CENTER, leading=18, spaceAfter=4),
        "cov_sub":  p("cov_sub",  fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#A0AEC0"),
                       alignment=TA_CENTER, spaceAfter=3),
        "cov_meta": p("cov_meta", fontName="Helvetica", fontSize=11, textColor=WHITE,
                       alignment=TA_CENTER, spaceAfter=4),
        "toc_num":  p("toc_num",  fontName="Helvetica-Bold", fontSize=10, textColor=GOLD),
        "toc_ttl":  p("toc_ttl",  fontName="Helvetica", fontSize=10, textColor=TEXT),
        "sec_hdr":  p("sec_hdr",  fontName="Helvetica-Bold", fontSize=13, textColor=WHITE,
                       alignment=TA_LEFT, leading=18),
        "sub":      p("sub",      fontName="Helvetica-Bold", fontSize=11, textColor=NAVY,
                       leading=15, spaceAfter=4, spaceBefore=10),
        "body":     p("body",     fontName="Helvetica", fontSize=10, textColor=TEXT,
                       leading=15, spaceAfter=6, alignment=TA_JUSTIFY),
        "bullet":   p("bullet",   fontName="Helvetica", fontSize=10, textColor=TEXT,
                       leading=14, spaceAfter=3, leftIndent=12),
        "yr":       p("yr",       fontName="Helvetica-Bold", fontSize=10, textColor=GOLD, leading=14),
        "ev":       p("ev",       fontName="Helvetica", fontSize=10, textColor=TEXT, leading=14),
        "ct":       p("ct",       fontName="Helvetica-Bold", fontSize=10, textColor=NAVY,
                       leading=14, spaceAfter=2),
        "cb":       p("cb",       fontName="Helvetica", fontSize=9, textColor=TEXT_MED, leading=13),
        "fit_sec":  p("fit_sec",  fontName="Helvetica-Bold", fontSize=11, textColor=GOLD,
                       leading=15, spaceBefore=10, spaceAfter=4),
        "fit_body": p("fit_body", fontName="Helvetica", fontSize=10, textColor=TEXT,
                       leading=15, spaceAfter=6, alignment=TA_JUSTIFY),
        "cat":      p("cat",      fontName="Helvetica-Bold", fontSize=9, textColor=GOLD,
                       leading=12, spaceBefore=8),
        "q":        p("q",        fontName="Helvetica-Bold", fontSize=10, textColor=TEXT,
                       leading=14, spaceAfter=2),
        "tip":      p("tip",      fontName="Helvetica-Oblique", fontSize=9, textColor=TEXT_MED,
                       leading=13, spaceAfter=6),
        "flag":     p("flag",     fontName="Helvetica", fontSize=10, textColor=RED_DARK,
                       leading=14, spaceAfter=3, leftIndent=12),
        "meta_k":   p("meta_k",   fontName="Helvetica-Bold", fontSize=9, textColor=TEXT_LITE),
        "meta_v":   p("meta_v",   fontName="Helvetica", fontSize=10, textColor=TEXT),
        "badge_init": p("badge_init", fontName="Helvetica-Bold", fontSize=28, textColor=NAVY,
                        alignment=TA_CENTER, leading=36),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────
def _banner(num_title: str, s: Dict) -> List:
    tbl = Table([[Paragraph(num_title, s["sec_hdr"])]], colWidths=[CONTENT_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return [tbl, Spacer(1, 10)]


def _gold_rule() -> HRFlowable:
    return HRFlowable(width=CONTENT_W, thickness=1.2, color=GOLD, spaceAfter=8, spaceBefore=2)


def _card(title: str, body: str, s: Dict, bg=None, accent=None) -> KeepTogether:
    bg = bg or LIGHT
    accent = accent or GOLD
    rows = [[Paragraph(title, s["ct"])], [Paragraph(body or "—", s["cb"])]]
    w = CONTENT_W - 0.4 * cm
    tbl = Table(rows, colWidths=[w])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEABOVE", (0, 0), (-1, 0), 2, accent),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
    ]))
    return KeepTogether([tbl, Spacer(1, 8)])


def _initials_badge(company_name: str, s: Dict) -> Table:
    initials = "".join(w[0].upper() for w in company_name.split()[:3] if w)[:2]
    badge_rows = [[Paragraph(initials, s["badge_init"])]]
    tbl = Table(badge_rows, colWidths=[2 * cm], rowHeights=[2 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GOLD),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", (0, 0), (-1, -1), 8),
    ]))
    return tbl


# ── Cover page ────────────────────────────────────────────────────────────────
def _cover(report: Dict, s: Dict) -> List:
    elems: List = [Spacer(1, 1.5 * cm)]
    company = report.get("company_name", "Company")

    # Badge + company block
    badge = _initials_badge(company, s)
    badge_wrap = Table([[badge]], colWidths=[CONTENT_W])
    badge_wrap.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 30),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    rows = [
        [Paragraph(company, s["cov_name"])],
    ]
    tagline = report.get("tagline")
    if tagline:
        rows.append([Paragraph(f'"{tagline}"', s["cov_tag"])])
    rows.append([Spacer(1, 10)])
    rows.append([HRFlowable(width=5 * cm, thickness=1.5, color=GOLD)])
    rows.append([Spacer(1, 12)])
    rows.append([Paragraph("COMPANY INTELLIGENCE REPORT", s["cov_sub"])])
    rows.append([Paragraph(datetime.now().strftime("%B %d, %Y"), s["cov_sub"])])
    rows.append([Spacer(1, 20)])

    for label, key in [("Founded", "founding_year"), ("HQ", "hq_location"),
                       ("Industry", "industry"), ("Size", "company_size"), ("Ticker", "stock_ticker")]:
        val = report.get(key)
        if val:
            rows.append([Paragraph(f"{label}: {val}", s["cov_meta"])])
    rows.append([Spacer(1, 12)])
    ceo = report.get("ceo")
    if ceo:
        rows.append([Paragraph(f"CEO: {ceo}", s["cov_meta"])])
    rows.append([Spacer(1, 30)])

    body_tbl = Table(rows, colWidths=[CONTENT_W])
    body_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 40),
        ("RIGHTPADDING", (0, 0), (-1, -1), 40),
    ]))

    elems += [badge_wrap, body_tbl]
    return elems


# ── Table of Contents ─────────────────────────────────────────────────────────
def _toc(s: Dict) -> List:
    elems: List = []
    elems += _banner("TABLE OF CONTENTS", s)

    rows = []
    for num, title in SECTIONS:
        rows.append([
            Paragraph(num, s["toc_num"]),
            Paragraph(title, s["toc_ttl"]),
        ])

    tbl = Table(rows, colWidths=[1.2 * cm, CONTENT_W - 1.6 * cm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, LIGHT),
    ]))
    elems += [tbl, Spacer(1, 12)]
    return elems


# ── Section builders ──────────────────────────────────────────────────────────
def _overview(report: Dict, s: Dict) -> List:
    elems = _banner("01  COMPANY OVERVIEW", s)
    rows = []
    for label, key in [("Company", "company_name"), ("Founded", "founding_year"),
                       ("Headquarters", "hq_location"), ("Industry", "industry"),
                       ("Size", "company_size"), ("Ticker", "stock_ticker"),
                       ("Website", "logo_url")]:
        val = report.get(key)
        if val:
            rows.append([Paragraph(label, s["meta_k"]), Paragraph(str(val), s["meta_v"])])
    tbl = Table(rows, colWidths=[3.2 * cm, CONTENT_W - 3.6 * cm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, LIGHT),
    ]))
    elems += [tbl, Spacer(1, 16)]
    return elems


def _leadership(report: Dict, s: Dict) -> List:
    elems = _banner("02  FOUNDERS & LEADERSHIP", s)
    ceo = report.get("ceo")
    if ceo:
        elems.append(Paragraph("Current CEO", s["sub"]))
        elems.append(Paragraph(ceo, s["body"]))
    founders = report.get("founders") or []
    if founders:
        elems.append(Paragraph("Founders", s["sub"]))
        for f in founders:
            elems.append(Paragraph(f"▸  {f}", s["bullet"]))
    c_suite = report.get("c_suite") or []
    if c_suite:
        elems.append(Paragraph("C-Suite & Key Leadership", s["sub"]))
        for person in c_suite:
            elems.append(Paragraph(f"▸  {person}", s["bullet"]))
    elems.append(Spacer(1, 12))
    return elems


def _history(report: Dict, s: Dict) -> List:
    elems = _banner("03  ORIGIN STORY & GROWTH TIMELINE", s)
    origin = report.get("origin_story")
    if origin:
        elems.append(Paragraph("Origin Story", s["sub"]))
        elems.append(Paragraph(origin, s["body"]))
    timeline = report.get("growth_timeline") or []
    if timeline:
        elems.append(Paragraph("Growth Timeline", s["sub"]))
        elems.append(_gold_rule())
        rows = []
        for item in timeline:
            rows.append([
                Paragraph(item.get("year", ""), s["yr"]),
                Paragraph(item.get("event", ""), s["ev"]),
            ])
        tbl = Table(rows, colWidths=[1.8 * cm, CONTENT_W - 2.2 * cm])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, LIGHT),
        ]))
        elems.append(tbl)
    elems.append(Spacer(1, 12))
    return elems


def _challenges(report: Dict, s: Dict) -> List:
    elems = _banner("04  PAST CHALLENGES & RESOLUTIONS", s)
    for item in (report.get("past_challenges") or []):
        elems.append(_card(f"Challenge: {item.get('challenge','')}", item.get("resolution",""), s))
    elems.append(Spacer(1, 8))
    return elems


def _current(report: Dict, s: Dict) -> List:
    elems = _banner("05  CURRENT PROJECTS & PRODUCTS", s)
    for item in (report.get("current_projects") or []):
        elems.append(_card(item.get("name",""), item.get("description",""), s))
    elems.append(Spacer(1, 8))
    return elems


def _roadmap(report: Dict, s: Dict) -> List:
    elems = _banner("06  FUTURE ROADMAP", s)
    for item in (report.get("future_roadmap") or []):
        tl = item.get("timeline","")
        title = f"{item.get('initiative','')}  [{tl}]" if tl else item.get("initiative","")
        elems.append(_card(title, item.get("description",""), s))
    elems.append(Spacer(1, 8))
    return elems


def _competition(report: Dict, s: Dict) -> List:
    elems = _banner("07  COMPETITIVE LANDSCAPE", s)
    for item in (report.get("competitors") or []):
        elems.append(_card(f"vs. {item.get('name','')}", item.get("comparison",""), s))
    differentiators = report.get("differentiators") or []
    if differentiators:
        elems.append(Paragraph("Key Differentiators", s["sub"]))
        elems.append(_gold_rule())
        for d in differentiators:
            elems.append(Paragraph(f"✦  {d}", s["bullet"]))
    elems.append(Spacer(1, 12))
    return elems


def _success(report: Dict, s: Dict) -> List:
    stories = report.get("struggles_turned_success") or []
    if not stories:
        return []
    elems = _banner("08  STRUGGLES TURNED INTO SUCCESS", s)
    for item in stories:
        body = (f"Struggle: {item.get('struggle','')}\n\n"
                f"Outcome: {item.get('outcome','')}")
        elems.append(_card(item.get("project",""), body, s, bg=GREEN_BG, accent=GREEN))
    elems.append(Spacer(1, 8))
    return elems


def _interview_prep(report: Dict, s: Dict) -> List:
    questions = report.get("interview_questions") or []
    if not questions:
        return []
    elems = _banner("09  INTERVIEW PREPARATION", s)
    elems.append(Paragraph(
        "Real questions asked at this company, organized by category.", s["body"]
    ))
    elems.append(Spacer(1, 8))

    by_cat: Dict[str, list] = {}
    for q in questions:
        cat = q.get("category", "General")
        by_cat.setdefault(cat, []).append(q)

    for cat, qs in by_cat.items():
        elems.append(Paragraph(cat, s["cat"]))
        elems.append(_gold_rule())
        for item in qs:
            elems.append(Paragraph(f"Q: {item.get('question','')}", s["q"]))
            tip = item.get("tip","")
            if tip:
                elems.append(Paragraph(f"💡 {tip}", s["tip"]))
    elems.append(Spacer(1, 12))
    return elems


def _culture(report: Dict, s: Dict) -> List:
    ci = report.get("culture_insights") or {}
    if not ci:
        return []
    elems = _banner("10  CULTURE & WORK ENVIRONMENT", s)
    fields = [
        ("Work-Life Balance", "work_life_balance"),
        ("Innovation Style", "innovation_style"),
        ("Career Growth", "career_growth"),
        ("Team Environment", "team_environment"),
    ]
    for label, key in fields:
        val = ci.get(key)
        if val:
            elems.append(Paragraph(label, s["sub"]))
            elems.append(Paragraph(val, s["body"]))
    perks = ci.get("notable_perks") or []
    if perks:
        elems.append(Paragraph("Notable Perks", s["sub"]))
        for perk in perks:
            elems.append(Paragraph(f"▸  {perk}", s["bullet"]))
    elems.append(Spacer(1, 12))
    return elems


def _red_flags(report: Dict, s: Dict) -> List:
    flags = report.get("red_flags") or []
    strategy = report.get("application_strategy") or ""
    tips = report.get("insider_tips") or []
    if not (flags or strategy or tips):
        return []

    elems = _banner("11  RED FLAGS & DUE DILIGENCE", s)
    if flags:
        elems.append(Paragraph(
            "Investigate these before accepting an offer:", s["body"]
        ))
        flag_rows = [[Paragraph(f"⚠  {f}", s["flag"])] for f in flags]
        tbl = Table(flag_rows, colWidths=[CONTENT_W - 0.4 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), RED_SOFT),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEABOVE", (0, 0), (-1, 0), 2, RED_DARK),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#FECACA")),
        ]))
        elems += [tbl, Spacer(1, 12)]

    return elems


def _strategy(report: Dict, s: Dict) -> List:
    strategy = report.get("application_strategy") or ""
    tips = report.get("insider_tips") or []
    if not (strategy or tips):
        return []

    elems = _banner("12  APPLICATION STRATEGY & INSIDER TIPS", s)
    if strategy:
        elems.append(Paragraph("Application Strategy", s["sub"]))
        strat_rows = [[Paragraph(strategy, s["fit_body"])]]
        tbl = Table(strat_rows, colWidths=[CONTENT_W])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GOLD_BG),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LINEABOVE", (0, 0), (-1, 0), 3, GOLD),
            ("BOX", (0, 0), (-1, -1), 0.5, GOLD),
        ]))
        elems += [tbl, Spacer(1, 12)]
    if tips:
        elems.append(Paragraph("Insider Tips", s["sub"]))
        elems.append(_gold_rule())
        for tip in tips:
            elems.append(Paragraph(f"✦  {tip}", s["bullet"]))
    elems.append(Spacer(1, 12))
    return elems


def _fit(report: Dict, s: Dict) -> List:
    elems: List = [PageBreak()]

    # Fit header
    fit_banner = Table(
        [[Paragraph("13  CANDIDATE FIT ANALYSIS", ParagraphStyle(
            "fh", fontName="Helvetica-Bold", fontSize=16, textColor=WHITE, alignment=TA_CENTER
        ))],
         [Paragraph("Personalized Analysis — How This Candidate Matches This Company",
                    ParagraphStyle("fs", fontName="Helvetica-Oblique", fontSize=10,
                                   textColor=GOLD_L, alignment=TA_CENTER))]],
        colWidths=[CONTENT_W],
    )
    fit_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
    ]))
    elems += [fit_banner, Spacer(1, 16)]

    matching = report.get("matching_skills") or []
    if matching:
        elems.append(Paragraph("Matching Skills & Qualifications", s["fit_sec"]))
        elems.append(_gold_rule())
        for skill in matching:
            elems.append(Paragraph(f"✦  {skill}", s["bullet"]))
        elems.append(Spacer(1, 10))

    for key, label in [
        ("contribution_current", "Contribution to Current Projects"),
        ("contribution_future",  "Impact on Future Roadmap"),
        ("competitive_advantage","Competitive Advantage This Candidate Brings"),
    ]:
        val = report.get(key)
        if val:
            elems.append(Paragraph(label, s["fit_sec"]))
            elems.append(_gold_rule())
            elems.append(Paragraph(val, s["fit_body"]))
            elems.append(Spacer(1, 8))

    hiring_case = report.get("hiring_case")
    if hiring_case:
        elems.append(Paragraph("Why This Company Should Hire This Candidate", s["fit_sec"]))
        elems.append(_gold_rule())
        case_tbl = Table([[Paragraph(hiring_case, s["fit_body"])]], colWidths=[CONTENT_W])
        case_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GOLD_BG),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LINEABOVE", (0, 0), (-1, 0), 3, GOLD),
            ("BOX", (0, 0), (-1, -1), 0.5, GOLD),
        ]))
        elems.append(case_tbl)
    return elems


# ── Main entry ────────────────────────────────────────────────────────────────
def generate_pdf(report: Dict[str, Any]) -> bytes:
    buf = BytesIO()
    company = report.get("company_name", "Company")
    decorator = _PageDecorator(company)

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=1.2 * cm,
        title=f"{company} Intelligence Report",
        author="CompanyIQ",
    )

    s = _S()
    story: List = []

    story += _cover(report, s)
    story.append(PageBreak())
    story += _toc(s)
    story.append(PageBreak())
    story += _overview(report, s)
    story += _leadership(report, s)
    story += _history(report, s)
    story += _challenges(report, s)
    story += _current(report, s)
    story += _roadmap(report, s)
    story += _competition(report, s)
    story += _success(report, s)
    story += _interview_prep(report, s)
    story += _culture(report, s)
    story += _red_flags(report, s)
    story += _strategy(report, s)
    story += _fit(report, s)

    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    return buf.getvalue()
