// Functions related to the interaction with the server, including html cleanup
// and error handling.


export { escape_html, hash, assert, api, api_put, api_login,
         storage_get, storage_set, storage_remove, is_valid_token };


// API calls.

// Return the data coming from an api endpoint (like "/trees/<id>/size").
async function api(endpoint) {
    const response = await fetch(endpoint);

    await assert(response.status === 200, "Request failed :(", response);

    return await response.json();
}


// Make a PUT api call.
async function api_put(endpoint, params=undefined) {
    let response = await api_put_with_login(endpoint, params);

    if (response.status === 401) {  // unauthorized
        storage_remove("login");  // so we'll try with guest login
        response = await api_put_with_login(endpoint, params);
    }

    await assert(response.status === 200, "Modification failed :(", response);
}

async function api_put_with_login(endpoint, params=undefined) {
    let login = storage_get("login");
    if (!login) {
        login = await api_login("guest");
        storage_set("login", login);
    }

    return await fetch(endpoint, {
        method: "PUT",
        headers: {"Content-Type": "application/json",
                  "Authorization": `Bearer ${login.token}`},
        body: JSON.stringify(params),
    });
}


// Log in as user and return credentials (includes the bearer token).
async function api_login(user, password) {
    if (user === "guest" && !password)
        password = "123";

    const response = await fetch("/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username: user, password: password}),
    });

    await assert(response.status === 200, `Cannot log in as ${user}`, response);

    return await response.json();
}


async function is_valid_token(token) {
    const response = await fetch("/info", {
        headers: {"Authorization": `Bearer ${token}`},
    });
    return response.status === 200;  // status will be 401 for unauthorized
}


// Convenience functions to get/set/remove an object from localStorage.

function storage_get(name) {
    return JSON.parse(localStorage.getItem(name));
}

function storage_set(name, data) {
    return localStorage.setItem(name, JSON.stringify(data));
}

function storage_remove(name) {
    localStorage.removeItem(name);
}


// Text manipulation.

// Return the original text with the given replacements made.
function escape_html(text, replacements=[
        "& &amp;", "< &lt;", "> &gt;", '" &quot;', "' &#039;"]) {
    const pairs = replacements.map(pair => pair.split(" "));
    return pairs.reduce((t, [a, b]) => t.replace(new RegExp(a, "g"), b), text);
}


// Return a ~64-bit hash. Inspired by https://stackoverflow.com/questions/7616461
function hash(str) {
    const acc = (h, char) => ((h << 5) - h + char.charCodeAt(0)) | 0;
    const hash32 = s => (s.split("").reduce(acc, 0) - (1 << 31)).toString(36);
    const h32 = hash32(str);
    return h32 + hash32(h32 + str);
}


// Error handling.

async function assert(condition, message, response=undefined) {
    if (!condition) {
        const response_error = response ? `<br><br>
            <b>Response status:</b> ${response.status}<br>
            <b>Message:</b> ${await get_error(response)}` : "";
        throw new Error(message + response_error);
    }
}

async function get_error(response) {
    try {
        const data = await response.json();
        return data.message;
    }
    catch (error) {
        return response.statusText;
    }
}
