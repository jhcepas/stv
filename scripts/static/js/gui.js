// Main file.

import { create_datgui } from "./menu.js";
import { init_events } from "./events.js";
import { update } from "./draw.js";
import { download_newick, download_image, download_svg } from "./download.js";
import { search, remove_searches } from "./search.js";
import { zoom_into_box } from "./zoom.js";
import { draw_minimap, update_minimap_visible_rect } from "./minimap.js";

export { view, datgui, on_tree_change, on_drawer_change, show_minimap,
         api, get_tid, on_box_click, coordinates, reset_view };


// Run main() when the page is loaded.
document.addEventListener("DOMContentLoaded", main);


// Global variables related to the current view on the tree.
// Most will be shown on the top-right gui (using dat.gui).
const view = {
    // tree
    tree: "",
    subtree: "",
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
    min_size: 6,

    // searches
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
    update_on_drag: false,
    select_text: false,

    // style
    node: {opacity: 0, color: "#222"},
    outline: {opacity: 0, color: "#DDF", width: 1},
    line: {color: "#000", width: 1},
    names_color: "#00A",
    lengths_color: "#888",
    font_family: "sans-serif",
    font_size_auto: true,
    font_size_scroller: undefined,
    font_size: 10,
    font_size_max: 15,

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

    set_query_string_values();

    await reset_zoom(view.zoom.x === 0, view.zoom.y === 0);
    draw_minimap();
    update();
}


// Return the data coming from an api endpoint (like "/trees/<id>/size").
async function api(endpoint) {
    const response = await fetch(endpoint);
    return await response.json();
}


// Fill global var trees, and view.tree with the first of the available trees.
async function init_trees() {
    const trees_info = await api("/trees");
    trees_info.forEach(t => trees[t.name] = t.id);
    view.tree = Object.keys(trees)[0];
}


function get_tid() {
    return trees[view.tree] + (view.subtree ? "," + view.subtree : "");
}


// What happens when the user selects a new tree in the datgui menu.
async function on_tree_change() {
    div_tree.style.cursor = "wait";
    remove_searches();
    await reset_zoom();
    reset_position();
    draw_minimap();
    update();
}


// What happens when the user selects a new drawer in the datgui menu.
async function on_drawer_change() {
    const has_aligned = view.drawer.startsWith("Align");
    div_aligned.style.display = has_aligned ? "initial" : "none";

    const reset_draw = (view.is_circular !== view.drawer.startsWith("Circ"));

    view.is_circular = view.drawer.startsWith("Circ");

    if (reset_draw) {
        await reset_zoom();
        reset_position();
        draw_minimap();
    }

    update();
}


async function reset_view() {
    await reset_zoom();
    reset_position();
    if (view.minimap_show && !view.minimap_uptodate)
        draw_minimap();
    update();
}


// Set values that have been given with the query string.
function set_query_string_values() {
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

    if (unknown_params.length != 0)
        Swal.fire(
            "Oops!",
            "There were unknown parameters passed: " + unknown_params.join(", "),
            "warning");
}


function show_minimap(show) {
    const status = (show ? "visible" : "hidden");
    div_minimap.style.visibility = div_visible_rect.style.visibility = status;
    if (show)
        update_minimap_visible_rect();
}


// Set the zoom so the full tree fits comfortably on the screen.
async function reset_zoom(reset_zx=true, reset_zy=true) {
    if (!(reset_zx || reset_zy))
        return;

    const size = await api(`/trees/${get_tid()}/size`);

    if (view.is_circular) {
        const min_w_h = Math.min(div_tree.offsetWidth, div_tree.offsetHeight);
        view.zoom.x = view.zoom.y = min_w_h / (view.rmin + size.width) / 2;
    }
    else {
        if (reset_zx)
            view.zoom.x = 0.5 * div_tree.offsetWidth / size.width;
        if (reset_zy)
            view.zoom.y = div_tree.offsetHeight / size.height;
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
        view.tl.x = 0;
        view.tl.y = 0;
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