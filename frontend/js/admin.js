"use strict";
/* Focused dashboard: all maintenance actions live on admin/pages/*.html. */
const API = window.Eventora.api;
const escapeAdmin = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const rupees = v => "₹" + Number(v || 0).toLocaleString("en-IN");
const adminDate = v => v ? new Date(v).toLocaleDateString("en-IN", {dateStyle:"medium"}) : "Date TBA";
const auth = () => ({Authorization: "Bearer " + window.Eventora.token()});
async function readAdmin(path) {
    const response = await fetch(API + path, {headers: auth()});
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(window.Eventora.error(data));
    }
    return response.json();
}
function tableRows(id, rows, empty, cells) {
    const tbody = document.getElementById(id);
    tbody.innerHTML = rows.length ? rows.map(record => `<tr>${cells(record).map(cell => `<td>${cell}</td>`).join("")}</tr>`).join("")
        : `<tr><td colspan="5" class="text-center text-muted py-4">${escapeAdmin(empty)}</td></tr>`;
}
async function loadAdminDashboard() {
    const status = document.getElementById("dashboardMessage");
    status.textContent = "Updating dashboard…";
    const results = await Promise.allSettled([
        readAdmin("/analytics/overview"),
        readAdmin("/events/admin/list?page=1&limit=5"),
        readAdmin("/admin/bookings/list?page=1&limit=5"),
        readAdmin("/admin/users/list?page=1&limit=5"),
        readAdmin("/analytics/bookings-by-month")
    ]);
    const [overview, events, bookings, users, monthly] = results.map(r => r.status === "fulfilled" ? r.value : null);
    const failed = results.filter(r => r.status === "rejected");
    if (overview) {
        document.getElementById("totalEvents").textContent = overview.total_events;
        document.getElementById("totalUsers").textContent = overview.total_users;
        document.getElementById("totalBookings").textContent = overview.total_bookings;
        document.getElementById("totalRevenue").textContent = rupees(overview.total_revenue);
    }
    if (events) tableRows("recentEventsTable", events.items || [], "No events yet", ev => [
        escapeAdmin(ev.title), escapeAdmin(ev.category || "—"), escapeAdmin(adminDate(ev.date_time)),
        ev.available_seats === null ? "Unlimited" : String(ev.available_seats ?? 0),
        `<a href="pages/admin_event.html" class="btn btn-sm btn-outline-primary">Manage</a>`]);
    if (bookings) tableRows("recentBookingsTable", bookings.items || [], "No bookings yet", b => [
        escapeAdmin(b.user_name), escapeAdmin(b.event_title), String(b.tickets || 0),
        `<a href="pages/admin_bookings.html">${escapeAdmin(b.status || "—")}</a>`]);
    if (users) tableRows("recentUsersTable", users.items || [], "No users yet", u => [
        escapeAdmin(u.full_name || u.username), escapeAdmin(u.email || "—"),
        escapeAdmin(u.role), escapeAdmin(adminDate(u.created_at))]);
    if (monthly && typeof Chart !== "undefined") {
        const canvas = document.getElementById("bookingsPerMonthChart");
        if (canvas) new Chart(canvas, {type:"bar",data:{labels:monthly.map(m=>m.month),datasets:[{label:"Bookings",data:monthly.map(m=>m.bookings)}]},options:{responsive:true}});
    }
    status.textContent = failed.length ? `${failed.length} dashboard sections could not load. Check API logs and your Aiven schema.`
        : `Updated ${new Date().toLocaleTimeString("en-IN")}`;
}
document.addEventListener("DOMContentLoaded", () => {
    const logout = document.querySelector(".logout-btn");
    logout?.addEventListener("click", () => {
        localStorage.removeItem("token");localStorage.removeItem("access_token");
        location.href = "../pages/login.html";
    });
    document.querySelector(".topbar .icon-btn")?.addEventListener("click", () => {location.href = "pages/admin_notifications.html";});
    const search = document.getElementById("adminEventSearch");
    search?.addEventListener("keydown", ev => {
        if (ev.key === "Enter") location.href = "pages/admin_event.html?q=" + encodeURIComponent(search.value.trim());
    });
    loadAdminDashboard().catch(error => {document.getElementById("dashboardMessage").textContent = error.message;});
});
