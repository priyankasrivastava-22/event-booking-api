"use strict";
// Enable strict JavaScript mode

const API_BASE_URL = window.API_BASE_URL || "http://127.0.0.1:8000";
// Backend API base URL

const eventId = new URLSearchParams(window.location.search).get("id");
// Read event ID from URL

let currentEvent = null;
// Store current event

let inventoryData = null;
// Store current inventory

let selectedSeats = [];
// Store selected physical seats

let selectedZone = null;
// Store selected zone

let selectedTicketType = null;
// Store selected ticket type

let quantity = 1;
// Store general admission quantity

let unitPrice = 0;
// Store current unit price

document.addEventListener("DOMContentLoaded", () => {
// Initialize page after DOM loads
    loadEventDetails();
// Load event and inventory
});
// End initialization

function getToken() {
// Return stored authentication token
    return localStorage.getItem("token") || localStorage.getItem("access_token") || sessionStorage.getItem("token") || sessionStorage.getItem("access_token");
// Read token from common storage keys
}
// End getToken

function authHeaders() {
// Build authenticated request headers
    const token = getToken();
// Read JWT token
    return token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
// Return headers
}
// End authHeaders

async function loadEventDetails() {
// Load event and inventory information
    if (!eventId) {
// Validate event ID
        showError("No event ID was provided.");
// Show error
        return;
// Stop execution
    }
// End validation
    showLoading(true);
// Show loading state
    try {
// Start request handling
        const eventResponse = await fetch(`${API_BASE_URL}/api/events/${eventId}`, { headers: authHeaders() });
// Request event details
        if (!eventResponse.ok) throw new Error(`Event request failed with status ${eventResponse.status}`);
// Validate event response
        currentEvent = await eventResponse.json();
// Parse event response
        renderEvent(currentEvent);
// Render event details
        await loadInventory();
// Load inventory after event
        showLoading(false);
// Show content
    } catch (error) {
// Handle request failure
        console.error("Event details error:", error);
// Log error
        showError(error.message || "Unable to load event details.");
// Show user-friendly error
    }
// End try/catch
}
// End loadEventDetails

async function loadInventory() {
// Load inventory for the event
    try {
// Start inventory request
        const response = await fetch(`${API_BASE_URL}/api/events/${eventId}/inventory`, { headers: authHeaders() });
// Request inventory
        if (!response.ok) {
// Handle unavailable inventory endpoint
            console.warn("Inventory endpoint returned:", response.status);
// Log backend response
            renderLegacyGeneralInventory();
// Fall back to event-level inventory
            return;
// Stop inventory request
        }
// End response validation
        inventoryData = await response.json();
// Parse inventory response
        renderInventory(inventoryData);
// Render inventory
    } catch (error) {
// Handle inventory failure
        console.error("Inventory loading error:", error);
// Log inventory error
        renderLegacyGeneralInventory();
// Use event-level fallback
    }
// End try/catch
}
// End loadInventory

function renderEvent(event) {
// Populate event information
    document.getElementById("title").textContent = event.title || "Event";
// Set title
    document.getElementById("description").textContent = event.description || "No description available.";
// Set description
    document.getElementById("location").textContent = event.location || "Location not specified";
// Set location
    document.getElementById("date").textContent = formatDate(event.date_time);
// Set date
    const category = event.category_rel?.name || event.category || "Event";
// Resolve category
    document.getElementById("categoryText").textContent = category;
// Set category badge
    document.getElementById("categoryTag").textContent = category;
// Set category tag
    document.getElementById("categoryStat").textContent = category;
// Set category statistic
    const inventoryType = normalizeInventoryType(event.inventory_type);
// Resolve inventory type
    document.getElementById("inventoryTypeTag").textContent = inventoryTypeLabel(inventoryType);
// Set inventory label
    const image = event.image_url || "../images/event-placeholder.jpg";
// Resolve image
    document.getElementById("eventImage").src = image;
// Set event image
    document.getElementById("eventImage").alt = event.title || "Event";
// Set image accessibility
    unitPrice = Number(event.price || 0);
// Set legacy/base price
    updateSummary();
// Update price summary
}
// End renderEvent

function renderInventory(data) {
// Render new inventory model
    const type = normalizeInventoryType(data.inventory_type || currentEvent?.inventory_type);
// Resolve backend inventory type
    inventoryData = data;
// Save inventory response
    if (type === "seat") {
// Render physical seats
        renderSeatInventory(data);
// Stop further rendering
        return;
// End seat condition
    }
// End inventory type condition
    if (type === "zone") {
// Render zones
        renderZoneInventory(data);
// Stop further rendering
        return;
// End zone condition
    }
// End zone condition
    renderGeneralInventory(data);
// Render general admission
}
// End renderInventory
function renderGeneralInventory(data = {}) {
    // Show general inventory section
    document.getElementById("generalInventory").classList.remove("d-none");

    // Hide other inventory types
    document.getElementById("zoneInventory").classList.add("d-none");
    document.getElementById("seatInventory").classList.add("d-none");

    // Read all ticket types from backend
    const tickets =
        Array.isArray(data.ticket_types)
            ? data.ticket_types
            : Array.isArray(data.ticketTypes)
                ? data.ticketTypes
                : [];

    const container = document.getElementById("generalTicketList");

    // If the new container exists, render all ticket types
    if (container) {
        container.innerHTML = "";

        if (!tickets.length) {
            selectedTicketType = null;
            unitPrice = Number(currentEvent?.price || 0);

            container.innerHTML = `
                <div class="empty-inventory">
                    General admission is currently unavailable.
                </div>
            `;

            document.getElementById("seats").textContent = "0";
            document.getElementById("availabilityStatus").textContent = "Sold Out";

            updateSummary();
            return;
        }

        tickets.forEach((ticket, index) => {
            const available = getAvailableQuantity(ticket, ticket);
            const price = Number(ticket.price ?? currentEvent?.price ?? 0);

            const card = document.createElement("button");

            card.type = "button";
            card.className = "ticket-type-option";
            card.dataset.ticketTypeId = ticket.id ?? "";

            card.innerHTML = `
                <div class="ticket-type-info">
                    <strong>${escapeHtml(ticket.name || `Ticket ${index + 1}`)}</strong>
                    <small>
                        ${
                            available === null
                                ? "Available"
                                : `${available} available`
                        }
                    </small>
                </div>

                <strong>₹${price}</strong>
            `;

            card.disabled = available === 0;

            card.addEventListener("click", () => {
                selectTicketType(ticket, price, card);
            });

            container.appendChild(card);
        });

        // Do not automatically select a ticket.
        selectedTicketType = null;

        document.getElementById("generalTicketName").textContent =
            "Select ticket type";

        document.getElementById("generalTicketAvailability").textContent =
            "Choose a ticket type";

        document.getElementById("quantity").value = 1;
        document.getElementById("quantity").max = "";

        quantity = 1;
        unitPrice = 0;

        const totalAvailable = tickets.reduce((sum, ticket) => {
            const available = getAvailableQuantity(ticket, ticket);
            return sum + (available === null ? 0 : Math.max(0, available));
        }, 0);

        document.getElementById("seats").textContent =
            totalAvailable || "Available";

        document.getElementById("capacityLabel").textContent =
            "Available";

        document.getElementById("availabilityStatus").textContent =
            totalAvailable > 0 ? "Available" : "Sold Out";

        updateSummary();

        return;
    }

    /*
     * Backward compatibility:
     * If old HTML does not have #generalTicketList,
     * use the first ticket type.
     */
    const ticket =
        tickets[0] ||
        data.ticket_type ||
        data.ticketType ||
        null;

    selectedTicketType = ticket;

    const eventPrice = Number(currentEvent?.price || 0);

    unitPrice = Number(ticket?.price ?? eventPrice);

    document.getElementById("generalTicketName").textContent =
        ticket?.name || "General Admission";

    const available = getAvailableQuantity(ticket, data);

    document.getElementById("generalTicketAvailability").textContent =
        available === null
            ? "Available"
            : `${available} available`;

    document.getElementById("seats").textContent =
        available === null ? "Available" : available;

    document.getElementById("capacityLabel").textContent =
        "Available";

    document.getElementById("availabilityStatus").textContent =
        available === 0 ? "Sold Out" : "Available";

    const input = document.getElementById("quantity");

    input.max =
        available !== null && available > 0
            ? available
            : "";

    if (available === 0) {
        input.value = 0;
    } else {
        input.value = 1;
    }

    quantity = Math.max(1, Number(input.value || 1));

    updateSummary();
}

function selectTicketType(ticket, price, element) {
    // Remove previous selection
    document
        .querySelectorAll(".ticket-type-option")
        .forEach(button => {
            button.classList.remove("selected");
        });

    // Highlight selected ticket
    element.classList.add("selected");

    // Store selected ticket type
    selectedTicketType = ticket;

    // Store price
    unitPrice = Number(price || 0);

    // Reset quantity
    quantity = 1;

    const input = document.getElementById("quantity");

    input.value = 1;

    // Set availability
    const available = getAvailableQuantity(ticket, ticket);

    input.max =
        available !== null && available > 0
            ? available
            : "";

    // Update displayed ticket information
    document.getElementById("generalTicketName").textContent =
        ticket.name || "Ticket";

    document.getElementById("generalTicketAvailability").textContent =
        available === null
            ? "Available"
            : `${available} available`;

    document.getElementById("availabilityStatus").textContent =
        available === 0
            ? "Sold Out"
            : "Available";

    updateSummary();
}

function renderZoneInventory(data) {
// Render zone inventory
    document.getElementById("generalInventory").classList.add("d-none");
// Hide general inventory
    document.getElementById("seatInventory").classList.add("d-none");
// Hide seats
    document.getElementById("zoneInventory").classList.remove("d-none");
// Show zones
    const zones = data.zones || data.items || data.event_zones || [];
// Read zones
    const zoneList = document.getElementById("zoneList");
// Get zone container
    zoneList.innerHTML = "";
// Clear old zones
    if (!zones.length) {
// Handle no zones
        zoneList.innerHTML = `<div class="empty-inventory">No zones are currently available.</div>`;
// Show empty state
        document.getElementById("availabilityStatus").textContent = "Sold Out";
// Update status
        return;
// Stop rendering
    }
// End empty condition
    zones.forEach((zone, index) => {
// Render each zone
        const available = getAvailableQuantity(zone, zone);
// Calculate availability
        const price = Number(zone.price ?? zone.base_price ?? currentEvent?.price ?? 0);
// Resolve zone price
        const card = document.createElement("button");
// Create zone selection button
        card.type = "button";
// Set button type
        card.className = "zone-option";
// Apply responsive zone style
        card.dataset.zoneId = zone.id ?? "";
// Store zone ID
        card.innerHTML = `<span><strong>${escapeHtml(zone.name || zone.code || `Zone ${index + 1}`)}</strong><small>${available === null ? "Available" : `${available} available`}</small></span><strong>₹${price}</strong>`;
// Build zone content
        card.disabled = available === 0;
// Disable sold-out zones
        card.addEventListener("click", () => selectZone(zone, price, card));
// Select zone
        zoneList.appendChild(card);
// Add zone to DOM
    });
// End zone loop
    document.getElementById("seats").textContent = zones.reduce((sum, zone) => sum + (Number(getAvailableQuantity(zone, zone)) || 0), 0) || "Available";
// Show total availability
    document.getElementById("availabilityStatus").textContent = zones.some(zone => getAvailableQuantity(zone, zone) !== 0) ? "Available" : "Sold Out";
// Set availability status
}
// End renderZoneInventory

function selectZone(zone, price, element) {
// Select a zone
    document.querySelectorAll(".zone-option").forEach(button => button.classList.remove("selected"));
// Clear old zone selection
    element.classList.add("selected");
// Highlight selected zone
    selectedZone = zone;
// Store zone
    unitPrice = price;
// Store price
    quantity = 1;
// Reset quantity
    document.getElementById("quantity").value = 1;
// Update quantity field
    document.getElementById("generalInventory").classList.remove("d-none");
// Show quantity selector
    document.getElementById("generalTicketName").textContent = zone.name || zone.code || "Zone";
// Set zone name
    const available = getAvailableQuantity(zone, zone);
// Get availability
    document.getElementById("generalTicketAvailability").textContent = available === null ? "Available" : `${available} available`;
// Set zone availability
    document.getElementById("quantity").max = available || "";
// Set quantity maximum
    updateSummary();
// Update summary
}
// End selectZone

function renderSeatInventory(data) {
// Render physical seat inventory
    document.getElementById("generalInventory").classList.add("d-none");
// Hide general inventory
    document.getElementById("zoneInventory").classList.add("d-none");
// Hide zones
    document.getElementById("seatInventory").classList.remove("d-none");
// Show seat inventory
    const seats = flattenSeats(data);
// Normalize seat response
    const seatMap = document.getElementById("seatMap");
// Get seat map
    seatMap.innerHTML = "";
// Clear old seats
    selectedSeats = [];
// Reset selected seats
    const availableSeats = seats.filter(seat => normalizeSeatStatus(seat.status) === "available");
// Find available seats
    document.getElementById("seats").textContent = availableSeats.length;
// Set available count
    document.getElementById("availabilityStatus").textContent = availableSeats.length ? "Available" : "Sold Out";
// Set status
    if (!seats.length) {
// Handle empty seat response
        seatMap.innerHTML = `<div class="empty-inventory">No seat inventory is currently available.</div>`;
// Show empty state
        return;
// Stop rendering
    }
// End empty condition
    const grouped = groupSeatsByRow(seats);
// Group seats by row
    Object.entries(grouped).forEach(([rowLabel, rowSeats]) => {
// Render each row
        const row = document.createElement("div");
// Create row
        row.className = "seat-row";
// Apply row style
        const label = document.createElement("span");
// Create row label
        label.className = "seat-row-label";
// Apply row label style
        label.textContent = rowLabel;
// Set row label
        row.appendChild(label);
// Add row label
        rowSeats.forEach(seat => {
// Render seats
            const button = document.createElement("button");
// Create seat button
            button.type = "button";
// Set button type
            button.className = `seat ${normalizeSeatStatus(seat.status)}`;
// Apply seat state
            button.textContent = seat.seat_number ?? seat.number ?? seat.seat_code ?? "?";
// Show seat number
            button.title = `${seat.seat_code || `Seat ${button.textContent}`} - ₹${seat.price ?? currentEvent?.price ?? 0}`;
// Set seat tooltip
            button.disabled = normalizeSeatStatus(seat.status) !== "available";
// Disable unavailable seats
            button.addEventListener("click", () => toggleSeat(seat, button));
// Add selection handler
            row.appendChild(button);
// Add seat to row
        });
// End seat loop
        seatMap.appendChild(row);
// Add row to map
    });
// End row loop
    updateSummary();
// Update summary
}
// End renderSeatInventory

function flattenSeats(data) {
// Normalize seats from multiple supported response shapes
    if (Array.isArray(data.seats)) return data.seats;
// Direct seats response
    if (Array.isArray(data.items)) return data.items;
// Inventory items response
    if (Array.isArray(data.sections)) return data.sections.flatMap(section => section.seats || []);
// Section-based response
    if (Array.isArray(data.zones)) return data.zones.flatMap(zone => zone.seats || []);
// Zone-based response
    return [];
// Empty fallback
}
// End flattenSeats

function groupSeatsByRow(seats) {
// Group physical seats by row
    return seats.reduce((groups, seat) => {
// Reduce seat list
        const row = seat.row_label || seat.row?.row_label || seat.row_number || seat.row_id || "Row";
// Resolve row
        if (!groups[row]) groups[row] = [];
// Initialize row
        groups[row].push(seat);
// Add seat
        return groups;
// Return groups
    }, {});
}
// End groupSeatsByRow

function toggleSeat(seat, button) {
// Toggle physical seat selection
    const seatId = seat.id;
// Resolve seat ID
    const existingIndex = selectedSeats.findIndex(item => item.id === seatId);
// Find current selection
    if (existingIndex >= 0) {
// Remove selected seat
        selectedSeats.splice(existingIndex, 1);
// Remove from selected list
        button.classList.remove("selected");
// Remove visual selection
    } else {
// Add selected seat
        const price = Number(seat.price ?? currentEvent?.price ?? 0);
// Resolve seat price
        selectedSeats.push({ id: seat.id, seat_code: seat.seat_code, price, zone_id: seat.zone_id });
// Store selected seat
        button.classList.add("selected");
// Add visual selection
    }
// End selection
    unitPrice = selectedSeats.length ? selectedSeats.reduce((sum, seatItem) => sum + seatItem.price, 0) / selectedSeats.length : Number(currentEvent?.price || 0);
// Calculate display unit price
    quantity = selectedSeats.length;
// Set selected quantity
    document.getElementById("selectedSeatText").textContent = selectedSeats.length ? `${selectedSeats.length} seat${selectedSeats.length > 1 ? "s" : ""} selected` : "No seats selected";
// Update selected seat text
    updateSummary();
// Update summary
}
// End toggleSeat

function changeQuantity(change) {
// Change general admission quantity
    const input = document.getElementById("quantity");
// Get quantity field
    const max = Number(input.max || 999999);
// Resolve maximum
    const next = Math.max(1, Math.min(max, Number(input.value || 1) + change));
// Calculate next quantity
    input.value = next;
// Update input
    quantity = next;
// Store quantity
    updateSummary();
// Update summary
}
// End changeQuantity

document.addEventListener("input", event => {
// Listen for quantity changes
    if (event.target.id === "quantity") {
// Check quantity field
        const value = Math.max(1, Number(event.target.value || 1));
// Normalize quantity
        event.target.value = value;
// Update input
        quantity = value;
// Store quantity
        updateSummary();
// Update summary
    }
// End quantity check
});
// End input listener

function updateSummary() {
    const count =
        selectedSeats.length ||
        quantity ||
        0;

    let total = 0;

    if (selectedSeats.length) {
        total = selectedSeats.reduce(
            (sum, seat) =>
                sum + Number(seat.price || 0),
            0
        );
    } else {
        total =
            Number(unitPrice || 0) *
            Number(quantity || 0);
    }

    const averagePrice =
        count > 0
            ? total / count
            : 0;

    document.getElementById(
        "ticketCount"
    ).textContent = count;

    document.getElementById(
        "priceSummary"
    ).textContent =
        `₹${averagePrice.toFixed(0)}`;

    document.getElementById(
        "total"
    ).textContent =
        `₹${Math.max(0, total).toFixed(0)}`;
}

async function bookEvent() {
    const button = document.getElementById("bookButton");

    if (!button) {
        console.error("bookButton not found");
        return;
    }

    const inventoryType =
        normalizeInventoryType(
            currentEvent?.inventory_type
        );

    // Validate fixed seats
    if (
        inventoryType === "seat" &&
        selectedSeats.length === 0
    ) {
        showMessage(
            "Please select your seats before continuing.",
            true
        );

        focusBookingSection();
        return;
    }

    // Validate zone
    if (
        inventoryType === "zone" &&
        !selectedZone
    ) {
        showMessage(
            "Please select a zone before continuing.",
            true
        );

        focusBookingSection();
        return;
    }

    // Validate general/pass
    if (
        inventoryType === "general" &&
        !selectedTicketType
    ) {
        showMessage(
            "Please select a ticket type before continuing.",
            true
        );

        focusBookingSection();
        return;
    }

    const count =
        selectedSeats.length || quantity;

    if (!count || count < 1) {
        showMessage(
            "Please select at least one ticket.",
            true
        );

        return;
    }

    button.disabled = true;
    button.textContent = "Holding inventory...";

    try {
        const payload =
            buildBookingPayload();

        console.log(
            "Creating inventory hold:",
            payload
        );

        const response = await fetch(
            `${API_BASE_URL}/api/bookings`,
            {
                method: "POST",
                headers: authHeaders(),
                body: JSON.stringify(payload)
            }
        );

        const data =
            await response
                .json()
                .catch(() => ({}));

        if (!response.ok) {
            throw new Error(
                data.detail ||
                data.message ||
                "Unable to hold inventory."
            );
        }

        // Save booking ID
        if (data.id) {
            sessionStorage.setItem(
                "eventora_booking_id",
                data.id
            );
        }

        // Save expiry
        if (data.expires_at) {
            sessionStorage.setItem(
                "eventora_booking_expires_at",
                data.expires_at
            );
        }

        // Request is complete, allow a fresh idempotency key
        sessionStorage.removeItem(
            "eventora_booking_request_key"
        );

        showMessage(
            "Tickets held successfully. Continuing to checkout...",
            false
        );

        setTimeout(() => {
            if (data.id) {
                window.location.href =
                    `booking-confirmation.html?id=${data.id}`;
            } else {
                window.location.href =
                    "my-bookings.html";
            }
        }, 700);

    } catch (error) {
        console.error(
            "Inventory hold error:",
            error
        );

        showMessage(
            error.message ||
            "Unable to hold inventory.",
            true
        );

        button.disabled = false;
        button.textContent =
            "Continue Booking";
    }
}

function buildBookingPayload() {
    const count = selectedSeats.length || quantity;

    const total = selectedSeats.length
        ? selectedSeats.reduce(
            (sum, seat) => sum + Number(seat.price || 0),
            0
        )
        : unitPrice * count;

    const idempotencyKey =
        sessionStorage.getItem("eventora_booking_request_key") ||
        crypto.randomUUID();

    sessionStorage.setItem(
        "eventora_booking_request_key",
        idempotencyKey
    );

    const payload = {
        event_id: Number(eventId),
        tickets: count,
        total_amount: Math.round(total),
        idempotency_key: idempotencyKey
    };

    // Fixed-seat event
    if (selectedSeats.length) {
        payload.seat_ids =
            selectedSeats.map(seat => seat.id);

        return payload;
    }

    // Zone event
    if (selectedZone?.id) {
        payload.zone_id =
            Number(selectedZone.id);

        return payload;
    }

    // General/pass event
    if (selectedTicketType?.id) {
        payload.ticket_type_id =
            Number(selectedTicketType.id);

        return payload;
    }

    throw new Error(
        "Please select a ticket, zone, or seat."
    );
}

function renderLegacyGeneralInventory() {
// Use event-level inventory when inventory endpoint is unavailable
    const available = Number(currentEvent?.available_seats ?? currentEvent?.total_seats ?? 0);
// Read legacy availability
    renderGeneralInventory({ ticket_type: { name: "General Admission", price: Number(currentEvent?.price || 0), inventory_limit: available } });
// Render general inventory
}
// End fallback

function getAvailableQuantity(primary, secondary) {
// Resolve availability from backend response
    const values = [primary?.available, primary?.available_count, primary?.available_seats, primary?.remaining, secondary?.available, secondary?.available_count, secondary?.available_seats, secondary?.remaining];
// Collect possible fields
    const found = values.find(value => value !== undefined && value !== null);
// Find first supported value
    return found === undefined ? null : Number(found);
// Return availability
}
// End getAvailableQuantity

function normalizeInventoryType(type) {
// Normalize backend inventory type
    const value = String(type || "general").toLowerCase();
// Normalize string
    if (value === "seat" || value === "seated") return "seat";
// Physical seat inventory
    if (value === "zone") return "zone";
// Zone inventory
    return "general";
// General admission
}
// End normalizeInventoryType

function inventoryTypeLabel(type) {
// Convert backend inventory type to display text
    if (type === "seat") return "Reserved Seating";
// Seat label
    if (type === "zone") return "Zone Admission";
// Zone label
    return "General Admission";
// General label
}
// End inventoryTypeLabel

function normalizeSeatStatus(status) {
// Normalize seat status
    const value = String(status || "available").toLowerCase();
// Normalize state
    if (value === "sold") return "sold";
// Sold state
    if (value === "locked") return "locked";
// Locked state
    if (value === "available") return "available";
// Available state
    return "inactive";
// Unknown state
}
// End normalizeSeatStatus

function formatDate(value) {
// Format event date and time
    if (!value) return "Date not specified";
// Empty date fallback
    const date = new Date(value);
// Parse date
    if (Number.isNaN(date.getTime())) return value;
// Return original invalid value
    return date.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
// Return localized date
}
// End formatDate

function escapeHtml(value) {
// Escape dynamic text before inserting HTML
    return String(value ?? "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[character]));
// Return escaped text
}
// End escapeHtml

function focusBookingSection() {
// Scroll to booking area
    document.getElementById("inventoryCard")?.scrollIntoView({ behavior: "smooth", block: "center" });
// Scroll smoothly
}
// End focusBookingSection

function goBack() {
// Return to event listing
    if (document.referrer) history.back();
// Use browser history
    else window.location.href = "events.html";
// Fallback events page
}
// End goBack

function toggleFavourite() {
// Toggle favourite visual state
    const icon = document.getElementById("favIcon");
// Find favourite icon
    icon.classList.toggle("bi-heart");
// Toggle empty heart
    icon.classList.toggle("bi-heart-fill");
// Toggle filled heart
}
// End toggleFavourite

async function shareEvent() {
// Share current event
    const shareData = { title: currentEvent?.title || "Eventora Event", text: `Check out ${currentEvent?.title || "this event"} on Eventora.`, url: window.location.href };
// Build share information
    try {
// Start share
        if (navigator.share) await navigator.share(shareData);
// Use native share
        else {
// Use clipboard fallback
            await navigator.clipboard.writeText(window.location.href);
// Copy URL
            showMessage("Event link copied.", false);
// Show confirmation
        }
// End share fallback
    } catch (error) {
// Handle cancelled share
        console.debug("Share cancelled.", error);
// Log harmless cancellation
    }
// End try/catch
}
// End shareEvent

function showLoading(show) {
// Toggle loading/content state
    document.getElementById("loadingState").classList.toggle("d-none", !show);
// Toggle loader
    document.getElementById("eventContent").classList.toggle("d-none", show);
// Toggle content
    document.getElementById("errorState").classList.add("d-none");
// Hide error
}
// End showLoading

function showError(message) {
// Display error state
    document.getElementById("loadingState").classList.add("d-none");
// Hide loading
    document.getElementById("eventContent").classList.add("d-none");
// Hide content
    document.getElementById("errorState").classList.remove("d-none");
// Show error
    document.getElementById("errorMessage").textContent = message;
// Set error message
}
// End showError

function showMessage(message, error = false) {
// Display booking status
    const element = document.getElementById("message");
// Get message element
    element.textContent = message;
// Set message
    element.className = `booking-message ${error ? "error" : "success"}`;
// Set message state
}
// End showMessage

let holdTimerInterval = null;

function startHoldCountdown(expiresAt) {
    const timer = document.getElementById("holdTimer");

    if (!timer || !expiresAt) {
        return;
    }

    if (holdTimerInterval) {
        clearInterval(holdTimerInterval);
    }

    timer.classList.remove("d-none");

    function updateTimer() {
        const expiry =
            new Date(expiresAt).getTime();

        const remaining =
            expiry - Date.now();

        if (remaining <= 0) {
            clearInterval(holdTimerInterval);

            timer.textContent =
                "Your ticket hold has expired.";

            timer.classList.add("expired");

            return;
        }

        const minutes =
            Math.floor(
                remaining / 60000
            );

        const seconds =
            Math.floor(
                (remaining % 60000) / 1000
            );

        timer.textContent =
            `Tickets reserved for ${minutes}:${String(seconds).padStart(2, "0")}`;
    }

    updateTimer();

    holdTimerInterval =
        setInterval(updateTimer, 1000);
}