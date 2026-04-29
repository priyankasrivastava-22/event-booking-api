const API_URL = "https://event-booking-api-gnww.onrender.com/api";

function showView(viewId) {
    document.querySelectorAll(".auth-view").forEach(v => {
        v.classList.add("d-none");
    });

    document.getElementById(viewId)?.classList.remove("d-none");
}

const form = document.getElementById("loginForm");

if (form) {
    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const username = document.getElementById("loginIdentifier").value.trim();
        const password = form.querySelector("input[type='password']").value.trim();

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

            console.log(result);

            if (response.ok) {
                localStorage.setItem("token", result.access_token);
                alert("Login Successful");
                window.location.href = "events.html";
            } else {
                alert(result.detail || "Invalid credentials");
            }

        } catch (error) {
            console.error(error);
            alert("Server error");
        }
    });
}