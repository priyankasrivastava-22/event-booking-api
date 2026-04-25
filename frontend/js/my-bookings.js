const API_URL = "http://127.0.0.1:8000";

async function loadBookings() {
    const token = localStorage.getItem("token");

    const res = await fetch(`${API_URL}/my-bookings`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const data = await res.json();

    const container = document.getElementById("bookingsContainer");
    container.innerHTML = "";

    if (!data.length) {
        container.innerHTML = "<p>No bookings yet</p>";
        return;
    }

    data.forEach(b => {
        container.innerHTML += `
            <div class="card p-3 mb-3">
                <h5>${b.event.title}</h5>
                <p>Tickets: ${b.tickets}</p>
                <p>Status: ${b.payment_status || "pending"}</p>

                <button class="btn btn-danger"
                    onclick="cancelBooking(${b.id})">
                    Cancel
                </button>
            </div>
        `;
    });
}

async function cancelBooking(id) {
    const token = localStorage.getItem("token");

    await fetch(`${API_URL}/book/${id}`, {
        method: "DELETE",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    alert("Booking cancelled");
    loadBookings();
}

loadBookings();