console.log("JS loaded");

const API_URL = "http://127.0.0.1:8000";

// ---------------- GET USER FROM TOKEN ----------------
function getUserFromToken() {
    const token = localStorage.getItem("token");
    if (!token) return null;

    try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload; // { sub, role }
    } catch {
        return null;
    }
}

// ---------------- ADMIN BUTTON CONTROL ----------------
// This ensures ONLY admin sees admin features in UI
function setupAdminUI() {
    const user = getUserFromToken();

    // If no user OR not admin → do nothing
    if (!user || user.role !== "admin") return;

    // Find navbar
    const navbar = document.querySelector(".navbar");

    if (!navbar) return;

    // Create Admin button
    const btn = document.createElement("button");
    btn.className = "btn btn-outline-light btn-sm ms-2";
    btn.innerText = "Admin";

    btn.onclick = () => {
        window.location.href = "admin.html";
    };

    // Add button to navbar
    navbar.appendChild(btn);
}

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

// ---------------- LOAD CATEGORIES ----------------
async function loadCategories() {
    const token = checkAuth();
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/categories`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        const categories = await res.json();
        console.log("Categories:", categories);

        const dropdown = document.getElementById("categoryFilter");

        // reset dropdown
        dropdown.innerHTML = `<option value="">All Categories</option>`;

        categories.forEach(cat => {
            const option = document.createElement("option");
            option.value = cat.name;
            option.textContent = cat.name;
            dropdown.appendChild(option);
        });

    } catch (err) {
        console.error("Category load error:", err);
    }
}

// ---------------- LOAD EVENTS ----------------
async function loadEvents() {
    const token = checkAuth();
    if (!token) return;

    const category = document.getElementById("categoryFilter")?.value || "";
    const search = document.getElementById("searchInput")?.value || "";

    let url = `${API_URL}/events`;

    if (category || search) {
        url = `${API_URL}/events/search?title=${search}&category=${category}`;
    }

    console.log("Fetching:", url);

    try {
        const res = await fetch(url, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        const data = await res.json();
        console.log("Events:", data);

        const container = document.getElementById("eventsContainer");
        container.innerHTML = "";

        if (!data || data.length === 0) {
            container.innerHTML = "<p>No events found</p>";
            return;
        }

        data.forEach(event => {
            const card = `
                <div class="col-md-4 mb-4">
                    <div class="card p-3 h-100 text-white">
                        <h5>${event.title}</h5>
                        <p>${event.location}</p>
                        <p>₹${event.price}</p>
                        <p>Category: ${event.category}</p>
                        <p>Seats: ${event.available_seats}</p>

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
        console.error("Event load error:", err);
    }
}

// ---------------- LOGOUT ----------------
function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

// ---------------- VIEW EVENT ----------------
function viewEvent(id) {
    window.location.href = `event-details.html?id=${id}`;
}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", () => {
    console.log("Page Loaded");

    setupAdminUI(); // ✅ ONLY ADDITION → controls admin visibility

    loadCategories();
    loadEvents();

    // filter change
    const categoryDropdown = document.getElementById("categoryFilter");
    if (categoryDropdown) {
        categoryDropdown.addEventListener("change", loadEvents);
    }

    // optional: live search
    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        searchInput.addEventListener("input", loadEvents);
    }
});