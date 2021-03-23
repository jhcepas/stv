'use strict';


document.addEventListener("DOMContentLoaded", update);


function get_login_info() {
    return JSON.parse(localStorage.getItem("login_info"));
}

function save_login_info(data) {
    localStorage.setItem("login_info", JSON.stringify(data));
}

function clear_login_info() {
    localStorage.removeItem("login_info");
}

window.clear_login_info = clear_login_info;  // so it can be called in onclick


function update() {
    const login = get_login_info();
    if (login !== null) {
        div_login.style.display = "none";
        div_upload.style.display = "initial";
        div_info.innerHTML =
            `Logged in as ${login.username} (${login.name})<br>` +
            `<a href="/users/${login.id}">info</a> | ` +
            `<a href="#" onclick="` +
                `clear_login_info(); update(); return false;` +
            `">log out</a>`;
    }
    else {
        div_upload.style.display = "none";
        div_login.style.display = "initial";
        div_info.innerHTML =
            `<a href="#" onclick="` +
                `guest_login(); return false;` +
            `">log in as guest</a><br>&nbsp;`;
    }
}


function guest_login() {
    [input_username.value, input_password.value] = ["guest", "123"];
    button_login.click();
}


div_login.addEventListener("keyup", event => {
    if (event.key === "Enter")
        button_login.click();
});


button_login.addEventListener("click", async () => {
    const [username, password] = [input_username.value, input_password.value];

    const response = await fetch("/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password}),
    });

    if (response.status !== 200) {
        const message = await get_error(response);
        div_info.innerHTML = `Login failed<br>(${response.status} - ${message})`;
        return;
    }

    save_login_info(await response.json());

    update();
});


button_upload.addEventListener("click", async () => {
    const [name, description] = [input_name.value, input_description.value];

    if (!name) {
        div_info.innerHTML = "Missing name<br>&nbsp;";
        return;
    }

    const data = new FormData();
    data.append("name", name);
    data.append("description", description);

    if (!input_newick_file.disabled) {
        if (input_newick_file.files.length === 0) {
            div_info.innerHTML = "Missing newick file";
            return;
        }
        const size_MB = input_newick_file.files[0].size / 1e6;
        if (size_MB > 10) {
            div_info.innerHTML =
                `Sorry, the file is too big<br>` +
                `(${size_MB.toFixed(1)} MB, the maximum is set to 10 MB)`;
            return;
        }
        data.append("newick", input_newick_file.files[0]);
    }
    else {
        data.append("newick", input_newick_string.value.trim());
    }

    const login = get_login_info();

    const response = await fetch("/trees", {
        method: "POST",
        headers: {"Authorization": `Bearer ${login.token}`},
        body: data,
    });

    if (response.status === 401) {
        div_info.innerHTML =
            `Upload failed - Unauthorized<br>` +
            `<a href="#" onclick="` +
                `clear_login_info(); update(); return false;` +
            `">You need to login again</a>`;
        return;
    }
    else if (response.status !== 201) {
        div_info.innerHTML =
            `Upload failed<br>` +
            `(${response.status} - ${await get_error(response)})`;
        return;
    }

    window.location.href = `gui.html?tree=${name}`;
});


async function get_error(response) {
    try {
        const data = await response.json();
        return data.message;
    }
    catch (error) {
        return response.statusText;
    }
}


radio_file.addEventListener("click", () => {
    input_newick_file.disabled = false;
    input_newick_string.disabled = true;
});

radio_string.addEventListener("click", () => {
    input_newick_string.disabled = false;
    input_newick_file.disabled = true;
});
