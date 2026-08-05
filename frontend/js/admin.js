"use strict";
const ENVIRONMENT = Object.freeze({
    LOCAL: "local",
    PRODUCTION: "production"
});

const CURRENT_ENV =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
        ? ENVIRONMENT.LOCAL
        : ENVIRONMENT.PRODUCTION;

/* API CONFIGURATION */
const API_CONFIG = Object.freeze({
    BASE_URL:
        CURRENT_ENV === ENVIRONMENT.LOCAL
            ? "http://127.0.0.1:8000/api"
            : "https://event-booking-api-gnww.onrender.com/api",
    TIMEOUT: 15000,
    RETRY_COUNT: 2,
    CACHE_DURATION: 5 * 60 * 1000,      // 5 minutes
    SEARCH_DELAY: 300,
    REFRESH_INTERVAL: 60000
});

/* APPLICATION CONSTANTS */
const APP = Object.freeze({
    NAME: "EVENTORA",
    VERSION: "1.0.0",
    PANEL: "Admin Dashboard",
    DEFAULT_SECTION: "stats"
});

/*  SECTION CONSTANTS */
const SECTIONS = Object.freeze({
    DASHBOARD: "stats",
    EVENTS: "events",
    CATEGORIES: "categories",
    USERS: "users",
    BOOKINGS: "bookings",
    ANALYTICS: "analytics",
    NOTIFICATIONS: "notifications",
    SETTINGS: "settings"
});

/* APPLICATION STATE */
const AppState = {
    initialized: false,
    loading: false,
    currentSection: APP.DEFAULT_SECTION,
    currentUser: null,
    token: null,
    online: navigator.onLine,
    searchQuery: "",
    lastRefresh: null
};

// CACHE STORAGE
const Cache = {
    sections: {},
    api: {},
    dashboard: {},
    users: {},
    events: {},
    bookings: {},
    analytics: {}
};

/* DOM REFERENCES */
const DOM = {
    body: null,
    sidebar: null,
    topbar: null,
    mainView: null,
    sectionTitle: null,
    headerActions: null,
    greeting: null,
    adminName: null,
    bannerAdminName: null,
    searchInput: null,
    loader: null
};

// REQUEST TRACKER
const RequestState = {
    activeRequests: 0,
    pendingRequests: new Set(),
    lastRequestTime: null
};

// SEARCH STATE
const SearchState = {
    query: "",
    debounceTimer: null,
    enabled: false,
    results: []
};

// DASHBOARD STATE
const DashboardState = {
    statsLoaded: false,
    stats: null,
    recentActivity: []
};

// PERFORMANCE FLAGS
const Performance = {
    enableCache: true,
    enableAnimations: true,
    enableLazyLoading: true,
    enableLogs: true
};

// DATE & TIME CONSTANTS
const DATE_FORMAT = Object.freeze({
    LOCALE: "en-IN",
    DATE: "dd MMM yyyy",
    TIME: "hh:mm A"
});

// STORAGE KEYS
const STORAGE_KEYS = Object.freeze({
    TOKEN: "token",
    USER: "user",
    THEME: "theme",
    SETTINGS: "admin_settings"
});

// DEFAULT PLACEHOLDERS
const PLACEHOLDER = Object.freeze({
    ADMIN_NAME: "Administrator",
    GREETING: "Welcome",
    EMPTY: "--",
    AVATAR: "A"
});

// GLOBAL ERROR STATE
const ErrorState = {
    hasError: false,
    lastError: null
};

// APPLICATION READY FLAG
Object.seal(AppState);
Object.seal(Cache);
Object.seal(DOM);

console.log(
    `%c${APP.NAME} ${APP.PANEL} Initialized`,
    "color:#6d5df6;font-weight:bold;font-size:14px;"
);

console.log("Environment :", CURRENT_ENV);
console.log("API :", API_CONFIG.BASE_URL);
console.log("Version :", APP.VERSION);

// TOKEN MANAGEMENT
function getToken() {
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN);
    if (!token) {
        console.warn("Authentication token not found.");
        return null;
    }
    return token;
}

function saveToken(token) {
    if (!token) return;
    localStorage.setItem(STORAGE_KEYS.TOKEN, token);
    AppState.token = token;
}

function removeToken() {
    localStorage.removeItem(STORAGE_KEYS.TOKEN);
    AppState.token = null;
}

// JWT PARSER
function decodeToken(token = getToken()) {
    if (!token) return null;
    try {
        const payload = token.split(".")[1];
        const decoded = JSON.parse(atob(payload));
        return decoded;
    } catch (error) {
        console.error("Invalid JWT Token", error);
        return null;
    }
}

// TOKEN EXPIRY
function isTokenExpired(token = getToken()) {
    const payload = decodeToken(token);
    if (!payload || !payload.exp) return true;
    const currentTime = Math.floor(Date.now() / 1000);
    return currentTime >= payload.exp;
}

// USER INFORMATION
function getCurrentUser() {
    const payload = decodeToken();
    if (!payload) return null;
    return {
        id: payload.user_id || payload.id,
        username: payload.sub || payload.username || "Administrator",
        email: payload.email || "",
        role: payload.role || "user"
    };
}

// ROLE VALIDATION
function isAdmin() {
    const user = getCurrentUser();
    if (!user) return false;
    return user.role.toLowerCase() === "admin";
}

// SESSION VALIDATION
function isAuthenticated() {
    const token = getToken();
    if (!token) return false;
    if (isTokenExpired(token)) {
        console.warn("Session expired.");
        logout();
        return false;
    }
    return true;
}

// ADMIN PROTECTION
function protectAdminPage() {
    if (!isAuthenticated()) {
        alert("Please login to continue.");
        redirectToLogin();
        return false;
    }
    if (!isAdmin()) {
        alert("Access Denied. Administrator privileges required.");
        window.location.href = "events.html";
        return false;
    }
    AppState.currentUser = getCurrentUser();
    AppState.token = getToken();
    return true;
}

// LOGIN REDIRECTION
function redirectToLogin() {
    window.location.href = "login.html";
}

// LOGOUT
function logout() {
    removeToken();
    localStorage.removeItem(STORAGE_KEYS.USER);
    AppState.currentUser = null;
    AppState.initialized = false;
    redirectToLogin();
}

// SESSION REFRESH CHECK
function validateSession() {
    const valid = protectAdminPage();
    if (!valid) return false;
    console.log("Admin session verified.");
    return true;
}

// AUTO SESSION WATCHER
function startSessionWatcher() {
    setInterval(() => {
        if (!getToken()) return;
        if (isTokenExpired()) {
            alert("Your session has expired. Please login again.");
            logout();
        }
    }, 60000);
}

// SECURITY HELPERS
function hasPermission(role) {
    const user = getCurrentUser();
    if (!user) return false;
    return user.role === role;
}

function requireAdmin(callback) {
    if (!protectAdminPage()) return;
    if (typeof callback === "function") {
        callback();
    }
}

// USER INITIALS
function getUserInitials() {
    const user = getCurrentUser();
    if (!user) return PLACEHOLDER.AVATAR;
    return user.username
        .trim()
        .charAt(0)
        .toUpperCase();
}

// CURRENT USER NAME
function getDisplayName() {
    const user = getCurrentUser();
    if (!user) {
        return PLACEHOLDER.ADMIN_NAME;
    }
    return user.username;
}

// PUBLIC SECURITY API
const Security = {
    getToken,
    saveToken,
    removeToken,
    decodeToken,
    isAuthenticated,
    isTokenExpired,
    getCurrentUser,
    isAdmin,
    protectAdminPage,
    validateSession,
    logout,
    startSessionWatcher,
    getUserInitials,
    getDisplayName,
    hasPermission
};
Object.freeze(Security);

// DOM INITIALIZATION
function initializeDOM() {
    console.log("Initializing DOM references...");
    // Layout
    DOM.body = document.body;
    DOM.sidebar = document.querySelector(".sidebar");
    DOM.topbar = document.querySelector(".topbar");
    DOM.mainView = document.getElementById("admin-main-view");

    /* ---------- Header ---------- */
    DOM.sectionTitle = document.getElementById("section-title");
    DOM.headerActions = document.getElementById("header-actions");

    /* ---------- Welcome Banner ---------- */
    DOM.greeting = document.getElementById("greeting");
    DOM.adminName = document.getElementById("adminName");
    DOM.bannerAdminName = document.getElementById("bannerAdminName");

    /* ---------- Search ---------- */
    DOM.searchInput = document.getElementById("adminEventSearch");

    /* ---------- Navigation ---------- */
    DOM.navigationLinks = document.querySelectorAll(".admin-nav");

    /* ---------- Profile ---------- */
    DOM.avatar = document.querySelector(".avatar");

    /* ---------- Notification ---------- */
    DOM.notificationButton = document.querySelector(".icon-btn");
    DOM.notificationDot = document.querySelector(".notification-dot");

    /* ---------- Welcome Banner ---------- */
    DOM.banner = document.querySelector(".welcome-banner");

    /* ---------- Dashboard ---------- */
    DOM.dashboardHeader = document.querySelector(".dashboard-header");

    /* ---------- Logout ---------- */
    DOM.logoutButton = document.querySelector(".logout-btn");

    console.log("DOM initialization completed.");
}

/* DOM VALIDATION */
function validateDOM() {
    const requiredElements = {
        mainView: DOM.mainView,
        sectionTitle: DOM.sectionTitle,
        greeting: DOM.greeting,
        adminName: DOM.adminName,
        bannerAdminName: DOM.bannerAdminName,
        searchInput: DOM.searchInput
    };

    const missing = [];
    for (const [name, element] of Object.entries(requiredElements)) {
        if (!element) {
            missing.push(name);
        }
    }
    if (missing.length > 0) {
        console.error("Missing DOM elements:", missing);
        throw new Error(
            `DOM Validation Failed: ${missing.join(", ")}`
        );
    }
    console.log("DOM validation successful.");
}

/* DOM READY CHECK */
function isDOMReady() {
    return document.readyState === "interactive" ||
           document.readyState === "complete";
}

/* SAFE DOM INITIALIZER */
function setupDOM() {
    initializeDOM();
    validateDOM();
    return true;
}

/* APPLICATION INITIALIZER */
function initializeApplication() {
    console.log("Starting EVENTORA Admin...");
    try {
        /* Prevent multiple initialization */
        if (AppState.initialized) {
            console.warn("Application already initialized.");
            return;
        }
        /* ---------- Security ---------- */
        if (!protectAdminPage()) {
            return;
        }
        /* ---------- DOM ---------- */
        setupDOM();
        /* ---------- Store User ---------- */
        AppState.currentUser = getCurrentUser();
        AppState.token = getToken();

        /* ---------- Core Event Listeners ---------- */
        bindCoreEvents();
        highlightActiveSidebarLink();

        /* ---------- Load Dashboard Data (only relevant on admin.html) ---------- */
        if (AppState.currentSection === SECTIONS.DASHBOARD && typeof loadDashboard === "function") {
            loadDashboard();
        }

        /* ---------- Session Monitor ---------- */
        startSessionWatcher();

        /* ---------- Application Ready ---------- */
        AppState.initialized = true;
        AppState.lastRefresh = new Date();

        console.log("EVENTORA Admin initialized successfully.");
    }
    catch (error) {
        console.error("Application initialization failed.", error);
        ErrorState.hasError = true;
        ErrorState.lastError = error;
    }
}

/* CORE EVENT BINDING */
function bindCoreEvents() {
    console.log("Binding core events...");
    /* ---------- Sidebar ---------- */
    if (DOM.navigationLinks) {
        DOM.navigationLinks.forEach(link => {
            link.addEventListener("click", handleNavigationClick);
        });
    }

    /* ---------- Search ---------- */
    if (DOM.searchInput) {
        DOM.searchInput.addEventListener(
            "input",
            handleSearchInput
        );
    }
    /* ---------- Logout ---------- */
    if (DOM.logoutButton) {
        DOM.logoutButton.addEventListener(
            "click",
            logout
        );
    }
    console.log("Core events attached.");
}

// MAP EACH SECTION TO ITS OWN PAGE FILE
const SECTION_PAGES = Object.freeze({
    stats: "admin.html",
    events: "events.html",
    categories: "categories.html",
    users: "users.html",
    bookings: "bookings.html",
    analytics: "analytics.html",
    notifications: "notifications.html",
    settings: "settings.html"
});

// NAVIGATION CLICK
// Each sidebar link already has the correct href in the HTML (e.g. events.html),
// so we let the browser navigate normally. We just remember which section was
// clicked so the next page (or a refresh of this one) can restore it if needed.
function handleNavigationClick(event) {
    const section = event.currentTarget.dataset.section;
    if (!section) return;
    console.log("Navigation:", section);
    saveActiveSection(section);
    // No event.preventDefault() here on purpose -- the browser must be
    // allowed to actually follow the link's href and load that page.
}

// PERSIST LAST VISITED SECTION (used only so a hard refresh of admin.html
// still knows which section was last active; each page highlights itself
// based on its own filename, see highlightActiveSidebarLink() below)
function saveActiveSection(section) {
    localStorage.setItem("eventora_admin_section", section);
}

// HIGHLIGHT THE SIDEBAR LINK THAT MATCHES THE PAGE CURRENTLY OPEN
// Call this once on every admin page's DOMContentLoaded. It looks at the
// current URL's filename (e.g. "events.html") and adds the "active" class
// to the matching sidebar link, removing it from all others.
function highlightActiveSidebarLink() {
    if (!DOM.navigationLinks) return;

    let currentFile = window.location.pathname.split("/").pop();
    if (!currentFile) currentFile = "admin.html";

    DOM.navigationLinks.forEach(link => {
        const section = link.dataset.section;
        const linkFile = SECTION_PAGES[section] || "";
        link.classList.toggle("active", linkFile === currentFile);
    });

    const matchedEntry = Object.entries(SECTION_PAGES)
        .find(([, file]) => file === currentFile);

    if (matchedEntry) {
        AppState.currentSection = matchedEntry[0];
        saveActiveSection(matchedEntry[0]);
    }
}

// SEARCH INPUT
function handleSearchInput(event) {
    SearchState.query = event.target.value.trim();
    /* Search implementation
       will be added in Part 1J */
}
/*  APPLICATION READY CALLBACK */
function onApplicationReady() {
    console.log("Application Ready.");
    // Dashboard data (if this is admin.html) is already loaded from
    // initializeApplication() -> highlightActiveSidebarLink() path below,
    // via the "stats" case inside DOMContentLoaded.
}

/*  DOM CONTENT LOADED */
document.addEventListener("DOMContentLoaded", () => {
    initializeApplication();
    onApplicationReady();
});

/* WINDOW RESIZE */
function handleWindowResize() {
    console.log(
        `Window resized : ${window.innerWidth} x ${window.innerHeight}`
    );
}

/*  ONLINE / OFFLINE */
function handleOnline() {
    AppState.online = true;
    console.log("Connection restored.");
}

function handleOffline() {
    AppState.online = false;
    console.warn("You are offline.");
}

/* PAGE VISIBILITY */
function handleVisibilityChange() {
    if (document.hidden) {
        console.log("Application moved to background.");
        return;
    }
    console.log("Application became active.");

    AppState.lastRefresh = new Date();
}

/* GLOBAL KEYBOARD SHORTCUTS */
function handleKeyboardShortcuts(event) {
    /* CTRL + / */
    if (event.ctrlKey && event.key === "/") {
        event.preventDefault();
        console.log("Shortcut triggered.");
    }
    /* ESC */
    if (event.key === "Escape") {
        console.log("Escape pressed.");
    }
}

/*  BEFORE PAGE EXIT */
function handleBeforeUnload() {

    console.log("Cleaning application resources...");

    SearchState.debounceTimer &&
        clearTimeout(SearchState.debounceTimer);

}

/*  GLOBAL ERROR LISTENER */
function handleGlobalError(event) {

    ErrorState.hasError = true;

    ErrorState.lastError = event.error;

    console.error("Unhandled Error:", event.error);

}

/* PROMISE REJECTION */
function handlePromiseRejection(event) {

    console.error("Unhandled Promise:", event.reason);

}

/* REGISTER GLOBAL LISTENERS */
function registerGlobalListeners() {

    window.addEventListener(
        "resize",
        handleWindowResize
    );

    window.addEventListener(
        "online",
        handleOnline
    );

    window.addEventListener(
        "offline",
        handleOffline
    );

    window.addEventListener(
        "beforeunload",
        handleBeforeUnload
    );

    window.addEventListener(
        "error",
        handleGlobalError
    );

    window.addEventListener(
        "unhandledrejection",
        handlePromiseRejection
    );

    document.addEventListener(
        "visibilitychange",
        handleVisibilityChange
    );

    document.addEventListener(
        "keydown",
        handleKeyboardShortcuts
    );

}

/* REMOVE GLOBAL LISTENERS */
function removeGlobalListeners() {

    window.removeEventListener(
        "resize",
        handleWindowResize
    );

    window.removeEventListener(
        "online",
        handleOnline
    );

    window.removeEventListener(
        "offline",
        handleOffline
    );

    window.removeEventListener(
        "beforeunload",
        handleBeforeUnload
    );

    window.removeEventListener(
        "error",
        handleGlobalError
    );

    window.removeEventListener(
        "unhandledrejection",
        handlePromiseRejection
    );

    document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange
    );

    document.removeEventListener(
        "keydown",
        handleKeyboardShortcuts
    );

}

/* REGISTER LIFECYCLE EVENTS */
registerGlobalListeners();

/*
   API URL BUILDER
 */

function buildApiUrl(endpoint = "") {

    if (!endpoint) {
        return API_CONFIG.BASE_URL;
    }

    endpoint = endpoint.trim();

    if (!endpoint.startsWith("/")) {
        endpoint = "/" + endpoint;
    }

    return API_CONFIG.BASE_URL + endpoint;

}

/*
   AUTHORIZATION HEADERS
 */

function getAuthorizationHeaders() {

    const token = getToken();

    const headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    };

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    return headers;

}

/*
   MULTIPART HEADERS
 */

function getMultipartHeaders() {

    const token = getToken();

    const headers = {};

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    return headers;

}

/*
   DEFAULT REQUEST CONFIGURATION
 */

function createRequestConfig(method = "GET", body = null) {

    const config = {

        method,

        headers: getAuthorizationHeaders()

    };

    if (body !== null) {

        config.body = JSON.stringify(body);

    }

    return config;

}

/*
   REQUEST TRACKING
 */

function beginRequest(url) {

    RequestState.activeRequests++;

    RequestState.lastRequestTime = new Date();

    RequestState.pendingRequests.add(url);

    AppState.loading = true;

    if (Performance.enableLogs) {

        console.log(
            `[API] Request Started (${RequestState.activeRequests})`,
            url
        );

    }

}

function finishRequest(url) {

    RequestState.pendingRequests.delete(url);

    RequestState.activeRequests = Math.max(
        0,
        RequestState.activeRequests - 1
    );

    AppState.loading = RequestState.activeRequests > 0;

    if (Performance.enableLogs) {

        console.log(
            `[API] Request Finished (${RequestState.activeRequests})`,
            url
        );

    }

}

/*
   ABORT CONTROLLER
 */

function createAbortController() {

    const controller = new AbortController();

    return controller;

}

/*
   REQUEST TIMEOUT
 */

function createTimeout(controller) {

    return setTimeout(() => {

        controller.abort();

    }, API_CONFIG.TIMEOUT);

}

/*
   CLEAR TIMEOUT
 */

function clearRequestTimeout(timeoutId) {

    if (timeoutId) {

        clearTimeout(timeoutId);

    }

}

/*
   API LOGGER
 */

function logApiRequest(method, url) {

    if (!Performance.enableLogs) return;

    console.groupCollapsed(
        `%c${method}`,
        "color:#6d5df6;font-weight:bold;"
    );

    console.log("URL :", url);

    console.log("Time :", new Date().toLocaleTimeString());

    console.groupEnd();

}

/*
   API LOGGER (RESPONSE)
 */

function logApiResponse(status, url) {

    if (!Performance.enableLogs) return;

    console.log(
        `[API] ${status} -> ${url}`
    );

}

/*
   NETWORK STATUS
 */

function ensureOnline() {

    if (!navigator.onLine) {

        throw new Error(
            "No internet connection."
        );

    }

}
/**********************************************************************
 * EVENTORA ADMIN PANEL
 * Part 1D.2 (UPDATED)
 * Generic HTTP Request Engine
 *
 * Responsibility:
 * - Execute HTTP Requests
 * - Manage Fetch Lifecycle
 * - Handle AbortController
 * - Handle Timeout
 * - Return Raw Response
 **********************************************************************/

/* ============================================================
   CORE REQUEST ENGINE
============================================================ */

async function apiRequest({

    method = "GET",

    endpoint,

    body = null,

    headers = {},

    signal = null

}) {

    ensureOnline();

    const url = buildApiUrl(endpoint);

    const controller = signal
        ? null
        : createAbortController();

    const activeSignal = signal || controller.signal;

    const timeoutId = controller
        ? createTimeout(controller)
        : null;

    beginRequest(url);

    logApiRequest(method, url);

    try {

        const config = {

            method,

            signal: activeSignal,

            headers: {

                ...getAuthorizationHeaders(),

                ...headers

            }

        };

        if (body !== null) {

            if (body instanceof FormData) {

                delete config.headers["Content-Type"];

                config.body = body;

            }

            else {

                config.body = JSON.stringify(body);

            }

        }

        const response = await fetch(

            url,

            config

        );

        return response;

    }

    finally {

        clearRequestTimeout(timeoutId);

        finishRequest(url);

    }

}

/* ============================================================
   GET
============================================================ */

async function apiGet(endpoint, headers = {}) {

    return apiRequest({

        method: "GET",

        endpoint,

        headers

    });

}

/* ============================================================
   POST
============================================================ */

async function apiPost(

    endpoint,

    body,

    headers = {}

) {

    return apiRequest({

        method: "POST",

        endpoint,

        body,

        headers

    });

}

/* ============================================================
   PUT
============================================================ */

async function apiPut(

    endpoint,

    body,

    headers = {}

) {

    return apiRequest({

        method: "PUT",

        endpoint,

        body,

        headers

    });

}

/* ============================================================
   PATCH
============================================================ */

async function apiPatch(

    endpoint,

    body,

    headers = {}

) {

    return apiRequest({

        method: "PATCH",

        endpoint,

        body,

        headers

    });

}

/* ============================================================
   DELETE
============================================================ */

async function apiDelete(

    endpoint,

    headers = {}

) {

    return apiRequest({

        method: "DELETE",

        endpoint,

        headers

    });

}

/* ============================================================
   FILE UPLOAD
============================================================ */

async function apiUpload(

    endpoint,

    formData,

    headers = {}

) {

    return apiRequest({

        method: "POST",

        endpoint,

        body: formData,

        headers

    });

}

/* ============================================================
   FILE DOWNLOAD
============================================================ */

async function apiDownload(endpoint) {

    const response = await apiGet(endpoint);

    return response.blob();

}

/* ============================================================
   API HEALTH CHECK
============================================================ */

async function pingAPI() {

    try {

        const response = await apiGet("/");

        return response.ok;

    }

    catch {

        return false;

    }

}


/**********************************************************************
 * EVENTORA ADMIN PANEL
 * Part 1D.3A - Response Parser
 * -------------------------------------------------
 * Purpose:
 * - Safe Response Parsing
 * - JSON Parsing
 * - Text Parsing
 * - Blob Parsing
 * - Empty Response Handling
 * - Standardized Response Format
 **********************************************************************/

/* ============================================================
   CONTENT TYPE
============================================================ */

function getResponseContentType(response) {

    return response.headers.get("content-type") || "";

}

/* ============================================================
   RESPONSE TYPE
============================================================ */

function isJsonResponse(response) {

    return getResponseContentType(response)
        .toLowerCase()
        .includes("application/json");

}

function isTextResponse(response) {

    const type = getResponseContentType(response).toLowerCase();

    return type.includes("text/") ||
           type.includes("html");

}

function isBlobResponse(response) {

    const type = getResponseContentType(response).toLowerCase();

    return (
        type.includes("image") ||
        type.includes("pdf") ||
        type.includes("octet-stream")
    );

}

/* ============================================================
   SAFE JSON PARSER
============================================================ */

async function parseJson(response) {

    try {

        return await response.json();

    }

    catch {

        return null;

    }

}

/* ============================================================
   SAFE TEXT PARSER
============================================================ */

async function parseText(response) {

    try {

        return await response.text();

    }

    catch {

        return "";

    }

}

/* ============================================================
   SAFE BLOB PARSER
============================================================ */

async function parseBlob(response) {

    try {

        return await response.blob();

    }

    catch {

        return null;

    }

}

/* ============================================================
   EMPTY RESPONSE
============================================================ */

function isEmptyResponse(response) {

    return response.status === 204;

}

/* ============================================================
   MAIN RESPONSE PARSER
============================================================ */

async function parseResponse(response) {

    if (isEmptyResponse(response)) {

        return {

            ok: response.ok,

            status: response.status,

            statusText: response.statusText,

            data: null,

            headers: response.headers

        };

    }

    let data = null;

    if (isJsonResponse(response)) {

        data = await parseJson(response);

    }

    else if (isTextResponse(response)) {

        data = await parseText(response);

    }

    else if (isBlobResponse(response)) {

        data = await parseBlob(response);

    }

    else {

        try {

            data = await response.text();

        }

        catch {

            data = null;

        }

    }

    return {

        ok: response.ok,

        status: response.status,

        statusText: response.statusText,

        data,

        headers: response.headers

    };

}

/* ============================================================
   RESPONSE CLONER
============================================================ */

function cloneParsedResponse(parsed) {

    return {

        ...parsed,

        data: structuredClone(parsed.data)

    };

}

/* ============================================================
   DEBUG LOGGER
============================================================ */

function logParsedResponse(parsed) {

    if (!Performance.enableLogs) return;

    console.groupCollapsed(

        `%cParsed Response (${parsed.status})`,

        "color:#10b981;font-weight:bold"

    );

    console.log("Success :", parsed.ok);

    console.log("Status  :", parsed.status);

    console.log("Data    :", parsed.data);

    console.groupEnd();

}

/* ============================================================
   PUBLIC PARSER
============================================================ */

async function parseApiResponse(response) {

    const parsed = await parseResponse(response);

    logParsedResponse(parsed);

    return parsed;

}

/**********************************************************************
 * END OF PART 1D.3A
 *
 * Next:
 * Part 1D.3B
 * HTTP Status Handler
 * APIError Class
 * Centralized Error Handling
 **********************************************************************/



 /**********************************************************************
 * EVENTORA ADMIN PANEL
 * Part 1D.3B - HTTP Status Handler & Centralized Error Handling
 * -------------------------------------------------------------
 * Purpose:
 * - APIError Class
 * - HTTP Status Handling
 * - Authentication Handling
 * - Authorization Handling
 * - Server Error Handling
 * - Client Error Handling
 **********************************************************************/

/* ============================================================
   API ERROR CLASS
============================================================ */

class APIError extends Error {

    constructor(message, status, data = null) {

        super(message);

        this.name = "APIError";

        this.status = status;

        this.data = data;

        this.timestamp = new Date();

    }

}

/* ============================================================
   SUCCESS STATUS
============================================================ */

function isSuccessStatus(status) {

    return status >= 200 && status < 300;

}

/* ============================================================
   CLIENT ERROR
============================================================ */

function isClientError(status) {

    return status >= 400 && status < 500;

}

/* ============================================================
   SERVER ERROR
============================================================ */

function isServerError(status) {

    return status >= 500;

}

/* ============================================================
   DEFAULT ERROR MESSAGE
============================================================ */

function getDefaultErrorMessage(status) {

    switch (status) {

        case 400:
            return "Bad Request.";

        case 401:
            return "Session expired. Please login again.";

        case 403:
            return "You don't have permission to perform this action.";

        case 404:
            return "Requested resource not found.";

        case 405:
            return "Method not allowed.";

        case 409:
            return "Resource conflict.";

        case 422:
            return "Validation failed.";

        case 429:
            return "Too many requests.";

        case 500:
            return "Internal server error.";

        case 502:
            return "Bad gateway.";

        case 503:
            return "Service temporarily unavailable.";

        default:
            return "Unexpected server response.";

    }

}

/* ============================================================
   AUTHENTICATION FAILURE
============================================================ */

function handleUnauthorized(parsed) {

    console.warn("Authentication expired.");

    removeToken();

    AppState.currentUser = null;

    redirectToLogin();

    throw new APIError(

        parsed.data?.detail ||

        "Authentication required.",

        parsed.status,

        parsed.data

    );

}

/* ============================================================
   AUTHORIZATION FAILURE
============================================================ */

function handleForbidden(parsed) {

    throw new APIError(

        parsed.data?.detail ||

        "Access denied.",

        parsed.status,

        parsed.data

    );

}

/* ============================================================
   VALIDATION FAILURE
============================================================ */

function handleValidationError(parsed) {

    throw new APIError(

        parsed.data?.detail ||

        "Validation failed.",

        parsed.status,

        parsed.data

    );

}

/* ============================================================
   SERVER FAILURE
============================================================ */

function handleServerError(parsed) {

    throw new APIError(

        getDefaultErrorMessage(parsed.status),

        parsed.status,

        parsed.data

    );

}

/* ============================================================
   GENERIC ERROR
============================================================ */

function handleGenericError(parsed) {

    const message =

        parsed.data?.detail ||

        parsed.statusText ||

        getDefaultErrorMessage(parsed.status);

    throw new APIError(

        message,

        parsed.status,

        parsed.data

    );

}

/* ============================================================
   MAIN STATUS HANDLER
============================================================ */

function processApiResponse(parsed) {

    if (isSuccessStatus(parsed.status)) {

        return parsed;

    }

    switch (parsed.status) {

        case 401:

            handleUnauthorized(parsed);

            break;

        case 403:

            handleForbidden(parsed);

            break;

        case 422:

            handleValidationError(parsed);

            break;

        case 500:

        case 502:

        case 503:

            handleServerError(parsed);

            break;

        default:

            handleGenericError(parsed);

    }

}

/* ============================================================
   SAFE PARSER
============================================================ */

async function handleApiResponse(response) {

    const parsed = await parseApiResponse(response);

    return processApiResponse(parsed);

}

/* ============================================================
   ERROR LOGGER
============================================================ */

function logAPIError(error) {

    if (!(error instanceof APIError)) {

        console.error(error);

        return;

    }

    console.groupCollapsed(

        `%cAPI ERROR ${error.status}`,

        "color:#ef4444;font-weight:bold"

    );

    console.log("Message :", error.message);

    console.log("Status  :", error.status);

    console.log("Time    :", error.timestamp);

    console.log("Data    :", error.data);

    console.groupEnd();

}

/**********************************************************************
 * END OF PART 1D.3B
 *
 * Next:
 * Part 1D.3C
 * Retry Engine
 * Timeout Recovery
 * Network Recovery
 **********************************************************************/



// =========================
// Part 1E.1 - Common Helpers
// =========================

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

const generateId = (prefix = "id") =>
    `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2,8)}`;

const deepClone = value => structuredClone(value);

const capitalize = str =>
    typeof str === "string" && str.length
        ? str.charAt(0).toUpperCase() + str.slice(1)
        : "";

const isString = value => typeof value === "string";

const isNumber = value => typeof value === "number" && !Number.isNaN(value);

const isObject = value =>
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value);

const isFunction = value => typeof value === "function";

const isEmpty = value => {

    if (value == null) return true;

    if (Array.isArray(value) || isString(value))
        return value.length === 0;

    if (isObject(value))
        return Object.keys(value).length === 0;

    return false;

};

const safeParseJSON = (json, fallback = null) => {

    try {

        return JSON.parse(json);

    } catch {

        return fallback;

    }

};

const safeStringify = (value, fallback = "") => {

    try {

        return JSON.stringify(value);

    } catch {

        return fallback;

    }

};

const escapeHTML = value => {

    if (!isString(value)) return "";

    return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");

};

const randomInt = (min, max) =>
    Math.floor(Math.random() * (max - min + 1)) + min;

const clamp = (value, min, max) =>
    Math.min(Math.max(value, min), max);

const noop = () => {};

const now = () => Date.now();

const timestamp = () => new Date().toISOString();

const hasOwn = (obj, key) =>
    Object.prototype.hasOwnProperty.call(obj, key);

const arrayify = value =>
    Array.isArray(value) ? value : [value];

const uniqueArray = array =>
    [...new Set(array)];

const removeDuplicates = uniqueArray;

const getRandomItem = array =>
    Array.isArray(array) && array.length
        ? array[randomInt(0, array.length - 1)]
        : null;

const chunkArray = (array, size = 10) => {

    const result = [];

    for (let i = 0; i < array.length; i += size)
        result.push(array.slice(i, i + size));

    return result;

};

const compareText = (a, b) =>
    String(a).localeCompare(String(b), undefined, {
        sensitivity: "base"
    });

const delayExecution = async (callback, ms = 300) => {

    await sleep(ms);

    if (isFunction(callback))
        callback();

};


// =========================
// Part 1E.2 - Date & Number Utilities
// =========================

// Current Date
const getCurrentDate = () => new Date();

// Current Timestamp
const getTimestamp = () => Date.now();

// Format Date
function formatDate(date, locale = "en-IN") {

    if (!date) return "-";

    return new Date(date).toLocaleDateString(locale, {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });

}

// Format Time
function formatTime(date, locale = "en-IN") {

    if (!date) return "-";

    return new Date(date).toLocaleTimeString(locale, {
        hour: "2-digit",
        minute: "2-digit"
    });

}

// Format Date & Time
function formatDateTime(date, locale = "en-IN") {

    if (!date) return "-";

    return new Date(date).toLocaleString(locale, {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });

}

// Relative Time
function timeAgo(date) {

    if (!date) return "-";

    const seconds = Math.floor((Date.now() - new Date(date)) / 1000);

    const units = [
        { limit: 60, value: 1, label: "second" },
        { limit: 3600, value: 60, label: "minute" },
        { limit: 86400, value: 3600, label: "hour" },
        { limit: 2592000, value: 86400, label: "day" },
        { limit: 31536000, value: 2592000, label: "month" },
        { limit: Infinity, value: 31536000, label: "year" }
    ];

    for (const unit of units) {

        if (seconds < unit.limit) {

            const value = Math.floor(seconds / unit.value);

            return `${value} ${unit.label}${value !== 1 ? "s" : ""} ago`;

        }

    }

}

// Format Currency
function formatCurrency(amount) {

    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0
    }).format(Number(amount || 0));

}

// Format Number
function formatNumber(number) {

    return new Intl.NumberFormat("en-IN").format(Number(number || 0));

}

// Format Percentage
function formatPercentage(value, digits = 1) {

    return `${Number(value || 0).toFixed(digits)}%`;

}

// Format File Size
function formatFileSize(bytes) {

    if (!bytes) return "0 B";

    const units = ["B", "KB", "MB", "GB", "TB"];

    let index = 0;
    let size = bytes;

    while (size >= 1024 && index < units.length - 1) {

        size /= 1024;
        index++;

    }

    return `${size.toFixed(2)} ${units[index]}`;

}

// Format Compact Number
function formatCompactNumber(number) {

    return new Intl.NumberFormat("en", {
        notation: "compact",
        maximumFractionDigits: 1
    }).format(Number(number || 0));

}

// Round Number
function round(value, decimals = 2) {

    return Number(Number(value).toFixed(decimals));

}

// Random Number
function randomBetween(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

// Check Valid Date
function isValidDate(date) {

    return !isNaN(new Date(date).getTime());

}


// =========================
// Part 1E.3 - DOM Utilities
// =========================

// Get single element
const $ = (selector, parent = document) =>
    parent.querySelector(selector);

// Get multiple elements
const $$ = (selector, parent = document) =>
    [...parent.querySelectorAll(selector)];

// Get element by ID
const byId = id =>
    document.getElementById(id);

// Check if element exists
const exists = element =>
    element !== null && element !== undefined;

// Create element
function createElement(tag, className = "", text = "") {

    const element = document.createElement(tag);

    if (className)
        element.className = className;

    if (text)
        element.textContent = text;

    return element;

}

// Append child
function append(parent, ...children) {

    children.forEach(child => {

        if (exists(child))
            parent.appendChild(child);

    });

}

// Remove element
function removeElement(element) {

    if (exists(element))
        element.remove();

}

// Remove all children
function clearElement(element) {

    if (exists(element))
        element.innerHTML = "";

}

// Show element
function show(element, display = "block") {

    if (exists(element))
        element.style.display = display;

}

// Hide element
function hide(element) {

    if (exists(element))
        element.style.display = "none";

}

// Toggle visibility
function toggle(element, visible) {

    if (!exists(element)) return;

    element.style.display = visible ? "block" : "none";

}

// Add class
function addClass(element, className) {

    if (exists(element))
        element.classList.add(className);

}

// Remove class
function removeClass(element, className) {

    if (exists(element))
        element.classList.remove(className);

}

// Toggle class
function toggleClass(element, className) {

    if (exists(element))
        element.classList.toggle(className);

}

// Check class
function hasClass(element, className) {

    return exists(element)
        ? element.classList.contains(className)
        : false;

}

// Set text
function setText(element, text = "") {

    if (exists(element))
        element.textContent = text;

}

// Set HTML
function setHTML(element, html = "") {

    if (exists(element))
        element.innerHTML = html;

}

// Get input value
function getValue(element) {

    return exists(element)
        ? element.value.trim()
        : "";

}

// Set input value
function setValue(element, value = "") {

    if (exists(element))
        element.value = value;

}

// Enable element
function enable(element) {

    if (exists(element))
        element.disabled = false;

}

// Disable element
function disable(element) {

    if (exists(element))
        element.disabled = true;

}

// Set attribute
function setAttribute(element, name, value) {

    if (exists(element))
        element.setAttribute(name, value);

}

// Remove attribute
function removeAttribute(element, name) {

    if (exists(element))
        element.removeAttribute(name);

}

// Scroll into view
function scrollToElement(element, behavior = "smooth") {

    if (exists(element)) {

        element.scrollIntoView({
            behavior,
            block: "start"
        });

    }

}

// Focus element
function focusElement(element) {

    if (exists(element))
        element.focus();

}

// Event listener
function on(element, event, handler, options = false) {

    if (exists(element))
        element.addEventListener(event, handler, options);

}

// Remove event listener
function off(element, event, handler) {

    if (exists(element))
        element.removeEventListener(event, handler);

}

// Dispatch custom event
function emit(name, detail = {}) {

    document.dispatchEvent(
        new CustomEvent(name, { detail })
    );

}

// =========================
// Part 1E.4 - Performance Utilities
// =========================

// Debounce function
function debounce(callback, delay = 300) {

    let timer;

    return function (...args) {

        clearTimeout(timer);

        timer = setTimeout(() => {
            callback.apply(this, args);
        }, delay);

    };

}

// Throttle function
function throttle(callback, limit = 300) {

    let waiting = false;

    return function (...args) {

        if (waiting) return;

        callback.apply(this, args);

        waiting = true;

        setTimeout(() => {
            waiting = false;
        }, limit);

    };

}

// Execute in next animation frame
function nextFrame(callback) {

    return requestAnimationFrame(callback);

}

// Cancel animation frame
function cancelFrame(id) {

    cancelAnimationFrame(id);

}

// Execute when browser is idle
function runWhenIdle(callback, timeout = 1000) {

    if ("requestIdleCallback" in window) {

        return requestIdleCallback(callback, { timeout });

    }

    return setTimeout(callback, 1);

}

// Cancel idle callback
function cancelIdle(id) {

    if ("cancelIdleCallback" in window) {

        cancelIdleCallback(id);

        return;
    }

    clearTimeout(id);

}

// Measure execution time
async function measureExecution(name, callback) {

    const start = performance.now();

    const result = await callback();

    const end = performance.now();

    console.log(`${name}: ${(end - start).toFixed(2)} ms`);

    return result;

}

// Simple performance profiler
function profile(name, callback) {

    console.time(name);

    const result = callback();

    console.timeEnd(name);

    return result;

}

// Execute asynchronously
function defer(callback) {

    return Promise.resolve().then(callback);

}

// Execute after current call stack
function nextTick(callback) {

    return queueMicrotask(callback);

}

// Batch DOM updates
function batchDOMUpdate(callback) {

    requestAnimationFrame(() => {

        callback();

    });

}

// Prevent duplicate execution
function once(callback) {

    let executed = false;

    let result;

    return function (...args) {

        if (executed) return result;

        executed = true;

        result = callback.apply(this, args);

        return result;

    };

}

// Retry execution
async function retry(callback, retries = 3, delay = 500) {

    for (let attempt = 1; attempt <= retries; attempt++) {

        try {

            return await callback();

        }

        catch (error) {

            if (attempt === retries)
                throw error;

            await sleep(delay);

        }

    }

}

// Poll until condition is true
function waitUntil(condition, interval = 100, timeout = 5000) {

    return new Promise((resolve, reject) => {

        const start = Date.now();

        const timer = setInterval(() => {

            if (condition()) {

                clearInterval(timer);

                resolve(true);

                return;

            }

            if (Date.now() - start >= timeout) {

                clearInterval(timer);

                reject(new Error("Operation timed out."));

            }

        }, interval);

    });

}

// Memoize expensive functions
function memoize(callback) {

    const cache = new Map();

    return (...args) => {

        const key = JSON.stringify(args);

        if (cache.has(key))
            return cache.get(key);

        const result = callback(...args);

        cache.set(key, result);

        return result;

    };

}

// Execute only if browser is online
function runIfOnline(callback) {

    if (navigator.onLine) {

        callback();

    }

}

// Execute after page is fully loaded
function onPageReady(callback) {

    if (document.readyState === "complete") {

        callback();

        return;

    }

    window.addEventListener("load", callback);

}

// =========================
// Part 1F - Loader & Error Handler
// =========================

// Show global loader
function showLoader(message = "Loading...") {

    if (!DOM.loader) return;

    DOM.loader.style.display = "flex";

    const text = DOM.loader.querySelector(".loader-text");

    if (text)
        text.textContent = message;

    AppState.loading = true;

}

// Hide global loader
function hideLoader() {

    if (!DOM.loader) return;

    DOM.loader.style.display = "none";

    AppState.loading = false;

}

// Toggle loader
function toggleLoader(show, message = "Loading...") {

    show
        ? showLoader(message)
        : hideLoader();

}

// Show button loading
function setButtonLoading(button, loading = true, text = "Loading...") {

    if (!button) return;

    if (loading) {

        button.dataset.originalText = button.innerHTML;

        button.disabled = true;

        button.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2"></span>
            ${text}
        `;

        return;

    }

    button.disabled = false;

    button.innerHTML =
        button.dataset.originalText || "Submit";

}

// Show alert
function showAlert(message, type = "info") {

    const classes = {

        success: "alert-success",

        danger: "alert-danger",

        warning: "alert-warning",

        info: "alert-info"

    };

    const container = byId("alertContainer");

    if (!container) {

        console.log(`[${type.toUpperCase()}] ${message}`);

        return;

    }

    container.innerHTML = `
        <div class="alert ${classes[type] || classes.info} alert-dismissible fade show">
            ${escapeHTML(message)}
            <button class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

}

// Success message
function showSuccess(message) {

    showAlert(message, "success");

}

// Error message
function showError(message) {

    showAlert(message, "danger");

}

// Warning message
function showWarning(message) {

    showAlert(message, "warning");

}

// Info message
function showInfo(message) {

    showAlert(message, "info");

}

// Clear alerts
function clearAlerts() {

    const container = byId("alertContainer");

    if (container)
        container.innerHTML = "";

}

// Handle API error
function handleError(error) {

    console.error(error);

    ErrorState.hasError = true;

    ErrorState.lastError = error;

    if (error instanceof APIError) {

        showToastError(error.message);

        return;

    }

    if (error.name === "AbortError") {

        showToastWarning("Request timed out.");

        return;

    }

    if (!navigator.onLine) {

        showToastWarning("No internet connection.");

        return;

    }

    showToastError("Something went wrong.");

}

// Reset error state
function clearErrorState() {

    ErrorState.hasError = false;

    ErrorState.lastError = null;

}

// Handle async actions
async function executeTask(task, loaderText = "Loading...") {

    try {

        showLoader(loaderText);

        clearErrorState();

        return await task();

    }

    catch (error) {

        handleError(error);

        throw error;

    }

    finally {

        hideLoader();

    }

}

// Confirm action
function confirmAction(message = "Are you sure?") {

    return window.confirm(message);

}

// Copy text
async function copyToClipboard(text) {

    try {

        await navigator.clipboard.writeText(text);

        showToastSuccess("Copied successfully.");

    }

    catch {

        showToastError("Unable to copy.");

    }

}

// Global JS errors
window.addEventListener("error", event => {

    handleError(event.error);

});

// Promise rejection
window.addEventListener("unhandledrejection", event => {

    handleError(event.reason);

});


// =========================
// Part 1F.2 - Toast Manager
// =========================

// Create toast container
function initializeToastContainer() {

    if (byId("toastContainer")) return;

    const container = createElement("div");

    container.id = "toastContainer";

    container.className =
        "toast-container position-fixed top-0 end-0 p-3";

    document.body.appendChild(container);

}

// Create toast
function createToast(message, type = "info", duration = 4000) {

    initializeToastContainer();

    const colors = {
        success: "success",
        danger: "danger",
        warning: "warning",
        info: "primary"
    };

    const toast = document.createElement("div");

    toast.className =
        `toast align-items-center text-bg-${colors[type] || "primary"} border-0`;

    toast.role = "alert";

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${escapeHTML(message)}
            </div>
            <button
                type="button"
                class="btn-close btn-close-white me-2 m-auto"
                data-bs-dismiss="toast">
            </button>
        </div>
    `;

    byId("toastContainer").appendChild(toast);

    const bsToast = new bootstrap.Toast(toast, {
        delay: duration
    });

    bsToast.show();

    toast.addEventListener("hidden.bs.toast", () => {

        toast.remove();

    });

}

// Success toast
function showToastSuccess(message) {

    createToast(message, "success");

}

// Error toast
function showToastError(message) {

    createToast(message, "danger");

}

// Warning toast
function showToastWarning(message) {

    createToast(message, "warning");

}

// Info toast
function showToastInfo(message) {

    createToast(message, "info");

}

// Clear all toasts
function clearToasts() {

    const container = byId("toastContainer");

    if (!container) return;

    container.innerHTML = "";

}

// =========================
// Part 1G - Dynamic Greeting & Header
// =========================

// Greeting based on current time
function getGreeting() {

    const hour = new Date().getHours();

    if (hour < 12) return "Good Morning";
    if (hour < 17) return "Good Afternoon";
    if (hour < 21) return "Good Evening";

    return "Good Night";

}

// Get user initials
function getInitials(name = "") {

    return name
        .trim()
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map(word => word[0].toUpperCase())
        .join("");

}

// Update greeting
function updateGreeting() {

    if (!DOM.greeting) return;

    setText(DOM.greeting, getGreeting());

}

// Update admin name (both header profile name + welcome banner name)
function updateAdminName() {

    const name =
        AppState.currentUser?.full_name ||
        AppState.currentUser?.name ||
        AppState.currentUser?.username ||
        "Administrator";

    if (DOM.adminName) {
        setText(DOM.adminName, name);
    }

    if (DOM.bannerAdminName) {
        setText(DOM.bannerAdminName, name);
    }

}

// Update admin role (no dedicated element in current HTML, kept as no-op guard)
function updateAdminRole() {

    if (!DOM.adminRole) return;

    const role =
        AppState.currentUser?.role ||
        "Administrator";

    setText(DOM.adminRole, capitalize(role));

}

// Update profile avatar (uses the .avatar element that actually exists)
function updateProfileAvatar() {

    if (!DOM.avatar) return;

    const name =
        AppState.currentUser?.full_name ||
        AppState.currentUser?.name ||
        AppState.currentUser?.username ||
        "Administrator";

    setText(
        DOM.avatar,
        getInitials(name)
    );

}

// Update current date (no dedicated element in current HTML, kept as no-op guard)
function updateCurrentDate() {

    if (!DOM.currentDate) return;

    setText(
        DOM.currentDate,
        formatDateTime(new Date())
    );

}

// Update page title (uses #section-title which actually exists)
function updatePageTitle(title = "Dashboard") {

    if (!DOM.sectionTitle) return;

    setText(DOM.sectionTitle, title);

}

// Refresh header
function refreshHeader() {

    updateGreeting();

    updateAdminName();

    updateAdminRole();

    updateProfileAvatar();

    updateCurrentDate();

}

// Refresh greeting every minute
function startGreetingTimer() {

    setInterval(() => {

        updateGreeting();

        updateCurrentDate();

    }, 60000);

}

// Get current section
function getCurrentSection() {

    return AppState.currentSection;

}


// =========================
// Part 1I.1 - Dashboard Data Loading
// =========================

// Load dashboard
async function loadDashboard() {

    try {

        showLoader("Loading Dashboard...");

        await Promise.all([
            loadDashboardStats(),
            loadRecentEvents(),
            loadRecentBookings(),
            loadRecentUsers()
        ]);

        renderDashboard();

    } catch (error) {

        handleError(error);

    } finally {

        hideLoader();

    }

}

// Load statistics
// NOTE: endpoint path depends on how main.py registers the analytics router's
// prefix (e.g. app.include_router(analytics.router, prefix="/analytics")).
// This matches analytics.py's "/stats" route. Adjust the prefix below if your
// main.py mounts it differently.
async function loadDashboardStats() {

    const response = await apiGet("/analytics/stats");

    const result = await handleApiResponse(response);

    AppState.dashboardStats = result.data || {};

}

// Load recent events
// NOTE: events.py's GET "/" route already supports "limit" as a query param.
// Adjust the prefix below to match how main.py mounts the events router.
async function loadRecentEvents() {

    const response = await apiGet("/events/?limit=5");

    const result = await handleApiResponse(response);

    AppState.recentEvents = result.data || [];

}

// Load recent bookings
// NOTE: admin.py only exposes GET "/bookings" (all bookings, no "recent" or
// "limit" support). We fetch everything and take the first 5 client-side
// until a dedicated "/recent" backend route is added.
async function loadRecentBookings() {

    const response = await apiGet("/admin/bookings");

    const result = await handleApiResponse(response);

    const all = result.data || [];

    AppState.recentBookings = all.slice(0, 5);

}

// Load recent users
// NOTE: admin.py only exposes GET "/users" (all users, no "recent" or
// "limit" support). We fetch everything and take the first 5 client-side
// until a dedicated "/recent" backend route is added.
async function loadRecentUsers() {

    const response = await apiGet("/admin/users");

    const result = await handleApiResponse(response);

    const all = result.data || [];

    AppState.recentUsers = all.slice(0, 5);

}

// Refresh dashboard
async function refreshDashboard() {

    await loadDashboard();

    renderDashboard();

}

// Auto refresh
function startDashboardRefresh(interval = 60000) {

    setInterval(() => {

        if (AppState.currentSection === "dashboard") {

            refreshDashboard();

        }

    }, interval);

}

// =========================
// Part 1I.2 - Dashboard Rendering
// =========================

// Render complete dashboard
function renderDashboard() {

    renderDashboardStats();

    renderRecentEvents();

    renderRecentBookings();

    renderRecentUsers();

    updateDashboardTimestamp();

}

// Render statistic cards
function renderDashboardStats() {
    const stats = AppState.dashboardStats || {};
    setText(byId("totalEvents"), formatNumber(stats.total_events || 0));
    setText(byId("totalUsers"), formatNumber(stats.total_users || 0));
    setText(byId("totalBookings"), formatNumber(stats.total_bookings || 0));
    setText(byId("totalRevenue"), formatCurrency(stats.revenue || stats.total_revenue || 0));
}

// Render recent events
function renderRecentEvents() {
    const table = byId("recentEventsTable");
    if (!table) return;
    const events = AppState.recentEvents || [];
    if (!events.length) {
        table.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-muted">
                    No events found
                </td>
            </tr>
        `;
        return;
    }
    table.innerHTML = events.map(event => `
        <tr>
            <td>${escapeHTML(event.title)}</td>
            <td>${escapeHTML(event.category || "-")}</td>
            <td>${formatDate(event.date_time)}</td>
            <td>${event.available_seats}</td>
        </tr>
    `).join("");
}

// Render recent bookings
function renderRecentBookings() {
    const table = byId("recentBookingsTable");
    if (!table) return;
    const bookings = AppState.recentBookings || [];
    if (!bookings.length) {
        table.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-muted">
                    No bookings found
                </td>
            </tr>
        `;
        return;
    }
    table.innerHTML = bookings.map(booking => `
        <tr>
            <td>${escapeHTML(booking.user_name || "-")}</td>
            <td>${escapeHTML(booking.event_title || ("Event #" + booking.event_id) || "-")}</td>
            <td>${booking.tickets ?? booking.seats ?? "-"}</td>
            <td>${formatDate(booking.booking_time || booking.booking_date)}</td>
        </tr>
    `).join("");
}

// Render recent users
function renderRecentUsers() {
    const table = byId("recentUsersTable");
    if (!table) return;
    const users = AppState.recentUsers || [];
    if (!users.length) {
        table.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-muted">
                    No users found
                </td>
            </tr>
        `;
        return;
    }
    table.innerHTML = users.map(user => `
        <tr>
            <td>${escapeHTML(user.name || user.username || "-")}</td>
            <td>${escapeHTML(user.email || "-")}</td>
            <td>${capitalize(user.role || "user")}</td>
            <td>${formatDate(user.created_at)}</td>
        </tr>
    `).join("");
}

// Update last refresh time
function updateDashboardTimestamp() {
    const element = byId("lastUpdated");
    if (!element) return;
    element.textContent =
        "Last Updated : " +
        formatTime(new Date());
}

// Clear dashboard
function clearDashboard() {
    AppState.dashboardStats = {};
    AppState.recentEvents = [];
    AppState.recentBookings = [];
    AppState.recentUsers = [];
    renderDashboard();
}