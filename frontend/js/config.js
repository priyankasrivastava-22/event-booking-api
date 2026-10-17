"use strict";
/* Shared by every customer and admin page. Do not hard-code hosted API URLs in feature files. */
(function configureEventora() {
    const host = window.location.hostname;
    const isLocal = ["localhost", "127.0.0.1"].includes(host);
    // PyCharm terminal: frontend on :5500, FastAPI on :8000.
    // For future hosting, configure window.API_BASE_URL before this script.
    window.API_BASE_URL = String(window.API_BASE_URL || (isLocal ? "http://127.0.0.1:8000" : window.location.origin)).replace(/\/$/, "");
    window.Eventora = Object.freeze({
        apiOrigin: window.API_BASE_URL,
        api: window.API_BASE_URL + "/api",
        token: () => localStorage.getItem("token") || localStorage.getItem("access_token") || sessionStorage.getItem("token"),
        loginUrl: (window.location.pathname.includes("/admin/") ? (window.location.pathname.includes("/admin/pages/") ? "../../" : "../") : "../") + "pages/login.html",
        error: (value) => typeof value?.detail === "string" ? value.detail : (typeof value?.error === "string" ? value.error : "The request could not be completed."),
    });
})();
