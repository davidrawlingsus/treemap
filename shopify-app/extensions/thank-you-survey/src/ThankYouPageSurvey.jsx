/** @jsxImportSource preact */
import { render } from "preact";
import { useState } from "preact/hooks";
import { SurveyCard, getSettings, forwardSurveySubmission } from "./shared.jsx";

export default function () {
  render(<ThankYouSurvey />, document.body);
}

function ThankYouSurvey() {
  const settings = getSettings();
  const [answerStep1, setAnswerStep1] = useState("");
  const [answerStep2, setAnswerStep2] = useState("");
  const [answerStep3, setAnswerStep3] = useState("");
  const hasStep3 = Boolean(settings.questionStep3);

  async function handleSubmit() {
    const payload = {
      idempotency_key: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
      shop_domain: shopify?.shop?.myshopifyDomain || "",
      shopify_order_id: shopify?.orderConfirmation?.order?.id || null,
      order_gid: shopify?.orderConfirmation?.order?.id || null,
      customer_reference: shopify?.customer?.email || null,
      survey_version: "v1",
      answers: {
        step_1: { question: settings.questionStep1, answer: answerStep1 },
        step_2: { question: settings.questionStep2, answer: answerStep2 },
        ...(hasStep3 ? { step_3: { question: settings.questionStep3, answer: answerStep3 } } : {}),
      },
      extension_context: {
        extension_target: "purchase.thank-you.block.render",
      },
      submitted_at: new Date().toISOString(),
    };
    await forwardSurveySubmission(payload, settings.apiBaseUrl);
  }

  return (
    <SurveyCard
      title={settings.title}
      description="Thanks for your order. Help us improve with a quick survey."
      submitLabel={settings.submitLabel}
      onSubmit={handleSubmit}
    >
      <s-text-field
        label={settings.questionStep1}
        value={answerStep1}
        onInput={(event) => setAnswerStep1(event.currentTarget.value)}
      />
      <s-text-field
        label={settings.questionStep2}
        value={answerStep2}
        onInput={(event) => setAnswerStep2(event.currentTarget.value)}
      />
      {hasStep3 ? (
        <s-text-field
          label={settings.questionStep3}
          value={answerStep3}
          onInput={(event) => setAnswerStep3(event.currentTarget.value)}
        />
      ) : null}
    </SurveyCard>
  );
}
