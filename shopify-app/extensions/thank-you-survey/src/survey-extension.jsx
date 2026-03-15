import {
  Banner,
  BlockStack,
  Button,
  Text,
  TextField,
  useApi,
  useSettings,
} from "@shopify/ui-extensions-react/checkout";
import { useMemo, useState } from "react";

function buildSurveyQuestions(settings) {
  const questionStep1 = String(settings.question_step_1 || "What made you choose us today?");
  const questionStep2 = String(settings.question_step_2 || "What nearly stopped you from purchasing?");
  const questionStep3 = String(settings.question_step_3 || "").trim();

  const questions = [
    { key: "step_1", label: questionStep1, required: true },
    { key: "step_2", label: questionStep2, required: true },
  ];

  if (questionStep3) {
    questions.push({ key: "step_3", label: questionStep3, required: false });
  }
  return questions;
}

function createIdempotencyKey() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function SurveyExtension() {
  const api = useApi();
  const settings = useSettings();
  const questions = useMemo(() => buildSurveyQuestions(settings), [settings]);

  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [idempotencyKey] = useState(() => createIdempotencyKey());

  const title = String(settings.survey_title || "Quick checkout survey");
  const submitLabel = String(settings.submit_label || "Submit feedback");
  const successMessage = String(settings.success_message || "Thanks for your feedback!");
  const appApiBaseUrl = String(settings.api_base_url || "").replace(/\/$/, "");
  const currentQuestion = questions[stepIndex];
  const isLastStep = stepIndex === questions.length - 1;
  const canGoBack = stepIndex > 0;

  const currentAnswer = answers[currentQuestion?.key] || "";

  const isCurrentStepValid = !currentQuestion?.required || Boolean(String(currentAnswer).trim());

  function updateCurrentAnswer(value) {
    setAnswers((prev) => ({
      ...prev,
      [currentQuestion.key]: value,
    }));
    if (submitError) {
      setSubmitError("");
    }
  }

  function handleNext() {
    if (!isCurrentStepValid) {
      setSubmitError("Please answer this question to continue.");
      return;
    }
    setSubmitError("");
    setStepIndex((prev) => Math.min(prev + 1, questions.length - 1));
  }

  function handleBack() {
    setSubmitError("");
    setStepIndex((prev) => Math.max(prev - 1, 0));
  }

  async function handleSubmit() {
    if (!appApiBaseUrl) {
      setSubmitError("Survey API URL is not configured for this block.");
      return;
    }

    for (const question of questions) {
      if (question.required && !String(answers[question.key] || "").trim()) {
        setSubmitError("Please complete all required survey steps.");
        return;
      }
    }

    try {
      setIsSubmitting(true);
      setSubmitError("");
      const token = await api.sessionToken.get();

      const payload = {
        idempotency_key: idempotencyKey,
        shop_domain: api.shop?.myshopifyDomain || "",
        shopify_order_id: api.orderConfirmation?.order?.id || null,
        order_gid: api.orderConfirmation?.order?.id || null,
        customer_reference: api.customer?.email || null,
        survey_version: "v1",
        answers: questions.reduce((acc, question) => {
          acc[question.key] = {
            question: question.label,
            answer: String(answers[question.key] || ""),
          };
          return acc;
        }, {}),
        extension_context: {
          extension_target: "purchase.thank-you.block.render",
          locale: api.localization?.language?.isoCode || null,
          market_region: api.localization?.market?.regionCode || null,
        },
        submitted_at: new Date().toISOString(),
      };

      const response = await fetch(`${appApiBaseUrl}/api/checkout-survey/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
          const body = await response.json();
          if (body?.detail) detail = body.detail;
        } catch (_error) {
          // keep fallback detail
        }
        throw new Error(detail);
      }

      setIsSubmitted(true);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Failed to submit survey.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isSubmitted) {
    return (
      <BlockStack spacing="tight">
        <Text emphasis="bold">{title}</Text>
        <Banner status="success">{successMessage}</Banner>
      </BlockStack>
    );
  }

  return (
    <BlockStack spacing="base">
      <Text emphasis="bold">{title}</Text>
      <Text size="small" appearance="subdued">
        Step {stepIndex + 1} of {questions.length}
      </Text>
      <TextField
        label={currentQuestion.label}
        multiline={4}
        value={String(currentAnswer)}
        onChange={updateCurrentAnswer}
      />

      {submitError ? <Banner status="critical">{submitError}</Banner> : null}

      <BlockStack spacing="tight">
        {canGoBack ? (
          <Button kind="secondary" onPress={handleBack} disabled={isSubmitting}>
            Back
          </Button>
        ) : null}

        {!isLastStep ? (
          <Button onPress={handleNext} disabled={isSubmitting}>
            Next
          </Button>
        ) : (
          <Button onPress={handleSubmit} loading={isSubmitting}>
            {submitLabel}
          </Button>
        )}
      </BlockStack>
    </BlockStack>
  );
}
