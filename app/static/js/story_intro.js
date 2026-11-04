(() => {
  const dialog = document.querySelector("[data-story-dialog]");
  if (!dialog || typeof dialog.showModal !== "function") return;

  const seenKey = "hydra-underground-story-seen";
  const url = new URL(window.location.href);
  const enteredFromPortal = url.searchParams.get("intro") === "1";
  if (enteredFromPortal) {
    url.searchParams.delete("intro");
    window.history.replaceState(null, "", url.pathname + url.search + url.hash);
  }

  let seen = false;
  try {
    seen = window.sessionStorage.getItem(seenKey) === "1";
  } catch (_) {
    // 即使瀏覽器停用儲存空間，簡報仍可正常開啟。
  }

  const openDialog = () => {
    if (!dialog.open) dialog.showModal();
  };

  document.querySelectorAll("[data-story-open]").forEach((button) => {
    button.addEventListener("click", openDialog);
  });
  dialog.querySelectorAll("[data-story-close]").forEach((button) => {
    button.addEventListener("click", () => dialog.close());
  });
  dialog.addEventListener("close", () => {
    try {
      window.sessionStorage.setItem(seenKey, "1");
    } catch (_) {
      // 儲存失敗不影響彈窗關閉。
    }
  });

  if (enteredFromPortal || !seen) openDialog();
})();

