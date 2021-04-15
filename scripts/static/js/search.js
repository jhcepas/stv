// Search-related functions.

import { view, datgui, get_tid } from "./gui.js";
import { update_tree } from "./draw.js";
import { api } from "./api.js";

export { search, remove_searches, get_search_class, colorize_searches };


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

            const qs = `text=${encodeURIComponent(text)}`;
            return api(`/trees/${get_tid()}/search?${qs}`);
        },
    });

    if (result.isConfirmed) {
        const res = result.value;  // shortcut

        if (res.message === 'ok') {
            const colors = ["#FF0", "#F0F", "#0FF", "#F00", "#0F0", "#00F"];
            const nsearches = Object.keys(view.searches).length;

            view.searches[search_text] = {
                results: {n: res.nresults,
                          opacity: 0.4,
                          color: colors[nsearches % colors.length]},
                parents: {n: res.nparents,
                          color: "#000",
                          width: 5},
            };

            add_search_to_datgui(search_text);

            update_tree();
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


// Return a class name related to the results of searching for text.
function get_search_class(text, type="results") {
    return "search_" + type + "_" + text.replace(/[^A-Za-z0-9_-]/g, '');
}


// Add a folder to the datgui that corresponds to the given search text
// and lets you change the result nodes color and so on.
function add_search_to_datgui(text) {
    const folder = datgui.__folders.searches.addFolder(text);

    const search = view.searches[text];

    search.remove = function() {
        delete view.searches[text];
        datgui.__folders.searches.removeFolder(folder);
        update_tree();
    }

    const folder_results = folder.addFolder(`results (${search.results.n})`);
    folder_results.add(search.results, "opacity", 0, 1).step(0.01).onChange(
        () => colorize(text));
    folder_results.addColor(search.results, "color").onChange(
        () => colorize(text));

    const folder_parents = folder.addFolder(`parents (${search.parents.n})`);
    folder_parents.addColor(search.parents, "color").onChange(
        () => colorize(text));
    folder_parents.add(search.parents, "width", 0.1, 20).onChange(
        () => colorize(text));

    folder.add(search, "remove");
}


function colorize(text) {
    const search = view.searches[text];

    const cresults = get_search_class(text, "results");
    Array.from(div_tree.getElementsByClassName(cresults)).forEach(e => {
        e.style.opacity = search.results.opacity;
        e.style.fill = search.results.color;
    });

    const cparents = get_search_class(text, "parents");
    Array.from(div_tree.getElementsByClassName(cparents)).forEach(e => {
        e.style.stroke = search.parents.color;
        e.style.strokeWidth = search.parents.width;
    });

}


function colorize_searches() {
    Object.keys(view.searches).forEach(text => colorize(text));
}


// Empty view.searches.
function remove_searches() {
    const texts = Object.keys(view.searches);
    texts.forEach(text => view.searches[text].remove());
}
