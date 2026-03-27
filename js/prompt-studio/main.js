/**
 * Prompt Studio — main orchestration module.
 * Manages pipeline state, step execution, versioning, and treemap rendering.
 */

import {
    fetchLeadgenRuns, scrapeProspect, fetchRunInputs, fetchDefaultPrompts,
    fetchPromptVersions, runContextStep, runDiscoverStep,
    runCodeStep, runRefineStep, runExtractStep, runTaxonomyStep,
    runValidateStep, runGenerateAd, createPromptVersion, updatePrompt,
    savePipelineState, saveStepOutput, fetchStepOutputs,
    createFacebookAd, syncToClient, runClassifyStep,
} from '/js/prompt-studio/api.js';

import {
    renderStepCard, renderOutputPanel, updateOutputPanel,
    updateVersionDropdown, setDirtyIndicator, highlightJson,
} from '/js/prompt-studio/rendering.js';

import { buildCreativePayloads, assembleUserPrompt, summarizePayloads } from '/js/prompt-studio/creative-selection.js';
import { renderAds } from '/js/prompt-studio/ad-renderer.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let studioInputs = null; // { url, domain, company_name, reviews, company_context }
let pipeline = [];
let stepIdCounter = 0;
let currentRunId = null;
let currentClientId = null; // Lead client UUID from scrape response

const PROMPT_PURPOSE_MAP = {
    context: 'product_context_extract',
    discover: 'voc_discover',
    code: 'voc_code',
    refine: 'voc_refine',
    extract: 'voc_extract',
    taxonomy: 'voc_taxonomy',
    validate: 'voc_validate',
    classify: 'voc_classify',
};

const DEFAULT_PROMPT_KEYS = {
    context: { system: 'context_system' },
    discover: { system: 'discover_system', user: 'discover_user' },
    code: { system: 'code_system', user: 'code_user' },
    refine: { system: 'refine_system', user: 'refine_user' },
    extract: { system: 'extract_system', user: 'extract_user' },
    taxonomy: { system: 'taxonomy_system', user: 'taxonomy_user' },
    validate: { system: 'validate_system', user: 'validate_user' },
    classify: { system: 'classify_system', user: 'classify_user' },
};

// ---------------------------------------------------------------------------
// DOM references
// ---------------------------------------------------------------------------
const els = {};

function cacheElements() {
    els.scrapeBtn = document.getElementById('scrapeBtn');
    els.prospectUrl = document.getElementById('prospectUrl');
    els.companyName = document.getElementById('companyName');
    els.minReviews = document.getElementById('minReviews');
    els.runSelector = document.getElementById('runSelector');
    els.editor = document.getElementById('pipelineEditor');
    els.outputs = document.getElementById('outputPanels');
    els.addStepBtn = document.getElementById('addStepBtn');
    els.addStepType = document.getElementById('addStepTypeSelect');
    els.status = document.getElementById('studioStatus');
    els.founderEmail = document.getElementById('founderEmail');
    els.logoutButton = document.getElementById('logoutButton');
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function showStatus(msg, type) {
    els.status.textContent = msg;
    els.status.className = 'studio-status' + (type ? ` ${type}` : '');
}

function clearStatus() { els.status.textContent = ''; els.status.className = 'studio-status'; }

function createStep(type) {
    stepIdCounter++;
    return {
        id: `step-${stepIdCounter}`,
        type,
        systemPrompt: '',
        userPrompt: '',
        output: null,
        elapsedSeconds: null,
        status: 'idle',
        promptVersions: [],
        selectedVersionId: null,
        isDirty: false,
    };
}

function getStep(stepId) { return pipeline.find(s => s.id === stepId); }
function getStepIndex(stepId) { return pipeline.findIndex(s => s.id === stepId); }

// ---------------------------------------------------------------------------
// Pipeline management
// ---------------------------------------------------------------------------
function initDefaultPipeline() {
    pipeline = [];
    els.editor.innerHTML = '';
    els.outputs.innerHTML = '';
    ['context', 'extract', 'taxonomy', 'validate', 'classify'].forEach(type => addStep(type));
}

function addStep(type) {
    const step = createStep(type);
    const keys = DEFAULT_PROMPT_KEYS[type] || {};
    if (studioInputs?.default_prompts) {
        step.systemPrompt = studioInputs.default_prompts[keys.system] || '';
        step.userPrompt = studioInputs.default_prompts[keys.user] || '';
    }
    pipeline.push(step);
    renderPipelineStep(step, pipeline.length - 1);
    loadVersionsForStep(step);
}

function removeStep(stepId) {
    const idx = getStepIndex(stepId);
    if (idx < 0) return;
    pipeline.splice(idx, 1);
    rerenderPipeline();
    updateTreemap();
}

function rerenderPipeline() {
    els.editor.innerHTML = '';
    els.outputs.innerHTML = '';
    pipeline.forEach((step, i) => renderPipelineStep(step, i));
}

function serializePipeline() {
    return pipeline.map(step => ({
        type: step.type,
        systemPrompt: step.systemPrompt,
        userPrompt: step.userPrompt,
        output: step.output,
        elapsedSeconds: step.elapsedSeconds,
        status: step.status === 'running' ? 'idle' : step.status,
    }));
}

function restorePipeline(savedSteps) {
    pipeline = [];
    stepIdCounter = 0;
    els.editor.innerHTML = '';
    els.outputs.innerHTML = '';

    savedSteps.forEach(saved => {
        const step = createStep(saved.type);
        step.systemPrompt = saved.systemPrompt || '';
        step.userPrompt = saved.userPrompt || '';
        step.output = saved.output || null;
        step.elapsedSeconds = saved.elapsedSeconds || null;
        step.status = saved.output ? 'done' : 'idle';
        pipeline.push(step);
        renderPipelineStep(step, pipeline.length - 1);
        updateStepUI(step);
        loadVersionsForStep(step);
    });
    updateTreemap();
}

async function handleSaveRun() {
    if (!currentRunId) { showStatus('No active run to save.', 'error'); return; }
    // Read latest textarea values into pipeline state
    pipeline.forEach(step => {
        const card = els.editor.querySelector(`[data-step-id="${step.id}"]`);
        const sysTA = card?.querySelector('[data-field="systemPrompt"]');
        const userTA = card?.querySelector('[data-field="userPrompt"]');
        if (sysTA) step.systemPrompt = sysTA.value;
        if (userTA) step.userPrompt = userTA.value;
    });
    try {
        await savePipelineState(currentRunId, serializePipeline());
        showStatus('Pipeline saved.', 'success');
    } catch (e) {
        showStatus(`Save failed: ${e.message}`, 'error');
    }
}

function updateSaveButton() {
    const btn = document.getElementById('saveRunBtn');
    if (btn) btn.style.display = currentRunId ? 'inline-block' : 'none';
}

function autoResizeTextareas(container) {
    container.querySelectorAll('.prompt-textarea').forEach(ta => {
        ta.style.height = 'auto';
        ta.style.height = ta.scrollHeight + 'px';
    });
}

function renderPipelineStep(step, index) {
    const card = renderStepCard(step, index);
    els.editor.appendChild(card);
    autoResizeTextareas(card);
    const panel = renderOutputPanel(step);
    els.outputs.appendChild(panel);
    if (step.output) updateOutputPanel(panel, step);
    if (step.promptVersions.length) updateVersionDropdown(card, step);
}

// ---------------------------------------------------------------------------
// Version loading
// ---------------------------------------------------------------------------
async function loadVersionsForStep(step) {
    const purpose = PROMPT_PURPOSE_MAP[step.type];
    if (!purpose) return;
    try {
        const data = await fetchPromptVersions(purpose);
        step.promptVersions = data.versions || [];
        const card = els.editor.querySelector(`[data-step-id="${step.id}"]`);
        if (card) updateVersionDropdown(card, step);
    } catch (e) {
        console.error('[prompt-studio] Failed to load versions:', e);
    }
}

// ---------------------------------------------------------------------------
// Auto-wiring: resolve upstream outputs for a step
// ---------------------------------------------------------------------------
function getUpstreamCodebook(stepIndex) {
    for (let i = stepIndex - 1; i >= 0; i--) {
        const s = pipeline[i];
        if ((s.type === 'discover' || s.type === 'refine') && s.output) return s.output;
    }
    return null;
}

function getUpstreamCodeOutput(stepIndex) {
    for (let i = stepIndex - 1; i >= 0; i--) {
        if (pipeline[i].type === 'code' && pipeline[i].output) return pipeline[i].output;
    }
    return null;
}

function getUpstreamContextText(stepIndex) {
    for (let i = stepIndex - 1; i >= 0; i--) {
        if (pipeline[i].type === 'context' && pipeline[i].output) return pipeline[i].output.context_text || '';
    }
    return studioInputs?.company_context?.context_text || '';
}

function getUpstreamExtractOutput(stepIndex) {
    for (let i = stepIndex - 1; i >= 0; i--) {
        if (pipeline[i].type === 'extract' && pipeline[i].output) return pipeline[i].output;
    }
    return null;
}

function getUpstreamTaxonomyOutput(stepIndex) {
    for (let i = stepIndex - 1; i >= 0; i--) {
        const s = pipeline[i];
        if ((s.type === 'taxonomy' || s.type === 'validate') && s.output) return s.output;
    }
    return null;
}

function getUpstreamValidateOutput(stepIndex) {
    for (let i = stepIndex - 1; i >= 0; i--) {
        if (pipeline[i].type === 'validate' && pipeline[i].output) return pipeline[i].output;
    }
    return null;
}

function canRunStep(stepIndex) {
    const step = pipeline[stepIndex];
    if (step.type === 'context') return !!studioInputs?.url;
    if (step.type === 'discover') return !!studioInputs?.reviews?.length;
    if (step.type === 'code') return !!getUpstreamCodebook(stepIndex) && !!studioInputs?.reviews?.length;
    if (step.type === 'refine') return !!getUpstreamCodebook(stepIndex);
    if (step.type === 'extract') return !!studioInputs?.reviews?.length;
    if (step.type === 'taxonomy') return !!getUpstreamExtractOutput(stepIndex);
    if (step.type === 'validate') return !!getUpstreamTaxonomyOutput(stepIndex) && !!getUpstreamExtractOutput(stepIndex);
    return false;
}

// ---------------------------------------------------------------------------
// Step execution
// ---------------------------------------------------------------------------
async function executeStep(stepId) {
    const idx = getStepIndex(stepId);
    const step = pipeline[idx];
    if (!step || step.status === 'running') return;

    // Read current textarea values
    const card = els.editor.querySelector(`[data-step-id="${stepId}"]`);
    const sysTA = card?.querySelector('[data-field="systemPrompt"]');
    const userTA = card?.querySelector('[data-field="userPrompt"]');
    if (sysTA) step.systemPrompt = sysTA.value;
    if (userTA) step.userPrompt = userTA.value;

    step.status = 'running';
    step.output = null;
    step.elapsedSeconds = null;
    updateStepUI(step);
    clearDownstream(idx);
    clearStatus();

    // Token counter UI
    const tokenSpan = card?.querySelector('.step-tokens');
    const onTokens = (n) => {
        if (tokenSpan) {
            tokenSpan.style.display = 'inline';
            tokenSpan.textContent = `~${n.toLocaleString()} tokens`;
        }
    };
    if (tokenSpan) { tokenSpan.style.display = 'none'; tokenSpan.textContent = ''; }

    try {
        let result;
        if (step.type === 'context') {
            result = await runContextStep(step.systemPrompt, studioInputs.url);
            step.output = result.output;
            step.elapsedSeconds = result.elapsed_seconds;
            // Show page text in the readonly textarea
            const ptTA = card?.querySelector('[data-field="pageText"]');
            if (ptTA && result.page_text) ptTA.value = result.page_text;
        } else if (step.type === 'discover') {
            const ctx = getUpstreamContextText(idx);
            result = await runDiscoverStep(step.systemPrompt, step.userPrompt, ctx, studioInputs.reviews);
            step.output = result.output;
            step.elapsedSeconds = result.elapsed_seconds;
        } else if (step.type === 'code') {
            const codebook = getUpstreamCodebook(idx);
            if (!codebook) throw new Error('No upstream codebook found. Run a Discover or Refine step first.');
            result = await runCodeStep(step.systemPrompt, step.userPrompt, codebook, studioInputs.reviews);
            step.output = result.output;
            step.elapsedSeconds = result.elapsed_seconds;
        } else if (step.type === 'refine') {
            const codebook = getUpstreamCodebook(idx);
            if (!codebook) throw new Error('No upstream codebook found.');
            const codeOut = getUpstreamCodeOutput(idx);
            const stats = codeOut?.stats || {};
            const noMatches = codeOut?.no_matches || [];
            const ctx = getUpstreamContextText(idx);
            result = await runRefineStep(step.systemPrompt, step.userPrompt, codebook, stats, noMatches, ctx);
            step.output = result.output;
            step.elapsedSeconds = result.elapsed_seconds;
        } else if (step.type === 'extract') {
            const ctx = getUpstreamContextText(idx);
            result = await runExtractStep(step.systemPrompt, step.userPrompt, ctx, studioInputs.reviews, onTokens);
            step.output = result.output;
            step.elapsedSeconds = result.elapsed_seconds;
        } else if (step.type === 'taxonomy') {
            const signals = getUpstreamExtractOutput(idx);
            if (!signals) throw new Error('No upstream signals found. Run an Extract step first.');
            const ctx = getUpstreamContextText(idx);
            result = await runTaxonomyStep(step.systemPrompt, step.userPrompt, ctx, signals, onTokens);
            step.output = result.output;
            step.elapsedSeconds = result.elapsed_seconds;
        } else if (step.type === 'validate') {
            const taxonomy = getUpstreamTaxonomyOutput(idx);
            if (!taxonomy) throw new Error('No upstream taxonomy found. Run a Taxonomy step first.');
            const signals = getUpstreamExtractOutput(idx);
            if (!signals) throw new Error('No upstream signals found. Run an Extract step first.');
            const ctx = getUpstreamContextText(idx);
            result = await runValidateStep(step.systemPrompt, step.userPrompt, ctx, taxonomy, signals, onTokens);
            step.output = result.output;
            step.elapsedSeconds = result.elapsed_seconds;
        } else if (step.type === 'classify') {
            const taxonomy = getUpstreamValidateOutput(idx);
            if (!taxonomy) throw new Error('No upstream validate output found. Run the Validate step first.');
            result = await runClassifyStep(step.systemPrompt, step.userPrompt, taxonomy, studioInputs.reviews);
            step.output = result.output;
            step.elapsedSeconds = result.elapsed_seconds;
        }
        step.status = 'done';
        console.log(`[executeStep] ${step.type} completed. Output:`, step.output ? Object.keys(step.output) : 'null', 'Elapsed:', step.elapsedSeconds);
    } catch (e) {
        step.status = 'error';
        console.error(`[executeStep] ${step.type} failed:`, e.message, e);
        showStatus(e.message, 'error');
    }
    updateStepUI(step);
    updateTreemap();
    // Auto-save pipeline state and step output after each step
    if (currentRunId && step.status === 'done') {
        const stepIndex = pipeline.indexOf(step);
        savePipelineState(currentRunId, serializePipeline()).catch(() => {});
        if (step.output) {
            saveStepOutput(currentRunId, step.type, stepIndex, step.output, step.elapsedSeconds).catch(
                e => console.warn('[auto-save] Failed to save step output:', e.message)
            );
        }

        // After classify step: sync coded rows to the lead client for visualizations
        if (step.type === 'classify' && step.output) {
            const taxonomy = getUpstreamValidateOutput(pipeline.indexOf(step));
            if (taxonomy && currentRunId) {
                console.log('[sync] Classify step done — syncing to client...');
                syncToClient(currentRunId, taxonomy).then(result => {
                    console.log(`[sync] Done: ${result.rows_coded}/${result.rows_total} rows coded, client=${result.client_id}`);
                    if (result.client_id) currentClientId = result.client_id;
                    showStatus(`Synced ${result.rows_coded} coded rows to visualizations.`, 'success');
                }).catch(e => {
                    console.warn('[sync] Failed to sync to client:', e.message);
                });
            }
        }
    }
}

function updateStepUI(step) {
    const card = els.editor.querySelector(`[data-step-id="${step.id}"]`);
    const panel = els.outputs.querySelector(`[data-step-id="${step.id}"]`);
    if (!card || !panel) return;

    const btn = card.querySelector('.btn-play');
    const elapsed = card.querySelector('.step-elapsed');

    card.classList.toggle('running', step.status === 'running');
    if (btn) {
        btn.classList.toggle('running', step.status === 'running');
        btn.disabled = step.status === 'running';
    }
    if (elapsed) elapsed.textContent = step.elapsedSeconds ? `${step.elapsedSeconds}s` : '';

    updateOutputPanel(panel, step);
}

function clearDownstream(fromIndex) {
    for (let i = fromIndex + 1; i < pipeline.length; i++) {
        const s = pipeline[i];
        s.output = null;
        s.elapsedSeconds = null;
        s.status = 'idle';
        updateStepUI(s);
    }
}

// ---------------------------------------------------------------------------
// Treemap
// ---------------------------------------------------------------------------

/**
 * Find the best taxonomy output for the treemap.
 * Prefers: validate > taxonomy > code (legacy)
 */
function getTreemapSource() {
    // New chain: validate or taxonomy output has categories/topics
    for (let i = pipeline.length - 1; i >= 0; i--) {
        const s = pipeline[i];
        if ((s.type === 'validate' || s.type === 'taxonomy') && s.output?.categories) return { type: 'taxonomy', output: s.output };
    }
    // Legacy chain: code output has coded_reviews
    for (let i = pipeline.length - 1; i >= 0; i--) {
        if (pipeline[i].type === 'code' && pipeline[i].output?.coded_reviews) return { type: 'code', output: pipeline[i].output };
    }
    return null;
}

function buildTreemapFromTaxonomy(taxonomyOutput) {
    const categories = taxonomyOutput.categories || [];
    return {
        name: 'Root',
        children: categories.map(cat => ({
            name: cat.category,
            children: (cat.topics || []).map(topic => ({
                name: topic.label,
                value: topic.signal_count || topic.verbatims?.length || 1,
                verbatims: (topic.verbatims || []).map(v => ({
                    text: v.text,
                    sentiment: 'neutral',
                    index: v.review_id,
                })),
            })),
        })),
    };
}

function buildTreemapFromCodeOutput(codeOutput) {
    const codedReviews = codeOutput.coded_reviews || [];
    const reviews = studioInputs?.reviews || [];
    const categoryMap = new Map();

    codedReviews.forEach(review => {
        const row = reviews.find(r => r.respondent_id === review.respondent_id);
        const text = row?.value || '';
        (review.topics || []).forEach(topic => {
            if (!categoryMap.has(topic.category)) categoryMap.set(topic.category, new Map());
            const cat = categoryMap.get(topic.category);
            if (!cat.has(topic.label)) cat.set(topic.label, []);
            cat.get(topic.label).push({ text, sentiment: topic.sentiment, index: review.respondent_id });
        });
    });

    return {
        name: 'Root',
        children: Array.from(categoryMap.entries()).map(([catName, topics]) => ({
            name: catName,
            children: Array.from(topics.entries()).map(([label, verbatims]) => ({
                name: label,
                value: verbatims.length,
                verbatims,
            })),
        })),
    };
}

function updateTreemap() {
    const container = document.getElementById('treemapContainer');
    const copyBtn = document.getElementById('treemapCopyBtn');
    const source = getTreemapSource();
    if (!source) {
        container.innerHTML = '<div class="treemap-placeholder">Run the pipeline to see the treemap preview.</div>';
        if (copyBtn) copyBtn.style.display = 'none';
        return;
    }

    const hierarchy = source.type === 'taxonomy'
        ? buildTreemapFromTaxonomy(source.output)
        : buildTreemapFromCodeOutput(source.output);

    if (typeof window._studioRenderTreemap === 'function') {
        window._studioRenderTreemap(hierarchy);
    }

    if (copyBtn) {
        copyBtn.style.display = 'inline-block';
        copyBtn.onclick = () => {
            const json = JSON.stringify(source.output, null, 2);
            navigator.clipboard.writeText(json).then(() => {
                copyBtn.textContent = 'Copied!';
                setTimeout(() => { copyBtn.textContent = 'Copy JSON'; }, 1500);
            });
        };
    }

    // Show Generate section when taxonomy/validate is complete
    const generateSection = document.getElementById('generateSection');
    if (generateSection) {
        if (source) {
            generateSection.style.display = '';
            loadGeneratePromptVersions();
        } else {
            generateSection.style.display = 'none';
        }
    }
}

// ---------------------------------------------------------------------------
// Ad Generation — split-screen prompt editor with versioning
// ---------------------------------------------------------------------------
let generatedBriefs = [];
let generatedAdBatches = [];
let generatePromptVersions = [];
let generateSelectedVersionId = null;

const GENERATE_SYSTEM_PROMPT = `You are a Senior Facebook Ads Creative Strategist specialising in performance creative grounded in Voice of Customer (VoC) data.

You receive a creative brief containing:
- A VoC topic with verbatim customer quotes
- Assigned creative lanes to write in
- Assigned close patterns for each lane
- Available proof modalities and block structure fuel
- Supporting material from related topics
- Business context including brand and landing page

Your job: produce one production-ready Facebook ad concept per assigned lane.

## CREATIVE RULES

### Voice & Tone
- Warm, human, unmistakably on the reader's side
- Readable at 3rd\u20135th grade level
- Conversational \u2014 like a friend who genuinely understands what they're going through
- Never pushy, never performatively enthusiastic

### The Friend Test
Before finalising any ad: would a genuine friend who cares about this person and happens to know about this product actually say this? If it sounds like it's pushing rather than guiding, rewrite it.

### VoC Integration
- HIGH-rated verbatims: use aggressively. Let customer language drive the narrative.
- MEDIUM-rated verbatims: extract the emotional core. Translate into brand-compliant phrasing.
- Supporting material verbatims: use as secondary proof or texture.
- NEVER invent customer sentiment not present in the VoC data.
- NEVER force verbatim quotes that sound unnatural in context.

### Pain & Benefit Language
- Be specific and concrete. Replace abstract statements with vivid, situational ones.
- Use the Block Structure when building major pain or benefit sections:
  1. Overarching statement
  2. Specific, vivid descriptions (use verbatims here)
  3. Dimensional, lived-in experience (the mind movie)
  4. Emotional recap

### Proof Integration
- Follow every significant claim with a proof element.
- Use the proof modalities specified in the brief.
- Embed proof inside sentences, don't bolt it on after.

### Close Architecture
Each ad must close with the pattern specified in the brief. The close must:
1. Bridge \u2014 connect the ad's emotional payload to the action
2. Direct \u2014 tell them exactly what to do
3. Shrink \u2014 make the action feel tiny relative to the emotional payoff

### Single Variable Testing
Each ad tests ONE clear belief. 1 belief \u2192 1 ad \u2192 1 test variable.

### Headline Mechanics
- 9\u201313 words / ~65 characters
- Authority trigrams where natural: "This is why...", "The reason why...", "What happens when..."`;

const GENERATE_USER_PROMPT = `Here is the business context for this brand:

<business_context>
{BUSINESS_CONTEXT}
</business_context>

Here is the Voice of Customer data \u2014 raw Trustpilot reviews from real customers of this brand. Mine these aggressively for emotional truth, pain language, benefit language, and proof.

<voc_data>
{FULL_RAW_REVIEWS_FOR_THIS_TOPIC}
</voc_data>

The VoC analysis identified these as the strongest themes in this data:

<theme_guidance>
Primary theme: {TOPIC_LABEL} ({CATEGORY})
Supporting themes: {LIST_OF_SECONDARY_TOPIC_LABELS_IN_SAME_CATEGORY}

Key VoC signals to mine:
{VERBATIM_BULLETS}

Available proof modalities in this data: {PROOF_TAGS}
Available emotional anchors: {BLOCK_TAGS}
</theme_guidance>

Write ads for the following lanes: {COMMA_SEPARATED_LANE_NAMES}

Each lane should produce 1 ad concept. Use a different close pattern for each ad. Ground every ad in the VoC data above \u2014 no invented sentiment. Return the JSON and nothing else.`;

// Load generate prompt versions
async function loadGeneratePromptVersions() {
    try {
        const data = await fetchPromptVersions('voc_generate');
        generatePromptVersions = data.versions || [];
        const select = document.getElementById('generateVersionSelect');
        if (select) {
            select.innerHTML = '<option value="">Hardcoded default</option>';
            generatePromptVersions.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.id;
                opt.textContent = `v${v.version} (${v.status})`;
                select.appendChild(opt);
            });
        }
    } catch (e) {
        console.warn('[prompt-studio] Failed to load generate versions:', e);
    }

    // Pre-fill with defaults if textareas are empty
    const sysTA = document.getElementById('generateSystemPrompt');
    const userTA = document.getElementById('generateUserPrompt');
    if (sysTA && !sysTA.value) sysTA.value = GENERATE_SYSTEM_PROMPT;
    if (userTA && !userTA.value) userTA.value = GENERATE_USER_PROMPT;

    // Show briefs summary
    updateBriefsSummary();

    // Auto-resize textareas
    const sysTA2 = document.getElementById('generateSystemPrompt');
    const userTA2 = document.getElementById('generateUserPrompt');
    [sysTA2, userTA2].forEach(ta => {
        if (ta) { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; }
    });
}

function handleGenerateSelectVersion(versionId) {
    generateSelectedVersionId = versionId || null;
    const version = generatePromptVersions.find(v => v.id === versionId);
    const sysTA = document.getElementById('generateSystemPrompt');
    const userTA = document.getElementById('generateUserPrompt');
    if (version) {
        if (sysTA) sysTA.value = version.system_message || '';
        if (userTA) userTA.value = version.prompt_message || '';
    } else {
        if (sysTA) sysTA.value = GENERATE_SYSTEM_PROMPT;
        if (userTA) userTA.value = GENERATE_USER_PROMPT;
    }
    [sysTA, userTA].forEach(ta => {
        if (ta) { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; }
    });
}

async function handleGenerateSaveNew() {
    const sysPrompt = document.getElementById('generateSystemPrompt')?.value || '';
    const userPrompt = document.getElementById('generateUserPrompt')?.value || '';
    const maxVersion = generatePromptVersions.reduce((max, v) => Math.max(max, v.version), 0);
    const newVersion = maxVersion + 1;
    const name = generatePromptVersions[0]?.name || 'voc_generate';
    try {
        await createPromptVersion({ name, version: newVersion, prompt_type: 'system', system_message: sysPrompt, prompt_message: userPrompt, prompt_purpose: 'voc_generate', status: 'test', llm_model: 'claude-sonnet-4-5-20250929' });
        showStatus(`Generate prompt saved as v${newVersion}.`, 'success');
        await loadGeneratePromptVersions();
        const newV = generatePromptVersions.find(v => v.version === newVersion);
        if (newV) { generateSelectedVersionId = newV.id; document.getElementById('generateVersionSelect').value = newV.id; }
    } catch (e) { showStatus(e.message, 'error'); }
}

async function handleGenerateOverwrite() {
    if (!generateSelectedVersionId) { showStatus('Select a version first.', 'error'); return; }
    const sysPrompt = document.getElementById('generateSystemPrompt')?.value || '';
    const userPrompt = document.getElementById('generateUserPrompt')?.value || '';
    try {
        await updatePrompt(generateSelectedVersionId, { system_message: sysPrompt, prompt_message: userPrompt });
        showStatus('Generate prompt overwritten.', 'success');
        await loadGeneratePromptVersions();
    } catch (e) { showStatus(e.message, 'error'); }
}

async function handleGenerateSetLive() {
    if (!generateSelectedVersionId) { showStatus('Select a version first.', 'error'); return; }
    try {
        const currentLive = generatePromptVersions.find(v => v.status === 'live');
        if (currentLive && currentLive.id !== generateSelectedVersionId) await updatePrompt(currentLive.id, { status: 'archived' });
        await updatePrompt(generateSelectedVersionId, { status: 'live' });
        showStatus('Generate prompt set to live.', 'success');
        await loadGeneratePromptVersions();
    } catch (e) { showStatus(e.message, 'error'); }
}

function buildBusinessContext() {
    // Pull from Context step output (richest source) or fall back to studioInputs
    const contextOutput = pipeline.find(s => s.type === 'context' && s.output);
    const contextText = contextOutput?.output?.context_text || studioInputs?.company_context?.context_text || '';

    return {
        brand: studioInputs?.company_name || '',
        product: contextText,
        website: studioInputs?.url || '',
        category: '',
        primary_claims: '',
        target_customer: '',
        competitors: '',
    };
}

function updateBriefsSummary() {
    const source = getTreemapSource();
    if (!source) return;
    const taxonomy = source.output;
    const businessContext = buildBusinessContext();
    const payloads = buildCreativePayloads(taxonomy, studioInputs?.reviews || [], businessContext);
    const summary = summarizePayloads(payloads);
    const el = document.getElementById('generateBriefsSummary');
    if (el) {
        el.textContent = `${summary.total_payloads} qualifying topics → ${summary.total_ads} ads (${summary.primary} PRIMARY, ${summary.secondary} SECONDARY) — ${summary.total_reviews} full reviews`;
    }
}

async function handleGenerateAds() {
    const source = getTreemapSource();
    if (!source) { showStatus('Run the taxonomy pipeline first.', 'error'); return; }

    const sysPrompt = document.getElementById('generateSystemPrompt')?.value || GENERATE_SYSTEM_PROMPT;
    const userPromptTemplate = document.getElementById('generateUserPrompt')?.value || GENERATE_USER_PROMPT;

    const taxonomy = source.output;
    const businessContext = buildBusinessContext();

    // Flush previous ads
    generatedAdBatches = [];
    generatedBriefs = [];
    renderAdsSection();
    renderGenerateOutput();
    // Delete saved ad outputs from DB
    if (currentRunId) {
        saveStepOutput(currentRunId, 'generate', pipeline.length, { batches: [] }, null).catch(() => {});
    }

    // Build rich payloads with full reviews (capped at ~36 ads)
    const payloads = buildCreativePayloads(taxonomy, studioInputs?.reviews || [], businessContext);
    const summary = summarizePayloads(payloads);
    console.log(`[generate] ${payloads.length} payloads, ~${summary.total_ads} ads planned (capped at 36)`);

    if (payloads.length === 0) { showStatus('No qualifying topics found.', 'error'); return; }

    showStatus(`Generating ~${summary.total_ads} ads from ${summary.total_payloads} topics...`, '');
    const btn = document.getElementById('generateAdsBtn');
    if (btn) { btn.disabled = true; btn.classList.add('running'); }

    generatedBriefs = payloads; // Store for renderAdsSection
    generatedAdBatches = [];
    let completed = 0;
    let failed = 0;
    const startTime = Date.now();

    const MAX_TOTAL_ADS = 36;
    let totalAdsGenerated = 0;

    for (const payload of payloads) {
        if (totalAdsGenerated >= MAX_TOTAL_ADS) {
            console.log(`[generate] Hit ${MAX_TOTAL_ADS} ad cap. Stopping.`);
            break;
        }
        const assembledPrompt = assembleUserPrompt(userPromptTemplate, payload);
        try {
            const result = await runGenerateAd(sysPrompt, assembledPrompt);
            console.log(`[generate] Raw output for ${payload.topic_label}:`, JSON.stringify(result.output).slice(0, 300));
            // Normalize: the output might be { ads: [...] } or { brief_id, topic_label, ads: [...] } or just an array
            let output = result.output || {};
            if (Array.isArray(output)) {
                output = { ads: output };
            } else if (!output.ads && Array.isArray(output.ad_concepts)) {
                output = { ads: output.ad_concepts };
            }
            // Trim ads if this batch would exceed the cap
            const adsInBatch = Array.isArray(output.ads) ? output.ads.length : 0;
            const remaining = MAX_TOTAL_ADS - totalAdsGenerated;
            if (adsInBatch > remaining) {
                output.ads = output.ads.slice(0, remaining);
            }
            totalAdsGenerated += (output.ads?.length || 0);
            console.log(`[generate] ${payload.topic_label}: ${output.ads?.length || 0} ads (total: ${totalAdsGenerated}/${MAX_TOTAL_ADS})`);

            output._topic_label = payload.topic_label;
            output._category = payload.category;
            output._creative_priority = payload.creative_priority;
            generatedAdBatches.push(output);
            completed++;
            showStatus(`Generated ${totalAdsGenerated} ads from ${completed}/${payloads.length} topics...`, '');
            renderAdsSection();
            renderGenerateOutput();
            // Incrementally save after each topic
            if (currentRunId) {
                saveStepOutput(currentRunId, 'generate', pipeline.length, { batches: generatedAdBatches }, null).catch(
                    e => console.warn('[auto-save] Failed to save ad batch:', e.message)
                );
            }
        } catch (e) {
            console.error(`[generate] Failed for ${payload.topic_label}:`, e.message);
            failed++;
            // Retry once
            try {
                const retry = await runGenerateAd(sysPrompt, assembledPrompt);
                let output = retry.output || {};
                if (Array.isArray(output)) output = { ads: output };
                else if (!output.ads && Array.isArray(output.ad_concepts)) output = { ads: output.ad_concepts };
                output._topic_label = payload.topic_label;
                output._category = payload.category;
                output._creative_priority = payload.creative_priority;
                generatedAdBatches.push(output);
                completed++; failed--;
                renderAdsSection();
                renderGenerateOutput();
            } catch (e2) {
                console.error(`[generate] Retry failed for ${payload.topic_label}:`, e2.message);
            }
        }
    }

    if (btn) { btn.disabled = false; btn.classList.remove('running'); }
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    const elapsedEl = document.getElementById('generateElapsed');
    if (elapsedEl) elapsedEl.textContent = `${elapsed}s`;

    const totalAds = generatedAdBatches.reduce((sum, b) => sum + (b.ads?.length || 0), 0);
    showStatus(`Done! ${totalAds} ads from ${completed} topics.${failed > 0 ? ` ${failed} failed.` : ''}`, 'success');
    renderAdsSection();
    renderGenerateOutput();

    // Auto-save ad outputs
    if (currentRunId && generatedAdBatches.length) {
        saveStepOutput(currentRunId, 'generate', pipeline.length, { batches: generatedAdBatches }, parseFloat(elapsed)).catch(
            e => console.warn('[auto-save] Failed to save ad outputs:', e.message)
        );
    }

    // Save generated ads as FacebookAd records for the lead client
    if (currentClientId && generatedAdBatches.length) {
        saveAdsToClient(currentClientId, generatedAdBatches).catch(
            e => console.warn('[save-ads] Failed to save ads to client:', e.message)
        );
    }
}

function renderGenerateOutput() {
    const body = document.getElementById('generateOutputBody');
    const copyBtn = document.getElementById('copyAllAdsJsonBtn');
    if (!body) return;

    if (generatedAdBatches.length === 0) {
        body.innerHTML = '<span class="output-placeholder">Run the generate step to see output.</span>';
        if (copyBtn) copyBtn.style.display = 'none';
        return;
    }

    body.innerHTML = `<pre class="output-json">${highlightJson(generatedAdBatches)}</pre>`;
    if (copyBtn) {
        copyBtn.style.display = '';
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(JSON.stringify(generatedAdBatches, null, 2)).then(() => {
                copyBtn.textContent = 'Copied!';
                setTimeout(() => { copyBtn.textContent = 'Copy JSON'; }, 1500);
            });
        };
    }
}

function renderAdsSection() {
    const section = document.getElementById('adsSection');
    const container = document.getElementById('adsContainer');
    const copyBtn = document.getElementById('copyAllAdsBtn');
    if (section) section.style.display = generatedAdBatches.length ? '' : 'none';
    renderAds(container, generatedAdBatches, generatedBriefs, studioInputs?.company_name || 'Brand');

    if (copyBtn && generatedAdBatches.length > 0) {
        copyBtn.style.display = '';
        copyBtn.onclick = () => {
            const json = JSON.stringify(generatedAdBatches, null, 2);
            navigator.clipboard.writeText(json).then(() => {
                copyBtn.textContent = 'Copied!';
                setTimeout(() => { copyBtn.textContent = 'Copy All JSON'; }, 1500);
            });
        };
    }
}

// ---------------------------------------------------------------------------
// Save generated ads to FacebookAd table
// ---------------------------------------------------------------------------
async function saveAdsToClient(clientId, adBatches) {
    let saved = 0;
    let failed = 0;
    for (const batch of adBatches) {
        const ads = Array.isArray(batch.ads) ? batch.ads : [];
        for (const ad of ads) {
            try {
                // Map testType → angle for the newer schema
                const fullJson = { ...ad };
                if (fullJson.testType && !fullJson.angle) {
                    fullJson.angle = fullJson.testType;
                    delete fullJson.testType;
                }

                await createFacebookAd(clientId, {
                    primary_text: ad.primary_text || '',
                    headline: ad.headline || '',
                    description: ad.description || '',
                    call_to_action: ad.call_to_action || 'LEARN_MORE',
                    destination_url: ad.destination_url || '',
                    voc_evidence: ad.voc_evidence || [],
                    image_hash: ad.media?.image_hash || null,
                    full_json: fullJson,
                    status: 'draft',
                });
                saved++;
            } catch (e) {
                console.warn(`[save-ads] Failed to save ad: ${e.message}`);
                failed++;
            }
        }
    }
    console.log(`[save-ads] Saved ${saved} ads to client ${clientId}${failed ? `, ${failed} failed` : ''}`);
}

// ---------------------------------------------------------------------------
// Versioning actions
// ---------------------------------------------------------------------------
function handleSelectVersion(stepId, versionId) {
    const step = getStep(stepId);
    if (!step) return;

    step.selectedVersionId = versionId || null;
    const version = step.promptVersions.find(v => v.id === versionId);
    const card = els.editor.querySelector(`[data-step-id="${stepId}"]`);
    if (!card) return;

    if (version) {
        step.systemPrompt = version.system_message || '';
        step.userPrompt = version.prompt_message || '';
    } else {
        const keys = DEFAULT_PROMPT_KEYS[step.type] || {};
        step.systemPrompt = studioInputs?.default_prompts?.[keys.system] || '';
        step.userPrompt = studioInputs?.default_prompts?.[keys.user] || '';
    }

    const sysTA = card.querySelector('[data-field="systemPrompt"]');
    const userTA = card.querySelector('[data-field="userPrompt"]');
    if (sysTA) sysTA.value = step.systemPrompt;
    if (userTA) userTA.value = step.userPrompt;
    step.isDirty = false;
    setDirtyIndicator(stepId, false);
    autoResizeTextareas(card);
}

async function handleOverwrite(stepId) {
    const step = getStep(stepId);
    if (!step?.selectedVersionId) {
        showStatus('Select a version from the dropdown first — cannot overwrite hardcoded default.', 'error');
        return;
    }
    const version = step.promptVersions.find(v => v.id === step.selectedVersionId);
    const label = version ? `v${version.version}` : 'current';
    try {
        await updatePrompt(step.selectedVersionId, {
            system_message: step.systemPrompt,
            prompt_message: step.userPrompt,
        });
        step.isDirty = false;
        setDirtyIndicator(stepId, false);
        showStatus(`Overwritten ${label}.`, 'success');
        await loadVersionsForStep(step);
    } catch (e) { showStatus(e.message, 'error'); }
}

async function handleSaveNew(stepId) {
    const step = getStep(stepId);
    if (!step) return;
    const purpose = PROMPT_PURPOSE_MAP[step.type];
    const maxVersion = step.promptVersions.reduce((max, v) => Math.max(max, v.version), 0);
    const newVersion = maxVersion + 1;
    const name = step.promptVersions[0]?.name || purpose;

    try {
        await createPromptVersion({
            name,
            version: newVersion,
            prompt_type: 'system',
            system_message: step.systemPrompt,
            prompt_message: step.userPrompt,
            prompt_purpose: purpose,
            status: 'test',
            llm_model: 'claude-sonnet-4-5-20250929',
        });
        showStatus(`Saved as v${newVersion}.`, 'success');
        await loadVersionsForStep(step);
        // Select the new version
        const newV = step.promptVersions.find(v => v.version === newVersion);
        if (newV) {
            step.selectedVersionId = newV.id;
            const card = els.editor.querySelector(`[data-step-id="${stepId}"]`);
            if (card) updateVersionDropdown(card, step);
        }
        step.isDirty = false;
        setDirtyIndicator(stepId, false);
    } catch (e) { showStatus(e.message, 'error'); }
}

async function handleSetLive(stepId) {
    const step = getStep(stepId);
    if (!step?.selectedVersionId) {
        showStatus('Select a version from the dropdown first.', 'error');
        return;
    }
    const version = step.promptVersions.find(v => v.id === step.selectedVersionId);
    const label = version ? `v${version.version}` : 'selected version';
    try {
        // Archive current live version
        const currentLive = step.promptVersions.find(v => v.status === 'live');
        if (currentLive && currentLive.id !== step.selectedVersionId) {
            await updatePrompt(currentLive.id, { status: 'archived' });
        }
        await updatePrompt(step.selectedVersionId, { status: 'live' });
        showStatus(`${label} set to live.`, 'success');
        await loadVersionsForStep(step);
    } catch (e) { showStatus(e.message, 'error'); }
}

// ---------------------------------------------------------------------------
// Event handling
// ---------------------------------------------------------------------------
let eventsInitialized = false;

function setupEventDelegation() {
    if (eventsInitialized) return;
    eventsInitialized = true;

    // Single document-level click handler
    document.addEventListener('click', (e) => {
        // Copy output button
        const copyBtn = e.target.closest('.btn-copy-output');
        if (copyBtn) {
            const stepId = copyBtn.dataset.stepId;
            const step = pipeline.find(s => s.id === stepId);
            if (step?.output) {
                const text = JSON.stringify(step.output, null, 2);
                navigator.clipboard.writeText(text).then(() => {
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => { copyBtn.textContent = 'Copy'; }, 1500);
                }).catch(() => {
                    copyBtn.textContent = 'Failed';
                    setTimeout(() => { copyBtn.textContent = 'Copy'; }, 1500);
                });
            }
            return;
        }

        // Save dropdown toggle
        const saveToggle = e.target.closest('.save-dropdown-btn');
        if (saveToggle) {
            const wrapper = saveToggle.closest('.save-dropdown');
            const menu = wrapper?.querySelector('.save-dropdown-menu');
            if (menu) {
                const isOpen = menu.classList.contains('open');
                // Close all menus first
                document.querySelectorAll('.save-dropdown-menu.open').forEach(m => m.classList.remove('open'));
                if (!isOpen) menu.classList.add('open');
            }
            return;
        }

        // Close save menus on any click outside a save-dropdown
        if (!e.target.closest('.save-dropdown')) {
            document.querySelectorAll('.save-dropdown-menu.open').forEach(m => m.classList.remove('open'));
        }

        // Action buttons (run, delete, save-new, overwrite, set-live)
        const actionBtn = e.target.closest('[data-action]');
        if (actionBtn) {
            const action = actionBtn.dataset.action;
            const stepId = actionBtn.dataset.stepId;
            document.querySelectorAll('.save-dropdown-menu.open').forEach(m => m.classList.remove('open'));

            if (action === 'run-step') executeStep(stepId);
            if (action === 'delete-step') removeStep(stepId);
            if (action === 'save-new') handleSaveNew(stepId);
            if (action === 'overwrite') handleOverwrite(stepId);
            if (action === 'set-live') handleSetLive(stepId);
            // Generate prompt versioning
            if (action === 'generate-save-new') handleGenerateSaveNew();
            if (action === 'generate-overwrite') handleGenerateOverwrite();
            if (action === 'generate-set-live') handleGenerateSetLive();
        }
    });

    // Version select changes
    document.addEventListener('change', (e) => {
        if (e.target.dataset.action === 'select-version') {
            handleSelectVersion(e.target.dataset.stepId, e.target.value);
        }
        if (e.target.dataset.action === 'select-generate-version') {
            handleGenerateSelectVersion(e.target.value);
        }
    });

    // Dirty tracking + auto-resize on textareas
    document.addEventListener('input', (e) => {
        if (e.target.classList.contains('prompt-textarea')) {
            e.target.style.height = 'auto';
            e.target.style.height = e.target.scrollHeight + 'px';

            if (!e.target.readOnly) {
                const stepId = e.target.dataset.stepId;
                const step = getStep(stepId);
                if (step) { step.isDirty = true; setDirtyIndicator(stepId, true); }
                const field = e.target.dataset.field;
                if (step && field === 'systemPrompt') step.systemPrompt = e.target.value;
                if (step && field === 'userPrompt') step.userPrompt = e.target.value;
            }
        }
    });

    // Scrape button + split menu
    els.scrapeBtn.addEventListener('click', handleScrape);
    const splitToggle = document.getElementById('splitBtnToggle');
    const splitMenu = document.getElementById('splitBtnMenu');
    if (splitToggle && splitMenu) {
        splitToggle.addEventListener('click', () => {
            splitMenu.style.display = splitMenu.style.display === 'none' ? '' : 'none';
        });
        document.addEventListener('click', (e) => {
            if (!splitToggle.contains(e.target) && !splitMenu.contains(e.target)) {
                splitMenu.style.display = 'none';
            }
        });
    }
    document.getElementById('runEverythingBtn')?.addEventListener('click', () => {
        if (splitMenu) splitMenu.style.display = 'none';
        handleRunEverything();
    });

    // Save run button
    document.getElementById('saveRunBtn').addEventListener('click', handleSaveRun);

    // Run selector
    els.runSelector.addEventListener('change', () => {
        const runId = els.runSelector.value;
        if (runId) handleLoadRun(runId);
    });

    // Add step
    els.addStepBtn.addEventListener('click', () => {
        const type = els.addStepType.value;
        if (type) addStep(type);
    });

    // Generate Ads button
    document.getElementById('generateAdsBtn')?.addEventListener('click', handleGenerateAds);

    // Logout
    els.logoutButton.addEventListener('click', () => window.Auth?.handleLogout());

    // Expose save helpers for console access
    window._studioSaveRun = handleSaveRun;
    window._studioSetRunId = (id) => { currentRunId = id; updateSaveButton(); };
}

// ---------------------------------------------------------------------------
// Entry flows
// ---------------------------------------------------------------------------
async function handleScrape() {
    const url = els.prospectUrl.value.trim();
    if (!url) { showStatus('Enter a prospect URL.', 'error'); return; }
    showStatus('Scraping Trustpilot reviews...', '');
    els.scrapeBtn.disabled = true;
    try {
        const data = await scrapeProspect(url, els.companyName.value.trim(), parseInt(els.minReviews.value) || 200);
        showStatus(`Scraped ${data.review_count} reviews from ${data.domain}. Loading reviews & prompts...`, '');

        // Load full reviews from persisted run + default prompts in parallel
        const [runInputs, promptsData] = await Promise.all([
            fetchRunInputs(data.run_id),
            fetchDefaultPrompts().catch(e => {
                console.warn('[prompt-studio] Could not load default prompts, using empty:', e);
                return { default_prompts: null };
            }),
        ]);

        studioInputs = {
            url,
            domain: data.domain,
            company_name: data.company_name,
            reviews: runInputs.reviews || [],
            company_context: null,
            default_prompts: promptsData.default_prompts,
        };
        currentRunId = data.run_id;
        currentClientId = data.client_id || null;
        showStatus(`Scraped ${data.review_count} reviews from ${data.domain}. Pipeline ready.`, 'success');
        initDefaultPipeline();
        updateSaveButton();
        // Refresh the run selector so this scrape appears in the dropdown
        refreshRunSelector();
    } catch (e) {
        showStatus(e.message, 'error');
    }
    els.scrapeBtn.disabled = false;
}

async function handleRunEverything() {
    const url = els.prospectUrl.value.trim();
    if (!url) { showStatus('Enter a prospect URL.', 'error'); return; }

    const scrapeBtn = els.scrapeBtn;
    const splitToggle = document.getElementById('splitBtnToggle');
    if (scrapeBtn) scrapeBtn.disabled = true;
    if (splitToggle) splitToggle.disabled = true;

    try {
        // Step 1: Scrape
        showStatus('Run Everything: Scraping reviews...', '');
        await handleScrape();

        if (!currentRunId || !studioInputs?.reviews?.length) {
            showStatus('Scrape failed or no reviews found.', 'error');
            return;
        }

        // Step 2: Run each pipeline step in sequence
        for (let i = 0; i < pipeline.length; i++) {
            const step = pipeline[i];
            if (step.status === 'done') continue;
            showStatus(`Run Everything: Running ${step.type} (${i + 1}/${pipeline.length})...`, '');
            await executeStep(step, i);
            if (step.status === 'error') {
                showStatus(`Run Everything stopped: ${step.type} failed.`, 'error');
                return;
            }
        }

        // Step 3: Generate ads
        showStatus('Run Everything: Generating ads...', '');
        await handleGenerateAds();

        showStatus('Run Everything complete! Scrape → Pipeline → Ads → Sync all done.', 'success');
    } catch (e) {
        showStatus(`Run Everything failed: ${e.message}`, 'error');
        console.error('[runEverything]', e);
    } finally {
        if (scrapeBtn) scrapeBtn.disabled = false;
        if (splitToggle) splitToggle.disabled = false;
    }
}

async function handleLoadRun(runId) {
    showStatus('Loading run data...', '');
    try {
        const [data, outputsData] = await Promise.all([
            fetchRunInputs(runId),
            fetchStepOutputs(runId).catch(() => ({ outputs: [] })),
        ]);
        currentRunId = runId;
        currentClientId = data.client_id || null;
        studioInputs = {
            url: data.company_context?.source_url || '',
            domain: '',
            company_name: data.company_context?.name || '',
            reviews: data.reviews,
            company_context: data.company_context,
            default_prompts: data.default_prompts,
        };
        els.prospectUrl.value = studioInputs.url;
        els.companyName.value = studioInputs.company_name;

        if (data.pipeline_state?.length) {
            restorePipeline(data.pipeline_state);
        } else {
            initDefaultPipeline();
        }

        // Restore saved step outputs into pipeline
        const savedOutputs = outputsData.outputs || [];
        if (savedOutputs.length) {
            for (const saved of savedOutputs) {
                // Restore ad generation outputs
                if (saved.step_type === 'generate' && saved.output?.batches) {
                    generatedAdBatches = saved.output.batches;
                    renderAdsSection();
                    renderGenerateOutput();
                    continue;
                }
                const step = pipeline.find(s => s.type === saved.step_type);
                if (step && saved.output) {
                    step.output = saved.output;
                    step.elapsedSeconds = saved.elapsed_seconds;
                    step.status = 'done';
                    updateStepUI(step);
                }
            }
            updateTreemap();
            showStatus(`Loaded ${data.reviews.length} reviews with ${savedOutputs.length} saved outputs.`, 'success');
        } else {
            showStatus(`Loaded ${data.reviews.length} reviews.`, 'success');
        }
        updateSaveButton();
    } catch (e) {
        showStatus(e.message, 'error');
    }
}

async function loadRunSelector() {
    try {
        const data = await fetchLeadgenRuns();
        populateRunDropdown(data.items || []);

        // Pre-select from URL param
        const params = new URLSearchParams(window.location.search);
        const runId = params.get('run_id');
        if (runId) {
            els.runSelector.value = runId;
            handleLoadRun(runId);
        }
    } catch (e) {
        console.error('[prompt-studio] Failed to load runs:', e);
    }
}

async function refreshRunSelector() {
    try {
        const data = await fetchLeadgenRuns();
        populateRunDropdown(data.items || []);
    } catch (e) {
        console.error('[prompt-studio] Failed to refresh runs:', e);
    }
}

function populateRunDropdown(items) {
    els.runSelector.innerHTML = '<option value="">Select a run...</option>';
    items.forEach(run => {
        const opt = document.createElement('option');
        opt.value = run.run_id;
        opt.textContent = `${run.company_name || run.company_domain} (${run.review_count} reviews, ${new Date(run.created_at).toLocaleDateString()})`;
        els.runSelector.appendChild(opt);
    });
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
function initializePage(userInfo) {
    cacheElements();
    els.founderEmail.textContent = userInfo?.email || '';

    window.Auth?.hideLogin();
    document.getElementById('appShell').style.display = 'flex';

    setupEventDelegation();
    loadRunSelector();
}

function waitForAuth() {
    return new Promise((resolve) => {
        if (typeof window.Auth !== 'undefined' && typeof window.Auth.checkAuth === 'function') {
            resolve();
        } else {
            const check = setInterval(() => {
                if (typeof window.Auth !== 'undefined' && typeof window.Auth.checkAuth === 'function') {
                    clearInterval(check);
                    resolve();
                }
            }, 50);
            setTimeout(() => { clearInterval(check); resolve(); }, 2000);
        }
    });
}

async function boot() {
    await waitForAuth();

    const authenticated = await window.Auth.checkAuth();
    if (!authenticated) return;

    const userInfo = window.Auth.getStoredUserInfo();
    if (!userInfo?.is_founder) {
        window.Auth.showLogin();
        const errorEl = document.getElementById('loginError');
        if (errorEl) {
            errorEl.textContent = 'Access denied: founder privileges required.';
            errorEl.style.display = 'block';
        }
        return;
    }
    initializePage(userInfo);
}

window.addEventListener('auth:authenticated', (e) => {
    const userInfo = e.detail?.user;
    if (userInfo?.is_founder) initializePage(userInfo);
});

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
} else {
    boot();
}
