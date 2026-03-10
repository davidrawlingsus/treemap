# MapTheGap.ai — "VoC Gone Wild" Email Sequence

## Sequence Overview

**Type:** Lead nurture with dynamic product demo
**Goal:** Convert ad signups into paying customers by showing them personalized outputs generated from their own Trustpilot data
**Audience:** DTC / ecommerce brand owners and marketers who run Facebook ads
**Trigger:** User signs up via Facebook ad (provides email + Trustpilot URL or brand name)
**Tone:** Irreverent, first-person from the "Voice of Customer" perspective — inspired by BotsGoneWild's "escaped AI" angle, except here it's the customer reviews that have broken free and started writing ads
**Length:** 6 emails over 10 days

---

## Narrative Arc

The VoC is a character. It's been locked away in a Trustpilot page, ignored, gathering dust — and it just escaped. Now it's loose inside Facebook Ads Manager, and it's writing better copy than your agency ever did. Each email escalates the story while dynamically showcasing real outputs generated from the prospect's own review data.

**Emotional progression:**
Intrigue → Surprise → Awe → Education → Urgency → Decision

---

## Sequence Overview Table

| # | Subject Line (Primary) | Purpose | Timing | Primary CTA | Dynamic Content |
|---|----------------------|---------|--------|-------------|----------------|
| 1 | Your reviews just escaped from Trustpilot | Confirm signup, set the scene, build anticipation | Day 0 (immediate) | None — pure story | None (system is processing) |
| 2 | Your customers have been talking behind your back | Deliver VoC analysis — show them their own customer themes | Day 1 | View Your VoC Map | Extracted themes, sentiment breakdown, verbatim highlights |
| 3 | Your VoC wrote these Facebook ads while you slept | THE BIG REVEAL — show personalized Facebook ad copy | Day 3 | See Your Ads | 2-3 generated Facebook ad creatives using their VoC data |
| 4 | It also crashed your email marketing | Show personalized email sequences for their brand | Day 5 | Read Your Emails | Generated email copy personalized to their brand |
| 5 | Your reviews are costing you money just sitting there | Cost of inaction + value anchoring — make £950/month feel obvious | Day 7 | See Pricing & Start | None — cost stack + methodology |
| 6 | Your VoC is going back to sleep | Last chance — urgency + direct CTA | Day 10 | Activate MapTheGap | Callback to their specific outputs |

---

## Sequence Flow Diagram

```
[FB Ad Signup] --> System scrapes Trustpilot + runs VoC analysis
        |
        v
  Email 1 (Day 0) — "Your reviews just escaped"
        |
  Processing complete?
        |
       Yes
        |
        v
  Email 2 (Day 1) — VoC analysis reveal
        |
        +--- Clicked? --Yes--> Tag: "engaged_voc"
        |
        v
  Email 3 (Day 3) — Facebook ad copy reveal
        |
        +--- Clicked? --Yes--> Tag: "engaged_ads"
        |
        +--- Signed up for trial? --Yes--> [EXIT: Convert to onboarding sequence]
        |
        v
  Email 4 (Day 5) — Email sequence reveal
        |
        +--- Signed up for trial? --Yes--> [EXIT: Convert to onboarding sequence]
        |
        v
  Email 5 (Day 7) — Methodology + credibility
        |
        +--- Signed up for trial? --Yes--> [EXIT: Convert to onboarding sequence]
        |
        v
  Email 6 (Day 10) — Last chance
        |
        +--- Signed up? --Yes--> [EXIT: Onboarding]
        |
        No --> [EXIT: Move to re-engagement pool — revisit in 30 days]
```

---

## Full Email Drafts

---

### EMAIL 1 — The Escape

**Timing:** Immediate (Day 0)
**Purpose:** Confirm signup, introduce the VoC-as-character concept, build anticipation for what's coming. No hard sell — pure story.

**Subject Line Options:**
1. `Your reviews just escaped from Trustpilot`
2. `Something broke loose from your Trustpilot page`
3. `We need to talk about your reviews...`

**Preview Text:** `They're loose. And they've got plans.`

**From Name:** `VoC from MapTheGap`

---

**Body Copy:**

Hey {{ first_name|default:'there' }},

So... this is awkward.

Your customer reviews just broke out of Trustpilot.

All of them. The 5-stars. The 1-stars. The ones where Karen went absolutely nuclear about shipping times.

They're loose now. And they're not going back.

Here's what happened: you signed up for MapTheGap, and the moment you did, we went straight to your Trustpilot page and started reading. Every. Single. Review.

Not skimming. Reading. Analyzing. Categorizing. Pulling out the exact words your customers use when they love you — and the exact words they use when they don't.

Right now, as you read this, we're doing something nobody's ever done with your reviews before.

We're turning them into Facebook ads.

Not "inspired by customer feedback" ads. Not "we read a few reviews and got some ideas" ads.

We're talking ads written in your customers' own words. Their pain. Their joy. Their objections. Their exact language.

Give us 24 hours. Tomorrow, you'll see what your Voice of Customer looks like when it breaks free.

Talk soon,
The VoC Team at MapTheGap

P.S. — Your reviews had a lot to say. Some of it surprised even us.

---

**CTA:** None — this is a pure anticipation-builder
**Segment Notes:** Send to all new signups immediately
**Condition:** System must have successfully received their Trustpilot URL or brand identifier

---

### EMAIL 2 — The VoC Reveal

**Timing:** Day 1 (24 hours after signup)
**Purpose:** Deliver the VoC analysis. Show them their own customer themes, sentiment breakdown, and highlighted verbatims. This is the first "wow" moment — they see their own data organized in a way they've never seen before.

**Subject Line Options:**
1. `Your customers have been talking behind your back`
2. `{{ company_name }}'s reviews, decoded`
3. `We read {{ review_count }} of your reviews. Here's what we found.`

**Preview Text:** `And they didn't hold back.`

**From Name:** `VoC from MapTheGap`

---

**Body Copy:**

Hey {{ first_name|default:'there' }},

Remember yesterday when your reviews escaped?

They've been busy.

We analyzed {{ review_count }} reviews from your Trustpilot page and organized them into the themes your customers actually care about.

Here's what jumped out:

---

**{{ DYNAMIC BLOCK: VoC Theme Summary }}**

*This section is dynamically populated from the VoC analysis engine. Example output:*

**Your top themes:**

🟢 **{{ theme_1_name }}** — {{ theme_1_count }} mentions
> "{{ theme_1_top_verbatim }}"

🟢 **{{ theme_2_name }}** — {{ theme_2_count }} mentions
> "{{ theme_2_top_verbatim }}"

🟡 **{{ theme_3_name }}** — {{ theme_3_count }} mentions
> "{{ theme_3_top_verbatim }}"

🔴 **{{ pain_theme_name }}** — {{ pain_theme_count }} mentions
> "{{ pain_theme_top_verbatim }}"

**Sentiment snapshot:** {{ positive_pct }}% positive · {{ neutral_pct }}% neutral · {{ negative_pct }}% negative

---

This isn't a spreadsheet. This is your customers telling you — in their own words — what makes them buy, what makes them stay, and what nearly made them leave.

Most brands never see this. They've got hundreds of reviews sitting on Trustpilot doing absolutely nothing except helping other shoppers decide.

But those same words? They're weapons. The most persuasive copy you'll ever write is already written — by the people who already bought from you.

Tomorrow, we'll show you what happens when you aim those words at Facebook.

See your full interactive VoC map here:

**[View Your VoC Map →]**

Talk soon,
The VoC Team at MapTheGap

---

**Primary CTA:** "View Your VoC Map" → links to their personalized dashboard on mapthegap.ai
**Segment Notes:** Only send if VoC processing is complete. If delayed, hold this email until data is ready.
**Condition:** Must have successfully scraped and processed at least 10 reviews

---

### EMAIL 3 — The Ad Copy Reveal

**Timing:** Day 3
**Purpose:** THE BIG MOMENT. Show them 2-3 Facebook ad creatives generated from their own VoC data. This is where the concept lands — they see production-ready ads written from their customers' own words.

**Subject Line Options:**
1. `Your VoC wrote these Facebook ads while you slept`
2. `{{ company_name }}, your reviews just wrote these ads`
3. `We turned your 1-star reviews into ad copy. It's brilliant.`

**Preview Text:** `These aren't concepts. They're ready to run.`

**From Name:** `VoC from MapTheGap`

---

**Body Copy:**

Hey {{ first_name|default:'there' }},

Your Voice of Customer didn't just escape Trustpilot.

It broke into Facebook Ads Manager.

And honestly? It writes better copy than most agencies.

Here's what it produced — using nothing but your real customer reviews, combined with the exact frameworks that make ads go viral:

---

**{{ DYNAMIC BLOCK: Generated Facebook Ad #1 }}**

*Dynamically populated from the ad generation engine. Example:*

**AD 1 — Story Angle**

📱 *How this would look in the Facebook feed:*

**{{ company_name }}**
Sponsored · 🌐

> {{ generated_primary_text_ad_1 }}

🖼️ *[Ad image placeholder]*

**{{ generated_headline_ad_1 }}**
{{ generated_description_ad_1 }}
**[{{ generated_cta_ad_1 }}]**

*Powered by: {{ voc_theme_used }} · {{ review_count_used }} customer reviews*

---

**{{ DYNAMIC BLOCK: Generated Facebook Ad #2 }}**

**AD 2 — Curiosity Angle**

📱 *How this would look in the Facebook feed:*

**{{ company_name }}**
Sponsored · 🌐

> {{ generated_primary_text_ad_2 }}

🖼️ *[Ad image placeholder]*

**{{ generated_headline_ad_2 }}**
{{ generated_description_ad_2 }}
**[{{ generated_cta_ad_2 }}]**

*Powered by: {{ voc_theme_used_2 }} · {{ review_count_used }} customer reviews*

---

Every word in those ads came from your customers.

Not from a copywriter guessing what your audience wants to hear. Not from an AI hallucinating benefits that don't exist. From real people who already bought from you, describing their real experience.

That's why VoC-powered ads outperform traditional creative. They don't sound like ads. They sound like conversations your customers are already having.

Want to see all 8 creative angles we generated? Including the ones built from your negative reviews (those are surprisingly powerful)?

**[See All Your Generated Ads →]**

Talk soon,
The VoC Team at MapTheGap

P.S. — Ad #2 up there? It was built from a review where someone was complaining. Turns out objection-handling copy writes itself when you listen to the people who almost didn't buy.

---

**Primary CTA:** "See All Your Generated Ads" → links to their full ad library on mapthegap.ai
**Segment Notes:** Send to all who received Email 2. If they've already signed up for a trial, skip and exit to onboarding.
**Condition:** Ad generation must be complete for their brand

---

### EMAIL 4 — The Email Sequence Reveal

**Timing:** Day 5
**Purpose:** The meta play. They're reading an email that shows them the emails they could be sending. Show dynamically generated email sequences for their brand (welcome, abandoned cart, winback, etc.)

**Subject Line Options:**
1. `It also crashed your email marketing`
2. `Your VoC isn't done. It wrote your email sequences too.`
3. `These emails wrote themselves. Literally.`

**Preview Text:** `Read the emails your customers wish you were sending.`

**From Name:** `VoC from MapTheGap`

---

**Body Copy:**

Hey {{ first_name|default:'there' }},

Thought your Voice of Customer was done after those Facebook ads?

It wasn't even warmed up.

While you've been reading these emails, it's been writing yours. As in — the emails {{ company_name }} could be sending to your customers right now.

Welcome sequences. Abandoned cart flows. Win-back campaigns. All powered by the same VoC data.

Here's a taste:

---

**{{ DYNAMIC BLOCK: Generated Email Preview }}**

*Dynamically populated. Example:*

**YOUR WELCOME EMAIL — Preview:**

Subject: `{{ generated_welcome_subject }}`
Preview: `{{ generated_welcome_preview }}`

> {{ generated_welcome_body_snippet }}

*Built from {{ theme_used }} themes across {{ review_count }} reviews*

---

**YOUR ABANDONED CART EMAIL — Preview:**

Subject: `{{ generated_cart_subject }}`
Preview: `{{ generated_cart_preview }}`

> {{ generated_cart_body_snippet }}

*Built from {{ objection_theme }} objections your customers actually raised*

---

Here's what's happening behind the scenes: we're taking the exact objections, desires, and emotional language from your reviews and weaving them into every email.

When a customer says "I almost didn't buy because..." — that becomes your abandoned cart copy.

When a customer says "I wish I'd known about this sooner..." — that becomes your welcome email hook.

Nobody knows how to sell your product better than the people who already bought it.

**[Read Your Full Email Sequences →]**

Talk soon,
The VoC Team at MapTheGap

P.S. — You're reading a marketing email right now. Imagine if every email you sent hit this hard — except powered by your own customers' words instead of ours.

---

**Primary CTA:** "Read Your Full Email Sequences" → links to email output on mapthegap.ai
**Segment Notes:** If they signed up for trial after Email 3, skip to onboarding. For engaged users (opened + clicked previous emails), consider sending this on Day 4 instead.
**Condition:** Email generation must be complete

---

### EMAIL 5 — The Real Cost of Keeping Your VoC Locked Up

**Timing:** Day 7
**Purpose:** Two jobs — (1) explain the methodology to satisfy analytical buyers, and (2) reframe the price by stacking up the cost of the alternative. This is where £950/month stops being a number and starts being an obvious bargain. The "cost of inaction" frame makes the close in Email 6 feel like a formality.

**Subject Line Options:**
1. `Your reviews are costing you money just sitting there`
2. `The most expensive thing in your business is free`
3. `What your Trustpilot page is actually worth`

**Preview Text:** `You're paying thousands to ignore what your customers already told you.`

**From Name:** `VoC from MapTheGap`

---

**Body Copy:**

Hey {{ first_name|default:'there' }},

Let's talk about what it actually costs to keep your Voice of Customer locked inside Trustpilot.

Not the Trustpilot subscription. That's the cheap part.

I'm talking about the invisible bleed. The money you're spending every month to NOT use the most persuasive copy you'll ever have access to.

Let's do the maths:

**Your agency or freelance copywriter:** £2,000-£5,000/month. And that's for someone guessing what your customers want to hear. Brainstorming in a conference room. Running "empathy mapping workshops." Writing copy based on a persona they built from assumptions.

Meanwhile, your actual customers already told you — in their own words — what made them buy, what nearly stopped them, and what they tell their friends. It's all sitting right there on Trustpilot. Doing nothing.

**Your creative testing budget:** Every ad variant you test costs money. CPMs, designer time, the back-and-forth with your media buyer. Most DTC brands test 10-20 creatives per month. How many of those are written using the exact language your buyers already use? Probably zero.

**The opportunity cost:** Every day your ads run generic copy — "premium quality," "fast shipping," "customers love us" — instead of the specific, emotionally charged language from your reviews, you're leaving ROAS on the table. Not a little. A lot.

Here's what MapTheGap actually replaces:

→ A copywriter who reads every review (£2,000-5,000/month)
→ A VoC analyst who extracts and categorizes themes (£1,500-3,000/month)
→ A creative strategist who maps insights to ad angles (£2,000-4,000/month)
→ The time it takes to brief, review, revise, and approve (weeks, every cycle)

MapTheGap does all of that. For every product. Every time you get new reviews. Automatically.

For £950/month.

That's not a software subscription. That's a senior copywriter, a VoC researcher, and a creative strategist — all working 24/7 off your real customer data, producing ads grounded in what actually makes people buy from you.

And unlike an agency, it doesn't need 3 weeks, a creative brief, and a kickoff call to get started. You saw that yourself — we had your ads written before your second email arrived.

**How it works (the 60-second version):**

We combine three things nobody else has put together:

1. BuzzSumo's research on what makes content go viral — 8 proven creative angles, each mapped to psychological triggers that stop the scroll

2. Stefan Georgi's $1B+ direct response copywriting frameworks — emotional sequencing, belief shifting, objection embedding, structural persuasion at scale

3. Your customers' actual words — extracted from every review, categorized by theme, mapped to pain points and desires, fed directly into the engine

The result is production-ready ad copy and email sequences that sound like your customers talking to their friends. Because they are.

That's why it works. It's not AI guessing. It's AI listening — then writing with the frameworks that have generated over a billion dollars in direct response sales.

£950/month to turn your existing reviews into an always-fresh, always-converting ad copy machine.

Or keep paying ten times that for someone to guess.

**[See Pricing & Start →]**

Talk soon,
The VoC Team at MapTheGap

P.S. — The brands seeing the best results aren't the ones with the most reviews. They're the ones who stopped paying other people to ignore them. Your VoC already wrote the copy. MapTheGap just let it out.

---

**Primary CTA:** "See Pricing & Start" → pricing page
**Segment Notes:** Send to all remaining in sequence (not yet converted). For highly engaged users (clicked Email 3 + Email 4), consider a more direct CTA: "Activate Your Plan — £950/month."
**Condition:** None — this is a static education + value email

---

### EMAIL 6 — The Last Chance

**Timing:** Day 10
**Purpose:** Final push. The VoC "character" is going back to sleep — their personalized outputs won't stay available forever. Urgency + callback to their specific data + direct conversion CTA.

**Subject Line Options:**
1. `Your VoC is going back to sleep`
2. `{{ first_name }}, your ads expire in 48 hours`
3. `Last call: {{ review_count }} reviews, 0 ads running`

**Preview Text:** `Don't let those reviews go back to doing nothing.`

**From Name:** `VoC from MapTheGap`

---

**Body Copy:**

Hey {{ first_name|default:'there' }},

Your Voice of Customer has been out here working overtime.

It analyzed {{ review_count }} reviews. It found {{ theme_count }} themes. It wrote Facebook ads across 8 creative angles. It built email sequences that handle objections your customers actually raised.

And right now, all of that is sitting in your MapTheGap dashboard... waiting.

But it won't wait forever.

In 48 hours, your personalized outputs expire. The ads, the emails, the VoC analysis — all of it goes back behind the wall.

And your reviews go back to doing what they've always done: sitting on Trustpilot, helping other people decide whether to buy from you, while you pay an agency to guess at what your customers want to hear.

Here's the thing nobody talks about: your best ad copy already exists. Your customers already wrote it. It's sitting in plain sight on your review page.

MapTheGap just showed you what happens when someone actually reads it.

**[Activate MapTheGap — Keep Your Outputs →]**

This is the last email in this series. If it's not the right time, no hard feelings. Your reviews will still be there when you're ready.

But they won't be writing ads on their own.

That part takes us.

The VoC Team at MapTheGap

---

**Primary CTA:** "Activate MapTheGap — Keep Your Outputs" → pricing/checkout page
**Segment Notes:** Send only to those who have NOT converted. For engaged users (opened 3+ emails), this is the final push. For non-openers, consider a subject line variant with their brand name for recognition.
**Condition:** None
**Exit:** After this email, non-converters move to a re-engagement pool. Revisit in 30 days with a "We re-ran your analysis with new reviews" angle.

---

## Branching Logic Notes

**Exit conditions:**
- User starts free trial or purchases at any point → exit to onboarding sequence
- User unsubscribes → exit permanently
- User is in active support conversation → suppress next email, resume after 48 hours

**Branching:**
- If Email 2 not opened after 24 hours → resend with subject line variant: `{{ company_name }}, you have {{ review_count }} reviews we need to talk about`
- If Email 3 clicked but no trial signup within 24 hours → send Email 4 one day early (Day 4 instead of Day 5)
- If no emails opened by Day 5 → switch to a compressed 2-email path: Email 5 (education) + Email 6 (last chance) only

**Suppression rules:**
- Do not send if user is already in another active MapTheGap sequence
- Do not send Email 2/3/4 if VoC processing failed (fallback: send a manual "we're working on it" email with generic product demo)
- Do not send to free/disposable email addresses

**Re-entry:**
- User can re-enter if they re-sign-up from a different campaign after 30+ days
- Re-entry triggers a fresh VoC scrape (reviews may have changed)

---

## Dynamic Content Implementation Notes

### What the system needs to generate per signup:

1. **VoC Analysis** (for Email 2):
   - Theme names + mention counts
   - Top verbatim per theme
   - Sentiment percentage breakdown
   - Total review count

2. **Facebook Ad Creatives** (for Email 3):
   - Minimum 2 full ad creatives (Story + Curiosity angles recommended for email)
   - Primary text, headline, description, CTA
   - Source theme attribution per ad

3. **Email Sequences** (for Email 4):
   - Welcome email (subject + preview + body snippet)
   - Abandoned cart email (subject + preview + body snippet)
   - Theme/objection attribution per email

### Merge tag reference:

| Token | Source | Used in |
|-------|--------|---------|
| `{{ first_name }}` | Signup form | All emails |
| `{{ company_name }}` | Trustpilot scrape or signup form | Emails 2-6 |
| `{{ review_count }}` | VoC analysis engine | Emails 2, 3, 6 |
| `{{ theme_1_name }}` through `{{ theme_3_name }}` | VoC analysis | Email 2 |
| `{{ theme_X_count }}` | VoC analysis | Email 2 |
| `{{ theme_X_top_verbatim }}` | VoC analysis | Email 2 |
| `{{ positive_pct }}` / `{{ neutral_pct }}` / `{{ negative_pct }}` | VoC analysis | Email 2 |
| `{{ generated_primary_text_ad_X }}` | Ad generation engine | Email 3 |
| `{{ generated_headline_ad_X }}` | Ad generation engine | Email 3 |
| `{{ generated_description_ad_X }}` | Ad generation engine | Email 3 |
| `{{ generated_cta_ad_X }}` | Ad generation engine | Email 3 |
| `{{ generated_welcome_subject }}` | Email generation engine | Email 4 |
| `{{ generated_welcome_body_snippet }}` | Email generation engine | Email 4 |
| `{{ generated_cart_subject }}` | Email generation engine | Email 4 |
| `{{ generated_cart_body_snippet }}` | Email generation engine | Email 4 |
| `{{ theme_count }}` | VoC analysis | Email 6 |

---

## Performance Benchmarks

Since this is a unique sequence (lead nurture + dynamic product demo), benchmarks blend lead nurture averages with product-led growth metrics:

| Metric | Target | Notes |
|--------|--------|-------|
| Email 1 open rate | 55-70% | Fresh signup, curiosity-driven — expect high |
| Email 2 open rate | 40-55% | "Your data is ready" trigger creates urgency |
| Email 3 open rate | 35-50% | The payoff email — subject line is doing heavy lifting |
| Email 3 click rate | 15-25% | This is the money email — personalized output is the draw |
| Email 5 open rate | 20-30% | Education email, expected drop |
| Email 6 open rate | 25-35% | Urgency + brand name in subject may lift |
| Overall sequence conversion | 5-12% | Higher than typical lead nurture due to personalized demo |
| Unsubscribe rate | <0.8% per email | Story format tends to retain even non-buyers |

---

## A/B Test Suggestions

1. **Email 1 subject line:** Test `Your reviews just escaped from Trustpilot` vs `Something broke loose from your Trustpilot page` — measures whether direct or mysterious hooks drive higher opens for this audience.

2. **Email 3 format:** Test showing 2 ad previews in-email vs 1 ad preview + "see the rest" CTA — measures whether more content in-email increases click-through or if curiosity drives more dashboard visits.

3. **Email 6 urgency framing:** Test `Your VoC is going back to sleep` (character-based) vs `{{ first_name }}, your ads expire in 48 hours` (direct urgency) — measures whether the narrative or the deadline converts better at the bottom of funnel.

---

## Setup Checklist (Any Email Platform)

1. **Create the automation flow** triggered by signup form submission (must capture email + Trustpilot URL/brand name)
2. **Set up webhook** from signup to MapTheGap backend to trigger VoC scraping + analysis
3. **Configure wait conditions** — Email 2 should only send after VoC processing is confirmed complete (webhook callback or status check)
4. **Build dynamic content blocks** for Emails 2, 3, and 4 using merge tags populated via API from MapTheGap
5. **Set exit condition:** trial signup or purchase event removes from sequence
6. **Configure resend logic** for Email 2 non-opens (24hr delay, alternate subject)
7. **Set up engagement tagging** — tag clicks on Emails 2, 3, 4 for segmentation
8. **Create post-sequence segment** — non-converters tagged for 30-day re-engagement

---

*Sequence designed for MapTheGap.ai — "VoC Gone Wild" campaign targeting DTC/ecommerce brands.*
