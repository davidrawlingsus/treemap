/** @jsxImportSource preact */
import { render } from "preact";
import { useState } from "preact/hooks";
import { SurveyCard, getSettings, forwardSurveySubmission } from "./shared.jsx";

export default function () {
  render(<OrderStatusSurvey />, document.body);
}

function OrderStatusSurvey() {
  const settings = getSettings();
  const [rating, setRating] = useState("");

  async function handleSubmit() {
    const payload = {
      idempotency_key: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
      shop_domain: shopify?.shop?.myshopifyDomain || "",
      shopify_order_id: shopify?.order?.id || null,
      order_gid: shopify?.order?.id || null,
      customer_reference: null,
      survey_version: "v1-order-status",
      answers: {
        step_1: {
          question: "How are you feeling about your purchase so far?",
          answer: rating,
        },
      },
      extension_context: {
        extension_target: "customer-account.order-status.block.render",
      },
      submitted_at: new Date().toISOString(),
    };
    await forwardSurveySubmission(payload, settings.apiBaseUrl);
  }

  return (
    <SurveyCard
      title="Post-purchase check-in"
      description="How are you feeling about your purchase so far?"
      submitLabel={settings.submitLabel}
      onSubmit={handleSubmit}
    >
      <s-choice-list
        name="order-status-survey"
        value={rating}
        onChange={(event) => setRating(event.currentTarget.values?.[0] || "")}
      >
        <s-choice value="great">Great</s-choice>
        <s-choice value="good">Good</s-choice>
        <s-choice value="neutral">Neutral</s-choice>
        <s-choice value="bad">Not great</s-choice>
      </s-choice-list>
    </SurveyCard>
  );
}
