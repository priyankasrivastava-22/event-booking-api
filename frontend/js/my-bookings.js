const API_URL = "https://event-booking-api-gnww.onrender.com/api";

// ---------------- AUTH ----------------
function getToken() {
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
    const token = getToken();
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/bookings/my-bookings`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        const data = await res.json();
        console.log("Bookings:", data);

        const container = document.getElementById("bookingsContainer");
        container.innerHTML = "";

        if (!data || data.length === 0) {
            container.innerHTML = "<p>No bookings yet</p>";
            return;
        }

        data.forEach(b => {
            const card = `
                <div class="col-md-4 mb-4">
                    <div class="card p-3 text-white">
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
    }
}

// ---------------- CANCEL BOOKING ----------------
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
            loadBookings(); // refresh list
        } else {
            alert(data.detail);
        }

    } catch (err) {
        console.error(err);
    }
}

// ---------------- LOGOUT ----------------
function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", loadBookings);