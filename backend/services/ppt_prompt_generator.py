from typing import Dict, Any


def generate_ppt_prompt(report: Dict[str, Any]) -> str:
    company = report.get("company_name", "the company")
    tagline = report.get("tagline", "")
    industry = report.get("industry", "Technology")
    ceo = report.get("ceo", "")
    founded = report.get("founding_year", "")
    hq = report.get("hq_location", "")

    founders_str = ", ".join(report.get("founders") or [])
    current = report.get("current_projects") or []
    competitors = report.get("competitors") or []
    matching = report.get("matching_skills") or []
    diff = report.get("differentiators") or []
    timeline = report.get("growth_timeline") or []
    questions = report.get("interview_questions") or []
    ci = report.get("culture_insights") or {}
    flags = report.get("red_flags") or []
    tips = report.get("insider_tips") or []
    strategy = report.get("application_strategy", "")
    hiring_case = report.get("hiring_case", "")

    return f"""╔══════════════════════════════════════════════════════════════════╗
║     COMPANYIQ — AI PRESENTATION GENERATOR PROMPT                 ║
║     Company: {company:<50}║
╚══════════════════════════════════════════════════════════════════╝

COPY THIS ENTIRE PROMPT AND PASTE INTO CHATGPT / GEMINI / GAMMA / BEAUTIFUL.AI

═══════════════════════════════════════════════════════════════════
DESIGN BRIEF
═══════════════════════════════════════════════════════════════════

Create a professional, visually stunning 20-slide presentation titled:
"{company}: Company Intelligence & Candidate Fit Report"

Theme: Dark navy (#0A1628) background, gold (#C9A84C) accents, white body text
Font: Inter or Helvetica Neue (Bold for headlines, Regular for body)
Style: Executive briefing / premium corporate
Format: 16:9 widescreen

═══════════════════════════════════════════════════════════════════
SLIDE-BY-SLIDE CONTENT
═══════════════════════════════════════════════════════════════════

SLIDE 1 — TITLE
• Main title: {company}
• Subtitle: "{tagline}"
• Label: "Company Intelligence Report"
• Design: Full dark navy, large white company name centered, gold tagline italic below,
  thin gold horizontal rule, date stamp at bottom right

SLIDE 2 — COMPANY AT A GLANCE
• 6-stat grid (icon + value):
  - Founded: {founded}
  - HQ: {hq}
  - Industry: {industry}
  - Size: {report.get('company_size','—')}
  - Ticker: {report.get('stock_ticker','Private')}
  - CEO: {ceo}
• Design: Dark navy cards, large gold numbers, white labels, minimal icons

SLIDE 3 — LEADERSHIP
• Founders: {founders_str or 'See report'}
• CEO: {ceo}
• Other C-suite: {', '.join((report.get('c_suite') or [])[:4])}
• Design: Profile card grid, circular avatar placeholders, gold border on CEO card

SLIDE 4 — ORIGIN STORY
• Content: {(report.get('origin_story') or '')[:280]}...
• Design: Large pull quote left, subtle timeline visual right, navy background

SLIDE 5 — GROWTH TIMELINE
• Milestones:
{chr(10).join(f"  • {i.get('year','')} — {i.get('event','')}" for i in timeline[:7])}
• Design: Horizontal timeline bar, gold dots at each milestone, year labels above,
  event descriptions below

SLIDE 6 — PAST CHALLENGES & RESILIENCE
• Show 2-3 challenge → resolution pairs:
{chr(10).join(f"  Challenge: {i.get('challenge','')} → {i.get('resolution','')[:60]}" for i in (report.get('past_challenges') or [])[:3])}
• Design: Red challenge card with arrow transforming into green resolution card

SLIDE 7 — CURRENT PRODUCTS & PROJECTS
• Products:
{chr(10).join(f"  • {i.get('name','')}: {i.get('description','')[:70]}" for i in current[:5])}
• Design: Product cards in 2-column grid, gold top border, icon placeholder per card

SLIDE 8 — FUTURE ROADMAP
• Initiatives:
{chr(10).join(f"  • {i.get('initiative','')} ({i.get('timeline','')})" for i in (report.get('future_roadmap') or [])[:5])}
• Design: Forward-looking roadmap with year markers, future phases in lighter gold

SLIDE 9 — COMPETITIVE LANDSCAPE
• Competitors:
{chr(10).join(f"  vs. {i.get('name','')}: {i.get('comparison','')[:70]}" for i in competitors[:4])}
• Design: Comparison matrix, {company} column highlighted in gold

SLIDE 10 — KEY DIFFERENTIATORS
• {chr(10).join(f"  {j+1}. {d}" for j,d in enumerate(diff[:5]))}
• Design: Numbered list, large gold numbers, concise statements, icon per item

SLIDE 11 — STRUGGLES TURNED SUCCESS
• 2-3 turnaround stories
{chr(10).join(f"  {i.get('project','')}: {i.get('struggle','')[:50]} → {i.get('outcome','')[:50]}" for i in (report.get('struggles_turned_success') or [])[:3])}
• Design: Before/after cards, "setback → breakthrough" visual metaphor

SLIDE 12 — CULTURE & WORK ENVIRONMENT
• Work-Life Balance: {ci.get('work_life_balance','—')[:80]}
• Innovation: {ci.get('innovation_style','—')[:80]}
• Growth: {ci.get('career_growth','—')[:80]}
• Perks: {', '.join((ci.get('notable_perks') or [])[:4])}
• Design: 2×2 insight cards, cultural icons, gold accent

SLIDE 13 — RED FLAGS & DUE DILIGENCE
• Flags to investigate:
{chr(10).join(f"  ⚠ {f}" for f in flags[:4])}
• Design: Amber/red warning card, honest framing ("Questions to ask before joining")

SLIDE 14 — TRANSITION: CANDIDATE FIT
• Headline: "Why This Candidate?"
• Subtext: "Personalized Fit Analysis"
• Design: Full navy, large centered gold headline, dividing line

SLIDE 15 — MATCHING SKILLS
• Matched skills:
{chr(10).join(f"  ✦ {skill}" for skill in matching[:7])}
• Design: Skill badges in gold/navy, checkmark icons, competency mapping

SLIDE 16 — CONTRIBUTION TO CURRENT PROJECTS
• {(report.get('contribution_current') or '')[:300]}
• Design: Current project icons linked to candidate contributions by arrows

SLIDE 17 — IMPACT ON FUTURE ROADMAP
• {(report.get('contribution_future') or '')[:300]}
• Design: Timeline visual with candidate's role annotated in gold callouts

SLIDE 18 — COMPETITIVE ADVANTAGE
• {(report.get('competitive_advantage') or '')[:300]}
• Design: Competitive matrix with "this hire" as differentiator column

SLIDE 19 — APPLICATION STRATEGY & INSIDER TIPS
• Strategy: {strategy[:200] if strategy else 'Refer to full report'}
• Tips:
{chr(10).join(f"  ✦ {tip}" for tip in tips[:5])}
• Design: Action items in gold checkboxes, clean list layout

SLIDE 20 — WHY HIRE THIS CANDIDATE
• {hiring_case[:400] if hiring_case else 'Refer to full report'}
• Design: Executive summary with gold border, 3-4 bold highlights, no clutter

SLIDE 21 — INTERVIEW QUESTIONS PREVIEW
• Top 5 questions to prepare:
{chr(10).join(f"  {j+1}. [{q.get('category','')}] {q.get('question','')}" for j,q in enumerate(questions[:5]))}
• Design: Q-card grid, category color-coded

SLIDE 22 — CLOSING
• Headline: "The Right Candidate. The Right Company. The Right Time."
• Design: Full dark navy, centered gold headline, horizontal rule, CompanyIQ branding

═══════════════════════════════════════════════════════════════════
DESIGN SPECIFICATIONS
═══════════════════════════════════════════════════════════════════

COLORS:
• Primary background:   #0A1628
• Secondary background: #0D2137
• Gold accent:          #C9A84C
• Gold light:           #E8C56E
• Body text:            #FFFFFF
• Secondary text:       #A0AEC0
• Card background:      rgba(255,255,255,0.05)

TYPOGRAPHY:
• H1 Headlines:   Bold, 36–44pt, White or Gold
• H2 Subheadings: SemiBold, 22–28pt, White or Gold
• Body text:      Regular, 14–16pt, White
• Data callouts:  Bold, 28–48pt, Gold

LAYOUT:
• 16:9 widescreen (1920×1080)
• 80px uniform margins
• Max 6 bullet points per slide
• Prefer visuals over text blocks
• Every slide: one dominant visual hierarchy

ANIMATIONS (PowerPoint / Google Slides):
• Transitions: Fade (0.4s)
• Content: Appear by click or 0.3s stagger
• Data: Bars/numbers count up

═══════════════════════════════════════════════════════════════════
TOOL-SPECIFIC INSTRUCTIONS
═══════════════════════════════════════════════════════════════════

FOR GAMMA (gamma.app):
  Paste this full prompt → select "Dark Professional" theme → Generate
  Gamma auto-layouts all slides. Apply navy + gold brand colors.

FOR CHATGPT:
  Prefix with: "Create a full PowerPoint outline with slide titles, bullets,
  speaker notes, and design instructions for each slide based on this brief:"

FOR GOOGLE SLIDES / CANVA:
  Search template: "Dark Executive Presentation"
  Replace content slide-by-slide using the guide above.
  Set brand colors: Primary #0A1628 / Accent #C9A84C

FOR BEAUTIFUL.AI:
  Select "Sleek" template → Apply custom brand colors → Paste per-slide content

═══════════════════════════════════════════════════════════════════
Generated by CompanyIQ · {company} Report
═══════════════════════════════════════════════════════════════════
"""
