"""Benefits worksheet PDF export.

Renders the quiz answers plus a MatchResponse into a single PDF the user can
print or save: their answers, every matched program with its application link,
document checklist, and next steps. This is a pre-filled worksheet for the
user to bring to an agency or keep beside them while applying — it is not an
official government application form.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (HRFlowable, ListFlowable, ListItem, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from models.match_result import MatchResponse
from models.user_profile import UserProfile

_BRACKET_LABELS = {
    "<15k": "Under $15,000", "15-30k": "$15,000–$30,000", "30-50k": "$30,000–$50,000",
    "50-75k": "$50,000–$75,000", "75k+": "Over $75,000",
}
_EMPLOYMENT_LABELS = {
    "employed": "Employed", "unemployed": "Not working",
    "self_employed": "Self-employed", "recently_unemployed": "Recently lost my job",
}
_INSURANCE_LABELS = {
    "uninsured": "No insurance", "employer": "Through an employer",
    "marketplace": "Marketplace plan", "medicaid_medicare": "Medicaid or Medicare",
    "other": "Something else",
}
_CITIZENSHIP_LABELS = {
    "citizen": "Yes", "not_citizen": "No", "prefer_not_to_say": "Prefer not to say",
}


def _yesno(value) -> str:
    return "Yes" if value else "No"


def _profile_rows(profile: UserProfile) -> list[list[str]]:
    kids = ", ".join(str(a) for a in profile.children_ages) if profile.children_ages else "—"
    rows = [
        ["State", profile.state],
        ["Household size", str(profile.household_size)],
        ["Annual income", _BRACKET_LABELS.get(profile.income_bracket or "", f"${profile.annual_income:,}")],
        ["Employment", _EMPLOYMENT_LABELS.get(profile.employment_status, profile.employment_status)],
        ["Age", str(profile.age)],
        ["Children under 19", kids if profile.has_children else "None"],
        ["Someone pregnant", _yesno(profile.is_pregnant)],
        ["Someone with a disability", _yesno(profile.has_disability)],
        ["Health insurance", _INSURANCE_LABELS.get(profile.insurance_status, profile.insurance_status)],
        ["US citizen or LPR", _CITIZENSHIP_LABELS.get(profile.citizenship, profile.citizenship)],
    ]
    if profile.receiving_disability_benefits is not None:
        rows.insert(-2, ["Already receiving disability benefits", _yesno(profile.receiving_disability_benefits)])
    return rows


def render_worksheet_pdf(profile: UserProfile, result: MatchResponse) -> bytes:
    styles = getSampleStyleSheet()
    title = ParagraphStyle("wtitle", parent=styles["Title"], fontSize=20, spaceAfter=4)
    h2 = ParagraphStyle("wh2", parent=styles["Heading2"], spaceBefore=14)
    body = ParagraphStyle("wbody", parent=styles["BodyText"], fontSize=10, leading=13)
    small = ParagraphStyle("wsmall", parent=body, fontSize=8, textColor=colors.grey)
    warn = ParagraphStyle("wwarn", parent=body, textColor=colors.HexColor("#92400e"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            title="BenefitsFinder Application Worksheet")
    story = [
        Paragraph("BenefitsFinder", title),
        Paragraph("Application worksheet — your answers and the programs you may qualify for",
                  ParagraphStyle("wsub", parent=body, textColor=colors.HexColor("#1d4ed8"))),
        Paragraph(f"Generated {datetime.now().strftime('%B %d, %Y')}", small),
        Spacer(1, 10), HRFlowable(width="100%", color=colors.HexColor("#d1d5db")),
    ]

    story.append(Paragraph("Your answers", h2))
    table = Table([[Paragraph(f"<b>{k}</b>", body), Paragraph(v, body)] for k, v in _profile_rows(profile)],
                  colWidths=[2.4 * inch, 4.2 * inch])
    table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(table)

    if result.warnings:
        story.append(Paragraph("Things to watch", h2))
        for w in result.warnings:
            story.append(Paragraph(f"• {w}", warn))

    headline = (f"You may qualify for up to ${round(result.total_estimated_annual_value):,}/year "
                f"across {result.program_count} program{'s' if result.program_count != 1 else ''}"
                if result.total_estimated_annual_value > 0
                else f"{result.program_count} program{'s' if result.program_count != 1 else ''} may fit your household")
    story.append(Paragraph("Programs you may qualify for", h2))
    story.append(Paragraph(f"<b>{headline}</b>", body))
    story.append(Spacer(1, 6))

    for p in result.matched_programs:
        value = f" — ~${round(p.monthly_value_usd):,}/month" if p.monthly_value_usd > 0 else ""
        story.append(Paragraph(f"<b>{p.program}</b>{value}", body))
        story.append(Paragraph(f"Confidence: {p.confidence}. {p.reason}", body))
        if p.application_url:
            story.append(Paragraph(f'Apply: <link href="{p.application_url}"><font color="#1d4ed8">{p.application_url}</font></link>', body))
        if p.processing_time:
            story.append(Paragraph(f"Processing time: {p.processing_time}", small))
        for s in p.next_steps or []:
            line = f"{s.step}. {s.action}"
            if s.time_required:
                line += f" ({s.time_required})"
            story.append(Paragraph(line, body))
            if s.documents:
                story.append(ListFlowable(
                    [ListItem(Paragraph(d, body), leftIndent=12) for d in s.documents],
                    bulletType="bullet", leftIndent=24))
            if s.note:
                story.append(Paragraph(s.note, small))
        if p.source:
            story.append(Paragraph(f"Source: {p.source}", small))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb"), thickness=0.5))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "This worksheet is not an official application. Eligibility is estimated from your answers; "
        "the agency decides. Dollar amounts for health coverage programs are government spending "
        "per enrollee, not money you receive.", small))

    doc.build(story)
    return buf.getvalue()
