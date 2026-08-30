const API_URL = "https://event-booking-api-gnww.onrender.com/api";
let otpPurpose = null;
let pendingValue = null;
let verificationToken = null;
let otpTimerInterval = null;

function getToken() {                                                                                                    /* AUTH */
    const token = localStorage.getItem("token");
    if (!token) {
        alert("Login required");
        window.location.href = "login.html";
        return null;
    }
    return token;
}

async function apiRequest(endpoint, options = {}) {                                                                      /* API HELPER */
    const token = getToken();
    if (!token) return null;
    const headers = {
        "Authorization": `Bearer ${token}`,
        ...(options.body
            ? { "Content-Type": "application/json" }
            : {})
    };
    try {
        const response = await fetch(
            `${API_URL}${endpoint}`,
            {
                ...options,
                headers: {
                    ...headers,
                    ...(options.headers || {})
                }
            }
        );
        if (response.status === 401) {
            alert("Your session has expired. Please login again.");
            localStorage.removeItem("token");
            window.location.href = "login.html";
            return null;
        }
        return response;
    } catch (error) {
        console.error("API ERROR:", error);
        alert("Unable to connect to Eventora server.");
        return null;
    }
}

async function loadProfile() {                                                                                           /* LOAD PROFILE */
    const token = getToken();
    if (!token) return;
    try {
        const response = await fetch(
            `${API_URL}/auth/me`,
            {
                headers: { "Authorization": `Bearer ${token}` }
            }
        );
        if (response.status === 401) {
            alert("Session expired");
            localStorage.removeItem("token");
            window.location.href = "login.html";
            return;
        }
        if (!response.ok) {
            throw new Error(`Profile request failed: ${response.status}`);
        }
        const data = await response.json();
        console.log("PROFILE DATA:", data);

        const username = data.username || "User";                                                                        /* USERNAME */
        document.getElementById("profileUsername").textContent = username;
        document.getElementById("usernameValue").textContent = username;

        document.getElementById("profileAvatar").textContent = username.charAt(0).toUpperCase();                         /* AVATAR */

        const role = data.role || "user";                                                                                /* ROLE */
        document.getElementById("profileRole").textContent = role.toUpperCase();
        document.getElementById("roleValue").textContent = role;

        const email = data.email || "Not available";                                                                     /* EMAIL */
        document.getElementById("profileEmail").textContent = email;
        document.getElementById("emailValue").textContent = email;
        const emailVerified = data.email_verified === true;
        const emailBadge = document.getElementById("emailVerifiedBadge");
        if (emailBadge) {
            emailBadge.style.display = emailVerified ? "inline-block" : "none";
        }
        const emailStatus = document.getElementById("activityEmailStatus");
        if (emailStatus) {
            emailStatus.textContent = emailVerified ? "Verified" : "Not Verified";
        }

        const phone = data.phone;                                                                                        /* PHONE */
        const phoneBadge = document.getElementById("phoneVerifiedBadge");
        const phoneStatus = document.getElementById("activityPhoneStatus");
        if (phone) {
            document.getElementById("phoneValue").textContent = phone;
            const phoneVerified = data.phone_verified === true;
            if (phoneBadge) {
                phoneBadge.style.display = phoneVerified ? "inline-block" : "none";
            }
            if (phoneStatus) {
                phoneStatus.textContent = phoneVerified ? "Verified" : "Not Verified";
            }
        } else {
            document.getElementById("phoneValue").textContent = "Not added";
            if (phoneBadge) {
                phoneBadge.style.display = "none";
            }
            if (phoneStatus) {
                phoneStatus.textContent = "Not Added";
            }
        }
        const bookings = data.bookings || 0;                                                                             /* BOOKINGS */
        document.getElementById("totalBookings").textContent = bookings;
        document.getElementById("activityBookings").textContent = bookings;

        const accountStatus = document.getElementById("accountStatus");                                                  /* ACCOUNT STATUS */
        if (accountStatus) {
            accountStatus.textContent = "Active";
        }

        const adminSection = document.getElementById("adminSection");                                                    /* ADMIN SECTION */
        if (adminSection) {
            adminSection.style.display = role === "admin" ? "flex" : "none";
        }
    } catch (error) {
        console.error("PROFILE ERROR:", error);
        alert("Unable to load your profile.");
    }
}

async function requestOtp(purpose, value = null) {                                                                       /* OTP FLOW */
    otpPurpose = purpose;
    pendingValue = value;
    verificationToken = null;
    const payload = { purpose: purpose };
    if (purpose === "change_email" || purpose === "change_phone") {
       if (!value) {
            alert(
                purpose === "change_email"
                    ? "Enter the new email address."
                    : "Enter the new phone number."
            );
            return;
        }
        payload.destination = value;
    }
    try {

        const response = await apiRequest(
            "/auth/otp/send",
            {
                method: "POST",
                body: JSON.stringify(payload)
            }
        );
        if (!response) return;
        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || data.error || "Unable to send OTP.");
            return;
        }
        const description = document.getElementById("otpDescription");
        if (description) {
            if (purpose === "change_phone") {
                description.textContent =
                    "A verification OTP has been sent to the phone number you entered.";
            } else if (purpose === "change_email") {
                description.textContent =
                    "A verification OTP has been sent to the new email address.";
            } else {
                description.textContent =
                    "A verification OTP has been sent to your registered email address.";
            }
        }
        const otpInput = document.getElementById("otpInput");
        if (otpInput) {
            otpInput.value = "";
        }
        const modalElement = document.getElementById("otpModal");
        if (!modalElement) {
            alert("OTP interface is unavailable.");
            return;
        }
        const otpModal = bootstrap.Modal.getOrCreateInstance(modalElement);
        otpModal.show();
        startOtpTimer();
    } catch (error) {
        console.error("OTP SEND ERROR:", error);
        alert("Unable to send OTP.");
    }
}

async function verifyOtp() {                                                                                             /* VERIFY OTP */
    const otpInput = document.getElementById("otpInput");
    if (!otpInput) return;
    const otp = otpInput.value.trim();
    if (!otp) {
        alert("Enter the OTP.");
        return;
    }
    if (!/^\d{6}$/.test(otp)) {
        alert("OTP must be 6 digits.");
        return;
    }
    if (!otpPurpose) {
        alert("OTP session expired. Please request a new OTP.");
        return;
    }
    try {
        const response = await apiRequest(
            "/auth/otp/verify",
            {
                method: "POST",
                body: JSON.stringify({
                    otp: otp,
                    purpose: otpPurpose
                })
            }
        );
        if (!response) return;
        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || data.error || "Invalid OTP.");
            return;
        }
        verificationToken = data.verification_token;
        if (!verificationToken) {
            alert("OTP verified, but verification token was not received.");
            return;
        }
        const modalElement = document.getElementById("otpModal");
        if (modalElement) {
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
        }
        otpInput.value = "";
        if (otpPurpose === "change_username") {
            showUsernameModal();
        } else if (otpPurpose === "change_password") {
            showPasswordModal();
        } else if (otpPurpose === "change_email") {
            completeEmailChange();
        } else if (otpPurpose === "change_phone") {
            completePhoneChange();
        }
    } catch (error) {
        console.error("OTP VERIFY ERROR:", error);
        alert("OTP verification failed.");
    }
}

async function resendOtp() {                                                                                             /* RESEND OTP */
    if (!otpPurpose) {
        alert("No OTP verification is currently active.");
        return;
    }
    await requestOtp(otpPurpose, pendingValue);
}

function startOtpTimer() {                                                                                               /* OTP TIMER */
    clearInterval(otpTimerInterval);
    let seconds = 60;
    const resendButton = document.getElementById("resendOtpBtn");
    const timer = document.getElementById("otpTimer");
    if (resendButton) {
        resendButton.disabled = true;
    }
    if (timer) {
        timer.textContent = `You can request another OTP in ${seconds} seconds.`;
    }
    otpTimerInterval = setInterval(() => {
        seconds--;
        if (timer) {
            timer.textContent =
                seconds > 0
                    ? `You can request another OTP in ${seconds} seconds.`
                    : "You can request a new OTP now.";
        }
        if (seconds <= 0) {
            clearInterval(otpTimerInterval);
            if (resendButton) {
                resendButton.disabled = false;
            }
        }
    }, 1000);
}

function startUsernameChange() {                                                                                         /* CHANGE USERNAME */
    const input = document.getElementById("newUsername");
    if (input) {
        input.value = "";
    }
    requestOtp("change_username");
}

function showUsernameModal() {
    const modalElement = document.getElementById("usernameModal");
    if (!modalElement) return;
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

async function saveUsername() {
    const input = document.getElementById("newUsername");
    if (!input) return;
    const username = input.value.trim();
    if (!username) {
        alert("Enter a username.");
        return;
    }
    if (username.length < 3 || username.length > 50) {
        alert("Username must be between 3 and 50 characters.");
        return;
    }
    if (!verificationToken) {
        alert("Please verify the OTP first.");
        return;
    }
    try {
        const response = await apiRequest(
            "/auth/change-username",
            {
                method: "POST",
                body: JSON.stringify({
                    username: username,
                    verification_token: verificationToken
                })
            }
        );
        if (!response) return;
        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || data.error || "Unable to change username.");
            return;
        }
        alert("Username changed successfully. Please login again.");
        resetOtpState();
        localStorage.removeItem("token");
        window.location.href = "login.html";
    } catch (error) {
        console.error("USERNAME CHANGE ERROR:", error);
        alert("Unable to change username.");
    }
}

function startEmailChange() {                                                                                            /* CHANGE EMAIL */
    const modalElement = document.getElementById("emailModal");
    if (!modalElement) return;
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

async function saveEmail() {
    const input = document.getElementById("newEmail");
    if (!input) return;
    const email = input.value.trim();
    if (!email) {
        alert("Enter a valid email.");
        return;
    }
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(email)) {
        alert("Enter a valid email address.");
        return;
    }
    pendingValue = email;
    const modalElement = document.getElementById("emailModal");
    if (modalElement) {
        const emailModal = bootstrap.Modal.getInstance(modalElement);
        if (emailModal) {
            emailModal.hide();
        }
    }
    await requestOtp("change_email", email);
}

async function completeEmailChange() {
    if (!verificationToken) {
        alert("Please verify the OTP first.");
        return;
    }
    if (!pendingValue) {
        alert("New email address is missing.");
        return;
    }
    try {
        const response = await apiRequest(
            "/auth/change-email",
            {
                method: "POST",
                body: JSON.stringify({
                    email: pendingValue,
                    verification_token: verificationToken
                })
            }
        );
        if (!response) return;
        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || data.error || "Unable to change email.");
            return;
        }
        alert("Email address changed successfully.");
        resetOtpState();
        await loadProfile();
    } catch (error) {
        console.error("EMAIL CHANGE ERROR:", error);
        alert("Unable to change email.");
    }
}

function startPhoneChange() {                                                                                            /* CHANGE PHONE */
    const modalElement = document.getElementById("phoneModal");
    if (!modalElement) return;
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

async function savePhone() {
    const input = document.getElementById("newPhone");
    if (!input) return;
    const phone = input.value.trim();
    if (!phone) {
        alert("Enter your phone number.");
        return;
    }
    if (!/^\+[1-9]\d{7,14}$/.test(phone)) {
        alert("Enter a valid phone number with country code. Example: +919876543210");
        return;
    }
    pendingValue = phone;
    const modalElement = document.getElementById("phoneModal");
    if (modalElement) {
        const phoneModal = bootstrap.Modal.getInstance(modalElement);
        if (phoneModal) {
            phoneModal.hide();
        }
    }
    await requestOtp("change_phone", phone);
}

async function completePhoneChange() {
    if (!verificationToken) {
        alert("Please verify the OTP first.");
        return;
    }
    if (!pendingValue) {
        alert("Phone number is missing.");
        return;
    }
    try {
        const response = await apiRequest(
            "/auth/change-phone",
            {
                method: "POST",
                body: JSON.stringify({
                    phone: pendingValue,
                    verification_token: verificationToken
                })
            }
        );
        if (!response) return;
        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || data.error || "Unable to update phone number.");
            return;
        }
        alert("Phone number updated successfully.");
        resetOtpState();
        await loadProfile();
    } catch (error) {
        console.error("PHONE CHANGE ERROR:", error);
        alert("Unable to update phone number.");
    }
}

function startPasswordChange() {                                                                                         /* CHANGE PASSWORD */
    requestOtp("change_password");
}
function showPasswordModal() {
    const modalElement = document.getElementById("passwordModal");
    if (!modalElement) return;
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}
async function savePassword() {
    const passwordInput = document.getElementById("newPassword");
    const confirmInput = document.getElementById("confirmPassword");
    if (!passwordInput || !confirmInput) return;
    const password = passwordInput.value;
    const confirmPassword = confirmInput.value;
    if (!password) {
        alert("Enter a new password.");
        return;
    }
    if (password !== confirmPassword) {
        alert("Passwords do not match.");
        return;
    }
    if (password.length < 8) {
        alert("Password must contain at least 8 characters.");
        return;
    }
    if (!/[A-Z]/.test(password)) {
        alert("Password must contain at least one uppercase letter.");
        return;
    }
    if (!/[a-z]/.test(password)) {
        alert("Password must contain at least one lowercase letter.");
        return;
    }
    if (!/[0-9]/.test(password)) {
        alert("Password must contain at least one number.");
        return;
    }
    if (!/[^A-Za-z0-9]/.test(password)) {
        alert("Password must contain at least one special character.");
        return;
    }
    if (!verificationToken) {
        alert("Please verify the OTP first.");
        return;
    }
    try {
        const response = await apiRequest(
            "/auth/change-password",
            {
                method: "POST",
                body: JSON.stringify({
                    verification_token: verificationToken,
                    new_password: password
                })
            }
        );
        if (!response) return;
        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || data.error || "Unable to change password.");
            return;
        }
        alert("Password changed successfully. Please login again.");
        resetOtpState();
        localStorage.removeItem("token");
        window.location.href = "login.html";
    } catch (error) {
        console.error("PASSWORD CHANGE ERROR:", error);
        alert("Unable to change password.");
    }
}

function requestAccountDeletion() {                                                                                      /* DELETE ACCOUNT */
    alert("Account deletion is currently unavailable.");
}

function logout() {                                                                                                      /* LOGOUT */
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

function resetOtpState() {                                                                                               /* RESET OTP STATE */
    otpPurpose = null;
    pendingValue = null;
    verificationToken = null;
    clearInterval(otpTimerInterval);
    otpTimerInterval = null;
    const otpInput = document.getElementById("otpInput");
    if (otpInput) {
        otpInput.value = "";
    }
    const newPassword = document.getElementById("newPassword");
    const confirmPassword = document.getElementById("confirmPassword");
    if (newPassword) {
        newPassword.value = "";
    }
    if (confirmPassword) {
        confirmPassword.value = "";
    }
}

document.addEventListener("DOMContentLoaded", loadProfile);                                                              /* INITIALIZATION */