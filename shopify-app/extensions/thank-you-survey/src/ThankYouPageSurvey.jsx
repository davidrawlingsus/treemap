/** @jsxImportSource preact */
import { render } from "preact";
import { useEffect, useMemo, useState } from "preact/hooks";
import { fetchActiveSurvey, getSettings, forwardSurveySubmission } from "./shared.jsx";

export default function () {
  render(<ThankYouSurvey />, document.body);
}

function ThankYouSurvey() {
  const settings = getSettings();
  const [runtimeSurvey, setRuntimeSurvey] = useState(null);
  const [runtimeError, setRuntimeError] = useState("");
  const [runtimeLoading, setRuntimeLoading] = useState(true);
  const [answers, setAnswers] = useState({});
  const [stepIndex, setStepIndex] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  useEffect(() => {
    let cancelled = false;
    async function loadRuntimeSurvey() {
      setRuntimeLoading(true);
      try {
        const survey = await fetchActiveSurvey(settings.apiBaseUrl, shopify?.shop?.myshopifyDomain || "");
        if (!cancelled) {
          setRuntimeSurvey(survey);
          setRuntimeError("");
        }
      } catch (error) {
        if (!cancelled) {
          setRuntimeSurvey(null);
          setRuntimeError(error instanceof Error ? error.message : "Failed to load active survey.");
        }
      } finally {
        if (!cancelled) setRuntimeLoading(false);
      }
    }
    loadRuntimeSurvey();
    return () => {
      cancelled = true;
    };
  }, [settings.apiBaseUrl]);

  const rulesByTarget = useMemo(() => {
    const byTarget = {};
    for (const rule of runtimeSurvey?.display_rules || []) {
      if (!rule?.target_question_key) continue;
      byTarget[rule.target_question_key] = byTarget[rule.target_question_key] || [];
      byTarget[rule.target_question_key].push(rule);
    }
    return byTarget;
  }, [runtimeSurvey]);

  function isQuestionVisible(question) {
    const rules = rulesByTarget[question.key] || [];
    if (!rules.length) return true;
    return rules.every((rule) => String(answers[rule.source_question_key] || "").trim() === String(rule.comparison_value || "").trim());
  }

  const runtimeQuestions = (runtimeSurvey?.questions || []).map((item) => ({
    id: item.id,
    key: item.question_key,
    label: item.title,
    type: item.answer_type === "choice_list" ? "choice_list" : item.answer_type === "multi_line_text" ? "textarea" : "text",
    required: Boolean(item.is_required),
    options: Array.isArray(item.options) ? item.options : [],
  }));
  const questions = runtimeQuestions.filter((question) => isQuestionVisible(question));

  if (!questions.length) {
    return (
      <s-box border="base" padding="base" borderRadius="base">
        <s-stack gap="base">
          <s-heading>{settings.title}</s-heading>
          <s-text appearance="subdued">
            No active published survey is available for this store yet.
          </s-text>
          {runtimeError ? <s-text appearance="critical">{runtimeError}</s-text> : null}
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
      survey_id: runtimeSurvey?.survey_id || null,
      survey_version_id: runtimeSurvey?.survey_version_id || null,
      shopify_order_id: shopify?.orderConfirmation?.order?.id || null,
      order_gid: shopify?.orderConfirmation?.order?.id || null,
      customer_reference: null,
      survey_version: String(runtimeSurvey?.survey_version_number || "v1"),
      answers: questions.reduce((accumulator, question) => {
        accumulator[question.key] = {
          question_id: question.id,
          question: question.label,
          answer: answers[question.key] || "",
        };
        return accumulator;
      }, {}),
      extension_context: {
        extension_target: "purchase.thank-you.block.render",
        runtime_loaded: Boolean(runtimeSurvey),
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
        {runtimeLoading ? <s-text appearance="subdued">Loading latest survey...</s-text> : null}
        {runtimeError ? <s-text appearance="critical">{runtimeError}</s-text> : null}
        {settings.description ? <s-text>{settings.description}</s-text> : null}

        {visibleQuestions.map((question) => {
          const value = answers[question.key] || "";

          if (question.type === "choice_list") {
            return (
              <s-stack key={question.key} gap="base">
                <s-text><strong>{question.label}</strong></s-text>
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
            <s-stack key={question.key} gap="base">
              <s-text><strong>{question.label}</strong></s-text>
              {question.type === "textarea" ? (
                <s-text-area
                  value={value}
                  rows={4}
                  onInput={(event) => updateAnswer(question.key, event.currentTarget.value)}
                />
              ) : (
                <s-text-field
                  value={value}
                  onInput={(event) => updateAnswer(question.key, event.currentTarget.value)}
                />
              )}
            </s-stack>
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
              {runtimeSurvey?.settings?.submit_label || settings.submitLabel}
            </s-button>
          )}
        </s-stack>
      </s-stack>
    </s-box>
  );
}
