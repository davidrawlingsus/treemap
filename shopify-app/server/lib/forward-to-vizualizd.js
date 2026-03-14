export async function forwardSurveySubmission({
  backendBaseUrl,
  ingestSecret,
  timeoutMs = 10000,
  payload,
}) {
  if (!backendBaseUrl) {
    throw new Error("VIZUALIZD_BACKEND_URL is required");
  }
  if (!ingestSecret) {
    throw new Error("VIZUALIZD_SHOPIFY_INGEST_SECRET is required");
  }

  const controller = new AbortController();
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
  const endpoint = `${backendBaseUrl.replace(/\/$/, "")}/api/shopify/survey-responses/raw`;

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Vizualizd-Shopify-Secret": ingestSecret,
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    let responseJson = null;
    try {
      responseJson = await response.json();
    } catch (_error) {
      responseJson = null;
    }

    if (!response.ok) {
      const detail = responseJson?.detail || `Forwarding failed with status ${response.status}`;
      throw new Error(detail);
    }

    return responseJson || { status: "ok" };
  } finally {
    clearTimeout(timeoutHandle);
  }
}
