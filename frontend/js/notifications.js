const API_URL = "http://127.0.0.1:8000";

async function loadNotifications() {
    const token = localStorage.getItem("token");

    const res = await fetch(`${API_URL}/my-notifications`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    const data = await res.json();

    const container = document.getElementById("notiContainer");
    container.innerHTML = "";

    data.forEach(n => {
        container.innerHTML += `
            <div class="card p-3 mb-2">
                <p>${n.message}</p>
                <small>${n.created_at}</small>
            </div>
        `;
    });
}

loadNotifications();