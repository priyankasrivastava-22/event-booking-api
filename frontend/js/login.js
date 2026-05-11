/* ======= LOGIN / REGISTER / DEMO AUTH SCRIPT. Handles local + deployed API environment ====== */

/* Detect local environment */
const isLocal =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1";

/* Set API URL based on environment */
const API_URL = isLocal
    ? "http://127.0.0.1:8000/api"
    : "https://event-booking-api-gnww.onrender.com/api";

/* Debug logs */
console.log("Using API URL:", API_URL);
console.log("login.js loaded");

/* Global JS error logger */
window.onerror = function (msg, url, line) {
    console.error("JS Error:", msg, "Line:", line);
};

/* VIEW SWITCHER Show Login / Register / Forgot Password sections */
function showView(viewId) {
    document.querySelectorAll(".auth-view").forEach(view => {
        view.classList.add("d-none");
    });

    document.getElementById(viewId)?.classList.remove("d-none");
}

/* LOGIN FORM SUBMIT */
const form = document.getElementById("loginForm");

if (form) {
    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const username = document
            .getElementById("loginIdentifier")
            .value.trim();

        const password = document
            .getElementById("loginPassword")
            .value.trim();

        console.log("Login clicked");

        try {
            const response = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const result = await response.json();

            console.log("Login Response:", result);

            if (response.ok) {
                localStorage.setItem("token", result.access_token);

                alert("Login Successful");

                window.location.href = "events.html";
            } else {
                alert(result.detail || "Invalid credentials");
            }

        } catch (error) {
            console.error("Login Error:", error);
            alert("Server error");
        }
    });
}

/* REGISTER FORM SUBMIT */
const registerForm = document.getElementById("registerForm");

if (registerForm) {
    registerForm.addEventListener("submit", async function (e) {
        e.preventDefault();

        const username = document
            .getElementById("regUsername")
            .value.trim();

        const email = document
            .getElementById("regEmail")
            .value.trim();

        const password = document
            .getElementById("regPassword")
            .value.trim();

        console.log("Register clicked");

        try {
            const response = await fetch(`${API_URL}/auth/register`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: username,
                    email: email,
                    password: password,
                    role: "user"
                })
            });

            const result = await response.json();

            console.log("Register Response:", result);

            if (response.ok) {
                alert("Registration Successful");

                registerForm.reset();

                showView("loginView");
            } else {
                alert(result.detail || "Registration failed");
            }

        } catch (error) {
            console.error("Register Error:", error);
            alert("Server error");
        }
    });
}

/* DEMO ACCOUNT ONE CLICK LOGIN */
async function fillDemoLogin() {
    const demoUsername = "demo";
    const demoPassword = "demo123";

    /* Autofill login inputs */
    document.getElementById("loginIdentifier").value = demoUsername;
    document.getElementById("loginPassword").value = demoPassword;

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: demoUsername,
                password: demoPassword
            })
        });

        const result = await response.json();

        console.log("Demo Login Response:", result);

        if (response.ok) {
            localStorage.setItem("token", result.access_token);

            alert("Demo Login Successful");

            window.location.href = "events.html";
        } else {
            alert(result.detail || "Demo login failed");
        }

    } catch (error) {
        console.error("Demo Login Error:", error);
        alert("Server error");
    }
}