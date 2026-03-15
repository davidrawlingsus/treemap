import path from "node:path";
import { fileURLToPath } from "node:url";
import { readFile } from "node:fs/promises";

import { requireShopifySession } from "../middleware/require-shopify-session.js";
import {
  createSurvey,
  deleteSurvey,
  getSurvey,
  listSurveyResponses,
  listSurveys,
  listSurveyTemplates,
  publishSurvey,
  unpublishSurvey,
  updateSurvey,
} from "../services/fastapi/survey-service.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function resolveAdminFile(fileName) {
  return path.join(__dirname, "../web/admin", fileName);
}

function getErrorMessage(error) {
  return error instanceof Error ? error.message : "Request failed";
}

export function registerAdminRoutes(app, config) {
  app.get("/app", async (_req, res) => {
    try {
      const html = await readFile(resolveAdminFile("index.html"), "utf8");
      const shopifyApiKey = String(config.shopifyApiKey || "");
      res.set("Cache-Control", "no-store").type("text/html").send(html.replaceAll("%SHOPIFY_API_KEY%", shopifyApiKey));
    } catch (error) {
      res.status(500).send("Failed to load admin app.");
    }
  });

  app.get("/app/main.js", (_req, res) => {
    res.set("Cache-Control", "no-store");
    res.type("application/javascript");
    res.sendFile(resolveAdminFile("main.js"));
  });

  app.get("/app/styles.css", (_req, res) => {
    res.set("Cache-Control", "no-store");
    res.type("text/css");
    res.sendFile(resolveAdminFile("styles.css"));
  });

  app.get("/api/admin/survey-templates", async (req, res) => {
    try {
      await requireShopifySession(req, config.shopifyApiSecret);
      const templates = await listSurveyTemplates({
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
      });
      res.json({ templates });
    } catch (error) {
      res.status(400).json({ ok: false, detail: getErrorMessage(error) });
    }
  });

  app.get("/api/admin/surveys", async (req, res) => {
    try {
      const session = await requireShopifySession(req, config.shopifyApiSecret);
      const surveys = await listSurveys({
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        shopDomain: session.shopDomain,
      });
      res.json({ surveys });
    } catch (error) {
      res.status(400).json({ ok: false, detail: getErrorMessage(error) });
    }
  });

  app.post("/api/admin/surveys", async (req, res) => {
    try {
      const session = await requireShopifySession(req, config.shopifyApiSecret);
      const survey = await createSurvey({
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        shopDomain: session.shopDomain,
        payload: req.body || {},
      });
      res.status(201).json({ survey });
    } catch (error) {
      res.status(400).json({ ok: false, detail: getErrorMessage(error) });
    }
  });

  app.get("/api/admin/surveys/:surveyId", async (req, res) => {
    try {
      const session = await requireShopifySession(req, config.shopifyApiSecret);
      const survey = await getSurvey({
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        shopDomain: session.shopDomain,
        surveyId: req.params.surveyId,
      });
      res.json({ survey });
    } catch (error) {
      res.status(400).json({ ok: false, detail: getErrorMessage(error) });
    }
  });

  app.put("/api/admin/surveys/:surveyId", async (req, res) => {
    try {
      const session = await requireShopifySession(req, config.shopifyApiSecret);
      const survey = await updateSurvey({
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        shopDomain: session.shopDomain,
        surveyId: req.params.surveyId,
        payload: req.body || {},
      });
      res.json({ survey });
    } catch (error) {
      res.status(400).json({ ok: false, detail: getErrorMessage(error) });
    }
  });

  app.post("/api/admin/surveys/:surveyId/publish", async (req, res) => {
    try {
      const session = await requireShopifySession(req, config.shopifyApiSecret);
      const survey = await publishSurvey({
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        shopDomain: session.shopDomain,
        surveyId: req.params.surveyId,
      });
      res.json({ survey });
    } catch (error) {
      res.status(400).json({ ok: false, detail: getErrorMessage(error) });
    }
  });

  app.post("/api/admin/surveys/:surveyId/unpublish", async (req, res) => {
    try {
      const session = await requireShopifySession(req, config.shopifyApiSecret);
      const survey = await unpublishSurvey({
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        shopDomain: session.shopDomain,
        surveyId: req.params.surveyId,
      });
      res.json({ survey });
    } catch (error) {
      res.status(400).json({ ok: false, detail: getErrorMessage(error) });
    }
  });

  app.delete("/api/admin/surveys/:surveyId", async (req, res) => {
    try {
      const session = await requireShopifySession(req, config.shopifyApiSecret);
      await deleteSurvey({
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        shopDomain: session.shopDomain,
        surveyId: req.params.surveyId,
      });
      res.status(204).send();
    } catch (error) {
      res.status(400).json({ ok: false, detail: getErrorMessage(error) });
    }
  });

  app.get("/api/admin/surveys/:surveyId/responses", async (req, res) => {
    try {
      const session = await requireShopifySession(req, config.shopifyApiSecret);
      const responses = await listSurveyResponses({
        backendBaseUrl: config.backendBaseUrl,
        ingestSecret: config.ingestSecret,
        shopDomain: session.shopDomain,
        surveyId: req.params.surveyId,
        limit: req.query.limit || 100,
        offset: req.query.offset || 0,
      });
      res.json(responses);
    } catch (error) {
      res.status(400).json({ ok: false, detail: getErrorMessage(error) });
    }
  });
}
