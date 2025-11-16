# 🚀 OpenAI Testing - Quick Start

## What You Have

✅ **4 JSON files ready for OpenAI Playground testing:**

1. **`wattbike_motivators_samples.json`** - Raw data (946 responses, 98 sampled)
2. **`wattbike_motivators_prompt_simple.json`** - Minimal prompt (fastest, cheapest)
3. **`wattbike_motivators_prompt_detailed.json`** - Rich context (best quality)
4. **`wattbike_motivators_prompt_structured.json`** - JSON output format (easiest to parse)

## Test in OpenAI Playground

### Step 1: Go to Playground
Open https://platform.openai.com/playground/chat

### Step 2: Load a Prompt
1. Open any `*_prompt_*.json` file in a text editor
2. Copy the entire JSON content
3. In the playground, click "View code" (top right)
4. Select "json" format
5. Paste the JSON
6. Click back to the chat view

### Step 3: Test Different Models
Try each model and note the quality:

| Model | Cost/1M tokens | Best For |
|-------|----------------|----------|
| **gpt-4o** | $5 / $15 | Highest quality, nuanced insights |
| **gpt-4o-mini** | $0.15 / $0.60 | ⭐ Best balance (recommended) |
| **gpt-3.5-turbo** | $0.50 / $1.50 | Fast, good enough for simple tasks |

### Step 4: Compare Prompt Styles

#### Simple Prompt
- Bare minimum context
- Just the responses
- Use for: Quick sentiment checks

#### Detailed Prompt
- Includes sentiment distribution
- Shows topic metadata
- Use for: **Comprehensive insights** ⭐ (recommended)

#### Structured Prompt
- Returns JSON output
- Consistent format
- Use for: Automated processing

## What to Look For

### Quality Checklist
- [ ] **Accurate**: Are insights actually in the data?
- [ ] **Actionable**: Can Wattbike act on these insights?
- [ ] **Novel**: Does it find patterns you didn't see?
- [ ] **Consistent**: Run 2-3 times, is output similar?
- [ ] **Comprehensive**: Does it cover the main themes?

### Red Flags
- ❌ Hallucinated insights not in the data
- ❌ Generic advice that could apply to any company
- ❌ Missing obvious patterns
- ❌ Wildly different results on same data

## Generate More Examples

### Try Different Dimensions
```bash
# See all dimensions
source venv/bin/activate
python test_openai_samples.py --client "Wattbike" --list-dimensions

# Generate for "UX friction"
python test_openai_samples.py \
  --client "Wattbike" \
  --dimension "ref_buc9x" \
  --output wattbike_ux_friction
```

### Try Different Clients
```bash
# See all clients
python test_openai_samples.py --list-clients

# Generate for another client
python test_openai_samples.py \
  --client "Ancient & Brave" \
  --dimension "ref_xyz" \
  --output ancient_brave_test
```

### Adjust Sample Size
```bash
# Smaller sample (cheaper, faster)
python test_openai_samples.py \
  --client "Wattbike" \
  --dimension "ref_14u6n" \
  --sample-size 50 \
  --output wattbike_small

# Larger sample (more comprehensive)
python test_openai_samples.py \
  --client "Wattbike" \
  --dimension "ref_14u6n" \
  --sample-size 200 \
  --output wattbike_large
```

## Cost Analysis

For **100 samples** (~5,000 tokens total):

| Model | Per Request | Per 1,000 Dimensions | Monthly (refresh) |
|-------|-------------|----------------------|-------------------|
| gpt-4o | $0.10 | $100 | $100 |
| **gpt-4o-mini** ⭐ | **$0.003** | **$3** | **$3** |
| gpt-3.5-turbo | $0.01 | $10 | $10 |

**Recommendation:** Start with **gpt-4o-mini** - it's 97% cheaper than gpt-4o and still excellent quality.

## Decision Time

### If Quality is Good ✅
I'll integrate this into your codebase:
1. Add database model for storing summaries
2. Create API endpoints
3. Add background job for batch generation
4. Build frontend UI to display summaries
5. Add refresh/regenerate functionality

### If Quality Needs Work 🔧
We can:
1. Adjust the prompt engineering
2. Try different sampling strategies
3. Add more context to prompts
4. Test with larger samples
5. Compare multiple models

### If Not Worth It ❌
We'll clean up:
```bash
bash cleanup_openai_test.sh
```
(Removes all test files, no trace in codebase)

## Next Steps

1. **Test the prompts** in OpenAI Playground (15 minutes)
2. **Try 3-5 different dimensions** to see consistency
3. **Compare models** to find quality/cost sweet spot
4. **Report back** with your findings

Let me know what you discover! 🚀

