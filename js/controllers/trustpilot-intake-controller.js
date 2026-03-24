import { generateTrustpilotPayload } from "/js/services/api-trustpilot-leadgen.js";

const formEl = document.getElementById("trustpilotIntakeForm");
const workEmailEl = document.getElementById("workEmail");
const companyUrlEl = document.getElementById("companyUrl");
const maxReviewsEl = document.getElementById("maxReviews");
const includeDebugDataEl = document.getElementById("includeDebugData");
const submitButtonEl = document.getElementById("submitButton");
const statusMessageEl = document.getElementById("statusMessage");
const progressStepsEl = document.getElementById("progressSteps");

function setStatus(message, kind = "neutral") {
    statusMessageEl.textContent = message;
    statusMessageEl.classList.remove("status-error", "status-success");
    if (kind === "error") statusMessageEl.classList.add("status-error");
    if (kind === "success") statusMessageEl.classList.add("status-success");
}

function setLoading(isLoading) {
    submitButtonEl.disabled = isLoading;
    submitButtonEl.textContent = isLoading ? "Generating..." : "Generate JSON";
}

function resetProgress() {
    if (!progressStepsEl) return;
    progressStepsEl.querySelectorAll("li").forEach((item) => {
        item.classList.remove("step-active", "step-complete", "step-error");
    });
}

function setProgress(step, state) {
    if (!progressStepsEl) return;
    const target = progressStepsEl.querySelector(`li[data-step="${step}"]`);
    if (!target) return;
    target.classList.remove("step-active", "step-complete", "step-error");
    if (state === "active") target.classList.add("step-active");
    if (state === "complete") target.classList.add("step-complete");
    if (state === "error") target.classList.add("step-error");
}

function setExpectedPipelineProgress() {
    resetProgress();
    setProgress("request", "complete");
    setProgress("fetch", "active");
    setProgress("extract", "active");
    setProgress("taxonomy", "active");
    setProgress("validate", "active");
    setProgress("persist", "active");
}

function applyProgressFromResult(response) {
    const rows = response?.payload?.process_voc_rows_import_ready || [];
    const processedCount = rows.filter((row) => row?.processed === true).length;
    const hasCoding = processedCount > 0;
    setProgress("request", "complete");
    setProgress("fetch", "complete");
    if (hasCoding) {
        setProgress("extract", "complete");
        setProgress("taxonomy", "complete");
        setProgress("validate", "complete");
    } else {
        setProgress("extract", "error");
        setProgress("taxonomy", "error");
        setProgress("validate", "error");
    }
    setProgress("persist", "complete");
}

function applyProgressFromError(errorMessage) {
    const message = (errorMessage || "").toLowerCase();
    setProgress("request", "complete");
    setProgress("fetch", "complete");
    if (message.includes("[extract]")) {
        setProgress("extract", "error");
    } else if (message.includes("[taxonomy]")) {
        setProgress("extract", "complete");
        setProgress("taxonomy", "error");
    } else if (message.includes("[validate]")) {
        setProgress("extract", "complete");
        setProgress("taxonomy", "complete");
        setProgress("validate", "error");
    } else if (message.includes("apify") || message.includes("trustpilot")) {
        setProgress("fetch", "error");
    } else {
        setProgress("extract", "error");
    }
}

function downloadJson(filename, payload) {
    const jsonString = JSON.stringify(payload, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
}

function parseIntOrDefault(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isNaN(parsed) ? fallback : parsed;
}

formEl.addEventListener("submit", async (event) => {
    event.preventDefault();

    const workEmail = (workEmailEl.value || "").trim();
    const companyUrl = (companyUrlEl.value || "").trim();
    const maxReviews = parseIntOrDefault(maxReviewsEl.value, 50);
    const includeDebugData = Boolean(includeDebugDataEl?.checked);

    if (!workEmail) {
        setStatus("Work email is required.", "error");
        return;
    }

    setLoading(true);
    setExpectedPipelineProgress();
    setStatus("Fetching company context and Trustpilot reviews...");

    try {
        const response = await generateTrustpilotPayload({
            work_email: workEmail,
            company_url: companyUrl || null,
            max_reviews: maxReviews,
            include_debug_data: includeDebugData,
        });

        applyProgressFromResult(response);
        downloadJson(response.file_name, response.payload);
        setStatus(
            `Done. Downloaded ${response.file_name} with ${response.review_count} review(s).`,
            "success",
        );
    } catch (error) {
        applyProgressFromError(error?.message || "");
        setStatus(error.message || "Failed to generate JSON payload.", "error");
    } finally {
        setLoading(false);
    }
});
