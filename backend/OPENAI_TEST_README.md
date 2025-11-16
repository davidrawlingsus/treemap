# OpenAI Testing Kit

This is a **standalone testing environment** for evaluating OpenAI's quality on your dimension data. Nothing here affects your production code.

## Quick Start

### 1. List Available Clients
```bash
cd backend
python test_openai_samples.py --list-clients
```

### 2. See Dimensions for a Client
```bash
python test_openai_samples.py --client "Wattbike" --list-dimensions
```

### 3. Extract Sample Data
```bash
python test_openai_samples.py \
  --client "Wattbike" \
  --dimension "ref_14u6n" \
  --sample-size 100 \
  --output wattbike_test
```

This creates 4 files:
- `wattbike_test_samples.json` - Raw data
- `wattbike_test_prompt_simple.json` - Simple prompt
- `wattbike_test_prompt_detailed.json` - Detailed prompt with metadata
- `wattbike_test_prompt_structured.json` - JSON response format

### 4. Test in OpenAI Playground

1. Go to https://platform.openai.com/playground
2. Open one of the `*_prompt_*.json` files
3. Copy the entire JSON content
4. Paste into the playground (use "View code" mode)
5. Test with different models:
   - `gpt-4o` - Best quality, most expensive (~$5/$15 per 1M tokens)
   - `gpt-4o-mini` - Good quality, cheaper (~$0.15/$0.60 per 1M tokens)
   - `gpt-3.5-turbo` - Fastest, cheapest (~$0.50/$1.50 per 1M tokens)

### 5. Compare Results

Test the same data with:
- Different models (quality vs cost)
- Different prompt styles (simple vs detailed vs structured)
- Different sample sizes (50, 100, 200)

## Prompt Styles

### Simple
- Minimal context
- Just the responses
- Quick, cheap
- Use for: Basic sentiment analysis

### Detailed
- Includes sentiment distribution
- Shows topics metadata
- Better context
- Use for: Comprehensive insights

### Structured
- Requests JSON output
- Consistent format
- Easy to parse
- Use for: Automated processing

## Advanced Options

```bash
# Filter by data source
python test_openai_samples.py \
  --client "Wattbike" \
  --dimension "ref_14u6n" \
  --data-source "email_survey"

# Use random sampling instead of smart sampling
python test_openai_samples.py \
  --client "Wattbike" \
  --dimension "ref_14u6n" \
  --strategy random

# Larger sample
python test_openai_samples.py \
  --client "Wattbike" \
  --dimension "ref_14u6n" \
  --sample-size 200
```

## Smart vs Random Sampling

**Smart Sampling** (recommended):
- Balances sentiments proportionally
- Includes variety in response lengths
- More representative of the whole dataset

**Random Sampling**:
- Pure random selection
- Faster
- May miss minority sentiments

## Cost Estimation

For 100 samples (~5,000 tokens including prompt):

| Model | Input | Output | Total per Request |
|-------|-------|--------|-------------------|
| gpt-4o | $0.025 | $0.075 | ~$0.10 |
| gpt-4o-mini | $0.0008 | $0.0024 | ~$0.003 |
| gpt-3.5-turbo | $0.0025 | $0.0075 | ~$0.01 |

For production (1000 dimensions × monthly refresh):
- gpt-4o: ~$100/month
- gpt-4o-mini: ~$3/month ✓ (recommended)
- gpt-3.5-turbo: ~$10/month

## Files Created (Safe to Delete)

These files are NOT part of your main codebase:
- `test_openai_samples.py` - Extraction script
- `OPENAI_TEST_README.md` - This guide
- `openai_test_*.json` - Generated sample files
- `cleanup_openai_test.sh` - Cleanup script

## Cleanup

When you're done testing:

```bash
bash cleanup_openai_test.sh
```

Or manually:
```bash
rm test_openai_samples.py
rm OPENAI_TEST_README.md
rm cleanup_openai_test.sh
rm openai_test_*.json
rm wattbike_test_*.json
# etc.
```

## Decision Checklist

After testing, evaluate:

- [ ] Quality: Do the summaries capture key themes?
- [ ] Accuracy: Are insights actually in the data?
- [ ] Actionability: Can you act on the insights?
- [ ] Consistency: Similar quality across dimensions?
- [ ] Cost: Worth $3-100/month for your use case?
- [ ] Speed: Fast enough for your workflow?

## Next Steps

If you're happy with the quality:
1. I'll integrate this into your main codebase
2. Add database model for storing summaries
3. Create API endpoints
4. Add frontend UI components

If not:
1. Adjust prompts and re-test
2. Try different sampling strategies
3. Consider alternative approaches

