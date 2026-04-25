console.log("JS loaded");
const API_URL = "http://127.0.0.1:8000";

async function loadEvents() {
    const token = localStorage.getItem("token");

    if (!token) {
        alert("Please login first");
        window.location.href = "login.html";
        return;
    }

    try {
        const res = await fetch(`${API_URL}/events`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        const data = await res.json();

        const container = document.getElementById("eventsContainer");
        container.innerHTML = "";

        // HANDLE EMPTY STATE
        if (!data || data.length === 0) {
            container.innerHTML = "<p>No events available</p>";
            return;
        }

        data.forEach(event => {
            const card = `
                <div class="col-md-4 mb-4">
                    <div class="card p-3 h-100 text-white">
                        <h5 class="text-white">${event.title}</h5>
                        <p class="text-light">${event.location}</p>
                        <p class="text-light">₹${event.price}</p>
                        <p class="text-light">Seats: ${event.available_seats}</p>


                        <button class="btn btn-primary w-100"
                            onclick="viewEvent(${event.id})">
                            View Details
                        </button>
                    </div>
                </div>
            `;

            container.innerHTML += card;
        });

    } catch (err) {
        console.error(err);
        document.getElementById("eventsContainer").innerHTML =
            "<p>Error loading events</p>";
    }
}

function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

function viewEvent(id) {
    window.location.href = `event-details.html?id=${id}`;
}

loadEvents();