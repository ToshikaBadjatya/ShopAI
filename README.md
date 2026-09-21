# ShopAI

## AI-Powered Outfit Planning & Shopping Assistant

ShopAI helps users decide what to wear, discover the best products online, and visualize outfits before making a purchase.

---

# Problem Statement

**Core Problem:** Women often spend a lot of time and money on outfit decisions due to decision fatigue, unlimited market options, limited personalisation, regrettable purchases, and poor reusability — solved via smart recommendations, marketplace discovery, visualisation, and personalised styling.

Shopping for clothing is often fragmented and time-consuming. Users struggle with:

- Deciding what to wear for a specific occasion
- Remembering what they already own in their wardrobe
- Searching across multiple marketplaces to find suitable products
- Comparing alternatives fairly across price, reviews, and style
- Understanding how an outfit will actually look on them before purchasing

These challenges often lead to decision fatigue, poor purchase confidence, and higher return rates.

**Goal:** Build an everyday-use AI assistant that reliably meets shopping requirements.
**Future Goal:** Become a marketplace in its own right — place orders and track them.

---

# Customer Discovery

## What we heard

Interviews and surveys probed how long outfit decisions take, which occasions are hardest to dress for, prior experience with AI-generated style advice, go-to inspiration sources, online vs. offline shopping habits, self-knowledge of personal style, past purchase regret, repeat-vs-experiment tendencies, and comfort with AI image edits.

**Key insights:**
- Gen Z spends the most time deciding — they prioritize experimentation over basics and struggle to land on combinations.
- Millennial working women and housewives play it safer, but feel the sharpest decision pressure around office and family events, where looking "appropriate" matters most.
- Most women disliked existing AI-recommended styles for feeling robotic and generic — Pinterest and Instagram remain the top inspiration sources, with friends and family a close second.
- Online shopping is rising fast among Gen Z and Millennials for convenience, variety, and cost — but size, color, and fit mismatches are the top complaint.
- Most purchase regret traces back to outfits that didn't suit the wearer's style or body type.
- ~60% of women have used AI tools for minor edits and are comfortable with it, but privacy and safety remain top of mind.

## Personas

| Persona | Profile | Behavior |
|---|---|---|
| Anjali | 38, Housewife | Plays it safe, often uncertain about occasion-specific outfits |
| Riya | 20, Student | Loves experimentation, trend- and social-driven |
| Aisha | 22, Influencer | Very particular about looks, spends real time curating outfits |
| Nandani | 32, Working Professional | Time-constrained, wants crisp corporate styling, prefers real-person references |

## Jobs to Be Done

- I want a solution that understands my style and recommends something I can actually wear.
- I want suggestions that are socially acceptable and on-trend so I can look fashionable.
- I want to visualize how it will look on me, get validation, and then decide to buy.
- I want a stylist that learns my style and shopping patterns so I avoid fashion mistakes and return pains.
- I want a marketplace comparator that finds the most economical deal for my preferences.
- I want a wardrobe manager that knows what I own and restyles it so I can reuse my outfits.

## Competitive Landscape

| Competitor | Strength | Gap |
|---|---|---|
| Generic AI tools | Recommendation & visualization | Boring, generic output |
| Meesho, Flipkart | Marketplace & recommendation | Time-consuming, low personalization |
| Personal stylists | High-quality, tailored advice | Expensive |
| Instagram / Pinterest | Rich inspiration | Manual, time-consuming, low personalization |

ShopAI is positioned to cover all four gaps at once: personalized, fast, low-cost, and marketplace-aware.

## Prioritization (Impact / Effort / Feasibility / Cost)

| Feature | Impact | Effort | Feasibility | Cost | Version |
|---|---|---|---|---|---|
| Recommendation | High | Medium | Medium | Low–Medium | V0 |
| Visualization | High | Medium | Medium | Medium | V0 |
| Wardrobe / Inventory | Medium | Low (identify + store) | High (vision model) | High (multiple visualizations) | V1 |
| Marketplace | Low | Medium | Low (API constraints) | Medium–High | V2 |

---

# Product Overview

ShopAI is an AI-powered outfit planning and shopping assistant that helps users:

1. Plan outfits based on occasions, preferences, and body type
2. Discover matching products from online marketplaces
3. Visualize complete outfits before purchasing

The platform combines:

- AI-driven outfit planning
- Marketplace product discovery
- Personalized outfit visualization

---

# Key Features (V1)

### 1. Occasion / Experimental Styling (V0)

- Deploys a recommendation engine that narrows choices based on occasion, mood, and personal preference
- Asks relevant clarifying questions (age, event, etc.) to confirm choices; pulls in weather and past purchase history as local factors, plus Instagram/Pinterest trend signals
- Shows the top 4 options and asks the user which one might work; if one is close, asks what specifically isn't working
- On selection, offers a preview — an AI-rendered model recommendation of the outfit
- If nothing works, asks for body-type details or an image to visualize the outfit on the user directly, then saves those details for next time
- Optionally rates the outfit (and suggests improvements below a threshold score) or lets the user share it with a friend for feedback

**User journeys observed per persona:**
- **Confident but risk-averse** — already knows the event brief (e.g. "office client meeting, professional, not too revealing, avoid blue"), fears over/under-dressing, wants multiple iterations and visualization for confidence.
- **Experimental & trendy** — wants a statement look distinct from their everyday style (e.g. "show me a trendy look for prom"), open to inspiration, trusts social validation.
- **Confused learner** — abrupt, low-context prompts ("I need to go to a dinner party, don't know what to wear"). Flow starts by building basic info and a personal-style profile before continuing, and gains trust from detailed "why this works" explanations and visualization on their own image.

### 2. Daily Styling & Wardrobe Usability (V1)

- Lets the user build a wardrobe by photographing pieces they own; identifies each item and its core properties into a database
- Learns daily outfit patterns — office, gym, family dinner — to build context on how the user likes to dress, including "dress like this person/style" reference extraction from the internet
- Can be scheduled to proactively suggest an outfit from the wardrobe at set times each day, or on request
- Bonus: visualization based on saved body parameters

**User journeys observed per persona:**
- **The Repeater** — wants to save time above all; repeats outfits straight from the wardrobe with few options and high confidence, at high frequency.
- **The Varietist** — wants variety across daily themes; simple looks come from the wardrobe alone, complex ones mix wardrobe + marketplace. Expects ShopAI to remember routines/plans and remind them explicitly (e.g. "plan an outfit for today's office" pulls from the wardrobe, checks repeat history, and offers both wardrobe-only and wardrobe+buy options).

### 3. Marketplace Discovery (V2)

- On completion of any request, if the wardrobe is populated but the suggested piece isn't in it, offers to search the marketplace for it
- Asks about pricing constraints, runs marketplace research, evaluates the options, and returns the top 5 links
- Flags platforms with a high return-rate history before including them, and confirms with the user first

### 4. Outfit Visualization

- Visualize how a recommended outfit may look based on body type,  skin color etc

---

# Out of Scope (V1)

- Social shopping features
- Community interactions
- Voice-first experiences
- Direct marketplace checkout integrations

---

# Target Users

## Persona A — The Overwhelmed Decision Maker

**Goals**
- Quickly decide what to wear
- Discover suitable outfit options

**Pain Points**
- Too many fashion choices
- Lack of styling confidence

**Primary Need**
Planning + Discovery

## Persona B — Price & Time Sensitive Shopper

**Goals**
- Find 2–3 strong options quickly
- Reduce shopping time

**Pain Points**
- Excessive browsing
- Conflicting reviews

**Primary Need**
Efficient Discovery

## Persona C — Body-Image Conscious Shopper

**Goals**
- Understand what styles suit their body type

**Pain Points**
- Uncertainty about personal style
- Low confidence in purchase decisions

**Primary Need**
Visualization & Confidence Building

---

# AI UX

## Basic Entry Points

The chat surfaces three broad flows: outfit planning, outfit visualization, and error/permission handling — each with its own conversational pattern (see the mobile chat components under `src/shopai/mobile/.../reusables/chat/`).

## Constraints & Edge Cases

- **Out-of-context questions** (not shopping-related): "I'm a shopping assistant, I can't do this job."
- **Restricted tasks**: "I'm not allowed to perform this task — ask for something else."
- **System errors**: "System is down, we'll be back by (estimated time)."
- **Uncertainty**: "I'm not sure I'm understanding this right" — shows its hypothesis, or asks a clarifying question if it can't form one.
- **Ungrounded responses**: asks the user for a specific resource to refer to, rather than guessing.
- **Permission asking**: explicitly asks before using a user's image in visualization or accessing socials (MVP-scoped).
- **Progress states for longer calls**: human-readable, process-oriented status — "Scanning for socials", "Collecting inspiration", "Thinking", "Getting visuals ready", "Validating hypothesis".
- **Image previews**: rendered as small, non-clickable squares in-chat.

---

# Safety, Responsible AI & Human-in-the-Loop

ShopAI denies requests that are:

1. Outside the scope of shopping, planning, and exploring styles
2. Unsolicited visualizations that invade privacy or decency, or that mock any caste, creed, or gender
3. Image uploads that violate decency guidelines

Human-in-the-loop checkpoints run throughout the journey — confirming body-type/style assumptions before saving them, asking permission before using a user's photo, and asking before sharing an outfit externally (e.g. to a friend via WhatsApp) for feedback.

---

# Success Metrics

## North Star Metric

### Qualified Purchase Assist Rate (QPAR)

Percentage of sessions where users successfully complete:

Plan → Discover → Visualize

within a defined time window (1 hour).

## Funnel Metrics

- Intent Capture Rate
- Shortlist Completion Rate
- Product Click-Through Rate (CTR)
- Recommendation Success Rate

## Quality Metrics

- Customer Satisfaction (CSAT)
- Recommendation Trust Score
- Safety Incident Rate

## Operational Metrics

- Average Response Latency
- Cost Per Assisted Session
- Agent Success Rate

---

# System Architecture

## Why Multi-Agent Architecture?

- Reduce hallucinations through focused context windows
- Optimize cost by using specialized models
- Improve reliability through deterministic workflows
- Increase scalability through modular agents
<img width="926" height="761" alt="Screenshot 2026-09-06 at 2 20 49 AM" src="https://github.com/user-attachments/assets/96361b8f-2614-4364-9688-03d94cd529d4" />


---

# Agent Model Selection

A deterministic **Validator** guardrail runs first (workflow, not an agent) — it filters out-of-scope or malformed requests and scores the valid ones, so only relevant requests reach the LLM agents. From there, the **Recommendation Master Agent** plans and delegates to specialist sub-agents, maintaining a task ledger and sharing memory/context between them.

| Agent | Model | Speciality |
|---|---|---|
| Validator (guardrail workflow) | Deterministic / keyword-scored | Filters out-of-scope requests, scores the valid ones (High / Medium / Low) before any LLM sees them |
| Recommendation Master Agent | Gemini 2.5 Flash | Core planner — builds task/context, delegates to specialists, maintains the task ledger, decides when to ask clarifying questions or request permission |
| Clarification Agent | Gemini 2.5 Flash (shared default) | Turns a Medium/Low-clarity request into the single next question to ask |
| Wardrobe Agent | Gemini 2.5 Flash | Manages the wardrobe and performs gap analysis |
| Recommendation Agent | Gemini 2.5 Flash | Generates recommendations from context |
| Recommendation Review Agent | GPT-OSS 120B (Groq) | Reviews recommendations against context (fit, occasion, budget) |
| Visualisation Agent | Nano Banana | Generates an image from the outfit description |
| MarketPlace Master Agent *(TODO)* | — | Marketplace price/inventory research and comparison — planned for V2 |
| User Shopping Agent *(TODO)* | — | Planned |

**Recommendation Master — reasoning logic:**
- Is there enough context? If not, ask more questions.
- Does the user know their own style? If not, run the style-building workflow first.
- For regular/daily outfit planning: is the wardrobe populated? If yes, style from wardrobe data; if no, run the wardrobe-building flow.

Color legend used in the system diagrams: **Blue** = workflows, **Yellow** = master/controller agents, **Pink** = sub-agents, **Light Pink** = tools, **Green** = RAG/grounding.

---

# Technology Stack

| Layer | Technology |
|---------|------------|
| Mobile App | Android |
| Backend API | FastAPI |
| Agent Framework | CrewAI |
| Planning / Recommendation Models | Gemini 2.5 Flash |
| Review Model | GPT-OSS 120B (Groq) |
| Intent & Guardrails | Deterministic scoring + Gemma 4 31B |
| Image Generation | Google Nano Banana |
| Persistence | Supabase (Postgres + RLS) |


---

# Future Enhancements

- Personalized style memory
- AI stylist chat experience
- Social outfit sharing
- Marketplace agent (V2) — price comparison and top-5 link discovery for pieces missing from the wardrobe

---

# Further Reading

Full product spec — customer discovery, user journeys, AI UX, safety & human-in-the-loop, system design, and individual agent designs:

https://sandy-source-975.notion.site/ShopAI-3b2fc9a58c1d80409af5df693f396762
