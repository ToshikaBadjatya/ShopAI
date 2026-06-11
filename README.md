# ShopAI

## AI-Powered Outfit Planning & Shopping Assistant

ShopAI helps users decide what to wear, discover the best products online, and visualize outfits before making a purchase.

---

# Problem Statement

Shopping for clothing is often fragmented and time-consuming.

Users struggle with:

- Deciding what to wear for a specific occasion
- Searching across multiple marketplaces to find suitable products
- Comparing alternatives fairly across price, reviews, and style
- Understanding how an outfit will actually look on them before purchasing

These challenges often lead to decision fatigue, poor purchase confidence, and higher return rates.

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

### Outfit Planning

- Understands user intent from:
  - Occasion
  - Style preferences
  - Body type
- Generates Top 5 outfit recommendations
- Allows users to explore additional outfit options

### Mix & Match Recommendations

Users can start with selected clothing pieces and generate complementary outfit suggestions around them.

### Shopping Discovery

- Finds matching products across marketplaces
- Provides direct purchase links
- Supports platforms such as Myntra, Amazon, Meesho, and more

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

## 1. Planning Agent

**Responsibility:** Convert user intent into a structured outfit planning request.

- Input: User Prompt (≤200 words), Preferences (≤500 words)
- Input Tokens: ~1,300–1,600
- Output: Structured JSON (~350 tokens)
- Context Window: 4K
- Latency: 2–5 sec
- Models: GPT-4.1 Mini, Claude Sonnet 4

## 2. Recommendation Agent

**Responsibility:** Find the best outfit recommendations and shopping links.

- Input Tokens: ~900–1,300
- Output: Top recommendations + purchase links
- Context Window: 4K
- Latency: ~3 sec
- Models: Gemini Flash, GPT-4.1 Mini

## 3. Visualization Agent

**Responsibility:** Generate outfit previews.

- Output: 1024×1024 image
- Latency: 7–8 sec
- Model: Google Nano Banana

---

# High-Level Workflow

```text
User Input
     |
     v
Planning Agent
     |
     v
Structured Outfit Plan
     |
     v
Recommendation Agent
     |
     +--> Marketplace Search
     +--> Product Ranking
     |
     v
Selected links
     |
     v
Visualization Agent
     |
     v
Outfit Preview 
```

---

# Technology Stack

| Layer | Technology |
|---------|------------|
| Mobile App | Android |
| Backend API | FastAPI |
| Agent Framework | CrewAI |
| Planning Models | GPT-4.1 Mini / Claude Sonnet 4 |
| Recommendation Models | Gemini Flash |
| Image Generation | Google Nano Banana |

---

# Future Enhancements

- Personalized style memory
- AI stylist chat experience
- Social outfit sharing
