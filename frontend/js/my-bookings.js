"use strict";
const API_URL = (window.API_BASE_URL || ((["localhost", "127.0.0.1"].includes(location.hostname)) ? "http://127.0.0.1:8000" : window.location.origin)).replace(/\/$/, "") + "/api";
let allBookings = [];
const token = () => localStorage.getItem("token") || localStorage.getItem("access_token") || sessionStorage.getItem("token");
const escapeHtml = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const formatDate = v => v ? new Date(v).toLocaleString("en-IN", {dateStyle:"medium",timeStyle:"short"}) : "Date TBA";
const container = () => document.getElementById("bookingsContainer");
const authHeaders = () => ({Authorization: `Bearer ${token()}`, "Content-Type": "application/json"});
async function loadBookings() {
    if (!token()) { location.href="login.html"; return; }
    container().innerHTML = `<div class="col-12 text-center py-5">Loading your bookings...</div>`;
    try {
        const res = await fetch(`${API_URL}/bookings/my-bookings`, {headers:authHeaders()});
        if (res.status === 401) {location.href="login.html"; return;}
        if (!res.ok) throw new Error("Unable to load your bookings");
        allBookings = await res.json();
        renderBookings();
    } catch (error) { container().innerHTML = `<div class="col-12 text-center py-5 text-danger">${escapeHtml(error.message)}</div>`; }
}
function renderBookings() {
    const query = (document.getElementById("bookingSearchInput")?.value || "").toLowerCase().trim();
    const bookings = allBookings.filter(b => !query || `${b.id} ${b.event?.title||""} ${b.status}`.toLowerCase().includes(query));
    if (!bookings.length) {container().innerHTML=`<div class="col-12 text-center py-5">No matching bookings. <a href="events.html">Browse events</a></div>`;return;}
    container().innerHTML = bookings.map(b => {
        const evt = b.event || {};
        const held = b.status === "held" && b.expires_at && new Date(b.expires_at).getTime() > Date.now();
        const paid = b.status === "confirmed" && b.payment_status === "paid";
        const tickets = paid ? (b.ticket_details || []).map(t => `<div class="ticket-code-row"><strong>${escapeHtml(t.label)}</strong><span>Ticket code: ${escapeHtml(t.ticket_code)}</span></div>`).join("") : "";
        const action = paid ? `<a class="btn btn-primary w-100 mt-2" href="booking-confirmation.html?id=${b.id}">View ticket receipt</a>`
            : held ? `<div class="d-grid gap-2"><a class="btn btn-primary" href="booking-confirmation.html?id=${b.id}">Complete simulated checkout</a><button class="btn btn-outline-danger" data-cancel-booking="${b.id}">Release reservation</button></div>`
            : `<span class="text-muted">${escapeHtml(b.status)}</span>`;
        return `<div class="col-lg-4 col-md-6 mb-4"><article class="card text-white h-100">
            ${evt.image_url ? `<img class="booking-image" src="${escapeHtml(evt.image_url)}" alt="${escapeHtml(evt.title)}">` : `<div class="booking-image-placeholder">${escapeHtml(evt.title || "Event")}</div>`}
            <div class="card-body"><h5>${escapeHtml(evt.title || "Event")}</h5><p>${escapeHtml(formatDate(evt.date_time))}<br>${escapeHtml(evt.location || "Location TBA")}</p>
            <p><strong>${b.tickets}</strong> ticket(s) · ₹${Number(b.total_amount).toLocaleString("en-IN")}</p>
            <p>Booking #${b.id} · <strong>${escapeHtml(b.status)}</strong> · Payment: ${escapeHtml(b.payment_status)}</p>
            <div class="ticket-code-list">${tickets}</div>${action}</div></article></div>`;
    }).join("");
    document.querySelectorAll("[data-cancel-booking]").forEach(btn => btn.addEventListener("click",()=>cancelBooking(Number(btn.dataset.cancelBooking))));
}
async function cancelBooking(id) {
    if (!confirm("Release this unpaid reservation?")) return;
    try {
        const res = await fetch(`${API_URL}/bookings/book/${id}`, {method:"DELETE", headers: authHeaders()});
        const data = await res.json().catch(()=>({}));
        if (!res.ok) throw new Error(data.detail || "Unable to release reservation");
        await loadBookings();
    } catch (err) { alert(err.message); }
}
document.addEventListener("DOMContentLoaded", () => {
    loadBookings();
    document.getElementById("bookingSearchInput")?.addEventListener("input", renderBookings);
    document.getElementById("backBtn")?.addEventListener("click",()=>location.href="events.html");
});
