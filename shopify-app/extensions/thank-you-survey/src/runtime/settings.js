const DEFAULT_API_BASE_URL = "https://connect.mapthegap.ai";

export function getSettings() {
  const settings = shopify?.settings?.current || shopify?.settings || {};
  const configuredBaseUrl = String(settings.api_base_url || "").trim().replace(/\/$/, "");

  return {
    title: "Post-purchase survey",
    description: "",
    questionConfigs: [],
    submitLabel: "Submit feedback",
    apiBaseUrl: configuredBaseUrl || DEFAULT_API_BASE_URL,
    successMessage: "Thanks for your feedback!",
  };
}
