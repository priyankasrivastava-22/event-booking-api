// event-details.js

const API_URL = "https://event-booking-api-gnww.onrender.com/api";
let eventData = null;

function getParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        id: params.get("id"),
        img: params.get("img")
    };
}

async function loadEvent() {
    const { id, img } = getParams();
    const token = localStorage.getItem("token");

    const eventImgElement = document.getElementById("eventImage");

    if (img) {
        eventImgElement.src = decodeURIComponent(img);
    } else {
        eventImgElement.src = "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=800";
    }

    try {
        const res = await fetch(`${API_URL}/events/events/${id}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!res.ok) throw new Error("Event not found");

        const data = await res.json();
        eventData = data;

        document.getElementById("title").innerText = data.title;
        document.getElementById("description").innerText = data.description;
        document.getElementById("location").innerText = data.location;
        document.getElementById("date").innerText = data.date;
        document.getElementById("price").innerText = data.price;
        document.getElementById("seats").innerText = data.available_seats;

        updateTotal();
        loadUser();
        loadNotificationCount();
        checkFavourite();

    } catch (err) {
        showMessage("Failed to load event details.", "danger");
    }
}

function updateTotal() {
    const qtyInput = document.getElementById("quantity");
    if (!eventData || !qtyInput) return;

    const qty = parseInt(qtyInput.value) || 1;
    document.getElementById("total").innerText = qty * eventData.price;
}

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
            body: JSON.stringify({
                event_id: parseInt(id),
                tickets: qty
            })
        });

        const data = await res.json();

        if (res.ok) {
            showMessage("Booking successful! Redirecting...", "success");
            setTimeout(() => {
                window.location.href = "my-bookings.html";
            }, 2000);
        } else {
            showMessage(data.detail || "Booking failed", "danger");
        }

    } catch {
        showMessage("Connection error", "danger");
    }
}

function showMessage(msg, type) {
    const el = document.getElementById("message");
    el.innerText = msg;
    el.className = `mt-2 text-${type} fw-bold`;
}

function goBack() {
    window.location.href = "events.html";
}

function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

function loadUser() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        document.getElementById("nav-username").innerText = payload.sub || "User";
    } catch {}
}

async function loadNotificationCount() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/engagement/my-notifications`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        const data = await res.json();
        const badge = document.getElementById("notifCount");

        const count = Array.isArray(data) ? data.length : 0;
        badge.innerText = count;
        badge.style.display = count ? "inline-block" : "none";

    } catch {}
}

function toggleFavourite() {
    const { id } = getParams();

    let favs = JSON.parse(localStorage.getItem("favourites")) || [];

    if (favs.includes(id)) {
        favs = favs.filter(x => x !== id);
    } else {
        favs.push(id);
    }

    localStorage.setItem("favourites", JSON.stringify(favs));
    checkFavourite();
}

function checkFavourite() {
    const { id } = getParams();

    const favs = JSON.parse(localStorage.getItem("favourites")) || [];
    const icon = document.getElementById("favIcon");

    if (favs.includes(id)) {
        icon.className = "bi bi-heart-fill text-danger";
    } else {
        icon.className = "bi bi-heart";
    }
}

async function shareEvent() {
    const url = window.location.href;
    const title = document.getElementById("title").innerText || "Event";

    if (navigator.share) {
        await navigator.share({
            title: title,
            text: "Check this event",
            url: url
        });
    } else {
        await navigator.clipboard.writeText(url);
        alert("Event link copied");
    }
}

document.getElementById("quantity")?.addEventListener("input", updateTotal);
document.addEventListener("DOMContentLoaded", loadEvent);