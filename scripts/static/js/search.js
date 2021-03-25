// Search-related functions.

import { view, datgui, api, get_tid, on_box_click, on_box_wheel } from "./gui.js";
import { create_rect, create_asec } from "./draw.js";
import { on_box_contextmenu } from "./contextmenu.js";

export { search, add_search_boxes, remove_searches };


// Search nodes and mark them as selected on the tree.
async function search() {
    let search_text;

    const result = await Swal.fire({
        input: "text",
        position: "bottom-start",
        inputPlaceholder: "Enter name or /r <regex> or /e <exp>",
        showConfirmButton: false,
        preConfirm: text => {
            if (!text)
                return false;  // prevent popup from closing

            search_text = text;  // to be used when checking the result later on

            let qs = `text=${encodeURIComponent(text)}&drawer=${view.drawer}` +
                     `&nmax=${view.search_nmax}`;
            if (view.is_circular)
                qs += `&rmin=${view.rmin}` +
                      `&amin=${view.angle.min}&amax=${view.angle.max}`;

            return api(`/trees/${get_tid()}/search?${qs}`);
        },
    });

    if (result.isConfirmed) {
        const res = result.value;  // shortcut

        if (res.message === 'ok') {
            show_search_results(search_text, res.nodes, view.search_nmax);

            if (res.nodes.length > 0) {
                const colors = ["#FF0", "#F0F", "#0FF", "#F00", "#0F0", "#00F"];
                const nsearches = Object.keys(view.searches).length;

                view.searches[search_text] = {
                    nodes: res.nodes,
                    max: view.search_nmax,
                    color: colors[nsearches % colors.length],
                };

              add_search_boxes(search_text);

              add_search_to_datgui(search_text);
            }
        }
        else {
            Swal.fire({
                position: "bottom-start",
                showConfirmButton: false,
                text: res.message,
                icon: "error",
            });
        }
    }
}


// Show a dialog with the selection results.
function show_search_results(search_text, nodes, max) {
    const n = nodes.length;

    const info = `Search: ${search_text}<br>` +
                 `Found ${n} node${n > 1 ? 's' : ''}<br><br>` +
                 (n < max ? "" : `Only showing the first ${max} matches. ` +
                 "There may be more.<br><br>");

    function link(node) {
        const [node_id, box] = node;
        const [x, y] = [box[0].toPrecision(4), box[1].toPrecision(4)];
        return `<a href="#" title="Coordinates: ${x} : ${y}" ` +
               `onclick="zoom_into_box([${box}]); return false;">` +
               `${node_id.length > 0 ? node_id : "root"}</a>`;
    }

    if (n > 0)
        Swal.fire({
            position: "bottom-start",
            html: info + nodes.map(link).join("<br>"),
        });
    else
        Swal.fire({
            position: "bottom-start",
            text: "No nodes found for search: " + search_text,
            icon: "warning",
        });
}


// Add boxes to the tree view that represent the visible nodes matched by
// the given search text.
function add_search_boxes(search_text) {
    const cname = get_search_class(search_text);
    const color = view.searches[search_text].color;
    const g = div_tree.children[0].children[0];

    view.searches[search_text].nodes.forEach(node => {
        const [node_id, ] = node;

        if (!(node_id in view.nodes.boxes))
            return;

        const box = view.nodes.boxes[node_id];  // get a nicer surrounding box

        const b = view.is_circular ?
            create_asec(box, view.tl, view.zoom.x, "search " + cname) :
            create_rect(box, view.tl, view.zoom.x, view.zoom.y, "search " + cname);

        b.addEventListener("click", event =>
            on_box_click(event, box, node_id));
        b.addEventListener("contextmenu", event =>
            on_box_contextmenu(event, box, "", {}, node_id));
        b.addEventListener("wheel", event =>
            on_box_wheel(event, box), {passive: false});

        b.style.fill = color;

        g.appendChild(b);
    });
}


// Return a class name related to the results of searching for text.
function get_search_class(text) {
    return 'search_' + text.replace(/[^A-Za-z0-9_-]/g, '');
}


// Add a folder that corresponds to the given search_text to the datgui,
// that lets you change the nodes color and remove them too.
function add_search_to_datgui(search_text) {
    const folder = datgui.__folders.searches.addFolder(search_text);

    const cname = get_search_class(search_text);

    function colorize() {
        const nodes = Array.from(div_tree.getElementsByClassName(cname));
        nodes.forEach(e => e.style.fill = view.searches[search_text]["color"]);
    }

    view.searches[search_text].show = function() {
        const search = view.searches[search_text];
        show_search_results(search_text, search.nodes, search.max);
    }

    view.searches[search_text].remove = function() {
        delete view.searches[search_text];
        const nodes = Array.from(div_tree.getElementsByClassName(cname));
        nodes.forEach(e => e.remove());
        datgui.__folders.searches.removeFolder(folder);
    }

    folder.add(view.searches[search_text], "show");
    folder.addColor(view.searches[search_text], "color").onChange(colorize);
    folder.add(view.searches[search_text], "remove");
}


// Empty view.searches.
function remove_searches() {
    const search_texts = Object.keys(view.searches);
    search_texts.forEach(text => view.searches[text].remove());
}
