console.log("navbar.js loaded");

const NAV_API_URL = "https://event-booking-api-gnww.onrender.com/api";

async function loadNavbar() {
    const container = document.getElementById("navbar-container");
    if (!container) return;

    try {
        const res = await fetch("navbar.html");
        const html = await res.text();
        container.innerHTML = html;
        setupNavbar();
    } catch (err) {
        console.error("Navbar load error:", err);
    }
}

function getUserFromToken() {
    const token = localStorage.getItem("token");
    if (!token) return null;

    try {
        return JSON.parse(atob(token.split(".")[1]));
    } catch {
        return null;
    }
}

function checkAuth() {
    const token = localStorage.getItem("token");
    if (!token) window.location.href = "login.html";
}

function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

function loadNavbarUser() {
    const user = getUserFromToken();
    const el = document.getElementById("nav-username");
    if (el) el.innerText = user?.sub || "User";
}

async function loadNotificationCount() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
        const res = await fetch(`${NAV_API_URL}/engagement/my-notifications`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        const data = await res.json();
        const badge = document.getElementById("notifCount");

        if (!badge) return;

        const count = Array.isArray(data) ? data.length : 0;
        badge.innerText = count;
        badge.style.display = count ? "inline-block" : "none";

    } catch (err) {
        console.error(err);
    }
}

function bindSearchForEventsPage() {
    const input = document.getElementById("searchInput");
    if (input && typeof loadEvents === "function") {
        input.addEventListener("input", loadEvents);
    }
}

function setupNavbar() {
    checkAuth();
    loadNavbarUser();
    loadNotificationCount();
    bindSearchForEventsPage();
    setupPageButtons();
    setInterval(loadNotificationCount, 5000);
}

document.addEventListener("DOMContentLoaded", loadNavbar);

function setupPageButtons() {
    const rightSide = document.querySelector(".navbar .d-flex.gap-3");

    if (!rightSide) return;

    const page = window.location.pathname.split("/").pop();

    if (
        page === "notifications.html" ||
        page === "my-bookings.html" ||
        page === "event-details.html"
    ) {
        const backBtn = document.createElement("button");

        backBtn.className = "btn btn-sm btn-outline-light";
        backBtn.innerHTML = '<i class="bi bi-arrow-left"></i>';

        backBtn.onclick = () => history.back();

        rightSide.prepend(backBtn);
    }
}