const API_URL = "https://event-booking-api-gnww.onrender.com/api";

// ---------------- AUTH ----------------
function getToken() {
    const token = localStorage.getItem("token");

    if (!token) {
        alert("Login required");
        window.location.href = "login.html";
        return null;
    }

    return token;
}

// ---------------- LOAD NOTIFICATIONS ----------------
async function loadNotifications() {
    const token = getToken();
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/my-notifications`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (res.status === 401) {
            alert("Session expired. Please login again.");
            localStorage.removeItem("token");
            window.location.href = "login.html";
            return;
        }

        const data = await res.json();
        console.log("Notifications:", data);

        renderNotifications(data);

    } catch (err) {
        console.error("Error:", err);
    }
}

// ---------------- RENDER ----------------
function renderNotifications(notifications) {
    const container = document.getElementById("notificationContainer"); // ✅ FIXED

    container.innerHTML = "";

    if (!notifications || notifications.length === 0) {
        container.innerHTML = "<p class='text-center'>No notifications yet</p>";
        return;
    }

    notifications.forEach(n => {
        const item = `
            <div class="notification">
                <p>${n.message}</p>
                <div class="time">
                    ${new Date(n.created_at).toLocaleString()}
                </div>
            </div>
        `;

        container.innerHTML += item;
    });
}

// ---------------- BACK BUTTON ----------------
function goBack() {
    window.history.back();
}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", loadNotifications);