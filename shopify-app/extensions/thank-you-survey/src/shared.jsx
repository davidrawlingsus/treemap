/** @jsxImportSource preact */
import { useState } from "preact/hooks";

export function SurveyCard({ title, description, submitLabel, onSubmit, children }) {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit() {
    setLoading(true);
    setErrorMessage("");
    try {
      await onSubmit();
      setSubmitted(true);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Submission failed. Please try again.";
      setErrorMessage(detail);
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <s-box border="base" padding="base" borderRadius="base">
        <s-stack gap="base">
          <s-heading>Thanks for your feedback!</s-heading>
          <s-text>Your response has been submitted.</s-text>
        </s-stack>
      </s-box>
    );
  }

  return (
    <s-box border="base" padding="base" borderRadius="base">
      <s-stack gap="base">
        <s-heading>{title}</s-heading>
        <s-text>{description}</s-text>
        {children}
        {errorMessage ? <s-text appearance="critical">{errorMessage}</s-text> : null}
        <s-button variant="secondary" onClick={handleSubmit} loading={loading}>
          {submitLabel}
        </s-button>
      </s-stack>
    </s-box>
  );
}

export function getSettings() {
  const settings = shopify?.settings?.current || shopify?.settings || {};
  return {
    title: String(settings.survey_title || "Post-purchase survey"),
    questionStep1: String(settings.question_step_1 || "How did you hear about us?"),
    questionStep2: String(settings.question_step_2 || "What nearly stopped you from purchasing?"),
    questionStep3: String(settings.question_step_3 || "").trim(),
    submitLabel: String(settings.submit_label || "Submit feedback"),
    apiBaseUrl: String(settings.api_base_url || "").replace(/\/$/, ""),
    successMessage: String(settings.success_message || "Thanks for your feedback!"),
  };
}

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
