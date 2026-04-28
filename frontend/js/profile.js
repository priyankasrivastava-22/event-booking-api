const API_URL = "https://event-booking-api-gnww.onrender.com";

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

// ---------------- LOAD PROFILE ----------------
async function loadProfile() {
    const token = getToken();
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/me`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (res.status === 401) {
            alert("Session expired");
            localStorage.removeItem("token");
            window.location.href = "login.html";
            return;
        }

        const data = await res.json();
        console.log("Profile:", data);

        document.getElementById("username").innerText = data.username;
        document.getElementById("role").innerText = data.role;
        document.getElementById("bookings").innerText = data.bookings;

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
document.addEventListener("DOMContentLoaded", loadProfile);