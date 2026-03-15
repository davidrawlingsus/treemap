export async function forwardSurveySubmission(payload, apiBaseUrl) {
  if (!apiBaseUrl) {
    throw new Error("Missing api_base_url setting in extension block.");
  }

  const endpoint = `${apiBaseUrl}/api/checkout-survey/submit`;
  const token = await shopify.sessionToken.get();
  let response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (_error) {
    throw new Error(`Network error posting to ${endpoint}`);
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) {
        detail = body.detail;
      }
    } catch (_error) {
      // Keep fallback detail if body parsing fails.
    }
    throw new Error(`${detail} (${endpoint})`);
  }
}

export async function fetchActiveSurvey(apiBaseUrl, shopDomain) {
  if (!apiBaseUrl) {
    throw new Error("Missing api_base_url setting in extension block.");
  }
  const endpoint = `${apiBaseUrl}/api/checkout-survey/active?shop_domain=${encodeURIComponent(shopDomain || "")}`;
  const token = await shopify.sessionToken.get();
  let response;
  try {
    response = await fetch(endpoint, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
  } catch (_error) {
    throw new Error(`Network error loading ${endpoint}`);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || `Failed to fetch active survey (${response.status})`);
  }
  const body = await response.json().catch(() => ({}));
  return body?.survey || null;
}
