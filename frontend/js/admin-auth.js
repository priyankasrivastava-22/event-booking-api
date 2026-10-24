"use strict";
(function () {
    document.documentElement.classList.add("eventora-auth-pending");
    const style = document.createElement("style");
    style.textContent = ".eventora-auth-pending body {visibility:hidden;}";
    document.head.appendChild(style);
    const loginUrl = window.Eventora.loginUrl;
    const token = window.Eventora.token();
    if (!token) { window.location.replace(loginUrl); return; }
    fetch(window.Eventora.api + "/auth/me", {headers:{Authorization:"Bearer " + token}})
        .then(async response => {
            if (response.status === 401 || response.status === 403) {
                localStorage.removeItem("token");
                window.location.replace(loginUrl);
                return;
            }
            if (!response.ok) throw new Error("Unable to verify your admin session.");
            const account = await response.json();
            if (account.role !== "admin") {window.location.replace(loginUrl);return;}
            document.documentElement.classList.remove("eventora-auth-pending");
        })
        .catch(() => {
            const errorPage = () => {
                document.body.replaceChildren();
                const panel = document.createElement("main");
                panel.setAttribute("role", "alert");
                panel.style.cssText = "max-width:42rem;margin:15vh auto;padding:2rem;font:16px system-ui;";
                panel.textContent = "The admin session could not be verified. Check that the backend is running, then reload this page.";
                document.body.appendChild(panel);
                document.documentElement.classList.remove("eventora-auth-pending");
            };
            if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", errorPage, {once:true});
            else errorPage();
        });
})();
