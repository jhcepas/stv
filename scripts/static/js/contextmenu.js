// Functions related to the context menu (right-click menu).

import { view, api_put, on_tree_change, reset_view } from "./gui.js";
import { draw_minimap } from "./minimap.js";
import { update } from "./draw.js";

export { on_box_contextmenu };


function on_box_contextmenu(event, box, name, properties, node_id) {
    event.preventDefault();

    div_contextmenu.innerHTML = "";

    if (node_id) {
        add_node_options(box, name, properties, node_id);
        add_element("hr");
    }
    add_tree_options();

    const s = div_contextmenu.style;
    s.left = event.pageX + "px";
    s.top = event.pageY + "px";
    s.visibility = "visible";
}


function add_node_options(box, name, properties, node_id) {
    const name_text = ": " +
        (name.length < 15 ? name : (name.slice(0, 5) + "..." + name.slice(-5)));

    add_label("Node" + (name.length > 0 ? name_text : ""));

    add_button("🔍 Zoom into node", () => zoom_into_box(box));
    add_button("📌 Go to subtree at node", () => {
        view.subtree += (view.subtree ? "," : "") + node_id;
        on_tree_change();
    }, "Explore the subtree starting at the current node.");
    add_button("❓ Show node id", () => {
        Swal.fire({text: `${node_id}`, position: "bottom",
                   showConfirmButton: false});
    });
    if ("taxid" in properties) {
        const taxid = properties["taxid"];
        add_button("📖 Show in taxonomy browser", () => {
            const urlbase = "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser";
            window.open(`${urlbase}/wwwtax.cgi?id=${taxid}`);
        }, `Open the NCBI Taxonomy Browser on this taxonomy ID: ${taxid}.`);
    }
    if (!view.subtree) {
        add_button("🎯 Root on this node ⚠️", async () => {
            await api_put("root_at", node_id);
            draw_minimap();
            update();
        }, "Set this node as the root of the tree. Changes the tree structure.");
    }
}


function add_tree_options() {
    add_label("Tree");

    add_button("🔭 Reset view", reset_view, "Fit tree to the window.");
    if (view.subtree) {
        add_button("⬅️ Go back to main tree", () => {
            view.subtree = "";
            on_tree_change();
        }, "Exit view on current subtree.");
    }
    add_button("🔃 Sort tree ⚠️", async () => {
        await api_put("sort");
        draw_minimap();
        update();
    }, "Sort the branches according to the current sorting function. " +
       "Changes the tree structure.");
}


function add_button(text, fn, tooltip) {
    const button = document.createElement("button");
    button.appendChild(document.createTextNode(text));
    button.addEventListener("click", event => {
        div_contextmenu.style.visibility = "hidden";
        fn(event);
    });
    button.classList.add("ctx_button");

    if (tooltip)
        button.setAttribute("title", tooltip);

    div_contextmenu.appendChild(button);
    add_element("br");
}


function add_label(text) {
    const p = document.createElement("p");
    p.appendChild(document.createTextNode(text));
    p.classList.add("ctx_label");

    div_contextmenu.appendChild(p);
}


function add_element(name) {
    div_contextmenu.appendChild(document.createElement(name));
}
