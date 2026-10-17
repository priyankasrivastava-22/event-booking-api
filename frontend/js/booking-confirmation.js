"use strict";
// Enable strict mode

// Set window.API_BASE_URL before this script to override for your deployment.
const API_BASE_URL = window.API_BASE_URL ||
    ((["localhost", "127.0.0.1"].includes(window.location.hostname))
        ? "http://127.0.0.1:8000"
        : window.location.origin);
// Backend API base URL — same default as event-details.js

const bookingId = new URLSearchParams(window.location.search).get("id");
// Read booking ID from ?id= query param, set by event-details.js on redirect

let currentBooking = null;
// Holds the last fetched booking status response

let currentEventData = null;
// Holds the fetched event (for title/date/location/image)

let countdownInterval = null;
// Reference to the running setInterval so it can be cleared

document.addEventListener("DOMContentLoaded", () => {
// Kick things off once the DOM is ready
    loadBooking();
// Fetch booking + event and render the page
});
// End init

function getToken() {
// Return stored authentication token
    return localStorage.getItem("token") || localStorage.getItem("access_token") || sessionStorage.getItem("token") || sessionStorage.getItem("access_token");
// Read token from the same keys event-details.js checks
}
// End getToken

function authHeaders() {
// Build authenticated request headers
    const token = getToken();
// Read JWT token
    return token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
// Return headers, with or without auth
}
// End authHeaders

async function loadBooking() {
// Load booking status and the related event, then render
    if (!bookingId) {
// Validate booking ID is present in the URL
        showError("No booking ID was provided.");
// Show error state
        return;
// Stop loading
    }
// End validation
    document.getElementById("loadingState").classList.remove("d-none");
// Show loading spinner
    document.getElementById("errorState").classList.add("d-none");
// Hide any previous error
    document.getElementById("confirmContent").classList.add("d-none");
// Hide content while (re)loading
    try {
// Start fetch sequence
        const res = await fetch(`${API_BASE_URL}/api/bookings/${bookingId}/status`, { headers: authHeaders() });
// Fetch booking status (returns id/status/total_amount/expires_at/event_id/tickets)
        if (res.status === 401) { window.location.href = "login.html"; return; }
// Redirect to login if the session has expired
        if (!res.ok) {
// Handle not-found / not-owned booking
            const data = await res.json().catch(() => ({}));
// Try to parse error body
            throw new Error(data.detail || "Booking not found.");
// Raise a readable error
        }
// End status check
        currentBooking = await res.json();
// Store booking status response
        const eventRes = await fetch(`${API_BASE_URL}/api/events/${currentBooking.event_id}`, { headers: authHeaders() });
// Fetch the related event for title/date/location/image
        currentEventData = eventRes.ok ? await eventRes.json() : null;
// Store event data if it loaded successfully, otherwise render without it
        renderBooking();
// Render everything now that data is available
    } catch (error) {
// Handle any failure in the sequence above
        console.error("Booking load error:", error);
// Log for debugging
        showError(error.message || "Unable to load this booking.");
// Show a readable error to the user
    }
// End try/catch
}
// End loadBooking

function showError(message) {
// Show the error state with a message
    document.getElementById("loadingState").classList.add("d-none");
// Hide loading spinner
    document.getElementById("confirmContent").classList.add("d-none");
// Hide content
    document.getElementById("errorState").classList.remove("d-none");
// Show error block
    document.getElementById("errorMessage").textContent = message;
// Set error text
}
// End showError

function renderBooking() {
// Populate the page from currentBooking + currentEventData
    document.getElementById("loadingState").classList.add("d-none");
// Hide loading spinner
    document.getElementById("confirmContent").classList.remove("d-none");
// Reveal content

    document.getElementById("bookingIdText").textContent = `#${currentBooking.id}`;
// Show booking reference
    document.getElementById("ticketQtyText").textContent = currentBooking.tickets ?? "—";
// Show ticket quantity
    document.getElementById("totalAmountText").textContent = Number(currentBooking.total_amount || 0).toFixed(0);
// Show total amount
    document.getElementById("payAmountText").textContent = Number(currentBooking.total_amount || 0).toFixed(0);
    document.getElementById("selectedItems").innerHTML = (currentBooking.items || []).map(item =>
        `<div class="summary-row"><span>${escapeHtml(item.label)} × ${item.quantity}</span><span>₹${Number(item.subtotal).toLocaleString("en-IN")}</span></div>`
    ).join("");
// Mirror amount onto the pay button

    if (currentEventData) {
// Fill in event details only if the event fetch succeeded
        document.getElementById("eventTitleText").textContent = currentEventData.title || "—";
// Show event title
        document.getElementById("eventDateText").textContent = formatDate(currentEventData.date_time);
// Show formatted date/time
        document.getElementById("eventLocationText").textContent = currentEventData.location || "—";
// Show location
        document.getElementById("snapshotTitle").textContent = currentEventData.title || "Event";
// Show title on the snapshot card
        document.getElementById("snapshotCategory").textContent = currentEventData.category || "";
// Show category on the snapshot card
        if (currentEventData.image_url) document.getElementById("snapshotImage").src = currentEventData.image_url;
// Use the real event image when available, otherwise keep the placeholder
    }
// End event data check

    const status = String(currentBooking.status || currentBooking.payment_status || "").toLowerCase();
// Normalize booking status for comparisons below

    if (status === "confirmed" || status === "success" || status === "paid") {
// Booking is already finalized — nothing left to pay
        showConfirmedState();
// Show the success screen
        return;
// Stop here, no timer needed
    }
// End confirmed branch

    if (status === "expired" || status === "cancelled" || status === "failed") {
// Hold already expired or booking failed before the user got here
        showExpiredState();
// Show the expired banner
        return;
// Stop here
    }
// End expired branch

    document.getElementById("expiredState").classList.add("d-none");
    document.getElementById("successSection").classList.add("d-none");
    document.getElementById("paymentSection").classList.toggle("d-none", status !== "held");
    if (status !== "held") { showError("This checkout has no active inventory hold."); return; }
// Show the payment step only for a real held booking
    // The API is authoritative about whether simulated checkout is permitted.
    configureCheckout().catch(() => {
        document.getElementById("paymentSection").classList.add("d-none");
        const message = document.getElementById("checkoutUnavailable");
        if (message) { message.classList.remove("d-none"); message.textContent = "Checkout status is unavailable. Check your API connection."; }
    });
    startHoldCountdown(currentBooking.expires_at);
// Start (or skip, if no expiry) the countdown timer
}
// End renderBooking

async function configureCheckout() {
    const response = await fetch(`${API_BASE_URL}/api/config/public`);
    if (!response.ok) throw new Error("Could not load payment configuration");
    const configuration = await response.json();
    const demo = configuration.checkout_mode === "demo" && configuration.payment_methods?.includes("mock");
    document.getElementById("paymentSection").classList.toggle("d-none", !demo);
    const message = document.getElementById("checkoutUnavailable");
    if (message) {
        message.classList.toggle("d-none", demo);
        message.textContent = demo ? "" : "Checkout is disabled for this database. Use an isolated test database and enable demo checkout, or integrate a verified payment provider before taking payments.";
    }
}

function startHoldCountdown(expiresAt) {
// Run a live countdown against the booking's hold expiry
    if (!expiresAt) return;
// Nothing to count down if the backend didn't send an expiry
    const timerEl = document.getElementById("holdTimer");
// Timer pill element
    const countdownEl = document.getElementById("holdCountdown");
// Countdown text element
    timerEl.classList.add("active");
// Reveal the timer pill
    const expiryTime = new Date(expiresAt).getTime();
// Parse expiry into a timestamp
    if (countdownInterval) clearInterval(countdownInterval);
    if (!Number.isFinite(expiryTime) || expiryTime <= Date.now()) { showExpiredState(); return; }
// Clear any previous interval before starting a new one
    countdownInterval = setInterval(() => {
// Tick every second
        const remainingMs = expiryTime - Date.now();
// Milliseconds left until expiry
        if (remainingMs <= 0) {
// Countdown has reached zero
            clearInterval(countdownInterval);
// Stop ticking
            showExpiredState();
// Switch to the expired state
            return;
// Stop this tick
        }
// End expiry check
        const totalSeconds = Math.floor(remainingMs / 1000);
// Convert to whole seconds
        const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
// Format minutes with leading zero
        const seconds = String(totalSeconds % 60).padStart(2, "0");
// Format seconds with leading zero
        countdownEl.textContent = `${minutes}:${seconds}`;
// Update the visible countdown
        timerEl.classList.toggle("urgent", totalSeconds <= 60);
// Switch to red/urgent styling under a minute
    }, 1000);
// Run every 1000ms
}
// End startHoldCountdown

function showExpiredState() {
// Show the expired-hold banner and disable payment
    document.getElementById("holdTimer").classList.remove("active");
// Hide the countdown pill
    document.getElementById("expiredState").classList.remove("d-none");
// Reveal the expired banner
    document.getElementById("paymentSection").classList.add("d-none");
// Hide the payment step, nothing left to pay for
}
// End showExpiredState

function showConfirmedState() {
// Show the final success screen
    document.getElementById("holdTimer").classList.remove("active");
// Hide the countdown pill, booking is already secured
    document.getElementById("paymentSection").classList.add("d-none");
// Hide the payment step
    document.getElementById("successSection").classList.remove("d-none");
    document.getElementById("expiredState").classList.add("d-none");
    const tickets = currentBooking?.ticket_details || [];
    document.getElementById("issuedTickets").innerHTML = tickets.length
        ? tickets.map(ticket => `<div class="issued-ticket"><strong>${escapeHtml(ticket.label)}</strong><span>Ticket: ${escapeHtml(ticket.ticket_code)}</span><span>₹${Number(ticket.price_paid).toLocaleString("en-IN")}</span></div>`).join("")
        : `<p class="text-muted">Your issued tickets will appear in My Bookings.</p>`;
    document.getElementById("transactionText").textContent = currentBooking?.payment?.transaction_id
        ? `Demo payment reference: ${currentBooking.payment.transaction_id}` : "";
// Reveal confirmed ticket details
}
// End showConfirmedState

async function confirmPayment() {
// Submit payment for the current held booking
    const button = document.getElementById("payButton");
// Pay button reference
    const message = document.getElementById("paymentMessage");
// Message paragraph reference
    const method = document.querySelector('input[name="paymentMethod"]:checked')?.value || "mock";
// Read selected payment method
    button.disabled = true;
// Prevent duplicate clicks while the request is in flight
    button.textContent = "Simulating checkout...";
// Update button label
    message.textContent = "";
// Clear any previous message
    message.className = "booking-message";
// Reset message styling
    try {
// Start payment request
        const res = await fetch(`${API_BASE_URL}/api/payment/`, { method: "POST", headers: authHeaders(), body: JSON.stringify({ booking_id: Number(bookingId), method }) });
// Call the payment endpoint with the booking ID and chosen method
        const data = await res.json().catch(() => ({}));
// Parse response body
        if (!res.ok) throw new Error(data.detail || "Demo checkout could not be completed.");
// Surface backend validation errors (e.g. hold already expired)
        await loadBooking();
// Re-fetch the authoritative issued tickets and payment receipt after confirmation
    } catch (error) {
// Handle payment failure
        console.error("Payment error:", error);
// Log for debugging
        message.textContent = error.message || "Demo checkout failed. Please try again.";
// Show the failure reason
        message.classList.add("is-error");
// Style as an error
        const statusRes = await fetch(`${API_BASE_URL}/api/bookings/${bookingId}/status`, {headers: authHeaders()}).catch(() => null);
        if (statusRes?.ok) {
            currentBooking = await statusRes.json();
            if (currentBooking.status === "confirmed") { await loadBooking(); return; }
            if (currentBooking.status === "expired") { showExpiredState(); return; }
        }
        button.disabled = false;
// Re-enable the button only if checkout is still held
        button.textContent = `Confirm demo booking ₹${document.getElementById("payAmountText").textContent}`;
// Restore the button label
    }
// End try/catch
}
// End confirmPayment

function formatDate(value) {
// Format an event date/time string for display
    if (!value) return "Date not specified";
// Handle missing date
    const date = new Date(value);
// Parse date
    if (Number.isNaN(date.getTime())) return value;
// Fall back to raw value if unparsable
    return date.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
// Return localized date string, matching event-details.js's formatDate
}
// End formatDate
function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
}
