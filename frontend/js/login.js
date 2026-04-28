const API_URL = "https://event-booking-api-gnww.onrender.com";

// Function to switch between Login, Register, and Forgot views
// This stays global so the HTML 'onclick' can find it.
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

// login.js
const form = document.getElementById("loginForm");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const identifier = form.querySelectorAll("input")[0].value;
  const passwordVal = form.querySelectorAll("input")[1].value;

  console.log("Attempting login for:", identifier);

  const params = new URLSearchParams();
  params.append('username', identifier);
  params.append('password', passwordVal);

  try {
    const res = await fetch("https://event-booking-api-gnww.onrender.com/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params
    });

    if (res.status === 404) {
        alert("Error 404: Endpoint nahi mila.");
        return;
    }

    const data = await res.json();

    if (res.ok) {
      localStorage.setItem("token", data.access_token);
      alert("Login success!");
      window.location.href = "events.html";
    } else {
      alert(data.detail || "Login failed");
    }
  } catch (err) {
    console.error("Fetch Error:", err);
    alert("Server error or Network issue");
  }
});