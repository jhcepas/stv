// Main file.

import { create_datgui } from "./menu.js";
import { init_events } from "./events.js";
import { update } from "./draw.js";
import { download_newick, download_image, download_svg } from "./download.js";
import { search, remove_searches } from "./search.js";
import { zoom_into_box, zoom_around, zoom_towards_box } from "./zoom.js";
import { draw_minimap, update_minimap_visible_rect } from "./minimap.js";

export { view, datgui, on_tree_change, on_drawer_change, show_minimap,
         api, api_put, get_tid, on_box_click, on_box_wheel, coordinates,
         reset_view, show_help, sort };


// Run main() when the page is loaded.
document.addEventListener("DOMContentLoaded", main);


// Global variables related to the current view on the tree.
// Most will be shown on the top-right gui (using dat.gui).
const view = {
    // tree
    tree: "",
    tree_size: {width: 0, height: 0},
    subtree: "",
    sorting: {sort: () => sort(),
              key: '(dy, dx, name)',
              reverse: false},
    upload: () => window.location.href = "upload_tree.html",
    download: {newick: () => download_newick(),
               svg:    () => download_svg(),
               image:  () => download_image()},

    // representation
    drawer: "Full",
    align_bar: 80,
    is_circular: false,
    rmin: 0,
    angle: {min: -180, max: 180},
    min_size: 20,

    // searches
    search_nmax: 10000,
    search: () => search(),
    searches: {},  // will contain the searches done and their results

    // info
    nodes: {boxes: {}, n: 0},  // will contain the visible nodeboxes
    pos: {cx: 0, cy: 0},  // in-tree current pointer position
    show_tree_info: () => show_tree_info(),

    // view
    reset_view: () => reset_view(),
    tl: {x: 0, y: 0},  // top-left of the view (in tree rectangular coordinates)
    zoom: {x: 0, y: 0},  // initially chosen depending on the size of the tree
    smart_zoom: true,
    select_text: false,

    // style
    node: {opacity: 0, color: "#222"},
    outline: {opacity: 0.1, color: "#A50", width: 0.2},
    line: {color: "#000", width: 1},
    names_color: "#00A",
    lengths_color: "#888",
    font_family: "sans-serif",
    font_size_auto: true,
    font_size_scroller: undefined,
    font_size: 10,
    font_size_max: 15,
    text_padding: 10,

    // help and sharing
    share_view: () => share_view(),
    show_help: () => show_help(),

    // minimap
    minimap_show: true,
    minimap_uptodate: false,
    minimap_zoom: {x: 1, y: 1},
};


const trees = {};  // will contain trees[tree_name] = tree_id
let datgui = undefined;


async function main() {
    await init_trees();
    const drawers = await api("/trees/drawers");
    datgui = create_datgui(Object.keys(trees), drawers);

    init_events();

    await set_query_string_values();

    reset_zoom(view.zoom.x === 0, view.zoom.y === 0);
    reset_position();
    draw_minimap();
    update();
}


// Return the data coming from an api endpoint (like "/trees/<id>/size").
async function api(endpoint) {
    const response = await fetch(endpoint);

    if (response.status !== 200) {
        Swal.fire({
            title: "Request failed :(",
            html: `${response.status} - ${await get_error(response)}`,
            icon: "error",
        });
        return undefined;
    }

    return await response.json();
}


// Return the most descriptive error message extracted from the response.
async function get_error(response) {
    try {
        const data = await response.json();
        return data.message;
    }
    catch (error) {
        return response.statusText;
    }
}


// NOTE: The next two functions are just used to bypass the authorization that is
// currently needed in the api to make changes to a tree (by using a PUT request).
function get_login_info() {
    return JSON.parse(localStorage.getItem("login_info"));
}

async function login_as_guest() {
    localStorage.clear();

    const [username, password] = ["guest", "123"];

    const response = await fetch("/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password}),
    });

    const data = await response.json();
    localStorage.setItem("login_info", JSON.stringify(data));
}

async function api_put(command, params=undefined) {
    await login_as_guest();
    const login = get_login_info();

    const response = await fetch(`/trees/${get_tid()}/${command}`, {
        method: "PUT",
        headers: {"Content-Type": "application/json",
                  "Authorization": `Bearer ${login.token}`},
        body: JSON.stringify(params),
    });

    if (response.status !== 200) {
        Swal.fire({
            title: "Tree modification failed :(",
            html: `${response.status} - ${await get_error(response)}`,
            icon: "error",
        });
        return;
    }

    const commands_modifying_size = ["root_at", "remove"];
    if (commands_modifying_size.includes(command))
        view.tree_size = await api(`/trees/${get_tid()}/size`);
}



// Fill global var trees, and view.tree with the first of the available trees.
async function init_trees() {
    const trees_info = await api("/trees");
    trees_info.forEach(t => trees[t.name] = t.id);

    view.tree = Object.keys(trees)[0];
    view.tree_size = await api(`/trees/${get_tid()}/size`);
}


function get_tid() {
    return trees[view.tree] + (view.subtree ? "," + view.subtree : "");
}


// What happens when the user selects a new tree in the datgui menu.
async function on_tree_change() {
    div_tree.style.cursor = "wait";
    remove_searches();
    view.tree_size = await api(`/trees/${get_tid()}/size`);
    reset_zoom();
    reset_position();
    draw_minimap();
    update();
}


// What happens when the user selects a new drawer in the datgui menu.
function on_drawer_change() {
    const has_aligned = view.drawer.startsWith("Align");
    div_aligned.style.display = has_aligned ? "initial" : "none";

    const reset_draw = (view.is_circular !== view.drawer.startsWith("Circ"));

    view.is_circular = view.drawer.startsWith("Circ");

    if (reset_draw) {
        reset_zoom();
        reset_position();
        draw_minimap();
    }

    update();
}


function reset_view() {
    reset_zoom();
    reset_position();
    if (!view.minimap_uptodate)
        draw_minimap();
    update();
}


// Set values that have been given with the query string.
async function set_query_string_values() {
    const unknown_params = [];
    const params = new URLSearchParams(location.search);

    for (const [param, value] of params) {
        if (param === "tree")
            view.tree = value;
        else if (param === "subtree")
            view.subtree = value;
        else if (param === "x")
            view.tl.x = Number(value);
        else if (param === "y")
            view.tl.y = Number(value);
        else if (param === "w")
            view.zoom.x = div_tree.offsetWidth / Number(value);
        else if (param === "h")
            view.zoom.y = div_tree.offsetHeight / Number(value);
        else if (param === "drawer")
            view.drawer = value;
        else
            unknown_params.push(param);
    }

    view.is_circular = view.drawer.startsWith("Circ");

    if (view.is_circular)
        view.zoom.x = view.zoom.y = Math.min(view.zoom.x, view.zoom.y);

    const has_aligned = view.drawer.startsWith("Align");
    div_aligned.style.display = has_aligned ? "initial" : "none";

    view.tree_size = await api(`/trees/${get_tid()}/size`);

    if (unknown_params.length != 0)
        Swal.fire(
            "Oops!",
            "There were unknown parameters passed: " + unknown_params.join(", "),
            "warning");
}


function show_minimap(show) {
    const status = (show ? "visible" : "hidden");
    div_minimap.style.visibility = div_visible_rect.style.visibility = status;
    if (show) {
        if (!view.minimap_uptodate)
            draw_minimap();
        update_minimap_visible_rect();
    }
}


// Set the zoom so the full tree fits comfortably on the screen.
function reset_zoom(reset_zx=true, reset_zy=true) {
    if (!(reset_zx || reset_zy))
        return;

    const size = view.tree_size;

    if (view.is_circular) {
        const min_w_h = Math.min(div_tree.offsetWidth, div_tree.offsetHeight);
        view.zoom.x = view.zoom.y = min_w_h / (view.rmin + size.width) / 2;
    }
    else {
        if (reset_zx)
            view.zoom.x = 0.6 * div_tree.offsetWidth / size.width;
        if (reset_zy)
            view.zoom.y = 0.9 * div_tree.offsetHeight / size.height;
    }
}


function reset_position() {
    if (view.is_circular) {
        if (!(view.angle.min === -180 && view.angle.max === 180)) {
            view.angle.min = -180;
            view.angle.max = 180;
            view.minimap_uptodate = false;
        }
        view.tl.x = -div_tree.offsetWidth / view.zoom.x / 2;
        view.tl.y = -div_tree.offsetHeight / view.zoom.y / 2;
    }
    else {
        view.tl.x = -0.10 * div_tree.offsetWidth / view.zoom.x;
        view.tl.y = -0.05 * div_tree.offsetHeight / view.zoom.y;
    }
}


// Return an url with the view of the given rectangle of the tree.
function get_url_view(x, y, w, h) {
    const qs = new URLSearchParams({
        x: x, y: y, w: w, h: h,
        tree: view.tree, subtree: view.subtree, drawer: view.drawer,
    }).toString();
    return window.location.origin + window.location.pathname + "?" + qs;
}


// Show an alert with information about the current tree and view.
async function show_tree_info() {
    const info = await api(`/trees/${get_tid()}`);
    const [name, tid, description] = [info.name, info.id, info.description];

    const w = div_tree.offsetWidth / view.zoom.x,
          h = div_tree.offsetHeight / view.zoom.y;
    const url = get_url_view(view.tl.x, view.tl.y, w, h);

    const result = await Swal.fire({
        title: "Tree Information",
        icon: "info",
        html: `${name} (<a href="/trees/${tid}">${tid}</a>)<br><br>` +
              (description ? `${description}<br><br>` : "") +
              `(<a href="${url}">current view</a>)`,
        confirmButtonText: navigator.clipboard ? "Copy view to clipboard" : "Ok",
        showCancelButton: true,
    });

    if (result.isConfirmed && navigator.clipboard)
        navigator.clipboard.writeText(url);
}


function share_view() {
    const w = div_tree.offsetWidth / view.zoom.x,
          h = div_tree.offsetHeight / view.zoom.y;
    const url = get_url_view(view.tl.x, view.tl.y, w, h);

    if (navigator.clipboard) {
        navigator.clipboard.writeText(url);
        Swal.fire({
            text: "Current view has been copied to the clipboard.",
            icon: "success",
        });
    }
    else {
        Swal.fire({
            html: "Right-click on link to copy to the clipboard:<br><br>" +
                  `<a href="${url}">-- link to current tree view --</a>`,
        });
    }
}


function show_help() {
    const help_text = `
<table style="margin: 0 auto">
<thead><tr><th>General Instructions</th></tr></thead>
<tbody style="text-align: left">
<tr><td><br>
Click and drag with the left mouse button to move around the tree.
</td></tr>
<tr><td><br>
Use the mouse wheel to zoom in and out. Press <kbd>Ctrl</kbd> or <kbd>Alt</kbd>
while using the wheel to zoom differently.
</td></tr>
<tr><td><br>
Click on the minimap to go to a different area or drag the current view.
</td></tr>
<tr><td><br>
Right-click on a node to show options to interact with it.
</td></tr>
<tr><td><br>
Use the options in the menu at the top right to change the visualization.
</td></tr>
</tbody>
</table>

<br>
<br>

<table style="margin: 0 auto">
<thead><tr><th colspan="2">Keyboard Shortcuts</th></tr></thead>
<tbody>
<tr><td> </td><td>&nbsp; </td></tr>
<tr><td><kbd>F1</kbd></td><td style="text-align: left">&nbsp; help</td></tr>
<tr><td><kbd>/</kbd></td><td style="text-align: left">&nbsp; search</td></tr>
<tr><td><kbd>r</kbd></td><td style="text-align: left">&nbsp; reset view</td></tr>
<tr><td><kbd>m</kbd></td><td style="text-align: left">&nbsp; toggle minimap</td></tr>
<tr><td><kbd>+</kbd></td><td style="text-align: left">&nbsp; zoom in</td></tr>
<tr><td><kbd>&ndash;</kbd></td><td style="text-align: left">&nbsp; zoom out</td></tr>
</tbody>
</table>

<br>

<hr>

<br>

<div style="font-size: 0.8em">
<p>
<img src="icon.png" alt="ETE Toolkit logo">
Tree Explorer is part of the
<a href="http://etetoolkit.org/">ETE Toolkit</a>.
</p>

<p>
<img src="https://chanzuckerberg.com/wp-content/themes/czi/img/logo.svg"
     width="50" alt="Chan Zuckerberg Initiative logo">
Smart visualization funded by
<a href="https://chanzuckerberg.com/">CZI</a>.
</p>
</div>

<br>
<br>
`;
    Swal.fire({
        title: "Tree Explorer",
        html: help_text,
        icon: "info",
    });
}


// Return the corresponding in-tree position of the given point (on the screen).
function coordinates(point) {
    const x = view.tl.x + point.x / view.zoom.x,
          y = view.tl.y + point.y / view.zoom.y;

    if (view.is_circular) {
        const r = Math.sqrt(x*x + y*y);
        const a = Math.atan2(y, x) * 180 / Math.PI;
        return [r, a];
    }
    else {
        return [x, y];
    }
}


function on_box_click(event, box, node_id) {
    if (event.detail === 2 || event.ctrlKey) {  // double-click or ctrl-click
        zoom_into_box(box);
    }
    else if (event.shiftKey) {  // shift-click
        view.subtree += (view.subtree ? "," : "") + node_id;
        on_tree_change();
    }
}


// Mouse wheel -- zoom in/out (instead of scrolling).
function on_box_wheel(event, box) {
    event.preventDefault();

    const point = {x: event.pageX, y: event.pageY};
    const zoom_in = event.deltaY < 0;
    const do_zoom = {x: !event.ctrlKey, y: !event.altKey};

    if (view.is_circular || !view.smart_zoom)
        zoom_around(point, zoom_in, do_zoom);
    else
        zoom_towards_box(box, point, zoom_in, do_zoom);
}


async function sort(node_id=[]) {
    await api_put("sort", [node_id, view.sorting.key, view.sorting.reverse]);
    draw_minimap();
    update();
}
