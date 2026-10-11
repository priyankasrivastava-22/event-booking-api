"use strict";

const API_BASE = "https://event-booking-api-gnww.onrender.com/api";
let currentPage = 1;

function getToken() { return localStorage.getItem("token") || localStorage.getItem("access_token"); }
function authHeaders() { const t = getToken(); return t ? { "Authorization": `Bearer ${t}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" }; }
function escapeHtml(v) { return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c])); }
function formatDate(v) { if (!v) return "—"; const d = new Date(v); return Number.isNaN(d.getTime()) ? v : d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); }

document.addEventListener("DOMContentLoaded", () => loadHistory(1));

// ---------------- SEND NOTIFICATION ----------------
async function sendNotification() {
    const title = document.getElementById("notifTitle").value.trim();
    const message = document.getElementById("notifMessage").value.trim();
    const audience = document.getElementById("notifAudience").value;
    const messageEl = document.getElementById("composeMessage");

    if (!title || !message) {
        messageEl.textContent = "Title and message are required.";
        messageEl.className = "compose-message is-error";
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/admin/announcements`, {
            method: "POST", headers: authHeaders(),
            body: JSON.stringify({ title, message, audience })
        });
        if (!res.ok) throw new Error("Failed to send notification.");
        const data = await res.json();

        messageEl.textContent = `Sent to ${data.sent_count} user(s).`;
        messageEl.className = "compose-message is-success";

        document.getElementById("notifTitle").value = "";
        document.getElementById("notifMessage").value = "";

        loadHistory(1);

    } catch (error) {
        messageEl.textContent = error.message;
        messageEl.className = "compose-message is-error";
    }
}

// ---------------- HISTORY TABLE ----------------
async function loadHistory(page = 1) {
    currentPage = page;
    const tbody = document.getElementById("historyTableBody");
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted py-4">Loading...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/admin/announcements?page=${page}&limit=5`, { headers: authHeaders() });
        if (res.status === 401) { window.location.href = "../../pages/login.html"; return; }
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        if (!data.items.length) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted py-4">No notifications sent yet.</td></tr>`;
            renderPagination(0, 1, 5);
            return;
        }

        tbody.innerHTML = data.items.map(a => `
            <tr>
                <td>${escapeHtml(a.title)}</td>
                <td>${a.audience === "all" ? "All Users" : "Registered Users"}</td>
                <td>${formatDate(a.created_at)}</td>
                <td><span class="status-badge sent">Sent</span></td>
            </tr>
        `).join("");

        renderPagination(data.total, data.page, data.limit);

    } catch (error) {
        console.error("Load history error:", error);
        tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger py-4">Unable to load history.</td></tr>`;
    }
}

function renderPagination(total, page, limit) {
    const totalPages = Math.max(1, Math.ceil(total / limit));
    const container = document.getElementById("paginationControls");
    const summary = document.getElementById("paginationSummary");

    let buttons = `<button ${page <= 1 ? "disabled" : ""} onclick="loadHistory(${page - 1})"><i class="bi bi-chevron-left"></i></button>`;
    let start = Math.max(1, page - 2);
    let end = Math.min(totalPages, start + 4);
    start = Math.max(1, end - 4);
    for (let i = start; i <= end; i++) buttons += `<button class="${i === page ? "active" : ""}" onclick="loadHistory(${i})">${i}</button>`;
    buttons += `<button ${page >= totalPages ? "disabled" : ""} onclick="loadHistory(${page + 1})"><i class="bi bi-chevron-right"></i></button>`;

    container.innerHTML = buttons;
    const from = total === 0 ? 0 : (page - 1) * limit + 1;
    const to = Math.min(page * limit, total);
    summary.textContent = `Showing ${from} to ${to} of ${total} notifications`;
}