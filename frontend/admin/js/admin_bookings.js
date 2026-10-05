"use strict";

const API_BASE = "https://event-booking-api-gnww.onrender.com/api";
let currentPage = 1;
let viewingBookingId = null;

function getToken() { return localStorage.getItem("token") || localStorage.getItem("access_token"); }
function authHeaders() { const t = getToken(); return t ? { "Authorization": `Bearer ${t}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" }; }
function escapeHtml(v) { return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c])); }
function debounce(fn, delay) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), delay); }; }
function formatDate(v) { if (!v) return "—"; const d = new Date(v); return Number.isNaN(d.getTime()) ? v : d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); }

document.addEventListener("DOMContentLoaded", () => {
    loadBookings(1);
    loadEventFilterOptions();
    document.getElementById("filterSearch").addEventListener("input", debounce(() => loadBookings(1), 400));
    document.getElementById("filterEvent").addEventListener("change", () => loadBookings(1));
    document.getElementById("filterStatus").addEventListener("change", () => loadBookings(1));
    document.getElementById("filterStartDate").addEventListener("change", () => loadBookings(1));
    document.getElementById("filterEndDate").addEventListener("change", () => loadBookings(1));
});

async function loadEventFilterOptions() {
    try {
        const res = await fetch(`${API_BASE}/events?limit=100`, { headers: authHeaders() });
        const events = await res.json();
        const select = document.getElementById("filterEvent");
        events.forEach(ev => { select.innerHTML += `<option value="${ev.id}">${escapeHtml(ev.title)}</option>`; });
    } catch (error) {
        console.error("Event filter load error:", error);
    }
}

async function loadBookings(page = 1) {
    currentPage = page;
    const search = document.getElementById("filterSearch").value.trim();
    const eventId = document.getElementById("filterEvent").value;
    const status = document.getElementById("filterStatus").value;
    const startDate = document.getElementById("filterStartDate").value;
    const endDate = document.getElementById("filterEndDate").value;

    const params = new URLSearchParams({ page, limit: 10 });
    if (search) params.append("search", search);
    if (eventId) params.append("event_id", eventId);
    if (status) params.append("status", status);
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);

    const tbody = document.getElementById("bookingsTableBody");
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4">Loading...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/admin/bookings/list?${params.toString()}`, { headers: authHeaders() });
        if (res.status === 401) { window.location.href = "../../pages/login.html"; return; }
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        document.getElementById("statToday").textContent = data.stats.today;
        document.getElementById("statPending").textContent = data.stats.pending;
        document.getElementById("statCompleted").textContent = data.stats.completed;
        document.getElementById("statCancelled").textContent = data.stats.cancelled;

        if (!data.items || !data.items.length) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4">No bookings found.</td></tr>`;
            renderPagination(0, 1, 10);
            return;
        }

        tbody.innerHTML = data.items.map(b => `
            <tr>
                <td class="booking-id-cell">BK-${1000 + b.id}</td>
                <td>${escapeHtml(b.user_name)}</td>
                <td>${escapeHtml(b.event_title)}</td>
                <td>${b.tickets}</td>
                <td>₹${Number(b.total_amount || 0).toLocaleString("en-IN")}</td>
                <td><span class="status-badge ${b.status}">${b.status}</span></td>
                <td>${formatDate(b.booking_time)}</td>
                <td><button class="action-icon-btn" title="View" onclick='viewBooking(${JSON.stringify(b)})'><i class="bi bi-eye"></i></button></td>
            </tr>
        `).join("");

        renderPagination(data.total, data.page, data.limit);

    } catch (error) {
        console.error("Load bookings error:", error);
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">Unable to load bookings.</td></tr>`;
    }
}

function renderPagination(total, page, limit) {
    const totalPages = Math.max(1, Math.ceil(total / limit));
    const container = document.getElementById("paginationControls");
    const summary = document.getElementById("paginationSummary");

    let buttons = `<button ${page <= 1 ? "disabled" : ""} onclick="loadBookings(${page - 1})"><i class="bi bi-chevron-left"></i></button>`;
    let start = Math.max(1, page - 2);
    let end = Math.min(totalPages, start + 4);
    start = Math.max(1, end - 4);
    for (let i = start; i <= end; i++) buttons += `<button class="${i === page ? "active" : ""}" onclick="loadBookings(${i})">${i}</button>`;
    buttons += `<button ${page >= totalPages ? "disabled" : ""} onclick="loadBookings(${page + 1})"><i class="bi bi-chevron-right"></i></button>`;

    container.innerHTML = buttons;
    const from = total === 0 ? 0 : (page - 1) * limit + 1;
    const to = Math.min(page * limit, total);
    summary.textContent = `Showing ${from} to ${to} of ${total} bookings`;
}

function viewBooking(booking) {
    viewingBookingId = booking.id;
    document.getElementById("viewBookingBody").innerHTML = `
        <p><strong>Booking ID:</strong> BK-${1000 + booking.id}</p>
        <p><strong>User:</strong> ${escapeHtml(booking.user_name)}</p>
        <p><strong>Event:</strong> ${escapeHtml(booking.event_title)}</p>
        <p><strong>Seats:</strong> ${booking.tickets}</p>
        <p><strong>Amount:</strong> ₹${Number(booking.total_amount || 0).toLocaleString("en-IN")}</p>
        <p><strong>Status:</strong> ${booking.status}</p>
        <p><strong>Date:</strong> ${formatDate(booking.booking_time)}</p>
    `;
    document.getElementById("cancelBookingBtn").style.display = booking.status === "cancelled" ? "none" : "inline-block";
    bootstrap.Modal.getOrCreateInstance(document.getElementById("viewBookingModal")).show();
}

document.getElementById("cancelBookingBtn").addEventListener("click", async () => {
    if (!viewingBookingId || !confirm("Cancel this booking? Inventory will be released.")) return;
    try {
        const res = await fetch(`${API_BASE}/admin/bookings/${viewingBookingId}`, { method: "DELETE", headers: authHeaders() });
        if (!res.ok) throw new Error();
        bootstrap.Modal.getOrCreateInstance(document.getElementById("viewBookingModal")).hide();
        loadBookings(currentPage);
    } catch (error) {
        alert("Unable to cancel booking.");
    }
});