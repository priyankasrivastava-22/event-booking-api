const API_URL = "http://127.0.0.1:8000";

// ---------------- AUTH ----------------
function checkAuth() {
    const token = localStorage.getItem("token");
    if (!token) {
        alert("Please login first");
        window.location.href = "login.html";
        return null;
    }
    return token;
}

// ---------------- LOAD NOTIFICATIONS ----------------
async function loadNotifications() {
    const token = checkAuth();
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/my-notifications`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        const data = await res.json();
        console.log("Notifications:", data);

        const container = document.getElementById("notificationContainer");
        container.innerHTML = "";

        if (!data || data.length === 0) {
            container.innerHTML = "<p>No notifications</p>";
            return;
        }

        data.forEach(n => {
            const time = new Date(n.created_at).toLocaleString();

            const item = `
                <div class="notification">
                    <p>${n.message}</p>
                    <span class="time">${time}</span>
                </div>
            `;

            container.innerHTML += item;
        });

    } catch (err) {
        console.error(err);
        document.getElementById("notificationContainer").innerHTML =
            "<p>Error loading notifications</p>";
    }
}

// ---------------- BACK ----------------
function goBack() {
    window.location.href = "events.html";
}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", loadNotifications);