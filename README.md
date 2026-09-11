# ShopAI

## AI-Powered Outfit Planning & Shopping Assistant

ShopAI helps users decide what to wear, discover the best products online, and visualize outfits before making a purchase.

---

# Problem Statement

**Core Problem:** Women often spend a lot of time and money on outfit decisions due to decision fatigue, unlimited market options, limited personalisation, regrettable purchases, and poor reusability — solved via smart recommendation, marketplace discovery, visualisation, and personalised styling.

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

### 1. Occasion / Experimental Styling

- Deploys a recommendation engine that narrows choices based on occasion, mood, and personal preference
- Asks clarifying questions (age, event, etc.) to confirm choices, pulling in weather and past purchase history as local factors
- Shows the top 4 options and asks the user which one might work
- On selection, offers a preview — an AI-rendered model recommendation of the outfit
- If nothing works, asks for body-type details or an image to visualize the outfit on the user directly
- Optionally rates the outfit or lets the user share it with a friend for feedback

### 2. Daily Styling & Wardrobe Usability

- Lets the user build a wardrobe by photographing pieces they own; identifies each item and its core properties into a database
- Learns daily outfit patterns — office, gym, family dinner — to build context on how the user likes to dress
- Can be scheduled to proactively suggest an outfit from the wardrobe at set times each day
- Bonus: visualization based on saved body parameters

### 3. Marketplace Discovery (V2)

- If a recommended piece isn't in the user's wardrobe, offers to search the marketplace for it
- Runs research against pricing constraints, evaluates options, and returns the top 5 links
- Flags platforms with a high return-rate history before including them

### Outfit Visualization

- Select products for each outfit component
- Generate an AI-rendered preview
- Visualize how the final outfit may look based on body type

---

# Out of Scope (V1)

- Social shopping features
- Community interactions
- Voice-first experiences
- Marketplace inventory synchronization
- Direct checkout integrations

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

---

# Agent Architecture

A Recommendation Master agent plans and delegates to specialist sub-agents, backed by a lightweight intent/guardrail check up front.

| Agent | Model | Speciality |
|---|---|---|
| Recommendation Master Agent | Gemini 2.5 Flash | Core planner agent — builds task and context description, routes to specialists |
| Wardrobe Agent | Gemini 2.5 Flash | Manages the wardrobe and performs gap analysis |
| Recommendation Agent | Gemini 2.5 Flash | Generates recommendations from context |
| Recommendation Review Agent | GPT-OSS 120B (Groq) | Reviews recommendations against context |
| Visualisation Agent | Nano Banana | Generates an image from the outfit description |
| Intent Identification & Guardrails | Gemma 4 31B | Validates the request and clarifies user intent before it reaches the master agent |

Color legend used in the system diagrams: **Blue** = workflows, **Yellow** = master/controller agents, **Pink** = sub-agents, **Light Pink** = tools, **Green** = RAG/grounding.

---

# High-Level Workflow

<img width="1450" height="615" alt="Screenshot 2026-06-17 at 7 08 36 PM" src="https://github.com/user-attachments/assets/ca20bf5f-cb04-420c-ac5e-dc5b5d6eeeac" />


---

# Technology Stack

| Layer | Technology |
|---------|------------|
| Mobile App | Android |
| Backend API | FastAPI |
| Agent Framework | CrewAI |
| Planning / Recommendation Models | Gemini 2.5 Flash |
| Review Model | GPT-OSS 120B (Groq) |
| Intent & Guardrails Model | Gemma 4 31B |
| Image Generation | Google Nano Banana |

---

# Video Link 
https://drive.google.com/drive/folders/17XrJHqIj90X74EYwHycOArIu4pMYTrKx?usp=sharing

---

# Future Enhancements

- Personalized style memory
- AI stylist chat experience
- Social outfit sharing

---

# Further Reading

Full product spec — customer discovery, user journeys, AI UX, safety & human-in-the-loop, evaluation, metrics, prompt versioning, and cost breakdown:

https://sandy-source-975.notion.site/ShopAI-3b2fc9a58c1d80409af5df693f396762
