function getRequiredConfig({ backendBaseUrl, ingestSecret }) {
  const baseUrl = String(backendBaseUrl || "").replace(/\/$/, "");
  const secret = String(ingestSecret || "").trim();
  if (!baseUrl) {
    throw new Error("VIZUALIZD_BACKEND_URL is required");
  }
  if (!secret) {
    throw new Error("VIZUALIZD_SHOPIFY_INGEST_SECRET is required");
  }
  return { baseUrl, secret };
}

async function callBackend({
  backendBaseUrl,
  ingestSecret,
  path,
  method = "GET",
  payload = null,
  timeoutMs = 10000,
}) {
  const { baseUrl, secret } = getRequiredConfig({ backendBaseUrl, ingestSecret });
  const endpoint = `${baseUrl}${path}`;
  const controller = new AbortController();
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(endpoint, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-Vizualizd-Shopify-Secret": secret,
      },
      body: payload ? JSON.stringify(payload) : undefined,
      signal: controller.signal,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body?.detail || `Backend request failed (${response.status})`);
    }
    return body;
  } finally {
    clearTimeout(timeoutHandle);
  }
}

export function listSurveyTemplates({ backendBaseUrl, ingestSecret, timeoutMs = 10000 }) {
  return callBackend({
    backendBaseUrl,
    ingestSecret,
    path: "/api/shopify/survey-templates",
    method: "GET",
    timeoutMs,
  });
}

export function listSurveys({ backendBaseUrl, ingestSecret, shopDomain, timeoutMs = 10000 }) {
  return callBackend({
    backendBaseUrl,
    ingestSecret,
    path: `/api/shopify/surveys/${encodeURIComponent(shopDomain)}`,
    method: "GET",
    timeoutMs,
  });
}

export function createSurvey({ backendBaseUrl, ingestSecret, shopDomain, payload, timeoutMs = 10000 }) {
  return callBackend({
    backendBaseUrl,
    ingestSecret,
    path: `/api/shopify/surveys/${encodeURIComponent(shopDomain)}`,
    method: "POST",
    payload,
    timeoutMs,
  });
}

export function getSurvey({ backendBaseUrl, ingestSecret, shopDomain, surveyId, timeoutMs = 10000 }) {
  return callBackend({
    backendBaseUrl,
    ingestSecret,
    path: `/api/shopify/surveys/${encodeURIComponent(shopDomain)}/${Number(surveyId)}`,
    method: "GET",
    timeoutMs,
  });
}

export function updateSurvey({
  backendBaseUrl,
  ingestSecret,
  shopDomain,
  surveyId,
  payload,
  timeoutMs = 10000,
}) {
  return callBackend({
    backendBaseUrl,
    ingestSecret,
    path: `/api/shopify/surveys/${encodeURIComponent(shopDomain)}/${Number(surveyId)}`,
    method: "PUT",
    payload,
    timeoutMs,
  });
}

export function publishSurvey({ backendBaseUrl, ingestSecret, shopDomain, surveyId, timeoutMs = 10000 }) {
  return callBackend({
    backendBaseUrl,
    ingestSecret,
    path: `/api/shopify/surveys/${encodeURIComponent(shopDomain)}/${Number(surveyId)}/publish`,
    method: "POST",
    payload: {},
    timeoutMs,
  });
}

export function unpublishSurvey({ backendBaseUrl, ingestSecret, shopDomain, surveyId, timeoutMs = 10000 }) {
  return callBackend({
    backendBaseUrl,
    ingestSecret,
    path: `/api/shopify/surveys/${encodeURIComponent(shopDomain)}/${Number(surveyId)}/unpublish`,
    method: "POST",
    payload: {},
    timeoutMs,
  });
}

export function listSurveyResponses({
  backendBaseUrl,
  ingestSecret,
  shopDomain,
  surveyId,
  limit = 100,
  offset = 0,
  timeoutMs = 10000,
}) {
  return callBackend({
    backendBaseUrl,
    ingestSecret,
    path:
      `/api/shopify/surveys/${encodeURIComponent(shopDomain)}/${Number(surveyId)}` +
      `/responses?limit=${Number(limit)}&offset=${Number(offset)}`,
    method: "GET",
    timeoutMs,
  });
}

export function getActiveRuntimeSurvey({ backendBaseUrl, ingestSecret, shopDomain, timeoutMs = 10000 }) {
  return callBackend({
    backendBaseUrl,
    ingestSecret,
    path: `/api/shopify/survey-runtime/active?shop_domain=${encodeURIComponent(shopDomain)}`,
    method: "GET",
    timeoutMs,
  });
}

export function ingestNormalizedSurveyResponse({
  backendBaseUrl,
  ingestSecret,
  payload,
  timeoutMs = 10000,
}) {
  return callBackend({
    backendBaseUrl,
    ingestSecret,
    path: "/api/shopify/survey-responses",
    method: "POST",
    payload,
    timeoutMs,
  });
}
