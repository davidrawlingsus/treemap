/** @jsxImportSource preact */
import { useState } from "preact/hooks";
import { getSettings } from "./runtime/settings.js";
import { fetchActiveSurvey, forwardSurveySubmission } from "./runtime/submission.js";

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

export { getSettings, forwardSurveySubmission, fetchActiveSurvey };
