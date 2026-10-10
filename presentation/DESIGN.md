# GenBuddy DORMATHON 2026 — Design Document

## Project Identity

| Attribute | Value |
| :--- | :--- |
| Project | GenBuddy_DORMATHON_2026 |
| Track | DORMATHON 2026 Track 2 — Agentic Solutions |
| Audience | Hackathon judges (technical + business) |
| Canvas | 1280×720 (16:9) |
| Slide Count | 10 |
| Tone | Modern, professional, evidence-driven |

## Color Palette

| Role | Hex | Usage |
| :--- | :--- | :--- |
| **Primary (Navy)** | `#0B1E3F` | Cover background, title bars, section anchors |
| **Secondary (Blue)** | `#2563EB` | Highlights, accent strokes, button-like elements |
| **Accent (Cyan)** | `#06B6D4` | Data viz, comparison lines, metric accents |
| **Alert (Amber)** | `#F59E0B` | HIGH-priority callouts, comparison deltas |
| **Critical (Red)** | `#EF4444` | CRITICAL-priority callouts, failure markers |
| **Light bg** | `#F8FAFC` | Page background for content slides |
| **White** | `#FFFFFF` | Cards, text on dark, content containers |
| **Text dark** | `#0F172A` | Body text on light backgrounds |
| **Text muted** | `#64748B` | Captions, footnotes, page numbers |

## Font System

| Layer | Font (CJK / Latin) | Size | Weight | Usage |
| :--- | :--- | :--- | :--- | :--- |
| Cover title | Source Han Sans SC Heavy / Inter | 64 | 800 | Slide 1 main title |
| Page title | Source Han Sans SC Bold / Inter | 32 | 700 | Section titles (top of each slide) |
| Sub-title | Source Han Sans SC Medium / Inter | 20 | 600 | Slide sub-headings |
| Body | Source Han Sans SC Regular / Inter | 16–18 | 400 | Paragraph text |
| Caption | Source Han Sans SC Light / Inter | 12–14 | 400 | Footer, captions, page numbers |
| Anchor number | Inter / JetBrains Mono | 60–88 | 800 | Hero numbers, key data points |

## Visual Anchors & Rhythm

- **Hero pages**: 1 (Cover), 4 (Architecture), 5 (Agentic Workflow) — emphasized with full-color bars, large diagrams
- **Supporting pages**: 7 — dense information cards, comparison tables, timelines
- **Visual anchors**: each page must contain at least one element ≥ 44px height OR ≥ 40% B-zone area

## Layout & Master Grid

Three-zone master (A/B/C):
- **A · Title bar**: 0–110px (slide number, title, top accent stripe)
- **B · Content zone**: 110–640px (530px usable height)
- **C · Footer bar**: 640–720px (page number + project name)

Padding: top 24, right 48, bottom 16, left 48.

## Diagram Standards

- **Flow arrows**: stroke 2px, color #2563EB, with triangular arrowheads
- **Process boxes**: rounded 8px corners, 2px border, white fill on light pages, navy fill on dark pages
- **Comparison deltas**: ↑ red for risk, ↓ green for OK, → amber for monitor
- **Timeline ticks**: 2px circles in #2563EB with connecting #94A3B8 line
- **Status badges**: rounded-full pills, color coded (CRITICAL red, HIGH amber, INFO blue)

## Assets Inventory

| File | Source | Used on |
| :--- | :--- | :--- |
| `assets/dashboard.png` | `test_data/dashboard_playback.png` (real project) | Slide 6 |
| `assets/icon_*` | SVG inline (L3 corner badges) | All slides (top-right or footer-left) |

## Page-by-Page Plan

| # | File | Type | Role | Key Visual | Color Allocation |
| :- | :--- | :--- | :--- | :--- | :--- |
| 01 | 01_cover.slide | cover | hero | Navy full-bleed + title + subtitle | Navy 80% + cyan accent |
| 02 | 02_problem.slide | content | supporting | 3-pane problem diagram | Light bg + blue accent |
| 03 | 03_solution.slide | content | supporting | Solution flow (telemetry → AI → action) | Light bg + cyan accent |
| 04 | 04_architecture.slide | content | hero | System flow diagram with split engineering/AI halves | Light bg + dual accent |
| 05 | 05_workflow.slide | content | hero | 5-step agentic loop + plan-vs-execute | Navy panel + cyan |
| 06 | 06_demo.slide | content | supporting | Dashboard screenshot + 4 example questions | Light bg + dashboard image |
| 07 | 07_results.slide | content | supporting | Timeline + 3 work orders table | Light bg + status colors |
| 08 | 08_planning.slide | content | supporting | Side-by-side comparison (Inv 1 vs Inv 2) | Light bg + amber accent |
| 09 | 09_value.slide | content | supporting | Value bullets + Limitations table | Light bg + cyan |
| 10 | 10_conclusion.slide | ending | supporting | Summary + URL placeholder | Navy + accent |