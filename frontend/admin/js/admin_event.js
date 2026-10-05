"use strict";

const API_BASE = "https://event-booking-api-gnww.onrender.com/api";   // apna backend URL confirm kar lena
let currentPage = 1;
let currentEditEventId = null;

function getToken() {
    return localStorage.getItem("token") || localStorage.getItem("access_token");
}

function authHeaders() {
    const token = getToken();
    return token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c]));
}

function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

document.addEventListener("DOMContentLoaded", () => {
    loadEvents(1);
    loadCategoryFilterOptions();
    document.getElementById("filterSearch").addEventListener("input", debounce(() => loadEvents(1), 400));
    document.getElementById("filterCategory").addEventListener("change", () => loadEvents(1));
    document.getElementById("filterStatus").addEventListener("change", () => loadEvents(1));
});

function debounce(fn, delay) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

// ---------------- LOAD EVENTS TABLE ----------------
async function loadEvents(page = 1) {
    currentPage = page;
    const search = document.getElementById("filterSearch").value.trim();
    const category = document.getElementById("filterCategory").value;
    const status = document.getElementById("filterStatus").value;

    const params = new URLSearchParams({ page, limit: 10 });
    if (search) params.append("title", search);
    if (category) params.append("category", category);
    if (status) params.append("status", status);

    const tbody = document.getElementById("eventsTableBody");
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">Loading...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/events/admin/list?${params.toString()}`, { headers: authHeaders() });
        if (res.status === 401) { window.location.href = "../../pages/login.html"; return; }
        const data = await res.json();

        if (!data.items || !data.items.length) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No events found.</td></tr>`;
            renderPagination(0, 1, 10);
            return;
        }

        tbody.innerHTML = data.items.map(event => `
            <tr>
                <td><img class="event-poster-thumb" src="${event.image_url || '../../images/event-placeholder.jpg'}" alt=""></td>
                <td>${escapeHtml(event.title)}</td>
                <td>${escapeHtml(event.category || "—")}</td>
                <td>${formatDate(event.date_time)}</td>
                <td>${event.available_seats}/${event.total_seats}</td>
                <td><span class="status-badge ${event.status || 'published'}">${event.status || 'published'}</span></td>
                <td>
                    <button class="action-icon-btn" title="View" onclick="window.open('../../pages/event-details.html?id=${event.id}', '_blank')"><i class="bi bi-eye"></i></button>
                    <button class="action-icon-btn" title="Edit" onclick="openEditEventModal(${event.id})"><i class="bi bi-pencil"></i></button>
                    <button class="action-icon-btn" title="Duplicate" onclick="duplicateEvent(${event.id})"><i class="bi bi-copy"></i></button>
                    <button class="action-icon-btn danger" title="Delete" onclick="deleteEvent(${event.id})"><i class="bi bi-trash"></i></button>
                </td>
            </tr>
        `).join("");

        renderPagination(data.total, data.page, data.limit);

    } catch (error) {
        console.error("Load events error:", error);
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">Unable to load events.</td></tr>`;
    }
}

// ---------------- PAGINATION ----------------
function renderPagination(total, page, limit) {
    const totalPages = Math.max(1, Math.ceil(total / limit));
    const container = document.getElementById("paginationControls");
    const summary = document.getElementById("paginationSummary");

    let buttons = `<button ${page <= 1 ? "disabled" : ""} onclick="loadEvents(${page - 1})"><i class="bi bi-chevron-left"></i></button>`;

    const maxButtons = 5;
    let start = Math.max(1, page - 2);
    let end = Math.min(totalPages, start + maxButtons - 1);
    start = Math.max(1, end - maxButtons + 1);

    for (let i = start; i <= end; i++) {
        buttons += `<button class="${i === page ? 'active' : ''}" onclick="loadEvents(${i})">${i}</button>`;
    }

    buttons += `<button ${page >= totalPages ? "disabled" : ""} onclick="loadEvents(${page + 1})"><i class="bi bi-chevron-right"></i></button>`;

    container.innerHTML = buttons;

    const shownFrom = total === 0 ? 0 : (page - 1) * limit + 1;
    const shownTo = Math.min(page * limit, total);
    summary.textContent = `Showing ${shownFrom} to ${shownTo} of ${total} events`;
}

// ---------------- CATEGORY FILTER + CREATE MODAL DROPDOWN ----------------
async function loadCategoryFilterOptions() {
    try {
        const res = await fetch(`${API_BASE}/engagement/categories`, { headers: authHeaders() });
        const categories = await res.json();

        const filterSelect = document.getElementById("filterCategory");
        categories.forEach(cat => {
            filterSelect.innerHTML += `<option value="${escapeHtml(cat.name)}">${escapeHtml(cat.name)}</option>`;
        });

        const modalSelect = document.getElementById("categorySelect");
        if (modalSelect) {
            modalSelect.innerHTML = categories.map(cat => `<option value="${cat.id}">${escapeHtml(cat.name)}</option>`).join("");
        }
    } catch (error) {
        console.error("Category load error:", error);
    }
}

// ---------------- CREATE EVENT ----------------
async function createEvent() {
    const title = document.getElementById("title").value.trim();
    const location = document.getElementById("location").value.trim();

    if (!title || !location) { alert("Title and location are required."); return; }

    const payload = {
        title,
        location,
        description: document.getElementById("description").value.trim() || null,
        price: Number(document.getElementById("price").value || 0),
        total_seats: Number(document.getElementById("seats").value || 0),
        date_time: document.getElementById("date").value || null,
        category_id: document.getElementById("categorySelect").value ? Number(document.getElementById("categorySelect").value) : null,
        age_limit: document.getElementById("ageLimit").value,
        duration: document.getElementById("duration").value.trim() || null,
        status: document.getElementById("statusSelect").value,
        inventory_type: document.getElementById("inventoryType").value
    };

    try {
        const res = await fetch(`${API_BASE}/events/`, { method: "POST", headers: authHeaders(), body: JSON.stringify(payload) });
        if (!res.ok) throw new Error("Failed to create event");
        bootstrap.Modal.getOrCreateInstance(document.getElementById("createEventModal")).hide();
        loadEvents(currentPage);
    } catch (error) {
        alert("Unable to create event.");
        console.error(error);
    }
}

// ---------------- EDIT EVENT ----------------
async function openEditEventModal(eventId) {
    try {
        const res = await fetch(`${API_BASE}/events/${eventId}`, { headers: authHeaders() });
        const event = await res.json();
        currentEditEventId = eventId;

        document.getElementById("edit_title").value = event.title || "";
        document.getElementById("edit_location").value = event.location || "";
        document.getElementById("edit_price").value = event.price || 0;
        document.getElementById("edit_seats").value = event.available_seats ?? event.total_seats;
        document.getElementById("edit_date").value = toDateTimeLocal(event.date_time);
        document.getElementById("edit_description").value = event.description || "";
        document.getElementById("edit_ageLimit").value = event.age_limit || "All Ages";
        document.getElementById("edit_duration").value = event.duration || "";
        document.getElementById("edit_status").value = event.status || "published";
        document.getElementById("edit_imagePreview").src = event.image_url || "../../images/event-placeholder.jpg";
        document.getElementById("edit_inventoryType").value = event.inventory_type || "general";
        updatePricingSectionVisibility(event.inventory_type || "general");
        if ((event.inventory_type || "general") === "zone") {
        await loadZonesForEvent(eventId);
           }
        loadTicketTypes(eventId);
        bootstrap.Modal.getOrCreateInstance(document.getElementById("editEventModal")).show();
    } catch (error) {
        alert("Unable to load event.");
        console.error(error);
    }
}

async function saveEditedEvent() {
    if (!currentEditEventId) return;

    const payload = {
        title: document.getElementById("edit_title").value.trim(),
        location: document.getElementById("edit_location").value.trim(),
        price: Number(document.getElementById("edit_price").value || 0),
        available_seats: Number(document.getElementById("edit_seats").value || 0),
        date_time: document.getElementById("edit_date").value || null,
        description: document.getElementById("edit_description").value.trim() || null,
        age_limit: document.getElementById("edit_ageLimit").value,
        duration: document.getElementById("edit_duration").value.trim() || null,
        status: document.getElementById("edit_status").value,
        inventory_type: document.getElementById("edit_inventoryType").value
    };

    try {
        const res = await fetch(`${API_BASE}/events/${currentEditEventId}`, { method: "PUT", headers: authHeaders(), body: JSON.stringify(payload) });
        if (!res.ok) throw new Error("Failed to update event");
        bootstrap.Modal.getOrCreateInstance(document.getElementById("editEventModal")).hide();
        currentEditEventId = null;
        loadEvents(currentPage);
    } catch (error) {
        alert("Unable to save changes.");
        console.error(error);
    }
}

function toDateTimeLocal(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return "";
    const pad = n => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// ---------------- TICKET TYPES ----------------
async function loadTicketTypes(eventId) {
    try {
        const res = await fetch(`${API_BASE}/events/${eventId}/ticket-types`, { headers: authHeaders() });
        const ticketTypes = await res.json();
        const container = document.getElementById("ticketTypesList");
        container.innerHTML = ticketTypes.length
            ? ticketTypes.map(tt => `
                <div class="d-flex justify-content-between align-items-center border border-secondary rounded px-2 py-1 mb-1">
                    <span>${escapeHtml(tt.name)} — ₹${tt.price} (${tt.inventory_limit ?? "Unlimited"})</span>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteTicketType(${tt.id})">×</button>
                </div>`).join("")
            : `<p class="text-muted small">No ticket types yet.</p>`;
    } catch (error) {
        console.error(error);
    }
}

async function addTicketType() {
    if (!currentEditEventId) return;
    const name = document.getElementById("newTicketName").value.trim();
    const price = Number(document.getElementById("newTicketPrice").value || 0);
    const limitRaw = document.getElementById("newTicketLimit").value.trim();

    if (!name) { alert("Ticket name is required."); return; }

    try {
        const res = await fetch(`${API_BASE}/events/${currentEditEventId}/ticket-types`, {
            method: "POST", headers: authHeaders(),
            body: JSON.stringify({ event_id: currentEditEventId, name, price, inventory_limit: limitRaw ? Number(limitRaw) : null })
        });
        if (!res.ok) throw new Error();
        document.getElementById("newTicketName").value = "";
        document.getElementById("newTicketPrice").value = "";
        document.getElementById("newTicketLimit").value = "";
        loadTicketTypes(currentEditEventId);
    } catch (error) {
        alert("Unable to add ticket type.");
    }
}

async function deleteTicketType(ticketTypeId) {
    try {
        await fetch(`${API_BASE}/events/ticket-types/${ticketTypeId}`, { method: "DELETE", headers: authHeaders() });
        loadTicketTypes(currentEditEventId);
    } catch (error) {
        alert("Unable to delete ticket type.");
    }
}

// ---------------- DUPLICATE / DELETE ----------------
async function duplicateEvent(eventId) {
    if (!confirm("Duplicate this event?")) return;
    try {
        const res = await fetch(`${API_BASE}/events/${eventId}/duplicate`, { method: "POST", headers: authHeaders() });
        if (!res.ok) throw new Error();
        loadEvents(currentPage);
    } catch (error) {
        alert("Unable to duplicate event.");
    }
}

async function deleteEvent(eventId) {
    if (!confirm("Delete this event? This cannot be undone.")) return;
    try {
        const res = await fetch(`${API_BASE}/events/${eventId}`, { method: "DELETE", headers: authHeaders() });
        if (!res.ok) throw new Error();
        loadEvents(currentPage);
    } catch (error) {
        alert("Unable to delete event.");
    }
}

let currentWizardStep = 1;
const totalWizardSteps = 5;

function showWizardStep(step) {
    document.querySelectorAll(".wizard-pane").forEach(pane => {
        pane.classList.toggle("active", Number(pane.dataset.pane) === step);
    });
    document.querySelectorAll(".wizard-step").forEach(stepEl => {
        const stepNum = Number(stepEl.dataset.step);
        stepEl.classList.toggle("active", stepNum === step);
        stepEl.classList.toggle("completed", stepNum < step);
    });
    document.getElementById("wizardBackBtn").textContent = step === 1 ? "Cancel" : "Back";
    document.getElementById("wizardNextBtn").textContent = step === totalWizardSteps ? "Save Changes" : "Next";
    currentWizardStep = step;
}

function wizardGoNext() {
    if (currentWizardStep === totalWizardSteps) {
        saveEditedEvent();       // last step ka "Next" button = Save
        return;
    }
    showWizardStep(currentWizardStep + 1);
}

function wizardGoBack() {
    if (currentWizardStep === 1) {
        bootstrap.Modal.getOrCreateInstance(document.getElementById("editEventModal")).hide();
        return;
    }
    showWizardStep(currentWizardStep - 1);
}


function updatePricingSectionVisibility(type) {
    document.getElementById("ticketTypesSection").style.display = type === "general" ? "block" : "none";
    document.getElementById("zonesSection").style.display = type === "zone" ? "block" : "none";
    document.getElementById("seatNotice").style.display = type === "seat" ? "block" : "none";
}

// Live-update jab admin dropdown badle modal khula rehte hue
document.getElementById("edit_inventoryType")?.addEventListener("change", async (e) => {
    updatePricingSectionVisibility(e.target.value);
    if (e.target.value === "zone" && currentEditEventId) {
        await loadZonesForEvent(currentEditEventId);
    }
});

let currentEventLayoutId = null;

async function loadZonesForEvent(eventId) {
    const container = document.getElementById("zonesList");
    container.innerHTML = `<p class="text-muted small">Loading...</p>`;

    try {
        let layoutRes = await fetch(`${API_BASE}/seating/admin/events/${eventId}/layout`, { headers: authHeaders() });

        if (layoutRes.status === 404) {
            const createRes = await fetch(`${API_BASE}/seating/admin/events/${eventId}/layout`, {
                method: "POST", headers: authHeaders(),
                body: JSON.stringify({ event_id: eventId, name: "Default Layout" })
            });
            if (!createRes.ok) throw new Error("Unable to initialize zone layout.");
            layoutRes = createRes;
        }

        const layout = await layoutRes.json();
        currentEventLayoutId = layout.id;

        const zonesRes = await fetch(`${API_BASE}/seating/admin/layouts/${layout.id}/zones`, { headers: authHeaders() });
        const zones = await zonesRes.json();

        container.innerHTML = zones.length
            ? zones.map(z => `
                <div class="d-flex justify-content-between align-items-center border border-secondary rounded px-2 py-1 mb-1">
                    <span>${escapeHtml(z.name)} (${escapeHtml(z.code)}) — ₹${z.base_price} · ${z.capacity} seats</span>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteZone(${z.id})">×</button>
                </div>`).join("")
            : `<p class="text-muted small">No zones yet.</p>`;

    } catch (error) {
        console.error("Load zones error:", error);
        container.innerHTML = `<p class="text-danger small">Unable to load zones.</p>`;
    }
}

async function addZone() {
    if (!currentEventLayoutId) { alert("Zone layout not ready yet, please wait."); return; }

    const name = document.getElementById("newZoneName").value.trim();
    const code = document.getElementById("newZoneCode").value.trim();
    const capacity = Number(document.getElementById("newZoneCapacity").value || 0);
    const price = Number(document.getElementById("newZonePrice").value || 0);

    if (!name || !code) { alert("Zone name and code are required."); return; }

    try {
        const res = await fetch(`${API_BASE}/seating/admin/layouts/${currentEventLayoutId}/zones`, {
            method: "POST", headers: authHeaders(),
            body: JSON.stringify({ event_id: currentEditEventId, layout_id: currentEventLayoutId, name, code, zone_type: "general", capacity, base_price: price })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to add zone.");

        document.getElementById("newZoneName").value = "";
        document.getElementById("newZoneCode").value = "";
        document.getElementById("newZoneCapacity").value = "";
        document.getElementById("newZonePrice").value = "";

        loadZonesForEvent(currentEditEventId);
    } catch (error) {
        alert(error.message);
    }
}

async function deleteZone(zoneId) {
    if (!confirm("Delete this zone?")) return;
    try {
        const res = await fetch(`${API_BASE}/seating/admin/zones/${zoneId}`, { method: "DELETE", headers: authHeaders() });
        if (!res.ok) throw new Error();
        loadZonesForEvent(currentEditEventId);
    } catch (error) {
        alert("Unable to delete zone.");
    }
}


// Clickable steps — direct jump bhi allow karo
document.querySelectorAll(".wizard-step").forEach(stepEl => {
    stepEl.addEventListener("click", () => showWizardStep(Number(stepEl.dataset.step)));
});

// Jab bhi edit modal khule, wizard ko step 1 pe reset karo
document.getElementById("editEventModal").addEventListener("show.bs.modal", () => showWizardStep(1));

// Image preview — file select hote hi turant dikhao
document.getElementById("edit_imageFile")?.addEventListener("change", function () {
    if (this.files && this.files[0]) {
        document.getElementById("edit_imagePreview").src = URL.createObjectURL(this.files[0]);
    }
});
