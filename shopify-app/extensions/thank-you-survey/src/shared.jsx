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
  const hasSurveyDescriptionSetting = Object.prototype.hasOwnProperty.call(
    settings,
    "survey_description",
  );
  const rawDescription = hasSurveyDescriptionSetting
    ? settings.survey_description
    : "Thanks for your order. Help us improve with a quick survey.";
  const parseType = (value) => {
    const normalized = String(value || "text").trim().toLowerCase();
    if (normalized === "choice_list" || normalized === "text" || normalized === "textarea") {
      return normalized;
    }
    return "text";
  };
  const parseRequired = (value) =>
    value === true || value === "true" || value === "1" || value === 1;
  const parseOptions = (value) =>
    String(value || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

  const questionConfigs = [1, 2, 3].map((index) => {
    const text = String(settings[`q${index}_text`] || "").trim();
    const type = parseType(settings[`q${index}_type`]);
    const required = parseRequired(settings[`q${index}_required`]);
    const options = parseOptions(settings[`q${index}_options`]);
    return {
      key: `q${index}`,
      text,
      type,
      required,
      options,
    };
  });
  const hasAnyNewQuestion = questionConfigs.some((question) => question.text);
  const legacyStep1 = String(settings.question_step_1 || "").trim();
  const legacyStep2 = String(settings.question_step_2 || "").trim();
  const legacyStep3 = String(settings.question_step_3 || "").trim();
  const legacyQuestionConfigs = [
    {
      key: "q1",
      text: legacyStep1 || "How did you hear about us?",
      type: "choice_list",
      required: true,
      options: ["Facebook / Instagram", "Google search", "Friend or family", "Other"],
    },
    {
      key: "q2",
      text: legacyStep2 || "What nearly stopped you from purchasing?",
      type: "text",
      required: true,
      options: [],
    },
    ...(legacyStep3
      ? [
          {
            key: "q3",
            text: legacyStep3,
            type: "textarea",
            required: false,
            options: [],
          },
        ]
      : []),
  ];

  return {
    title: String(settings.survey_title || "Post-purchase survey"),
    description: String(rawDescription ?? "").trim(),
    questionConfigs: hasAnyNewQuestion ? questionConfigs : legacyQuestionConfigs,
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
