const API_URL = "http://127.0.0.1:8000";

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

// ---------------- ADMIN PROTECTION (ADDED) ----------------
// This ensures ONLY admin can access this page
function getUserFromToken() {
    const token = localStorage.getItem("token");
    if (!token) return null;

    try {
        return JSON.parse(atob(token.split(".")[1]));
    } catch {
        return null;
    }
}

function protectAdminPage() {
    const user = getUserFromToken();

    if (!user || user.role !== "admin") {
        alert("Access denied. Admins only.");
        window.location.href = "events.html";
    }
}

// ---------------- LOAD CATEGORIES ----------------
async function loadCategories() {
    const token = getToken();
    if (!token) return;

    const res = await fetch(`${API_URL}/categories`, {
        headers: { "Authorization": `Bearer ${token}` }
    });

    const data = await res.json();

    const dropdown = document.getElementById("categorySelect");
    dropdown.innerHTML = "";

    data.forEach(cat => {
        const option = document.createElement("option");
        option.value = cat.id;
        option.textContent = cat.name;
        dropdown.appendChild(option);
    });
}

// ---------------- CREATE CATEGORY ----------------
async function createCategory() {
    const token = getToken();
    if (!token) return;

    const name = document.getElementById("categoryName").value;

    const res = await fetch(`${API_URL}/admin/categories`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ name })
    });

    const data = await res.json();

    if (res.ok) {
        alert("Category created");
        loadCategories();
    } else {
        alert(data.detail);
    }
}

// ---------------- CREATE EVENT ----------------
async function createEvent() {
    const token = getToken();
    if (!token) return;

    const body = {
        title: document.getElementById("title").value,
        description: document.getElementById("description").value,
        location: document.getElementById("location").value,
        price: parseInt(document.getElementById("price").value),
        total_seats: parseInt(document.getElementById("seats").value),
        available_seats: parseInt(document.getElementById("seats").value),
        category_id: parseInt(document.getElementById("categorySelect").value),
        date_time: document.getElementById("date").value
    };

    const res = await fetch(`${API_URL}/events`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(body)
    });

    const data = await res.json();

    if (res.ok) {
        alert("Event created");
    } else {
        alert(data.detail);
    }
}

// ---------------- SEND NOTIFICATION ----------------
async function sendNotification() {
    const token = getToken();
    if (!token) return;

    const message = document.getElementById("message").value;
    const user_name = document.getElementById("username").value || null;

    const res = await fetch(`${API_URL}/admin/notify`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ message, user_name })
    });

    const data = await res.json();

    if (res.ok) {
        alert("Notification sent");
    } else {
        alert(data.detail);
    }
}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", () => {
    protectAdminPage();
    loadCategories();
});