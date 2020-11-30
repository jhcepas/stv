'use strict';


document.addEventListener("DOMContentLoaded", update);


const login = () => JSON.parse(window.localStorage.getItem("login_info"));


function update() {
    if (login() !== null) {
        div_login.style.display = "none";
        div_upload.style.display = "initial";
        div_info.innerHTML =
          `Logged in as ${login().username} (${login().name})<br>` +
          `<a href="/users/${login().id}">info</a> | ` +
          `<a href="" onclick="window.localStorage.clear(); update();">log out</a>`;
    } else {
        div_upload.style.display = "none";
        div_login.style.display = "initial";
        div_info.innerHTML = "";
    }
}


button_login.addEventListener("click", () => {
    const [username, password] = [input_username.value, input_password.value];
    fetch("/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({username, password})})
        .then(response => {
            if (response.status === 200) {
                return response.json();
            }
            else {
                div_info.innerHTML = "Login unsuccessful";
            }
        })
        .then(data => {
            if (data) {
                window.localStorage.setItem("login_info", JSON.stringify(data));
                update();
            }
        })
        .catch(error => console.log(error));
});


button_upload.addEventListener("click", async () => {
    const [name, description] = [input_name.value, input_description.value];

    const size_MB = input_newick_file.files[0].size / 1e6;
    if (size_MB > 10) {
        div_info.innerHTML = `Sorry, the file is too big ` +
            `(${size_MB.toFixed(1)} MB, the maximum is set to 10 MB)`;
        return;
    }

    const newick = (await input_newick_file.files[0].text()).trim();

    fetch("/trees", {
            method: "POST",
            headers: {"Content-Type": "application/json",
                      "Authorization": `Bearer ${login().token}`},
            body: JSON.stringify({name, description, newick})})
        .then(response => response.json())
        .then(data => {
            window.location.href = `gui.html?id=${data.id}&name=${name}`;
        })
        .catch(error => console.log(error));
});
