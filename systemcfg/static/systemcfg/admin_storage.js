(() => {
  const BACKENDS = {
    local: "local",
    s3: "s3",
    webdav: "webdav",
  };

  function showRow(row, show) {
    if (!row) return;
    row.style.display = show ? "" : "none";
  }

  function rowForField(fieldName) {
    const input = document.getElementById(`id_${fieldName}`);
    if (!input) return null;
    return input.closest(".form-row") || input.closest(".fieldBox") || input.closest("div");
  }

  function applyVisibility(backend) {
    const localFields = ["local_subdir", "local_base_url"];
    const s3Fields = ["s3_endpoint_url", "s3_region", "s3_bucket", "s3_access_key", "s3_secret_key", "s3_base_url"];
    const webdavFields = ["webdav_base_url", "webdav_username", "webdav_password", "webdav_upload_path"];

    for (const f of localFields) showRow(rowForField(f), backend === BACKENDS.local);
    for (const f of s3Fields) showRow(rowForField(f), backend === BACKENDS.s3);
    for (const f of webdavFields) showRow(rowForField(f), backend === BACKENDS.webdav);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const backendSelect = document.getElementById("id_backend");
    if (!backendSelect) return;
    applyVisibility(backendSelect.value);
    backendSelect.addEventListener("change", () => applyVisibility(backendSelect.value));
  });
})();

