"use strict";

const API_BASE = "https://event-booking-api-gnww.onrender.com/api";
let revenueChartInstance = null;

function getToken() { return localStorage.getItem("token") || localStorage.getItem("access_token"); }
function authHeaders() { const t = getToken(); return t ? { "Authorization": `Bearer ${t}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" }; }
function escapeHtml(v) { return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c])); }

document.addEventListener("DOMContentLoaded", () => {
    populateYearSelect();
    const year = document.getElementById("yearSelect").value;
    loadAnalytics(year);
    document.getElementById("yearSelect").addEventListener("change", e => loadAnalytics(e.target.value));
});

function populateYearSelect() {
    const currentYear = new Date().getFullYear();
    const select = document.getElementById("yearSelect");
    for (let y = currentYear; y >= currentYear - 3; y--) {
        select.innerHTML += `<option value="${y}">${y === currentYear ? "This Year" : y}</option>`;
    }
}

async function loadAnalytics(year) {
    await Promise.all([
        loadOverviewStats(year),
        loadRevenueChart(year),
        loadTopEvents(year)
    ]);
}

// ---------------- 4 STAT CARDS ----------------
async function loadOverviewStats(year) {
    try {
        const res = await fetch(`${API_BASE}/analytics/overview?year=${year}`, { headers: authHeaders() });
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        setStat("statRevenue", `₹${Number(data.total_revenue).toLocaleString("en-IN")}`, "statRevenueTrend", data.revenue_change_pct);
        setStat("statBookings", data.total_bookings.toLocaleString("en-IN"), "statBookingsTrend", data.bookings_change_pct);
        setStat("statUsers", data.total_users.toLocaleString("en-IN"), "statUsersTrend", data.users_change_pct);
        setStat("statEvents", data.total_events.toLocaleString("en-IN"), "statEventsTrend", data.events_change_pct);

    } catch (error) {
        console.error("Overview stats error:", error);
    }
}

function setStat(valueId, valueText, trendId, changePct) {
    document.getElementById(valueId).textContent = valueText;
    const trendEl = document.getElementById(trendId);
    const isPositive = changePct >= 0;
    trendEl.textContent = `${isPositive ? "+" : ""}${changePct}% vs last year`;
    trendEl.classList.toggle("negative", !isPositive);
}

// ---------------- REVENUE OVER TIME CHART ----------------
async function loadRevenueChart(year) {
    try {
        const res = await fetch(`${API_BASE}/analytics/revenue-by-month?year=${year}`, { headers: authHeaders() });
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        const canvas = document.getElementById("revenueChart");
        if (revenueChartInstance) revenueChartInstance.destroy();

        const ctx = canvas.getContext("2d");
        const gradient = ctx.createLinearGradient(0, 0, 0, 200);
        gradient.addColorStop(0, "rgba(109, 93, 246, 0.35)");
        gradient.addColorStop(1, "rgba(109, 93, 246, 0)");

        revenueChartInstance = new Chart(canvas, {
            type: "line",
            data: {
                labels: data.map(d => d.month),
                datasets: [{
                    data: data.map(d => d.revenue),
                    borderColor: "#8b7cff",
                    backgroundColor: gradient,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#94a3b8" } },
                    y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8", callback: v => `${v / 1000}k` } }
                }
            }
        });

    } catch (error) {
        console.error("Revenue chart error:", error);
    }
}

// ---------------- TOP PERFORMING EVENTS ----------------
async function loadTopEvents(year) {
    try {
        const res = await fetch(`${API_BASE}/analytics/top-events?year=${year}&limit=5`, { headers: authHeaders() });
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        const list = document.getElementById("topEventsList");

        if (!data.length) {
            list.innerHTML = `<li class="text-muted">No bookings yet for this year.</li>`;
            return;
        }

        list.innerHTML = data.map((event, index) => `
            <li>
                <span><span class="rank-number">${index + 1}.</span>${escapeHtml(event.title)}</span>
                <span class="event-revenue">₹${Number(event.revenue).toLocaleString("en-IN")}</span>
            </li>
        `).join("");

    } catch (error) {
        console.error("Top events error:", error);
    }
}