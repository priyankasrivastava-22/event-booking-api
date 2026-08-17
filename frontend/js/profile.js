const API_URL = "https://event-booking-api-gnww.onrender.com/api";


/* 
   STATE
    */

let otpPurpose = null;
let pendingValue = null;
let otpTimerInterval = null;


/* 
   AUTH
    */

function getToken() {

    const token =
        localStorage.getItem("token");

    if (!token) {

        alert("Login required");

        window.location.href =
            "login.html";

        return null;
    }

    return token;
}


/* 
   API HELPER
    */

async function apiRequest(
    endpoint,
    options = {}
) {

    const token = getToken();

    if (!token) return null;

    const headers = {
        "Authorization":
            `Bearer ${token}`,

        ...(options.body
            ? {
                "Content-Type":
                    "application/json"
            }
            : {})
    };

    const response =
        await fetch(
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

        alert(
            "Your session has expired. Please login again."
        );

        localStorage.removeItem("token");

        window.location.href =
            "login.html";

        return null;
    }


    return response;
}


/* 
   LOAD PROFILE
    */

async function loadProfile() {

    const token = getToken();

    if (!token) return;


    try {

        const response =
            await fetch(
                `${API_URL}/auth/me`,
                {
                    headers: {
                        "Authorization":
                            `Bearer ${token}`
                    }
                }
            );


        if (response.status === 401) {

            alert("Session expired");

            localStorage.removeItem("token");

            window.location.href =
                "login.html";

            return;
        }


        if (!response.ok) {

            throw new Error(
                "Failed to load profile"
            );
        }


        const data =
            await response.json();


        console.log(
            "PROFILE DATA:",
            data
        );


        /* Username */

        const username =
            data.username || "User";

        document.getElementById(
            "profileUsername"
        ).textContent = username;

        document.getElementById(
            "usernameValue"
        ).textContent = username;


        /* Avatar */

        document.getElementById(
            "profileAvatar"
        ).textContent =
            username
                .charAt(0)
                .toUpperCase();


        /* Role */

        const role =
            data.role || "user";


        document.getElementById(
            "profileRole"
        ).textContent =
            role.toUpperCase();


        document.getElementById(
            "roleValue"
        ).textContent =
            role;


        /* Email */

        const email =
            data.email || "Not available";


        document.getElementById(
            "profileEmail"
        ).textContent =
            email;


        document.getElementById(
            "emailValue"
        ).textContent =
            email;


        /* Phone */

        if (data.phone) {

            document.getElementById(
                "phoneValue"
            ).textContent =
                data.phone;

            document.getElementById(
                "phoneVerifiedBadge"
            ).style.display =
                "inline-block";

            document.getElementById(
                "activityPhoneStatus"
            ).textContent =
                "Verified";

        } else {

            document.getElementById(
                "phoneValue"
            ).textContent =
                "Not added";

            document.getElementById(
                "phoneVerifiedBadge"
            ).style.display =
                "none";

            document.getElementById(
                "activityPhoneStatus"
            ).textContent =
                "Not Added";
        }


        /* Bookings */

        const bookings =
            data.bookings || 0;


        document.getElementById(
            "totalBookings"
        ).textContent =
            bookings;


        document.getElementById(
            "activityBookings"
        ).textContent =
            bookings;


        /* Admin */

        if (role === "admin") {

            document.getElementById(
                "adminSection"
            ).style.display =
                "flex";
        }


    } catch (error) {

        console.error(
            "PROFILE ERROR:",
            error
        );

        alert(
            "Unable to load your profile."
        );
    }
}


/* 
   OTP FLOW
    */

async function requestOtp(
    purpose,
    value = null
) {

    otpPurpose = purpose;

    pendingValue = value;


    try {

        const response =
            await apiRequest(
                "/auth/send-otp",
                {
                    method: "POST",

                    body: JSON.stringify({
                        purpose: purpose,
                        value: value
                    })
                }
            );


        if (!response) return;


        const data =
            await response.json();


        if (!response.ok) {

            alert(
                data.detail ||
                "Unable to send OTP."
            );

            return;
        }


        document.getElementById(
            "otpDescription"
        ).textContent =
            "A verification OTP has been sent to your registered contact.";


        const otpModal =
            new bootstrap.Modal(
                document.getElementById(
                    "otpModal"
                )
            );


        otpModal.show();


        startOtpTimer();


    } catch (error) {

        console.error(error);

        alert(
            "Unable to send OTP."
        );
    }
}


/* 
   VERIFY OTP
    */

async function verifyOtp() {

    const otp =
        document.getElementById(
            "otpInput"
        ).value.trim();


    if (!otp) {

        alert("Enter the OTP.");

        return;
    }


    try {

        const response =
            await apiRequest(
                "/auth/verify-otp",
                {
                    method: "POST",

                    body: JSON.stringify({
                        otp: otp,
                        purpose: otpPurpose,
                        value: pendingValue
                    })
                }
            );


        if (!response) return;


        const data =
            await response.json();


        if (!response.ok) {

            alert(
                data.detail ||
                "Invalid OTP."
            );

            return;
        }


        bootstrap.Modal
            .getInstance(
                document.getElementById(
                    "otpModal"
                )
            )
            .hide();


        document.getElementById(
            "otpInput"
        ).value = "";


        /* Continue original action */

        if (
            otpPurpose ===
            "change_username"
        ) {

            showUsernameModal();

        } else if (
            otpPurpose ===
            "change_password"
        ) {

            showPasswordModal();

        } else if (
            otpPurpose ===
            "change_email"
        ) {

            completeEmailChange();

        } else if (
            otpPurpose ===
            "change_phone"
        ) {

            completePhoneChange();

        }


    } catch (error) {

        console.error(error);

        alert(
            "OTP verification failed."
        );
    }
}


/* 
   RESEND OTP
    */

async function resendOtp() {

    await requestOtp(
        otpPurpose,
        pendingValue
    );
}


/* 
   OTP TIMER
    */

function startOtpTimer() {

    clearInterval(
        otpTimerInterval
    );


    let seconds = 60;


    document.getElementById(
        "resendOtpBtn"
    ).disabled = true;


    document.getElementById(
        "otpTimer"
    ).textContent =
        `You can request another OTP in ${seconds} seconds.`;


    otpTimerInterval =
        setInterval(() => {

            seconds--;


            document.getElementById(
                "otpTimer"
            ).textContent =
                `You can request another OTP in ${seconds} seconds.`;


            if (seconds <= 0) {

                clearInterval(
                    otpTimerInterval
                );


                document.getElementById(
                    "resendOtpBtn"
                ).disabled = false;


                document.getElementById(
                    "otpTimer"
                ).textContent =
                    "You can request a new OTP now.";
            }

        }, 1000);
}


/* 
   CHANGE USERNAME
    */

function startUsernameChange() {

    requestOtp(
        "change_username"
    );
}


function showUsernameModal() {

    const modal =
        new bootstrap.Modal(
            document.getElementById(
                "usernameModal"
            )
        );

    modal.show();
}


async function saveUsername() {

    const username =
        document.getElementById(
            "newUsername"
        ).value.trim();


    if (!username) {

        alert(
            "Enter a username."
        );

        return;
    }


    try {

        const response =
            await apiRequest(
                "/users/change-username",
                {
                    method: "PUT",

                    body: JSON.stringify({
                        username: username
                    })
                }
            );


        if (!response) return;


        const data =
            await response.json();


        if (!response.ok) {

            alert(
                data.detail ||
                "Unable to change username."
            );

            return;
        }


        alert(
            "Username changed successfully."
        );


        location.reload();


    } catch (error) {

        console.error(error);

        alert(
            "Unable to change username."
        );
    }
}


/* 
   CHANGE EMAIL
    */

function startEmailChange() {

    const modal =
        new bootstrap.Modal(
            document.getElementById(
                "emailModal"
            )
        );

    modal.show();
}


async function saveEmail() {

    const email =
        document.getElementById(
            "newEmail"
        ).value.trim();


    if (!email) {

        alert(
            "Enter a valid email."
        );

        return;
    }


    pendingValue = email;


    /*
       Important:

       For changing email, OTP should preferably
       be sent to the NEW email address.

       Backend should handle that securely.
    */

    await requestOtp(
        "change_email",
        email
    );
}


async function completeEmailChange() {

    try {

        const response =
            await apiRequest(
                "/users/change-email",
                {
                    method: "PUT",

                    body: JSON.stringify({
                        email: pendingValue
                    })
                }
            );


        if (!response) return;


        const data =
            await response.json();


        if (!response.ok) {

            alert(
                data.detail ||
                "Unable to change email."
            );

            return;
        }


        alert(
            "Email address changed successfully."
        );


        location.reload();


    } catch (error) {

        console.error(error);

        alert(
            "Unable to change email."
        );
    }
}


/* 
   PHONE
    */

function startPhoneChange() {

    const modal =
        new bootstrap.Modal(
            document.getElementById(
                "phoneModal"
            )
        );

    modal.show();
}


async function savePhone() {

    const phone =
        document.getElementById(
            "newPhone"
        ).value.trim();


    if (!phone) {

        alert(
            "Enter your phone number."
        );

        return;
    }


    pendingValue = phone;


    await requestOtp(
        "change_phone",
        phone
    );
}


async function completePhoneChange() {

    try {

        const response =
            await apiRequest(
                "/users/change-phone",
                {
                    method: "PUT",

                    body: JSON.stringify({
                        phone: pendingValue
                    })
                }
            );


        if (!response) return;


        const data =
            await response.json();


        if (!response.ok) {

            alert(
                data.detail ||
                "Unable to update phone number."
            );

            return;
        }


        alert(
            "Phone number updated successfully."
        );


        location.reload();


    } catch (error) {

        console.error(error);

        alert(
            "Unable to update phone number."
        );
    }
}



function startPasswordChange() {                                                                                         /* PASSWORD */
    requestOtp("change_password");
}
function showPasswordModal() {
    const modal = new bootstrap.Modal(document.getElementById("passwordModal"));
    modal.show();
}
async function savePassword() {
    const password = document.getElementById("newPassword").value;
    const confirmPassword = document.getElementById("confirmPassword").value;
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
    try {
        const response = await apiRequest("/users/change-password",
        {
           method: "PUT", body: JSON.stringify({ password: password })
        });
        if (!response) return;
        const data = await response.json();
        if (!response.ok) {
            alert( data.detail || "Unable to change password.");
            return;
        }
        alert("Password changed successfully. Please login again.");
        localStorage.removeItem("token");
        window.location.href = "login.html";
    } catch (error) {
        console.error(error);
        alert("Unable to change password.");
    }
}

function requestAccountDeletion() {                                                                                      /* DELETE ACCOUNT */
    const modal = new bootstrap.Modal( document.getElementById( "deleteModal" ));
    modal.show();
}
async function deleteAccount() {
    const password = document.getElementById( "deletePassword").value;
    if (!password) {
        alert( "Enter your password." );
        return;
    }
    const confirmed = confirm("Are you absolutely sure you want to delete your account?");
    if (!confirmed) return;
    try {
        const response = await apiRequest("/users/delete-account",
                {
                    method: "DELETE",
                    body: JSON.stringify({ password: password })
                }
            );
        if (!response) return;
        const data = await response.json();
        if (!response.ok) {
            alert( data.detail || "Unable to delete account." );
            return;
        }
        localStorage.clear();
        alert( "Your account has been deleted." );
        window.location.href = "login.html";
    } catch (error) {
        console.error(error);
        alert("Unable to delete account." );
    }
}

function logout() {                                                                                                      /* LOGOUT */
    localStorage.removeItem( "token" );
    window.location.href = "login.html";
}

document.addEventListener( "DOMContentLoaded", loadProfile );                                                            /* INIT */