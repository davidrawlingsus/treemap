# Production-Ready Prompt Template

## Key Learnings from Testing

### ✅ What Works

1. **Topic-Stratified Sampling** - Ensures all major categories represented
2. **Full Dataset Context** - Give OpenAI the statistical breakdown
3. **Explicit Top 3 Emphasis** - "~85%: Category A, Category B, Category C"
4. **Focus on Statistical Weight** - "Not anecdotal or rare mentions"
5. **Concise Output Format** - Max 2 paragraphs + structured bullets

### ❌ What Doesn't Work

1. ~~Sentiment-only sampling~~ - Misses important categories
2. ~~No context in prompt~~ - OpenAI can't weight properly
3. ~~Long-form responses~~ - Too much detail, loses focus
4. ~~Enumerating every nuance~~ - Noise over signal

## Prompt Template

```
Analyze customer feedback for "{DIMENSION_NAME}" from {CLIENT_NAME}.

📊 FULL DATASET CONTEXT (THIS IS CRITICAL):
Total Responses: {TOTAL_COUNT:,}
Sample Size: {SAMPLE_SIZE} (topic-stratified for accuracy)

TOPIC CATEGORY DISTRIBUTION (Full Dataset):
{CATEGORY_DISTRIBUTION_LIST}

TOP SPECIFIC TOPICS (Full Dataset):
{TOP_10_TOPICS_WITH_PERCENTAGES}

SAMPLE RESPONSES:
{FORMATTED_SAMPLES}

Provide a concise, insight-rich summary (max 2 short paragraphs) that:

• Reflects the true weighting of the dataset, with emphasis on the top 3 categories (~85%): {TOP_3_CATEGORIES}
• Captures the core motivations without over-explaining subtopics or long-tail reasons
• Focuses on what matters most statistically, not on anecdotal or rare mentions
• Uses clear, synthesised language rather than enumerating every nuance

Then provide:

1. KEY INSIGHTS (3–5 bullets):
   Actionable insights weighted by category importance (e.g., why certain categories dominate, how they shape purchase intent, what drives the behavior).

2. CATEGORY SNAPSHOT (1 sentence each):
   A crisp line per major category summarising what customers meant.

3. PATTERNS:
   Only the strongest sentiment or behavioural themes — avoid deep dives.
```

## System Prompt

```
You are an expert customer insights analyst. You specialize in voice-of-customer analysis and always weight your insights by the statistical distribution of topics in the full dataset.
```

## Model Configuration

```json
{
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 800
}
```

## Expected Output Format

```
SUMMARY (2 short paragraphs):
Paragraph 1: Core insight emphasizing top 3 categories
Paragraph 2: Secondary themes and context

KEY INSIGHTS:
• Insight 1 (related to top category)
• Insight 2 (related to second category)
• Insight 3 (cross-category or pattern)
• Insight 4 (actionable recommendation)
• Insight 5 (opportunity or risk)

CATEGORY SNAPSHOT:
• Category 1: One crisp sentence summarizing customer intent
• Category 2: One crisp sentence summarizing customer intent
• Category 3: One crisp sentence summarizing customer intent
[etc for major categories]

PATTERNS:
Brief note on strongest sentiment or behavioral themes
```

## Example Output Quality

### ✅ Good Output
> "Winter weather avoidance (38% of responses) and fitness goals (32%) drive the majority of Wattbike purchases, with customers seeking reliable year-round training solutions. A secondary but significant group (16%) explicitly wanted to train at home rather than adapt outdoor bikes for indoor use."
>
> **KEY INSIGHTS:**
> • Winter training dominates: UK weather patterns create 8-month demand for indoor solutions
> • Fitness goals split between maintenance (existing cyclists) vs improvement (new adopters)
> • Turbo trainer frustration drives 11% of purchases - hassle of setup/teardown

### ❌ Bad Output
> "Customers mentioned many reasons including winter, summer, spring training, and some people have injuries while others don't like the weather and a few mentioned COVID and their friends recommended it..."

## Cost Analysis

**Per Dimension:**
- Tokens: ~5,000 (prompt + response)
- Cost (gpt-4o-mini): ~$0.003
- Cost (gpt-4o): ~$0.10

**For 1,000 Dimensions:**
- gpt-4o-mini: **$3/month** ⭐ Recommended
- gpt-4o: $100/month (use if quality gap found)

## Integration Checklist

When ready for production:

- [ ] Add `OPENAI_API_KEY` to environment variables
- [ ] Create `DimensionSummary` database model
- [ ] Implement topic-stratified sampling (use `test_openai_samples_v2.py` logic)
- [ ] Add API endpoint: `POST /api/dimensions/{id}/generate-summary`
- [ ] Add API endpoint: `GET /api/dimensions/{id}/summary`
- [ ] Add batch generation endpoint for multiple dimensions
- [ ] Add regeneration capability (with `force=true` flag)
- [ ] Track token usage for cost monitoring
- [ ] Add frontend UI to display summaries
- [ ] Add refresh mechanism (monthly? on-demand?)

## Testing Checklist

Before going live:

- [ ] Test with 5-10 different dimensions
- [ ] Verify all major categories are covered
- [ ] Check consistency across multiple runs (same dimension)
- [ ] Validate against manual analysis
- [ ] Test with different clients/domains
- [ ] Verify cost tracking is accurate
- [ ] Test error handling (API failures, rate limits)
- [ ] Load test (100+ simultaneous requests)

## Monitoring in Production

Track these metrics:

1. **Quality Metrics:**
   - Category coverage (% of major categories mentioned)
   - Insight relevance (user feedback)
   - Consistency (variance across regenerations)

2. **Performance Metrics:**
   - API response time
   - Token usage per request
   - Cost per dimension
   - Error rate

3. **Usage Metrics:**
   - Summaries generated per day
   - Regeneration frequency
   - Most-analyzed dimensions
   - User engagement with summaries

## Rollout Strategy

1. **Alpha (Internal):** Test with 10 dimensions, validate quality
2. **Beta (Select Clients):** 3-5 clients, gather feedback
3. **Production (All):** Full rollout with monitoring
4. **Optimization:** Adjust based on usage patterns and feedback

