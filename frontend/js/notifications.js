const API_URL = (window.API_BASE_URL || ((["localhost", "127.0.0.1"].includes(window.location.hostname)) ? "http://127.0.0.1:8000" : window.location.origin)).replace(/\/$/, "") + "/api";

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
        const res = await fetch(`${API_URL}/engagement/notifications/my`, {
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
    const container = document.getElementById("notificationContainer");

    container.innerHTML = "";

    if (!notifications || notifications.length === 0) {
        container.innerHTML = "<p class='text-center text-white p-4'>No notifications yet</p>";
        return;
    }

    notifications.forEach(n => {
        // FIXED: Added 'notification-item', 'notif-text', and 'notif-time' classes
        const item = `
            <div class="notification-item">
                <p class="notif-text">${escapeNotificationHtml(n.message)}</p>
                <div class="notif-time">
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
function escapeNotificationHtml(value) { return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
