/**
 * Page-world media downloader.
 * Runs in the MAIN world (page's JS context) so fetch() uses facebook.com origin.
 * Communicates with the ISOLATED world content script via window.postMessage.
 */

window.addEventListener("message", async (event) => {
  if (event.source !== window) return;
  if (event.data?.type !== "VZD_DOWNLOAD_REQUEST") return;

  const { requestId, url } = event.data;
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const blob = await resp.blob();
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
    window.postMessage({
      type: "VZD_DOWNLOAD_RESULT",
      requestId,
      success: false,
      error: e.message,
    }, "*");
  }
});
