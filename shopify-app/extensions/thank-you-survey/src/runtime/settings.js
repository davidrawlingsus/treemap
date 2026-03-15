function parseType(value) {
  const normalized = String(value || "text").trim().toLowerCase();
  if (normalized === "choice_list" || normalized === "text" || normalized === "textarea") {
    return normalized;
  }
  return "text";
}

function parseRequired(value) {
  return value === true || value === "true" || value === "1" || value === 1;
}

function parseOptions(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
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
