// Where the browser finds the two services. These are the local docker compose ports;
// the deploy workflow overwrites this file with the Azure URLs. Pages read URLs only from here.
window.APP_CONFIG = {
    PROPERTY_URL: "http://localhost:8001",
    TASKS_URL: "http://localhost:8002",
};
