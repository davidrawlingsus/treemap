/** @jsxImportSource preact */
import { render } from "preact";
import { useState } from "preact/hooks";
import { getSettings, forwardSurveySubmission } from "./shared.jsx";

export default function () {
  render(<ThankYouSurvey />, document.body);
}

function ThankYouSurvey() {
  const settings = getSettings();
  const [answers, setAnswers] = useState({});
  const [stepIndex, setStepIndex] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const questions = settings.questionConfigs
    .filter((item) => item.text)
    .map((item) => ({
      key: item.key,
      label: item.text,
      type: item.type,
      required: item.required,
      options:
        item.type === "choice_list"
          ? item.options.length
            ? item.options
            : ["Option 1", "Option 2"]
          : [],
    }));

  if (!questions.length) {
    return (
      <s-box border="base" padding="base" borderRadius="base">
        <s-stack gap="base">
          <s-heading>{settings.title}</s-heading>
          <s-text appearance="subdued">
            No questions configured yet. Add at least one q*_text value in block settings.
          </s-text>
        </s-stack>
      </s-box>
    );
  }
  const hasMultipleQuestions = questions.length > 1;
  const visibleQuestions = [questions[stepIndex]];
  const currentQuestion = questions[stepIndex];

  function updateAnswer(key, value) {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  }

  function isAnswered(question) {
    if (!question.required) return true;
    return Boolean(String(answers[question.key] || "").trim());
  }

  function canContinueCurrentStep() {
    if (!currentQuestion) return false;
    return isAnswered(currentQuestion);
  }

  function handleNext() {
    if (!canContinueCurrentStep()) {
      setErrorMessage("Please answer this question to continue.");
      return;
    }
    setErrorMessage("");
    setStepIndex((prev) => Math.min(prev + 1, questions.length - 1));
  }

  function handleBack() {
    setErrorMessage("");
    setStepIndex((prev) => Math.max(prev - 1, 0));
  }

  async function handleSubmit() {
    const missingRequired = questions.some((question) => !isAnswered(question));
    if (missingRequired) {
      setErrorMessage("Please complete all required questions before submitting.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");
    const payload = {
      idempotency_key: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
      shop_domain: shopify?.shop?.myshopifyDomain || "",
      shopify_order_id: shopify?.orderConfirmation?.order?.id || null,
      order_gid: shopify?.orderConfirmation?.order?.id || null,
      customer_reference: shopify?.customer?.email || null,
      survey_version: "v1",
      answers: questions.reduce((accumulator, question) => {
        accumulator[question.key] = {
          question: question.label,
          answer: answers[question.key] || "",
        };
        return accumulator;
      }, {}),
      extension_context: {
        extension_target: "purchase.thank-you.block.render",
      },
      submitted_at: new Date().toISOString(),
    };
    try {
      await forwardSurveySubmission(payload, settings.apiBaseUrl);
      setIsSubmitted(true);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to submit feedback.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isSubmitted) {
    return (
      <s-box border="base" padding="base" borderRadius="base">
        <s-stack gap="base">
          <s-text>{settings.successMessage}</s-text>
        </s-stack>
      </s-box>
    );
  }

  return (
    <s-box border="base" padding="base" borderRadius="base">
      <s-stack gap="base">
        <s-heading>{settings.title}</s-heading>
        {settings.description ? <s-text>{settings.description}</s-text> : null}

        {visibleQuestions.map((question) => {
          const value = answers[question.key] || "";

          if (question.type === "choice_list") {
            return (
              <s-stack key={question.key} gap="base">
                <s-text>{question.label}</s-text>
                <s-choice-list
                  name={question.key}
                  value={value}
                  onChange={(event) => updateAnswer(question.key, event.currentTarget.values?.[0] || "")}
                >
                  {question.options.map((option) => (
                    <s-choice key={option} value={option}>
                      {option}
                    </s-choice>
                  ))}
                </s-choice-list>
              </s-stack>
            );
          }

          return (
            question.type === "textarea" ? (
              <s-text-area
                key={question.key}
                label={question.label}
                value={value}
                rows={4}
                onInput={(event) => updateAnswer(question.key, event.currentTarget.value)}
              />
            ) : (
              <s-text-field
                key={question.key}
                label={question.label}
                value={value}
                onInput={(event) => updateAnswer(question.key, event.currentTarget.value)}
              />
            )
          );
        })}

        {errorMessage ? <s-text appearance="critical">{errorMessage}</s-text> : null}

        <s-stack direction="inline" gap="base">
          {hasMultipleQuestions && stepIndex > 0 ? (
            <s-button variant="secondary" onClick={handleBack} disabled={isSubmitting}>
              Back
            </s-button>
          ) : null}

          {hasMultipleQuestions && stepIndex < questions.length - 1 ? (
            <s-button variant="secondary" onClick={handleNext} disabled={isSubmitting}>
              Next
            </s-button>
          ) : (
            <s-button variant="secondary" onClick={handleSubmit} loading={isSubmitting}>
              {settings.submitLabel}
            </s-button>
          )}
        </s-stack>
      </s-stack>
    </s-box>
  );
}
