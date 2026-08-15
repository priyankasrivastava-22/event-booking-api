const API_URL = "https://event-booking-api-gnww.onrender.com/api";
function getToken() {                                                          /* Check login token */
    const token = localStorage.getItem("token");
    if (!token) {
        alert("Please login first");
        window.location.href = "login.html";
        return null;
    }
    return token;
}

async function loadBookings() {                                                   /* Load all bookings */
    const token = getToken();
    if (!token) return;
    try {
        const res = await fetch(`${API_URL}/bookings/my-bookings`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });
        if (res.status === 401) {                                                   /* Handle expired session */
            alert("Session expired. Please login again.");
            localStorage.removeItem("token");
            window.location.href = "login.html";
            return;
        }
        const container = document.getElementById("bookingsContainer");
        if (!container) return;
        container.innerHTML = "";
        if (!res.ok) {                                                               /* Handle failed response */
            container.innerHTML = `
                <div class="col-12 text-center text-white py-5">
                    <h5>Unable to load bookings</h5>
                </div>
            `;
            return;
        }
        const data = await res.json();
        console.log("MY BOOKINGS RESPONSE:", data);
        if (!Array.isArray(data) || data.length === 0) {                              /* Show empty state */
            container.innerHTML = `
                <div class="col-12 text-center text-white py-5">
                    <h5>No bookings yet</h5>
                </div>
            `;
            return;
        }

       data.forEach(b => {                                                        /* Render booking cards */
       console.log("BOOKING:", b.id);
       console.log("EVENT:", b.event);
       const imageUrl = b.event ? b.event.image_url : "";
       console.log("IMAGE URL:", imageUrl);
       const card = `
        <div class="col-md-4 mb-4">
            <div class="card text-white h-100">
                ${
                    imageUrl
                    ? `
                        <img
                            src="${imageUrl}"
                            alt="${b.event.title}"
                            class="booking-image"
                        >
                    `
                    : `
                        <div class="booking-image-placeholder">
                            <i class="bi bi-image"></i>
                            <span>No image available</span>
                        </div>
                    `
                }
                <div class="card-body">
                    <h5>${b.event.title}</h5>
                    <p>
                        Date:
                        ${new Date(b.event.date_time).toLocaleString()}
                    </p>
                    <p>
                        Location:
                        ${b.event.location}
                    </p>
                    <p>
                        Tickets:
                        ${b.tickets}
                    </p>
                    <p>
                        Status:
                        ${b.status || "confirmed"}
                    </p>
                    <button
                        class="btn btn-danger w-100 mt-2"
                        onclick="cancelBooking(${b.id})">
                        Cancel Booking
                    </button>
                </div>
            </div>
        </div>
      `;
       container.innerHTML += card;
    });

    } catch (err) {
        console.error("Bookings loading error:", err);
        const container = document.getElementById("bookingsContainer");
        if (container) {
            container.innerHTML = `
                <div class="col-12 text-center text-white py-5">
                    <h5>Unable to load bookings</h5>
                </div>
            `;
        }
    }
}

async function cancelBooking(id) {                                                /* Cancel selected booking */
    const token = getToken();
    if (!token) return;
    if (!confirm("Are you sure you want to cancel this booking?")) {
        return;
    }
    try {
        const res = await fetch(`${API_URL}/bookings/book/${id}`, {
            method: "DELETE",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });
        const data = await res.json();
        if (res.ok) {
            alert("Booking cancelled");
            loadBookings();
        } else {
            alert(data.detail || "Unable to cancel booking");
        }
    } catch (err) {
        console.error("Cancel booking error:", err);
    }
}

document.addEventListener("DOMContentLoaded", function () {                           /* Run page scripts */
    loadBookings();
    const backBtn = document.getElementById("backBtn");
    if (backBtn) {                                                                    /* Back button action */
        backBtn.addEventListener("click", function () {
            window.location.href = "events.html";
        });
    }
});