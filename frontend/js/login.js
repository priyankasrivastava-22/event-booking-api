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

// Existing Login Logic
const form = document.getElementById("loginForm");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const username = form.querySelector("input[type='email']").value;
  const password = form.querySelector("input[type='password']").value;

  try {
    const res = await fetch("https://event-booking-api-gnww.onrender.com/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
       username: email,
       password: password
     }),
    });

    const data = await res.json();

    if (res.ok) {
      console.log("LOGIN SUCCESS", data);
      localStorage.setItem("token", data.access_token);
      alert("Login successful");
      window.location.href = "events.html";
    } else {
      alert(data.detail || "Invalid credentials");
    }
  } catch (err) {
    console.error(err);
    alert("Server error");
  }
});
