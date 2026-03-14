const SHOPIFY_AUTH_BASE_URL = "https://connect.mapthegap.ai";
const SHOPIFY_DOMAIN_SUFFIX = ".myshopify.com";
const SHOP_SLUG_PATTERN = /^[a-z0-9][a-z0-9-]*$/;

function getElements() {
  return {
    form: document.getElementById("connectShopifyForm"),
    shopDomainInput: document.getElementById("shopDomain"),
    statusMessage: document.getElementById("statusMessage"),
    installAppButton: document.getElementById("installAppButton"),
  };
}

function readShopFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const rawShop = String(params.get("shop") || "").trim().toLowerCase();
  if (!rawShop) return "";
  if (rawShop.endsWith(SHOPIFY_DOMAIN_SUFFIX)) {
    return rawShop.slice(0, -SHOPIFY_DOMAIN_SUFFIX.length);
  }
  return rawShop;
}

function normalizeShopSlug(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(SHOPIFY_DOMAIN_SUFFIX, "")
    .replace(/[^a-z0-9-]/g, "");
}

function buildMyShopifyDomain(shopSlug) {
  const normalized = normalizeShopSlug(shopSlug);
  if (!normalized || !SHOP_SLUG_PATTERN.test(normalized)) {
    return "";
  }
  return `${normalized}${SHOPIFY_DOMAIN_SUFFIX}`;
}

function setStatus(elements, message, isError = false) {
  elements.statusMessage.textContent = message;
  elements.statusMessage.classList.toggle("error", isError);
}

function redirectToOAuth(shopDomain) {
  const authUrl = new URL("/auth", SHOPIFY_AUTH_BASE_URL);
  authUrl.searchParams.set("shop", shopDomain);
  window.location.href = authUrl.toString();
}

function init() {
  const elements = getElements();
  if (!elements.form || !elements.shopDomainInput || !elements.statusMessage || !elements.installAppButton) {
    return;
  }

  const queryShop = readShopFromUrl();
  if (queryShop) {
    elements.shopDomainInput.value = normalizeShopSlug(queryShop);
  }

  elements.form.addEventListener("submit", (event) => {
    event.preventDefault();
    const shopDomain = buildMyShopifyDomain(elements.shopDomainInput.value);
    if (!shopDomain) {
      setStatus(elements, "Enter a valid Shopify store domain.", true);
      return;
    }

    setStatus(elements, "Redirecting to Shopify to install app...");
    elements.installAppButton.disabled = true;
    redirectToOAuth(shopDomain);
  });
}

init();
