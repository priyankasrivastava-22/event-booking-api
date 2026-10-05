"use strict";
// Enable strict JavaScript mode

const API_BASE_URL = window.API_BASE_URL || "http://127.0.0.1:8000";
// Backend API base URL

const eventId = new URLSearchParams(window.location.search).get("id");
// Read event ID from URL

let currentEvent = null;                                          // Store current event
let inventoryData = null;                                         // Store current inventory response
let selectedSeats = [];                                           // Store selected physical seats
let selectedZone = null;                                          // Store selected zone
let selectedTicketType = null;                                    // Store selected general-admission ticket type
let quantity = 1;                                                 // Store general/zone ticket quantity
let unitPrice = 0;                                                // Store the price of whatever is currently selected
let holdTimerInterval = null;                                     // Reference to the running countdown interval

document.addEventListener("DOMContentLoaded", () => {
    loadEventDetails();                                           // Load event + inventory once the page is ready
});

function getToken() {
    return localStorage.getItem("token") || localStorage.getItem("access_token") || sessionStorage.getItem("token") || sessionStorage.getItem("access_token");
    // Read token from every key used elsewhere in the app
}

function authHeaders() {
    const token = getToken();                                     // Read JWT token
    return token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

async function loadEventDetails() {
    if (!eventId) { showError("No event ID was provided."); return; }
    showLoading(true);                                            // Show spinner while fetching
    try {
        const eventResponse = await fetch(`${API_BASE_URL}/api/events/${eventId}`, { headers: authHeaders() });
        if (!eventResponse.ok) throw new Error(`Event request failed with status ${eventResponse.status}`);
        currentEvent = await eventResponse.json();                // Parse event
        renderEvent(currentEvent);                                // Render static event info
        await loadInventory();                                    // Then load and render inventory
        showLoading(false);                                       // Reveal content
    } catch (error) {
        console.error("Event details error:", error);
        showError(error.message || "Unable to load event details.");
    }
}

async function loadInventory() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/events/${eventId}/inventory`, { headers: authHeaders() });
        if (!response.ok) { console.warn("Inventory endpoint returned:", response.status); renderLegacyGeneralInventory(); return; }
        inventoryData = await response.json();                    // Parse inventory response
        renderInventory(inventoryData);                           // Render according to inventory_type
    } catch (error) {
        console.error("Inventory loading error:", error);
        renderLegacyGeneralInventory();                           // Fall back to the event's legacy price/seats
    }
}

function renderEvent(event) {
    document.getElementById("title").textContent = event.title || "Event";
    document.getElementById("description").textContent = event.description || "No description available.";
    document.getElementById("location").textContent = event.location || "Location not specified";
    document.getElementById("date").textContent = formatDate(event.date_time);
    const category = event.category_rel?.name || event.category || "Event";
    document.getElementById("categoryText").textContent = category;
    document.getElementById("categoryTag").textContent = category;
    document.getElementById("categoryStat").textContent = category;
    document.getElementById("eventTypeIcon").className = `bi ${getCategoryIcon(category)}`;   // naya — category ke hisaab se icon badlega
    const inventoryType = normalizeInventoryType(event.inventory_type);
    document.getElementById("inventoryTypeTag").textContent = inventoryTypeLabel(inventoryType);
    document.getElementById("eventImage").src = event.image_url || "../images/event-placeholder.jpg";
    document.getElementById("eventImage").alt = event.title || "Event";
    document.getElementById("ageLimitStat").textContent = event.age_limit || "All Ages";
    document.getElementById("durationStat").textContent = event.duration || "—";
    unitPrice = Number(event.price || 0);                         // Temporary base price until real inventory price loads
    syncTopPrice();                                                // FIX: keep the "Starting From" price in sync with unitPrice
    updateSummary();
}

function renderInventory(data) {
    const type = normalizeInventoryType(data.inventory_type || currentEvent?.inventory_type);
    inventoryData = data;
    document.getElementById("quantitySection").classList.toggle("d-none", type === "seat");   // Quantity stepper only applies to general/zone, not seat-map
    if (type === "seat") { renderSeatInventory(data); return; }
    if (type === "zone") { renderZoneInventory(data); return; }
    renderGeneralInventory(data);
}

/* ---------------- GENERAL ADMISSION ---------------- */

function renderGeneralInventory(data = {}) {
    document.getElementById("generalInventory").classList.remove("d-none");
    document.getElementById("zoneInventory").classList.add("d-none");
    document.getElementById("seatInventory").classList.add("d-none");
    document.getElementById("quantitySection").classList.remove("d-none");

    const tickets = Array.isArray(data.ticket_types) ? data.ticket_types : Array.isArray(data.ticketTypes) ? data.ticketTypes : [];
    const container = document.getElementById("generalTicketList");
    container.innerHTML = "";

    if (!tickets.length) {                                        // No ticket types configured at all
        selectedTicketType = null;
        unitPrice = Number(currentEvent?.price || 0);
        container.innerHTML = `<div class="empty-inventory">General admission is currently unavailable.</div>`;
        document.getElementById("quantitySection").classList.add("d-none");
        setAvailabilityUI(0, 0);
        syncTopPrice();
        updateSummary();
        return;
    }

    tickets.forEach((ticket, index) => {
        const available = getAvailableQuantity(ticket, ticket);
        const price = Number(ticket.price ?? currentEvent?.price ?? 0);
        const card = document.createElement("button");
        card.type = "button";
        card.className = "zone-option ticket-type-option";        // FIX: reuse the already-styled .zone-option look so this card is actually visible
        card.dataset.ticketTypeId = ticket.id ?? "";
        card.innerHTML = `<span><strong>${escapeHtml(ticket.name || `Ticket ${index + 1}`)}</strong><small>${available === null ? "Available" : `${available} available`}</small></span><strong>₹${price}</strong>`;
        card.disabled = available === 0;
        card.addEventListener("click", () => selectTicketType(ticket, price, card));
        container.appendChild(card);
    });

    const firstAvailable = tickets.find(t => getAvailableQuantity(t, t) !== 0) || tickets[0];   // FIX: auto-select a sensible default so quantity + total are never out of sync with nothing selected
    const firstCard = container.querySelector(`[data-ticket-type-id="${firstAvailable.id ?? ""}"]`);
    selectTicketType(firstAvailable, Number(firstAvailable.price ?? currentEvent?.price ?? 0), firstCard);

    const totalAvailable = tickets.reduce((sum, t) => { const a = getAvailableQuantity(t, t); return sum + (a === null ? 0 : Math.max(0, a)); }, 0);
    setAvailabilityUI(totalAvailable, tickets.length);
}

function selectTicketType(ticket, price, element) {
    document.querySelectorAll("#generalTicketList .zone-option").forEach(button => button.classList.remove("selected"));
    element?.classList.add("selected");
    selectedTicketType = ticket;
    unitPrice = Number(price || 0);
    quantity = 1;
    const input = document.getElementById("quantity");
    input.value = 1;
    const available = getAvailableQuantity(ticket, ticket);
    input.max = available !== null && available > 0 ? available : "";
    document.getElementById("generalTicketAvailability").textContent = available === null ? "Available" : `${available} available`;
    syncTopPrice();                                                // FIX: reflect the chosen ticket's price at the top of the page too
    updateSummary();
}

/* ---------------- ZONE ---------------- */

function renderZoneInventory(data) {
    document.getElementById("generalInventory").classList.add("d-none");
    document.getElementById("seatInventory").classList.add("d-none");
    document.getElementById("zoneInventory").classList.remove("d-none");
    document.getElementById("quantitySection").classList.remove("d-none");

    const zones = data.zones || data.items || data.event_zones || [];
    const zoneList = document.getElementById("zoneList");
    zoneList.innerHTML = "";

    if (!zones.length) {
        zoneList.innerHTML = `<div class="empty-inventory">No zones are currently available.</div>`;
        document.getElementById("quantitySection").classList.add("d-none");
        setAvailabilityUI(0, 0);
        return;
    }

    zones.forEach((zone, index) => {
        const available = getAvailableQuantity(zone, zone);
        const price = Number(zone.price ?? zone.base_price ?? currentEvent?.price ?? 0);
        const card = document.createElement("button");
        card.type = "button";
        card.className = "zone-option";
        card.dataset.zoneId = zone.id ?? "";
        card.innerHTML = `<span><strong>${escapeHtml(zone.name || zone.code || `Zone ${index + 1}`)}</strong><small>${available === null ? "Available" : `${available} available`}</small></span><strong>₹${price}</strong>`;
        card.disabled = available === 0;
        card.addEventListener("click", () => selectZone(zone, price, card));
        zoneList.appendChild(card);
    });

    const firstAvailable = zones.find(z => getAvailableQuantity(z, z) !== 0) || zones[0];   // FIX: auto-select a default zone, same reasoning as tickets
    const firstCard = zoneList.querySelector(`[data-zone-id="${firstAvailable.id ?? ""}"]`);
    selectZone(firstAvailable, Number(firstAvailable.price ?? firstAvailable.base_price ?? currentEvent?.price ?? 0), firstCard);

    const totalAvailable = zones.reduce((sum, z) => sum + (Number(getAvailableQuantity(z, z)) || 0), 0);
    setAvailabilityUI(totalAvailable, zones.length);
}

function selectZone(zone, price, element) {
    document.querySelectorAll("#zoneList .zone-option").forEach(button => button.classList.remove("selected"));
    element?.classList.add("selected");
    selectedZone = zone;
    unitPrice = Number(price || 0);
    quantity = 1;
    const input = document.getElementById("quantity");
    input.value = 1;
    const available = getAvailableQuantity(zone, zone);
    input.max = available !== null && available > 0 ? available : "";
    document.getElementById("generalTicketAvailability").textContent = available === null ? "Available" : `${available} available`;
    syncTopPrice();                                                // FIX: reflect the chosen zone's price at the top of the page too
    updateSummary();
}

/* ---------------- SEATS ---------------- */

function renderSeatInventory(data) {
    document.getElementById("generalInventory").classList.add("d-none");
    document.getElementById("zoneInventory").classList.add("d-none");
    document.getElementById("seatInventory").classList.remove("d-none");
    const seats = flattenSeats(data);
    const seatMap = document.getElementById("seatMap");
    seatMap.innerHTML = "";
    selectedSeats = [];
    const availableSeats = seats.filter(seat => normalizeSeatStatus(seat.status) === "available");
    setAvailabilityUI(availableSeats.length, seats.length);
    if (!seats.length) { seatMap.innerHTML = `<div class="empty-inventory">No seat inventory is currently available.</div>`; return; }
    const grouped = groupSeatsByRow(seats);
    Object.entries(grouped).forEach(([rowLabel, rowSeats]) => {
        const row = document.createElement("div");
        row.className = "seat-row";
        const label = document.createElement("span");
        label.className = "seat-row-label";
        label.textContent = rowLabel;
        row.appendChild(label);
        rowSeats.forEach(seat => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = `seat ${normalizeSeatStatus(seat.status)}`;
            button.textContent = seat.seat_number ?? seat.number ?? seat.seat_code ?? "?";
            button.title = `${seat.seat_code || `Seat ${button.textContent}`} - ₹${seat.price ?? currentEvent?.price ?? 0}`;
            button.disabled = normalizeSeatStatus(seat.status) !== "available";
            button.addEventListener("click", () => toggleSeat(seat, button));
            row.appendChild(button);
        });
        seatMap.appendChild(row);
    });
    unitPrice = Number(currentEvent?.price || 0);                 // Base price shown until the user selects at least one seat
    syncTopPrice();
    updateSummary();
}

function toggleSeat(seat, button) {
    const existingIndex = selectedSeats.findIndex(item => item.id === seat.id);
    if (existingIndex >= 0) { selectedSeats.splice(existingIndex, 1); button.classList.remove("selected"); }
    else { const price = Number(seat.price ?? currentEvent?.price ?? 0); selectedSeats.push({ id: seat.id, seat_code: seat.seat_code, price, zone_id: seat.zone_id }); button.classList.add("selected"); }
    unitPrice = selectedSeats.length ? selectedSeats.reduce((sum, s) => sum + s.price, 0) / selectedSeats.length : Number(currentEvent?.price || 0);
    quantity = selectedSeats.length;
    document.getElementById("selectedSeatText").textContent = selectedSeats.length ? `${selectedSeats.length} seat${selectedSeats.length > 1 ? "s" : ""} selected` : "No seats selected";
    document.getElementById("selectedSeatCount").textContent = selectedSeats.length;
    syncTopPrice();
    updateSummary();
}

/* ---------------- QUANTITY ---------------- */

function changeQuantity(change) {
    const input = document.getElementById("quantity");
    const max = Number(input.max || 999999);
    const next = Math.max(1, Math.min(max, Number(input.value || 1) + change));
    input.value = next;
    quantity = next;
    updateSummary();
}

document.addEventListener("input", event => {
    if (event.target.id === "quantity") {
        const value = Math.max(1, Number(event.target.value || 1));
        event.target.value = value;
        quantity = value;
        updateSummary();
    }
});

/* ---------------- SUMMARY / PRICE SYNC ---------------- */

function syncTopPrice() {
    const priceEl = document.getElementById("price");             // FIX: guard this — the top price card was removed from the UI, so this element may no longer exist
    if (priceEl) priceEl.textContent = Number(unitPrice || 0).toFixed(0);
}

function updateSummary() {
    const count = selectedSeats.length || quantity || 0;
    const total = selectedSeats.length ? selectedSeats.reduce((sum, seat) => sum + Number(seat.price || 0), 0) : Number(unitPrice || 0) * Number(quantity || 0);
    const averagePrice = count > 0 ? total / count : Number(unitPrice || 0);
    document.getElementById("ticketCount").textContent = count;
    document.getElementById("priceSummary").textContent = averagePrice.toFixed(0);       // FIX: no "₹" here — the HTML already has a static ₹ next to this span
    document.getElementById("total").textContent = Math.max(0, total).toFixed(0);        // FIX: same — avoid the doubled ₹₹ symbol
}

function setAvailabilityUI(availableCount, totalCount) {
    const status = availableCount > 0 ? "Available" : "Sold Out";
    const seatsEl = document.getElementById("seats");
    if (seatsEl) seatsEl.textContent = availableCount || (availableCount === 0 ? "0" : "Available");
    const availabilityStatusEl = document.getElementById("availabilityStatus");
    if (availabilityStatusEl) availabilityStatusEl.textContent = status;
    const eventStatusTagEl = document.getElementById("eventStatusTag");
    if (eventStatusTagEl) eventStatusTagEl.textContent = status;
    const ticketStatusEl = document.getElementById("ticketStatus");             // FIX: guarded — this id no longer exists after the stats-card redesign
    if (ticketStatusEl) ticketStatusEl.textContent = status;
    const percent = totalCount > 0 ? Math.max(4, Math.round((availableCount / totalCount) * 100)) : (availableCount > 0 ? 100 : 0);
    const progressEl = document.getElementById("availabilityProgress");
    if (progressEl) { progressEl.style.width = `${percent}%`; progressEl.classList.toggle("low", percent <= 20); }
}

/* ---------------- BOOKING ---------------- */

async function bookEvent() {
    const button = document.getElementById("bookButton");
    if (!button) { console.error("bookButton not found"); return; }
    const inventoryType = normalizeInventoryType(currentEvent?.inventory_type);

    if (inventoryType === "seat" && selectedSeats.length === 0) { showMessage("Please select your seats before continuing.", true); focusBookingSection(); return; }
    if (inventoryType === "zone" && !selectedZone) { showMessage("Please select a zone before continuing.", true); focusBookingSection(); return; }
    if (inventoryType === "general" && !selectedTicketType) { showMessage("Please select a ticket type before continuing.", true); focusBookingSection(); return; }

    const count = selectedSeats.length || quantity;
    if (!count || count < 1) { showMessage("Please select at least one ticket.", true); return; }

    button.disabled = true;
    button.textContent = "Holding inventory...";

    try {
        const payload = buildBookingPayload();
        const response = await fetch(`${API_BASE_URL}/api/bookings`, { method: "POST", headers: authHeaders(), body: JSON.stringify(payload) });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || data.message || "Unable to hold inventory.");

        if (data.id) sessionStorage.setItem("eventora_booking_id", data.id);
        if (data.expires_at) sessionStorage.setItem("eventora_booking_expires_at", data.expires_at);
        sessionStorage.removeItem("eventora_booking_request_key");

        if (data.expires_at) startHoldCountdown(data.expires_at);            // Show the countdown immediately, in case the redirect below is delayed
        showMessage("Tickets held successfully. Continuing to checkout...", false);

        setTimeout(() => {
            window.location.href = data.id ? `booking-confirmation.html?id=${data.id}` : "my-bookings.html";
        }, 700);

    } catch (error) {
        console.error("Inventory hold error:", error);
        showMessage(error.message || "Unable to hold inventory.", true);
        button.disabled = false;
        button.textContent = "Continue Booking";
    }
}

function buildBookingPayload() {
    const count = selectedSeats.length || quantity;
    const total = selectedSeats.length ? selectedSeats.reduce((sum, seat) => sum + Number(seat.price || 0), 0) : unitPrice * count;
    const idempotencyKey = sessionStorage.getItem("eventora_booking_request_key") || crypto.randomUUID();
    sessionStorage.setItem("eventora_booking_request_key", idempotencyKey);
    const payload = { event_id: Number(eventId), tickets: count, total_amount: Math.round(total), idempotency_key: idempotencyKey };
    if (selectedSeats.length) { payload.seat_ids = selectedSeats.map(seat => seat.id); return payload; }
    if (selectedZone?.id) { payload.zone_id = Number(selectedZone.id); return payload; }
    if (selectedTicketType?.id) { payload.ticket_type_id = Number(selectedTicketType.id); return payload; }
    throw new Error("Please select a ticket, zone, or seat.");
}

function renderLegacyGeneralInventory() {
    const available = Number(currentEvent?.available_seats ?? currentEvent?.total_seats ?? 0);
    renderGeneralInventory({ ticket_types: [{ id: null, name: "General Admission", price: Number(currentEvent?.price || 0), available }] });
    // FIX: wraps in ticket_types array (not the old singular ticket_type) so it goes through the SAME card-rendering path as real inventory, instead of a separate silent fallback
}

/* ---------------- HOLD COUNTDOWN ---------------- */

function startHoldCountdown(expiresAt) {
    const timer = document.getElementById("holdTimer");
    const timerText = document.getElementById("holdTimerText");
    if (!timer || !expiresAt) return;
    if (holdTimerInterval) clearInterval(holdTimerInterval);
    timer.classList.remove("d-none");
    timer.classList.add("active");
    function updateTimer() {
        const remaining = new Date(expiresAt).getTime() - Date.now();
        if (remaining <= 0) { clearInterval(holdTimerInterval); timerText.textContent = "Your ticket hold has expired."; timer.classList.add("urgent"); return; }
        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        timerText.textContent = `Tickets reserved for ${minutes}:${String(seconds).padStart(2, "0")}`;
        timer.classList.toggle("urgent", remaining <= 60000);
    }
    updateTimer();
    holdTimerInterval = setInterval(updateTimer, 1000);
}

/* ---------------- HELPERS ---------------- */

function flattenSeats(data) {
    if (Array.isArray(data.seats)) return data.seats;
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.sections)) return data.sections.flatMap(section => section.seats || []);
    if (Array.isArray(data.zones)) return data.zones.flatMap(zone => zone.seats || []);
    return [];
}

function groupSeatsByRow(seats) {
    return seats.reduce((groups, seat) => {
        const row = seat.row_label || seat.row?.row_label || seat.row_number || seat.row_id || "Row";
        if (!groups[row]) groups[row] = [];
        groups[row].push(seat);
        return groups;
    }, {});
}

function getAvailableQuantity(primary, secondary) {
    const values = [primary?.available, primary?.available_count, primary?.available_seats, primary?.remaining, secondary?.available, secondary?.available_count, secondary?.available_seats, secondary?.remaining];
    const found = values.find(value => value !== undefined && value !== null);
    return found === undefined ? null : Number(found);
}

function normalizeInventoryType(type) {
    const value = String(type || "general").toLowerCase();
    if (value === "seat" || value === "seated") return "seat";
    if (value === "zone") return "zone";
    return "general";
}

function inventoryTypeLabel(type) {
    if (type === "seat") return "Reserved Seating";
    if (type === "zone") return "Zone Admission";
    return "General Admission";
}

function normalizeSeatStatus(status) {
    const value = String(status || "available").toLowerCase();
    if (value === "sold") return "sold";
    if (value === "locked") return "locked";
    if (value === "available") return "available";
    return "inactive";
}

function formatDate(value) {
    if (!value) return "Date not specified";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[character]));
}

function focusBookingSection() { document.getElementById("inventoryCard")?.scrollIntoView({ behavior: "smooth", block: "center" }); }

function goBack() { if (document.referrer) history.back(); else window.location.href = "events.html"; }

function toggleFavourite() { document.getElementById("favIcon").classList.toggle("bi-heart"); document.getElementById("favIcon").classList.toggle("bi-heart-fill"); }

async function shareEvent() {
    const shareData = { title: currentEvent?.title || "Eventora Event", text: `Check out ${currentEvent?.title || "this event"} on Eventora.`, url: window.location.href };
    try { if (navigator.share) await navigator.share(shareData); else { await navigator.clipboard.writeText(window.location.href); showMessage("Event link copied.", false); } }
    catch (error) { console.debug("Share cancelled.", error); }
}

function showLoading(show) {
    document.getElementById("loadingState").classList.toggle("d-none", !show);
    document.getElementById("eventContent").classList.toggle("d-none", show);
    document.getElementById("errorState").classList.add("d-none");
}

function showError(message) {
    document.getElementById("loadingState").classList.add("d-none");
    document.getElementById("eventContent").classList.add("d-none");
    document.getElementById("errorState").classList.remove("d-none");
    document.getElementById("errorMessage").textContent = message;
}

function showMessage(message, error = false) {
    const element = document.getElementById("message");
    element.textContent = message;
    element.className = `booking-message ${error ? "is-error" : "is-success"}`;   // FIX: matches the .is-error/.is-success classes actually defined in the CSS
}

function getCategoryIcon(category) {                                       // Return the right Bootstrap icon class for a category, matching events.html's category-grid
    const value = String(category || "").toLowerCase();
    if (value.includes("music") || value.includes("concert")) return "bi-music-note-beamed";
    if (value.includes("sport")) return "bi-trophy";
    if (value.includes("tech")) return "bi-cpu";
    if (value.includes("business")) return "bi-briefcase";
    if (value.includes("education")) return "bi-mortarboard";
    if (value.includes("health")) return "bi-heart-pulse";
    if (value.includes("comedy")) return "bi-emoji-laughing";
    if (value.includes("festival")) return "bi-stars";
    return "bi-calendar-event";                                            // fallback for anything unmatched
}