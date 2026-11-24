// Helpers shared by every page. Load config.js before this file.
const PROPERTY_URL = window.APP_CONFIG.PROPERTY_URL;
const TASKS_URL = window.APP_CONFIG.TASKS_URL;

// The login token from the property service, kept in the browser between pages.
function getToken() {
    return localStorage.getItem("token");
}

function saveToken(token) {
    localStorage.setItem("token", token);
}

// Logging out only forgets the token: the services keep no session.
function logOut() {
    localStorage.removeItem("token");
}

// Pages that need a logged-in user call this first.
function requireLogin() {
    if (!getToken()) {
        window.location.href = "login.html";
    }
}

// Calls one service and returns its JSON body (null for an empty 204 reply).
// On failure it throws an Error whose message is the service's own "error" text.
async function api(baseUrl, path, method = "GET", body = undefined) {
    const headers = {};
    if (getToken()) {
        headers["Authorization"] = "Bearer " + getToken();
    }
    if (body !== undefined) {
        headers["Content-Type"] = "application/json";
    }

    let response;
    try {
        response = await fetch(baseUrl + path, {
            method: method,
            headers: headers,
            body: body === undefined ? undefined : JSON.stringify(body),
        });
    } catch {
        // fetch only rejects when no reply came back at all: the service is down or unreachable
        throw new Error("could not reach the service");
    }

    // a missing or expired token: back to the login page (but a wrong password on /login is shown)
    if (response.status === 401 && path !== "/login") {
        logOut();
        window.location.href = "login.html";
    }

    const data = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error((data && data.error) || "Request failed (HTTP " + response.status + ")");
    }
    return data;
}

// Creates an element with an optional class and text. textContent (never innerHTML)
// means text from the server is shown as text and can never run as HTML.
function el(tag, className = "", text = "") {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
}

// Shows a message in an (initially hidden) error paragraph; an empty message hides it.
function showError(element, message) {
    element.textContent = message;
    element.hidden = !message;
}
