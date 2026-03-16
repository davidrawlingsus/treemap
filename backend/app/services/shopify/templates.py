from app.schemas.shopify import ShopifySurveyTemplateItem, ShopifySurveyTemplateQuestion


SURVEY_TEMPLATES: list[ShopifySurveyTemplateItem] = [
    ShopifySurveyTemplateItem(
        key="why_buy_today",
        name="Why did you buy today?",
        description="Understand the primary conversion trigger for this purchase.",
        questions=[
            ShopifySurveyTemplateQuestion(
                question_key="q1",
                title="What made you decide to buy today?",
                answer_type="choice_list",
                is_required=True,
                options=["Price/promotion", "Need became urgent", "Product trust/reviews", "Recommendation", "Other"],
            ),
            ShopifySurveyTemplateQuestion(
                question_key="q2",
                title="What specific benefit convinced you most?",
                answer_type="single_line_text",
                is_required=False,
            ),
        ],
    ),
    ShopifySurveyTemplateItem(
        key="how_did_you_hear",
        name="How did you hear about us?",
        description="Track top acquisition sources directly from new customers.",
        questions=[
            ShopifySurveyTemplateQuestion(
                question_key="q1",
                title="How did you first hear about us?",
                answer_type="choice_list",
                is_required=True,
                options=["Instagram/Facebook", "Google search", "YouTube/TikTok", "Friend/family", "Other"],
            ),
            ShopifySurveyTemplateQuestion(
                question_key="q2",
                title="Anything about that source that stood out?",
                answer_type="multi_line_text",
                is_required=False,
            ),
        ],
    ),
    ShopifySurveyTemplateItem(
        key="what_almost_stopped",
        name="What almost stopped you buying?",
        description="Identify friction before purchase for conversion optimization.",
        settings={
            "widget_title": "Quick question before you go...",
        },
        questions=[
            ShopifySurveyTemplateQuestion(
                question_key="q1",
                title="If anything nearly stopped you ordering today, what was it? Thanks!",
                answer_type="multi_line_text",
                is_required=False,
            ),
        ],
    ),
]


def get_survey_templates() -> list[ShopifySurveyTemplateItem]:
    return SURVEY_TEMPLATES
