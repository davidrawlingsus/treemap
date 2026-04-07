/**
 * MapTheGap Ad Library Extractor — Content Script
 * Runs on facebook.com/ads/library/* pages.
 * Extracts ad data from the DOM when triggered by the popup.
 */

(() => {
  // ---- helpers ----
  const META_MEDIA_URL = /(scontent|fbcdn\.net|video\.[a-z0-9-]+\.fna\.fbcdn|cdninstagram)/i;

  function isAdMediaUrl(url) {
    if (!url || typeof url !== "string") return false;
    const u = url.toLowerCase();
    if (u.includes("s60x60") || u.includes("_s60x60")) return false;
    if (u.includes("/rsrc.php/") || u.includes("static.xx.fbcdn")) return false;
    return META_MEDIA_URL.test(url);
  }

  function hasAdMedia(el) {
    const vid = el.querySelector("video[src]");
    if (vid && isAdMediaUrl(vid.src || vid.getAttribute("src"))) return true;
    for (const img of el.querySelectorAll("img[src]")) {
      const src = img.src || img.getAttribute("src");
      if (!isAdMediaUrl(src)) continue;
      const w = img.naturalWidth || img.width || 0;
      const h = img.naturalHeight || img.height || 0;
      if (w > 0 && w < 80 && h > 0 && h < 80) continue;
      return true;
    }
    return false;
  }

  function findContainer(span) {
    let container = span;
    let bestContainer = span;
    for (let i = 0; i < 20 && container.parentElement; i++) {
      container = container.parentElement;
      if (hasAdMedia(container)) return container;
      const anyMetaImg = container.querySelector(
        'img[src*="scontent"], img[src*="fbcdn"]'
      );
      if (anyMetaImg) bestContainer = container;
      let libIdCount = 0;
      for (const s of container.querySelectorAll("span")) {
        if (/^Library ID:\s*\d+$/.test(s.textContent?.trim() || "")) {
          libIdCount++;
          if (libIdCount > 1) return bestContainer;
        }
      }
    }
    return bestContainer;
  }

  function findMediaInContainer(el) {
    const videos = [];
    const images = [];
    const seen = new Set();
    function walk(node, depth) {
      if (depth > 30 || node.nodeType !== 1) return;
      if (node.tagName === "VIDEO") {
        const src = node.src || node.getAttribute("src");
        const poster = node.poster || node.getAttribute("poster");
        if (src && isAdMediaUrl(src) && !seen.has(src)) {
          seen.add(src);
          videos.push({ url: src, poster: poster || null });
        } else if (!src && poster && isAdMediaUrl(poster) && !seen.has(poster)) {
          seen.add(poster);
          videos.push({ url: poster, poster });
        }
        return;
      }
      if (node.tagName === "IMG") {
        const src = node.src || node.getAttribute("src");
        if (src && isAdMediaUrl(src) && !seen.has(src)) {
          seen.add(src);
          images.push({ url: src });
        }
        return;
      }
      for (const c of node.children || []) walk(c, depth + 1);
    }
    walk(el, 0);
    return { videos, images };
  }

  // ---- main extraction ----
  function extractAds() {
    const results = [];
    const allSpans = document.querySelectorAll("span");
    const adCards = new Map();

    // 1. Locate ad cards via Library ID / metadata spans
    for (const span of allSpans) {
      const text = span.textContent?.trim() || "";

      const libraryIdMatch = text.match(/^Library ID:\s*(\d+)$/);
      if (libraryIdMatch) {
        const key = findContainer(span);
        if (!adCards.has(key))
          adCards.set(key, {
            libraryId: null,
            startedRunningOn: null,
            endedRunningOn: null,
            status: null,
            adsUsingCreative: null,
          });
        adCards.get(key).libraryId = libraryIdMatch[1];
      }
      const dateMatch = text.match(
        /^Started running on\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})$/
      );
      if (dateMatch) {
        const key = findContainer(span);
        if (!adCards.has(key))
          adCards.set(key, {
            libraryId: null,
            startedRunningOn: null,
            endedRunningOn: null,
            status: null,
            adsUsingCreative: null,
          });
        adCards.get(key).startedRunningOn = dateMatch[1];
      }
      const endedMatch = text.match(
        /Ended\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})/
      );
      if (endedMatch) {
        const key = findContainer(span);
        if (adCards.has(key)) adCards.get(key).endedRunningOn = endedMatch[1];
      }
      if (/^Active$|^Paused$|^Ended$/i.test(text)) {
        const key = findContainer(span);
        if (!adCards.has(key))
          adCards.set(key, {
            libraryId: null,
            startedRunningOn: null,
            endedRunningOn: null,
            status: null,
            adsUsingCreative: null,
          });
        adCards.get(key).status = text;
      }
      const adsMatch = text.match(/(\d+)\s+ads?\s+use this creative/i);
      if (adsMatch) {
        const key = findContainer(span);
        if (!adCards.has(key))
          adCards.set(key, {
            libraryId: null,
            startedRunningOn: null,
            endedRunningOn: null,
            status: null,
            adsUsingCreative: null,
          });
        adCards.get(key).adsUsingCreative = parseInt(adsMatch[1], 10);
      }
    }

    // 2. Extract copy, media, links from each card
    for (const [container, data] of adCards) {
      let bodyText = "";
      let headlineText = "";
      let descriptionText = "";

      // Primary text
      for (const div of container.querySelectorAll(
        'div[style*="white-space: pre-wrap"]'
      )) {
        const t = (div.innerText || div.textContent || "").trim();
        if (t.length > bodyText.length && t.length > 20) bodyText = t;
      }

      // Headline + description from CTA link area
      const ctaLink = container.querySelector(
        'a[target="_blank"][href*="l.facebook.com"], a[target="_blank"][href*="l.php"]'
      );
      if (ctaLink) {
        for (const div of ctaLink.querySelectorAll(
          'div[style*="line-clamp"]'
        )) {
          const t = (div.innerText || div.textContent || "").trim();
          if (!t) continue;
          const style = div.getAttribute("style") || "";
          const heightMatch = style.match(/max-height:\s*(\d+)px/);
          const height = heightMatch ? parseInt(heightMatch[1], 10) : 0;
          if (height >= 20 && height <= 30 && t.length > 0 && !headlineText) {
            headlineText = t;
          } else if (t.length > 0 && t !== headlineText && !descriptionText) {
            descriptionText = t;
          }
        }
      }

      // Fallback headline
      if (!headlineText) {
        for (const div of container.querySelectorAll(
          'div[style*="line-clamp"]'
        )) {
          const t = (div.innerText || div.textContent || "").trim();
          const clean = t.replace(/^Sponsored\s*/i, "").trim();
          if (clean.length > 0 && clean.length <= 200) headlineText = clean;
        }
      }

      const fullText = (
        container.innerText ||
        container.textContent ||
        ""
      ).trim();
      if (bodyText.length < 10 && fullText.length >= 10) bodyText = fullText;
      if (bodyText.length < 5) continue;

      // Media
      const { videos, images } = findMediaInContainer(container);
      const video = videos[0];
      let adFormat = "image";
      if (video) adFormat = "video";
      else if (images.length > 1) adFormat = "carousel";

      let mediaThumbnailUrl = null;
      if (video && video.poster) mediaThumbnailUrl = video.poster;
      else if (video && video.url) mediaThumbnailUrl = video.url;
      else if (images.length > 0) mediaThumbnailUrl = images[0].url;

      // CTA
      let cta = null;
      let destinationUrl = null;
      let pageName = null;
      let pageUrl = null;
      let pageProfileImageUrl = null;

      for (const btn of container.querySelectorAll('div[role="button"]')) {
        const t = (btn.innerText || btn.textContent || "").trim();
        if (
          /^(learn more|shop now|sign up|get offer|download|watch more|send message|apply now|book now|start trial|take quiz|subscribe|order now|get quote|listen now|see menu|request time|get directions|contact us|message page)$/i.test(
            t
          )
        ) {
          cta = t;
          break;
        }
      }

      for (const a of container.querySelectorAll('a[target="_blank"][href]')) {
        const href = (a.getAttribute("href") || a.href || "").trim();
        if (!href || href.startsWith("#")) continue;
        const text = (a.innerText || a.textContent || "").trim();
        if (
          href.includes("facebook.com") &&
          !href.includes("l.php") &&
          text &&
          text.length > 0 &&
          text.length <= 100
        ) {
          pageUrl = href;
          pageName = text;
        }
        if (
          href.includes("l.facebook.com/l.php") ||
          href.includes("l.php")
        ) {
          try {
            const u = new URL(href);
            const uParam = u.searchParams.get("u");
            destinationUrl = uParam ? decodeURIComponent(uParam) : href;
          } catch (_) {
            destinationUrl = href;
          }
        } else if (
          href.startsWith("http") &&
          !href.includes("facebook.com")
        ) {
          destinationUrl = href;
        }
        if (!cta && destinationUrl && text && text.length <= 100) cta = text;
        if (destinationUrl) break;
      }

      // Profile image
      const profileImg = container.querySelector(
        'img[alt][src*="scontent"], img[alt][src*="fbcdn"]'
      );
      if (
        profileImg &&
        profileImg.alt &&
        pageName &&
        (profileImg.alt === pageName || profileImg.alt.includes(pageName))
      ) {
        pageProfileImageUrl = profileImg.src;
      } else {
        const smallImg = container.querySelector(
          'img[src*="s60x60"], img[src*="_s60x60"]'
        );
        if (smallImg) pageProfileImageUrl = smallImg.src;
      }

      // Build media items array
      const mediaItems = [];
      if (video && video.url) {
        let durSec = null;
        const containerText = container.innerText || "";
        const slashMatch = containerText.match(/\/\s*(\d+):(\d+)/);
        if (slashMatch)
          durSec =
            parseInt(slashMatch[1], 10) * 60 + parseInt(slashMatch[2], 10);
        else {
          const m = containerText.match(/(\d+):(\d+)/);
          if (m) durSec = parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
        }
        mediaItems.push({
          media_type: "video",
          url: video.url,
          poster_url: video.poster || null,
          duration_seconds: durSec,
          sort_order: 0,
        });
      }
      for (let i = 0; i < images.length; i++) {
        const src = images[i].url;
        if (src && !mediaItems.some((m) => m.url === src)) {
          mediaItems.push({
            media_type: "image",
            url: src,
            poster_url: null,
            duration_seconds: null,
            sort_order: mediaItems.length,
          });
        }
      }

      // Clean body text
      let primaryText = bodyText
        .replace(/Library ID:\s*\d+/gi, "")
        .replace(/Started running on\s+[A-Za-z]+\s+\d{1,2},?\s+\d{4}/gi, "")
        .replace(/\n\s*\n/g, "\n")
        .trim();

      results.push({
        primary_text: primaryText.substring(0, 5000),
        headline: headlineText || null,
        description: descriptionText || null,
        library_id: data.libraryId || null,
        started_running_on: data.startedRunningOn || null,
        ad_delivery_start_time: data.startedRunningOn || null,
        ad_delivery_end_time: data.endedRunningOn || null,
        ad_format: adFormat,
        cta: cta || null,
        destination_url: destinationUrl || null,
        media_thumbnail_url: mediaThumbnailUrl || null,
        status: data.status || null,
        platforms: null,
        ads_using_creative_count: data.adsUsingCreative || null,
        page_name: pageName || null,
        page_url: pageUrl || null,
        page_profile_image_url: pageProfileImageUrl || null,
        media_items: mediaItems,
      });
    }

    return results;
  }

  // Download a media file from FB CDN via the MAIN world page-downloader.js
  // (content script fetch uses extension origin which FB CDN blocks via CORS)
  // page-downloader.js runs in MAIN world and listens for VZD_DOWNLOAD_REQUEST
  function downloadMedia(url) {
    return new Promise((resolve, reject) => {
      const requestId = Math.random().toString(36).slice(2);

      function onMessage(event) {
        if (event.source !== window) return;
        if (event.data?.type !== "VZD_DOWNLOAD_RESULT") return;
        if (event.data?.requestId !== requestId) return;
        window.removeEventListener("message", onMessage);

        if (event.data.success) {
          resolve({
            dataUrl: event.data.dataUrl,
            type: event.data.blobType,
            size: event.data.size,
          });
        } else {
          reject(new Error(event.data.error || "Page download failed"));
        }
      }
      window.addEventListener("message", onMessage);

      // Send request to MAIN world script
      window.postMessage({
        type: "VZD_DOWNLOAD_REQUEST",
        requestId,
        url,
      }, "*");

      // Timeout after 120s
      setTimeout(() => {
        window.removeEventListener("message", onMessage);
        reject(new Error("Download timed out (120s)"));
      }, 120000);
    });
  }

  // Listen for messages from the popup / service worker
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "extractAds") {
      try {
        const ads = extractAds();
        sendResponse({ success: true, ads, url: window.location.href });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
      return true;
    }

    if (message.action === "downloadMedia") {
      downloadMedia(message.url)
        .then((result) => sendResponse({ success: true, ...result }))
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true; // keep channel open for async
    }
  });
})();
