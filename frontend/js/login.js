const API_URL = "https://event-booking-api-gnww.onrender.com";

// Function to switch between Login, Register, and Forgot views
function showView(viewId) {
    const views = document.querySelectorAll(".auth-view");

    views.forEach(v => {
        v.classList.add("d-none"); // Hide all views
    });

    const activeView = document.getElementById(viewId);
    if (activeView) {
        activeView.classList.remove("d-none"); // Show the one you clicked
    }
}

// 1. Form selection
const form = document.getElementById("loginForm");

// 2. Event Listener properly attach
if (form) {
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const identifierInput = form.querySelectorAll("input")[0].value;
        const passwordInput = form.querySelectorAll("input")[1].value;

        const loginPayload = {
            username: identifierInput,
            password: passwordInput
        };

        try {
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(loginPayload)
            });

            const result = await response.json();

            if (response.ok) {
                localStorage.setItem('token', result.access_token);
                alert("Login Successful!");
                window.location.href = 'events.html';
            } else {
                alert("Error: " + (result.detail || "Invalid Username or Password"));
            }
        } catch (err) {
            console.error("Fetch Error:", err);
            alert("Server connection failed. Please try again later.");
        }
    });
}

// login.js
async function handleLogin(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    // BACKEND CHECK:
    const loginPayload = {
        username: data.username || data.identifier, // Dono try karega
        password: data.password
    };

    try {
        const response = await fetch('https://event-booking-api-gnww.onrender.com/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(loginPayload)
        });

        const result = await response.json();

        if (response.ok) {
            localStorage.setItem('token', result.access_token);
            alert("Login Successful!");
            window.location.href = 'events.html';
        } else {
            alert("Error: " + (result.detail || "Invalid Username or Password"));
        }
    } catch (err) {
        console.error("Fetch Error:", err);
        alert("Server connection failed. Please try again later.");
    }
}