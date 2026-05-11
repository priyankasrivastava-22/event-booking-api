/* MY BOOKINGS PAGE SCRIPT */

const API_URL = "https://event-booking-api-gnww.onrender.com/api";

/* Check login token */
function getToken() {
    const token = localStorage.getItem("token");

    if (!token) {
        alert("Please login first");
        window.location.href = "login.html";
        return null;
    }

    return token;
}

/* Load all bookings */
async function loadBookings() {
    const token = getToken();
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/bookings/my-bookings`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        /* Handle expired session */
        if (res.status === 401) {
            alert("Session expired. Please login again.");
            localStorage.removeItem("token");
            window.location.href = "login.html";
            return;
        }

        const container = document.getElementById("bookingsContainer");
        if (!container) return;

        container.innerHTML = "";

        /* Handle failed response */
        if (!res.ok) {
            container.innerHTML = `
                <div class="col-12 text-center text-white py-5">
                    <h5>Unable to load bookings</h5>
                </div>
            `;
            return;
        }

        const data = await res.json();

        /* Show empty state */
        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center text-white py-5">
                    <h5>No bookings yet</h5>
                </div>
            `;
            return;
        }

        /* Render booking cards */
        data.forEach(b => {
            const card = `
                <div class="col-md-4 mb-4">
                    <div class="card p-3 text-white h-100">
                        <h5>${b.event.title}</h5>
                        <p>Date: ${b.event.date_time}</p>
                        <p>Location: ${b.event.location}</p>
                        <p>Tickets: ${b.tickets}</p>
                        <p>Status: ${b.status || "confirmed"}</p>

                        <button class="btn btn-danger w-100 mt-2"
                            onclick="cancelBooking(${b.id})">
                            Cancel Booking
                        </button>
                    </div>
                </div>
            `;

            container.innerHTML += card;
        });

    } catch (err) {
        console.error(err);

        const container = document.getElementById("bookingsContainer");

        if (container) {
            container.innerHTML = `
                <div class="col-12 text-center text-white py-5">
                    <h5>No bookings yet</h5>
                </div>
            `;
        }
    }
}

/* Cancel selected booking */
async function cancelBooking(id) {
    const token = getToken();
    if (!token) return;

    if (!confirm("Are you sure you want to cancel this booking?")) return;

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
        console.error(err);
    }
}

/* Run page scripts */
document.addEventListener("DOMContentLoaded", function () {

    loadBookings();

    const backBtn = document.getElementById("backBtn");

    /* Back button action */
    if (backBtn) {
        backBtn.addEventListener("click", function () {
            window.location.href = "events.html";
        });
    }

});