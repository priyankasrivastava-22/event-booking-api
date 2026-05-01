const API_URL = "https://event-booking-api-gnww.onrender.com/api";
let eventData = null;

// 1. URL se ID aur Image nikalne ke liye
function getParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        id: params.get("id"),
        img: params.get("img")
    };
}

// 2. Load Event Details
async function loadEvent() {
    const { id, img } = getParams();
    const token = localStorage.getItem("token");

    // Pehle hi image set kar dete hain jo URL se aayi hai
    const eventImgElement = document.getElementById("eventImage");
    if (img) {
        eventImgElement.src = decodeURIComponent(img);
    } else {
        eventImgElement.src = "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=800"; // Default image
    }

    try {
        const res = await fetch(`${API_URL}/events/events/${id}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!res.ok) throw new Error("Event not found");

        const data = await res.json();
        eventData = data;

        // UI Update
        document.getElementById("title").innerText = data.title;
        document.getElementById("description").innerText = data.description;
        document.getElementById("location").innerText = data.location;
        document.getElementById("date").innerText = data.date;
        document.getElementById("price").innerText = data.price;
        document.getElementById("seats").innerText = data.available_seats;

        updateTotal();
    } catch (err) {
        console.error("Error loading event:", err);
        showMessage("Failed to load event details.", "danger");
    }
}

// 3. Price Calculation
function updateTotal() {
    const qtyInput = document.getElementById("quantity");
    if (!eventData || !qtyInput) return;

    const qty = parseInt(qtyInput.value) || 1;
    const total = qty * eventData.price;
    document.getElementById("total").innerText = total;
}

// 4. Booking Logic
async function bookEvent() {
    const token = localStorage.getItem("token");
    const { id } = getParams();
    const qty = parseInt(document.getElementById("quantity").value);

    if (!eventData || qty > eventData.available_seats) {
        showMessage("Not enough seats available", "danger");
        return;
    }

    try {
        const res = await fetch(`${API_URL}/bookings/book`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ event_id: parseInt(id), tickets: qty })
        });

        const data = await res.json();

        if (res.ok) {
            showMessage("Booking successful! Redirecting...", "success");
            setTimeout(() => { window.location.href = "my-bookings.html"; }, 2000);
        } else {
            showMessage(data.detail || "Booking failed", "danger");
        }
    } catch (err) {
        showMessage("Connection error", "danger");
    }
}

function showMessage(msg, type) {
    const el = document.getElementById("message");
    if (el) {
        el.innerText = msg;
        el.className = `mt-2 text-${type} fw-bold`;
    }
}

function goBack() {
    window.location.href = "events.html";
}

// Listeners
document.getElementById("quantity")?.addEventListener("input", updateTotal);

// Initialize
document.addEventListener("DOMContentLoaded", loadEvent);