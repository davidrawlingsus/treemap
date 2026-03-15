/** @jsxImportSource preact */
import { render } from "preact";
import { useEffect, useState } from "preact/hooks";
import { SurveyCard, fetchActiveSurvey, getSettings, forwardSurveySubmission } from "./shared.jsx";

export default function () {
  render(<OrderStatusSurvey />, document.body);
}

function OrderStatusSurvey() {
  const settings = getSettings();
  const [runtimeSurvey, setRuntimeSurvey] = useState(null);
  const [answer, setAnswer] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function loadRuntime() {
      try {
        const survey = await fetchActiveSurvey(settings.apiBaseUrl, shopify?.shop?.myshopifyDomain || "");
        if (!cancelled) {
          setRuntimeSurvey(survey);
          setErrorMessage("");
        }
      } catch (error) {
        if (!cancelled) {
          setRuntimeSurvey(null);
          setErrorMessage(error instanceof Error ? error.message : "Failed to load active survey.");
        }
      }
    }
    loadRuntime();
    return () => {
      cancelled = true;
    };
  }, [settings.apiBaseUrl]);

  const firstQuestion = runtimeSurvey?.questions?.[0] || null;
  const optionList = Array.isArray(firstQuestion?.options) ? firstQuestion.options : ["Great", "Good", "Neutral", "Not great"];
  const questionLabel = firstQuestion?.title || "How are you feeling about your purchase so far?";

  async function handleSubmit() {
    const payload = {
      idempotency_key: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
      shop_domain: shopify?.shop?.myshopifyDomain || "",
      survey_id: runtimeSurvey?.survey_id || null,
      survey_version_id: runtimeSurvey?.survey_version_id || null,
      shopify_order_id: shopify?.order?.id || null,
      order_gid: shopify?.order?.id || null,
      customer_reference: null,
      survey_version: String(runtimeSurvey?.survey_version_number || "v1-order-status"),
      answers: {
        [firstQuestion?.question_key || "step_1"]: {
          question_id: firstQuestion?.id || null,
          question: questionLabel,
          answer,
        },
      },
      extension_context: {
        extension_target: "customer-account.order-status.block.render",
        runtime_loaded: Boolean(runtimeSurvey),
      },
      submitted_at: new Date().toISOString(),
    };
    await forwardSurveySubmission(payload, settings.apiBaseUrl);
  }

  return (
    <SurveyCard
      title="Post-purchase check-in"
      description={questionLabel}
      submitLabel={settings.submitLabel}
      onSubmit={handleSubmit}
    >
      {errorMessage ? <s-text appearance="critical">{errorMessage}</s-text> : null}
      <s-choice-list
        name="order-status-survey"
        value={answer}
        onChange={(event) => setAnswer(event.currentTarget.values?.[0] || "")}
      >
        {optionList.map((option) => (
          <s-choice key={option} value={option}>
            {option}
          </s-choice>
        ))}
      </s-choice-list>
    </SurveyCard>
  );
}
