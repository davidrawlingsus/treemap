/**
 * Page-world media downloader.
 * Runs in the MAIN world (page's JS context) so fetch() uses facebook.com origin.
 * Communicates with the ISOLATED world content script via window.postMessage.
 */

console.log("[MTG page-dl] page-downloader.js loaded in MAIN world on", location.href);

window.addEventListener("message", async (event) => {
  if (event.source !== window) return;
  if (event.data?.type !== "VZD_DOWNLOAD_REQUEST") return;

  const { requestId, url } = event.data;
  console.log("[MTG page-dl] fetching from page context:", url?.substring(0, 100));
  try {
    const resp = await fetch(url);
    console.log("[MTG page-dl] fetch response:", resp.status, resp.statusText, "content-type:", resp.headers.get("content-type"));
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const blob = await resp.blob();
    console.log("[MTG page-dl] blob:", blob.size, "bytes, type=", blob.type);
    const reader = new FileReader();
    reader.onloadend = () => {
      window.postMessage({
        type: "VZD_DOWNLOAD_RESULT",
        requestId,
        success: true,
        dataUrl: reader.result,
        blobType: blob.type,
        size: blob.size,
      }, "*");
    };
    reader.onerror = () => {
      window.postMessage({
        type: "VZD_DOWNLOAD_RESULT",
        requestId,
        success: false,
        error: "FileReader failed",
      }, "*");
    };
    reader.readAsDataURL(blob);
  } catch (e) {
    console.error("[MTG page-dl] fetch failed:", e?.message, "for", url?.substring(0, 100));
    window.postMessage({
      type: "VZD_DOWNLOAD_RESULT",
      requestId,
      success: false,
      error: e.message,
    }, "*");
  }
});
