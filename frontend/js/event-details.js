const API_URL = "https://event-booking-api-gnww.onrender.com";

let eventData = null;

// ---------------- GET EVENT ID FROM URL ----------------
function getEventId() {
    const params = new URLSearchParams(window.location.search);
    return params.get("id");
}

// ---------------- LOAD EVENT ----------------
async function loadEvent() {
    const id = getEventId();
    const token = localStorage.getItem("token");

    const res = await fetch(`${API_URL}/events/${id}`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const data = await res.json();
    eventData = data;

    document.getElementById("title").innerText = data.title;
    document.getElementById("description").innerText = data.description;
    document.getElementById("location").innerText = data.location;
    document.getElementById("date").innerText = data.date;
    document.getElementById("price").innerText = data.price;
    document.getElementById("seats").innerText = data.available_seats;

    updateTotal();
}

// ---------------- PRICE CALCULATION ----------------
function updateTotal() {
    const qty = document.getElementById("quantity").value;
    const total = qty * eventData.price;
    document.getElementById("total").innerText = total;
}

document.getElementById("quantity").addEventListener("input", updateTotal);

// ---------------- BOOK EVENT ----------------
async function bookEvent() {
    const token = localStorage.getItem("token");
    const id = getEventId();
    const qty = parseInt(document.getElementById("quantity").value);

    if (qty > eventData.available_seats) {
        showMessage("Not enough seats", "danger");
        return;
    }

    const res = await fetch(`${API_URL}/book`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            event_id: id,
            tickets: qty
        })
    });

    const data = await res.json();

    if (res.ok) {
        showMessage("Booking successful!", "success");
         window.location.href = "my-bookings.html";

        // live update seats
        eventData.available_seats -= qty;
        document.getElementById("seats").innerText = eventData.available_seats;
    } else {
        showMessage(data.detail || "Booking failed", "danger");
    }
}

// ---------------- MESSAGE HANDLER ----------------
function showMessage(msg, type) {
    const el = document.getElementById("message");
    el.innerText = msg;
    el.className = `text-${type}`;
}

// ---------------- BACK ----------------
function goBack() {
    window.location.href = "events.html";
}

// ---------------- INIT ----------------
loadEvent();