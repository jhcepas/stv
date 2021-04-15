// Functions related to the context menu (right-click menu).

import { view, tree_command, on_tree_change, reset_view, sort, datgui } from "./gui.js";
import { draw_minimap } from "./minimap.js";
import { update } from "./draw.js";
import { download_newick } from "./download.js";
import { zoom_into_box } from "./zoom.js";

export { on_box_contextmenu, colorize_tags };


function on_box_contextmenu(event, box, name, properties, node_id=[]) {
    event.preventDefault();

    div_contextmenu.innerHTML = "";

    if (box) {
        const name_text = ": " + (name.length < 20 ? name :
                                  (name.slice(0, 8) + "..." + name.slice(-8)));

        add_label("Node" + (name.length > 0 ? name_text : ""));

        add_button("🔍 Zoom into node", () => zoom_into_box(box));

        if (node_id.length > 0) {
            add_node_options(box, name, properties, node_id);
        }

        add_element("hr");
    }

    add_label("Tree");

    add_tree_options();

    const x_max = div_tree.offsetWidth - div_contextmenu.offsetWidth,
          y_max = div_tree.offsetHeight - div_contextmenu.offsetHeight;
    div_contextmenu.style.left = Math.min(event.pageX, x_max) + "px";
    div_contextmenu.style.top = Math.min(event.pageY, y_max) + "px";
    div_contextmenu.style.visibility = "visible";
}


function add_node_options(box, name, properties, node_id) {
    add_button("📌 Go to subtree at node", () => {
        view.subtree += (view.subtree ? "," : "") + node_id;
        on_tree_change();
    }, "Explore the subtree starting at the current node.");
    add_button("❓ Show node id", () => {
        Swal.fire({text: `${node_id}`, position: "bottom",
                   showConfirmButton: false});
    });
    add_button("📥 Download newick from node", () => download_newick(node_id),
               "Download subtree starting at this node as a newick file.");
    if ("taxid" in properties) {
        const taxid = properties["taxid"];
        add_button("📖 Show in taxonomy browser", () => {
            const urlbase = "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser";
            window.open(`${urlbase}/wwwtax.cgi?id=${taxid}`);
        }, `Open the NCBI Taxonomy Browser on this taxonomy ID: ${taxid}.`);
    }
    add_button("🏷️ Tag node", async () => {
        let tag_name;
        const result = await Swal.fire({
            input: "text",
            inputPlaceholder: "Enter tag",
            preConfirm: name => {
                if (!name)
                    return false;  // prevent popup from closing

                tag_name = name;  // to be used when checking the result later on

                if (name in view.tags) {
                    view.tags[name].nodes.push(node_id);
                    return;
                }

                const folder = datgui.__folders.tags.addFolder(name);
                const colors = ["#FF0", "#F0F", "#0FF", "#F00", "#0F0", "#00F"];
                const ntags = Object.keys(view.tags).length;
                view.tags[name] = {
                    nodes: [node_id],
                    opacity: 0.4,
                    color: colors[ntags % colors.length],
                };

                view.tags[name].remove = function() {
                    view.tags[name].opacity = view.node.opacity;
                    view.tags[name].color = view.node.color;
                    colorize(name);
                    delete view.tags[name];
                    datgui.__folders.tags.removeFolder(folder);
                }

                folder.add(view.tags[name], "opacity", 0, 1).step(0.01).onChange(
                    () => colorize(name));
                folder.addColor(view.tags[name], "color").onChange(
                    () => colorize(name));

                folder.add(view.tags[name], "remove");
            },
        });
        if (result.isConfirmed)
            colorize(tag_name);
    });

    if (view.allow_modifications)
        add_node_modifying_options(box, name, properties, node_id);
}


function colorize(name) {
    const tags = view.tags[name];
    tags.nodes.forEach(node_id => {
        const node = document.getElementById(node_id);
        if (node) {
            node.style.opacity = tags.opacity;
            node.style.fill = tags.color;
        }
    });
}


function colorize_tags() {
    Object.keys(view.tags).forEach(name => colorize(name));
}


function add_node_modifying_options(box, name, properties, node_id) {
    add_button("🖊️ Rename node  ⚠️", async () => {
        const result = await Swal.fire({
            input: "text",
            inputPlaceholder: "Enter new name",
            preConfirm: async name => {
                return await tree_command("rename", [node_id, name]);
            },
        });
        if (result.isConfirmed)
            update();
    }, "Change the name of this node. Changes the tree structure.");
    if (!view.subtree) {
        add_button("🎯 Root on this node ⚠️", async () => {
            await tree_command("root_at", node_id);
            draw_minimap();
            update();
        }, "Set this node as the root of the tree. Changes the tree structure.");
    }
    add_button("⬆️ Move node up ⚠️", async () => {
        await tree_command("move", [node_id, -1]);
        draw_minimap();
        update();
    }, "Move the current node one step above its current position. " +
        "Changes the tree structure.");
    add_button("⬇️ Move node down ⚠️", async () => {
        await tree_command("move", [node_id, +1]);
        draw_minimap();
        update();
    }, "Move the current node one step below its current position. " +
        "Changes the tree structure.");
    add_button("🔃 Sort from node ⚠️", () => sort(node_id),
        "Sort branches below this node according to the current sorting " +
        "function. Changes the tree structure.");
    add_button("✂️ Remove node ⚠️", async () => {
        await tree_command("remove", node_id);
        draw_minimap();
        update();
    }, "Prune this branch from the tree. Changes the tree structure.");
}


function add_tree_options() {
    add_button("🔭 Reset view", reset_view, "Fit tree to the window.");
    if (view.subtree) {
        add_button("⬅️ Go back to main tree", () => {
            view.subtree = "";
            on_tree_change();
        }, "Exit view on current subtree.");
    }

    if (view.allow_modifications) {
        add_button("🔃 Sort tree ⚠️", () => sort(),
            "Sort all branches according to the current sorting function. " +
            "Changes the tree structure.");
    }
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
