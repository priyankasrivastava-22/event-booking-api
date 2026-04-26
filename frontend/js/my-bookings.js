const API_URL = "http://127.0.0.1:8000";

// ---------------- AUTH CHECK ----------------
function checkAuth() {
    const token = localStorage.getItem("token");
    if (!token) {
        alert("Please login first");
        window.location.href = "login.html";
        return null;
    }
    return token;
}

// ---------------- LOAD BOOKINGS ----------------
async function loadBookings() {
    const token = checkAuth();
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/my-bookings`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        const data = await res.json();
        console.log("Bookings:", data);

        const container = document.getElementById("bookingContainer");
        container.innerHTML = "";

        if (!data || data.length === 0) {
            container.innerHTML = "<p>No bookings yet</p>";
            return;
        }

        data.forEach(b => {
            const card = `
                <div class="col-md-4 mb-4">
                    <div class="card p-3">
                        <h5>${b.event_title || "Event"}</h5>
                        <p>Tickets: ${b.tickets}</p>
                        <p>Status: ${b.status || "Confirmed"}</p>

                        <button class="btn btn-danger w-100"
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
    }
}

// ---------------- CANCEL BOOKING ----------------
async function cancelBooking(id) {
    const token = checkAuth();
    if (!token) return;

    if (!confirm("Are you sure you want to cancel this booking?")) return;

    try {
        const res = await fetch(`${API_URL}/book/${id}`, {
            method: "DELETE",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (res.ok) {
            alert("Booking cancelled");
            loadBookings(); // refresh
        } else {
            const data = await res.json();
            alert(data.detail || "Cancel failed");
        }

    } catch (err) {
        console.error(err);
    }
}

// ---------------- BACK ----------------
function goBack() {
    window.location.href = "events.html";
}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", loadBookings);