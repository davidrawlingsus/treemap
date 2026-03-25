/**
 * Vizualizd Popup Survey Widget
 * Embeddable vanilla JS widget for collecting survey responses on any website.
 *
 * Usage:
 *   <script>
 *     window.VizualizdSurvey = {
 *       apiKey: "vzd_...",
 *       apiBaseUrl: "https://app.vizualizd.com"
 *     };
 *   </script>
 *   <script src="https://app.vizualizd.com/static/widget/vizualizd-survey.js" defer></script>
 */
(function () {
  "use strict";

  // ── Config ──────────────────────────────────────────────────────

  var cfg = window.VizualizdSurvey || {};
  if (!cfg.apiKey) {
    console.warn("[Vizualizd] Missing apiKey in window.VizualizdSurvey");
    return;
  }
  var API_BASE = (cfg.apiBaseUrl || "").replace(/\/+$/, "");
  if (!API_BASE) {
    console.warn("[Vizualizd] Missing apiBaseUrl in window.VizualizdSurvey");
    return;
  }
  var API_KEY = cfg.apiKey;
  var PREFIX = "vzd-survey";
  var ICON_CLOSE = "https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/survey-icons/close_icon-bX0w8aJ2pJgf5aUuXZoEpQHw6dwtFB.svg";
  var ICON_COLLAPSE = "https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/survey-icons/collapse_icon-RYPksPuuo9v7xJYQPMkpaxgaByqYas.svg";

  // ── API client ──────────────────────────────────────────────────

  function apiHeaders() {
    return { "X-API-Key": API_KEY, "Content-Type": "application/json" };
  }

  function fetchActiveSurvey(cb) {
    fetch(API_BASE + "/api/widget-surveys/active", { headers: apiHeaders() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) { cb(data && data.survey ? data.survey : null); })
      .catch(function () { cb(null); });
  }

  function submitResponse(payload, cb) {
    fetch(API_BASE + "/api/widget-surveys/responses", {
      method: "POST",
      headers: apiHeaders(),
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json(); })
      .then(cb)
      .catch(function () { cb(null); });
  }

  function sendHeartbeat() {
    var body = JSON.stringify({ page_url: location.href });
    if (navigator.sendBeacon) {
      var blob = new Blob([body], { type: "application/json" });
      // sendBeacon doesn't support custom headers, use fetch with keepalive
      fetch(API_BASE + "/api/widget-surveys/heartbeat", {
        method: "POST",
        headers: apiHeaders(),
        body: body,
        keepalive: true,
      }).catch(function () {});
    } else {
      fetch(API_BASE + "/api/widget-surveys/heartbeat", {
        method: "POST",
        headers: apiHeaders(),
        body: body,
      }).catch(function () {});
    }
  }

  function sendImpression(surveyId, versionId) {
    fetch(API_BASE + "/api/widget-surveys/impression", {
      method: "POST",
      headers: apiHeaders(),
      body: JSON.stringify({
        survey_id: surveyId,
        survey_version_id: versionId,
        page_url: location.href,
      }),
      keepalive: true,
    }).catch(function () {});
  }

  // ── Clarity integration ─────────────────────────────────────────

  function getClaritySessionId() {
    try {
      var match = document.cookie.match(/(?:^|;\s*)_clsk=([^;]*)/);
      if (!match) return null;
      var parts = decodeURIComponent(match[1]).split("|");
      return parts[0] || null;
    } catch (e) {
      return null;
    }
  }

  function detectClarityProjectId() {
    var scripts = document.querySelectorAll("script[src]");
    for (var i = 0; i < scripts.length; i++) {
      var src = scripts[i].src || "";
      if (src.indexOf("clarity.ms") !== -1) {
        var m = src.match(/clarity\.ms\/tag\/([a-z0-9]+)/i);
        if (m) return m[1];
      }
    }
    return null;
  }

  function waitForClarity(serverProjectId, cb, timeout) {
    // If server already has it configured, use that
    if (serverProjectId) {
      cb(serverProjectId, "configured");
      return;
    }
    // Try immediate detection
    var id = detectClarityProjectId();
    if (id) {
      cb(id, "detected");
      return;
    }
    // Wait for GTM to inject Clarity (MutationObserver)
    var resolved = false;
    var observer = new MutationObserver(function () {
      if (resolved) return;
      var id = detectClarityProjectId();
      if (id) {
        resolved = true;
        observer.disconnect();
        cb(id, "detected");
      }
    });
    observer.observe(document.head, { childList: true, subtree: true });
    setTimeout(function () {
      if (!resolved) {
        resolved = true;
        observer.disconnect();
        cb(null, null);
      }
    }, timeout || 5000);
  }

  // ── URL targeting ───────────────────────────────────────────────

  function matchesUrlTargeting(urlTargeting) {
    if (!urlTargeting || !urlTargeting.patterns || urlTargeting.patterns.length === 0) {
      return true; // No patterns = show on all pages
    }
    var url = location.href;
    var mode = urlTargeting.mode || "contains";
    for (var i = 0; i < urlTargeting.patterns.length; i++) {
      var pattern = urlTargeting.patterns[i];
      if (mode === "regex") {
        try {
          if (new RegExp(pattern).test(url)) return true;
        } catch (e) {
          // Invalid regex, skip
        }
      } else {
        if (url.indexOf(pattern) !== -1) return true;
      }
    }
    return false;
  }

  // ── Frequency / suppression ─────────────────────────────────────

  var STORAGE_PREFIX = "vzd_survey_";

  function shouldShow(frequency) {
    var mode = (frequency && frequency.mode) || "until_answered";
    if (mode === "once") {
      return !localStorage.getItem(STORAGE_PREFIX + "shown");
    }
    if (mode === "until_answered") {
      return !localStorage.getItem(STORAGE_PREFIX + "answered");
    }
    if (mode === "every_n_days") {
      var last = localStorage.getItem(STORAGE_PREFIX + "last_shown");
      if (!last) return true;
      var days = (frequency && frequency.days) || 7;
      var elapsed = (Date.now() - parseInt(last, 10)) / 86400000;
      return elapsed >= days;
    }
    return true;
  }

  function markShown(frequency) {
    var mode = (frequency && frequency.mode) || "until_answered";
    if (mode === "once") {
      localStorage.setItem(STORAGE_PREFIX + "shown", "1");
    }
    if (mode === "every_n_days") {
      localStorage.setItem(STORAGE_PREFIX + "last_shown", String(Date.now()));
    }
  }

  function markAnswered() {
    localStorage.setItem(STORAGE_PREFIX + "answered", "1");
  }

  // ── Styles ──────────────────────────────────────────────────────

  function injectStyles() {
    if (document.getElementById(PREFIX + "-styles")) return;
    var style = document.createElement("style");
    style.id = PREFIX + "-styles";
    style.textContent = [
      "." + PREFIX + "-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:999999;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .2s ease}",
      "." + PREFIX + "-overlay.visible{opacity:1}",
      "." + PREFIX + "-overlay.slideup{background:none;pointer-events:none;align-items:flex-end;justify-content:flex-end;padding:0 24px 24px}",
      "." + PREFIX + "-overlay.slideup.pos-bottom-left{justify-content:flex-start}",
      "." + PREFIX + "-overlay.slideup .vzd-survey-modal{pointer-events:all;transform:translateY(20px);transition:transform .25s ease,opacity .25s ease}",
      "." + PREFIX + "-overlay.slideup.visible .vzd-survey-modal{transform:translateY(0)}",
      "." + PREFIX + "-modal{background:#fff;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,0.3);max-width:480px;width:90%;max-height:90vh;overflow-y:auto;padding:32px;position:relative;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1a1a1a;line-height:1.5}",
      "." + PREFIX + "-overlay.slideup ." + PREFIX + "-modal{max-width:380px;width:380px;padding:24px;box-shadow:0 4px 24px rgba(0,0,0,0.15);border-radius:12px}",
      "." + PREFIX + "-close{position:absolute;top:16px;right:16px;background:none;border:none;cursor:pointer;padding:4px;border-radius:4px;line-height:0}",
      "." + PREFIX + "-close:hover{color:#333;background:#f0f0f0}",
      "." + PREFIX + "-title{margin:0 0 8px;font-size:20px;font-weight:600}",
      "." + PREFIX + "-overlay.slideup ." + PREFIX + "-title{font-size:16px;margin:0 0 4px}",
      "." + PREFIX + "-desc{margin:0 0 24px;color:#666;font-size:14px}",
      "." + PREFIX + "-q-title{font-size:16px;font-weight:500;margin:0 0 12px}",
      "." + PREFIX + "-overlay.slideup ." + PREFIX + "-q-title{font-size:14px;margin:0 0 8px}",
      "." + PREFIX + "-q-title .required{color:#e53e3e;margin-left:2px}",
      "." + PREFIX + "-option{display:flex;align-items:center;padding:10px 14px;margin:0 0 8px;border:1px solid #e2e8f0;border-radius:8px;cursor:pointer;transition:border-color .15s,background .15s;font-size:14px}",
      "." + PREFIX + "-option:hover{border-color:#a0aec0;background:#f7fafc}",
      "." + PREFIX + "-option.selected{border-color:#4F46E5;background:#EEF2FF}",
      "." + PREFIX + "-option input{margin-right:10px;accent-color:#4F46E5}",
      "." + PREFIX + "-input," + "." + PREFIX + "-textarea{width:100%;padding:10px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;font-family:inherit;box-sizing:border-box;transition:border-color .15s}",
      "." + PREFIX + "-input:focus," + "." + PREFIX + "-textarea:focus{outline:none;border-color:#4F46E5;box-shadow:0 0 0 3px rgba(79,70,229,0.1)}",
      "." + PREFIX + "-textarea{min-height:80px;resize:vertical}",
      "." + PREFIX + "-actions{display:flex;justify-content:space-between;margin-top:24px;gap:12px}",
      "." + PREFIX + "-btn{padding:10px 20px;border-radius:8px;font-size:14px;font-weight:500;cursor:pointer;border:none;transition:background .15s}",
      "." + PREFIX + "-btn-primary{background:var(--vzd-btn-color,#4F46E5);color:#fff}",
      "." + PREFIX + "-btn-primary:hover{filter:brightness(0.9)}",
      "." + PREFIX + "-btn-primary:disabled{opacity:0.5;cursor:not-allowed}",
      "." + PREFIX + "-btn-secondary{background:#f7fafc;color:#4a5568;border:1px solid #e2e8f0}",
      "." + PREFIX + "-btn-secondary:hover{background:#edf2f7}",
      "." + PREFIX + "-success{text-align:center;padding:20px 0}",
      "." + PREFIX + "-success h3{margin:0 0 8px;font-size:18px;color:#38a169}",
      "." + PREFIX + "-success p{margin:0;color:#666;font-size:14px}",
      "." + PREFIX + "-step-indicator{font-size:12px;color:#a0aec0;margin-bottom:16px}",
      /* Dark theme overrides */
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-modal{background:#1a1a1a;color:#f0f0f0}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-close{color:#777}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-close:hover{color:#ddd;background:#333}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-title{color:#f0f0f0}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-q-title{color:#f0f0f0}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-option{border-color:#333;color:#e0e0e0}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-option:hover{border-color:#555;background:#2a2a2a}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-option.selected{border-color:#6366f1;background:#2d2b55}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-input," + "." + PREFIX + "-overlay.dark ." + PREFIX + "-textarea{background:#2a2a2a;border-color:#333;color:#e0e0e0}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-input:focus," + "." + PREFIX + "-overlay.dark ." + PREFIX + "-textarea:focus{border-color:#6366f1;box-shadow:0 0 0 3px rgba(99,102,241,0.15)}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-btn-secondary{background:#2a2a2a;color:#ccc;border-color:#444}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-btn-secondary:hover{background:#333}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-actions{border-top-color:#333}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-success h3{color:#4ade80}",
      "." + PREFIX + "-overlay.dark ." + PREFIX + "-success p{color:#aaa}",
    ].join("\n");
    document.head.appendChild(style);
  }

  // ── Renderer ────────────────────────────────────────────────────

  function renderSurvey(survey) {
    injectStyles();

    var questions = survey.questions || [];
    var displayRules = survey.display_rules || [];
    var answers = {};
    var stepIndex = 0;
    var isSubmitting = false;
    var clarityProjectId = null;
    var clarityProjectIdSource = null;

    // Theme & colors
    var surveySettings = survey.settings || {};
    var isDark = surveySettings.theme === "dark";
    var btnColor = surveySettings.button_color || "#4F46E5";

    // Resolve Clarity project ID
    waitForClarity(survey.clarity_project_id, function (id, source) {
      clarityProjectId = id;
      clarityProjectIdSource = source;
    });

    // Build rules map: target_question_key -> [{ source_question_key, operator, comparison_value }]
    var rulesByTarget = {};
    for (var i = 0; i < displayRules.length; i++) {
      var rule = displayRules[i];
      var key = rule.target_question_key;
      if (!rulesByTarget[key]) rulesByTarget[key] = [];
      rulesByTarget[key].push(rule);
    }

    function isQuestionVisible(q) {
      var rules = rulesByTarget[q.question_key];
      if (!rules || rules.length === 0) return true;
      for (var i = 0; i < rules.length; i++) {
        var r = rules[i];
        var srcAnswer = answers[r.source_question_key];
        if (r.operator === "equals") {
          if (srcAnswer !== r.comparison_value) return false;
        }
      }
      return true;
    }

    function getVisibleQuestions() {
      var visible = [];
      for (var i = 0; i < questions.length; i++) {
        if (questions[i].is_enabled && isQuestionVisible(questions[i])) {
          visible.push(questions[i]);
        }
      }
      return visible;
    }

    // Resolve display settings
    var dType = (survey.settings && survey.settings.display_type) || "popover";
    var slidePos = (survey.settings && survey.settings.slideup_position) || "bottom-right";

    // Create overlay
    var overlay = document.createElement("div");
    overlay.className = PREFIX + "-overlay" + (dType === "slideup" ? " slideup pos-" + slidePos : "") + (isDark ? " dark" : "");
    overlay.style.setProperty("--vzd-btn-color", btnColor);

    var modal = document.createElement("div");
    modal.className = PREFIX + "-modal";
    overlay.appendChild(modal);

    // Click outside to dismiss
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) dismiss();
    });

    function dismiss() {
      overlay.classList.remove("visible");
      setTimeout(function () {
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      }, 200);
    }

    function render() {
      modal.innerHTML = "";

      // Close/collapse button
      var closeBtn = document.createElement("button");
      closeBtn.className = PREFIX + "-close";
      var closeIcon = document.createElement("img");
      closeIcon.src = dType === "slideup" ? ICON_COLLAPSE : ICON_CLOSE;
      closeIcon.alt = dType === "slideup" ? "Collapse" : "Close";
      closeIcon.style.cssText = "width:20px;height:20px;display:block;";
      if (isDark) closeIcon.style.filter = "invert(0.7)";
      closeBtn.textContent = "";
      closeBtn.appendChild(closeIcon);
      closeBtn.addEventListener("click", dismiss);
      modal.appendChild(closeBtn);

      // Title — use widget_title (display heading), only on first step
      var displayTitle = survey.widget_title;
      if (displayTitle && stepIndex === 0) {
        var title = document.createElement("h2");
        title.className = PREFIX + "-title";
        title.textContent = displayTitle;
        modal.appendChild(title);
      }

      var visible = getVisibleQuestions();

      // Clamp step index
      if (stepIndex >= visible.length) stepIndex = visible.length - 1;
      var currentQ = visible[stepIndex];

      // Question title
      var qTitle = document.createElement("div");
      qTitle.className = PREFIX + "-q-title";
      qTitle.textContent = currentQ.title;
      if (currentQ.is_required) {
        var reqSpan = document.createElement("span");
        reqSpan.className = "required";
        reqSpan.textContent = "*";
        qTitle.appendChild(reqSpan);
      }
      modal.appendChild(qTitle);

      // Question input
      var currentAnswer = answers[currentQ.question_key] || "";

      if (currentQ.answer_type === "choice_list" && currentQ.options) {
        for (var i = 0; i < currentQ.options.length; i++) {
          (function (opt) {
            var optDiv = document.createElement("div");
            optDiv.className = PREFIX + "-option" + (currentAnswer === opt ? " selected" : "");

            var radio = document.createElement("input");
            radio.type = "radio";
            radio.name = PREFIX + "-q-" + currentQ.question_key;
            radio.checked = currentAnswer === opt;

            var label = document.createElement("span");
            label.textContent = opt;

            optDiv.appendChild(radio);
            optDiv.appendChild(label);
            optDiv.addEventListener("click", function () {
              answers[currentQ.question_key] = opt;
              render();
            });
            modal.appendChild(optDiv);
          })(currentQ.options[i]);
        }
      } else if (currentQ.answer_type === "multi_line_text") {
        var textarea = document.createElement("textarea");
        textarea.className = PREFIX + "-textarea";
        textarea.placeholder = "Your answer...";
        textarea.value = currentAnswer;
        textarea.addEventListener("input", function () {
          answers[currentQ.question_key] = textarea.value;
        });
        modal.appendChild(textarea);
      } else {
        var input = document.createElement("input");
        input.type = "text";
        input.className = PREFIX + "-input";
        input.placeholder = "Your answer...";
        input.value = currentAnswer;
        input.addEventListener("input", function () {
          answers[currentQ.question_key] = input.value;
        });
        modal.appendChild(input);
      }

      // Actions
      var actions = document.createElement("div");
      actions.className = PREFIX + "-actions";

      if (stepIndex > 0) {
        var backBtn = document.createElement("button");
        backBtn.className = PREFIX + "-btn " + PREFIX + "-btn-secondary";
        backBtn.textContent = "Back";
        backBtn.addEventListener("click", function () {
          stepIndex--;
          render();
        });
        actions.appendChild(backBtn);
      } else {
        actions.appendChild(document.createElement("div")); // Spacer
      }

      var isLast = stepIndex === visible.length - 1;
      var nextBtn = document.createElement("button");
      nextBtn.className = PREFIX + "-btn " + PREFIX + "-btn-primary";
      nextBtn.textContent = isLast ? (survey.submit_label || "Submit") : "Next";

      if (isSubmitting) {
        nextBtn.disabled = true;
        nextBtn.textContent = "Submitting...";
      }

      nextBtn.addEventListener("click", function () {
        // Validate required
        if (currentQ.is_required && !answers[currentQ.question_key]) {
          return;
        }
        if (isLast) {
          doSubmit();
        } else {
          stepIndex++;
          render();
        }
      });
      actions.appendChild(nextBtn);
      modal.appendChild(actions);
    }

    function doSubmit() {
      isSubmitting = true;
      render();

      var visible = getVisibleQuestions();
      var answersList = [];
      for (var i = 0; i < visible.length; i++) {
        var q = visible[i];
        var val = answers[q.question_key];
        if (val !== undefined && val !== "") {
          answersList.push({
            question_id: q.id,
            question_key: q.question_key,
            answer_text: String(val),
          });
        }
      }

      var payload = {
        idempotency_key: Date.now() + "-" + Math.random().toString(36).slice(2, 10),
        survey_id: survey.survey_id,
        survey_version_id: survey.survey_version_id,
        site_domain: location.hostname,
        page_url: location.href,
        clarity_session_id: getClaritySessionId(),
        clarity_project_id: clarityProjectId,
        clarity_project_id_source: clarityProjectIdSource,
        answers: answersList,
        submitted_at: new Date().toISOString(),
      };

      submitResponse(payload, function () {
        markAnswered();
        isSubmitting = false;
        showSuccess();
      });
    }

    function showSuccess() {
      modal.innerHTML = "";

      var closeBtn = document.createElement("button");
      closeBtn.className = PREFIX + "-close";
      var successCloseIcon = document.createElement("img");
      successCloseIcon.src = ICON_CLOSE;
      successCloseIcon.alt = "Close";
      successCloseIcon.style.cssText = "width:20px;height:20px;display:block;";
      if (isDark) successCloseIcon.style.filter = "invert(0.7)";
      closeBtn.appendChild(successCloseIcon);
      closeBtn.addEventListener("click", dismiss);
      modal.appendChild(closeBtn);

      var successDiv = document.createElement("div");
      successDiv.className = PREFIX + "-success";

      var heading = surveySettings.success_heading || "Thank you!";
      var message = surveySettings.success_message || "Your feedback has been submitted.";
      var dismissSeconds = surveySettings.success_dismiss_seconds;
      if (dismissSeconds === undefined || dismissSeconds === null) dismissSeconds = 3;

      var h3 = document.createElement("h3");
      h3.textContent = heading;
      successDiv.appendChild(h3);

      var p = document.createElement("p");
      p.textContent = message;
      successDiv.appendChild(p);

      modal.appendChild(successDiv);

      if (dismissSeconds > 0) {
        setTimeout(dismiss, dismissSeconds * 1000);
      }
    }

    // Initial render
    render();
    document.body.appendChild(overlay);
    requestAnimationFrame(function () {
      overlay.classList.add("visible");
    });

    // Track impression
    markShown(survey.frequency);
    sendImpression(survey.survey_id, survey.survey_version_id);
  }

  // ── Trigger engine ──────────────────────────────────────────────

  function fireTrigger(survey) {
    var trigger = survey.trigger_rules || {};
    var type = trigger.type || "immediate";

    if (type === "delay") {
      var ms = trigger.delay_ms || 3000;
      setTimeout(function () { renderSurvey(survey); }, ms);
    } else if (type === "exit_intent") {
      // Desktop: detect mouse leaving viewport
      var fired = false;
      var handler = function (e) {
        if (e.clientY < 0 && !fired) {
          fired = true;
          document.documentElement.removeEventListener("mouseleave", handler);
          renderSurvey(survey);
        }
      };
      document.documentElement.addEventListener("mouseleave", handler);
      // Mobile fallback: delay
      if ("ontouchstart" in window) {
        setTimeout(function () {
          if (!fired) {
            fired = true;
            document.documentElement.removeEventListener("mouseleave", handler);
            renderSurvey(survey);
          }
        }, 3000);
      }
    } else {
      // immediate
      renderSurvey(survey);
    }
  }

  // ── Main ────────────────────────────────────────────────────────

  function init() {
    // Always send heartbeat (before URL targeting check)
    sendHeartbeat();

    // Fetch active survey config
    fetchActiveSurvey(function (survey) {
      if (!survey) return;

      // Check URL targeting
      if (!matchesUrlTargeting(survey.url_targeting)) return;

      // Check frequency/suppression
      if (!shouldShow(survey.frequency)) return;

      // Fire the trigger
      fireTrigger(survey);
    });
  }

  // Wait for DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Expose manual show API
  cfg.show = function () {
    fetchActiveSurvey(function (survey) {
      if (survey) renderSurvey(survey);
    });
  };
})();
