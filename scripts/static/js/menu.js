// Functions related to the top-right menu.

import { view, on_tree_change, on_drawer_change, show_minimap } from "./gui.js";
import { draw_minimap } from "./minimap.js";
import { update } from "./draw.js";

export { create_datgui };


// Create the top-right box ("gui") with all the options we can see and change.
function create_datgui(trees, drawers) {
    const dgui = new dat.GUI({autoPlace: false});
    div_datgui.appendChild(dgui.domElement);

    add_menu_tree(dgui, trees);

    add_menu_representation(dgui, drawers);

    add_menu_searches(dgui);

    dgui.addFolder("tags");

    add_menu_info(dgui);

    add_menu_view(dgui);

    add_menu_style(dgui);

    add_menu_minimap(dgui);

    dgui.add(view, "smart_zoom").name("smart zoom");
    dgui.add(view, "share_view").name("share view");
    dgui.add(view, "show_help").name("help");

    return dgui;
}


function add_menu_tree(dgui, trees) {
    const folder_tree = dgui.addFolder("tree");

    folder_tree.add(view, "tree", trees).onChange(() => {
        view.subtree = "";
        on_tree_change();
    });
    folder_tree.add(view, "subtree").onChange(on_tree_change);

    const folder_sort = folder_tree.addFolder("sort");
    folder_sort.add(view.sorting, "sort");
    folder_sort.add(view.sorting, "key");
    folder_sort.add(view.sorting, "reverse");

    folder_tree.add(view, "upload");

    const folder_download = folder_tree.addFolder("download");
    folder_download.add(view.download, "newick");
    folder_download.add(view.download, "svg");
    folder_download.add(view.download, "image");
}


function add_menu_representation(dgui, drawers) {
    const folder_repr = dgui.addFolder("representation");

    folder_repr.add(view.drawer, "name", drawers).name("drawer").onChange(
        on_drawer_change);
    folder_repr.add(view, "align_bar", 0, 100).name("align bar").onChange(
        (value) => div_aligned.style.width = `${100 - value}%`);

    const folder_circ = folder_repr.addFolder("circular");

    function update_with_minimap() {
        draw_minimap();
        update();
    }
    folder_circ.add(view, "rmin").name("radius min").onChange(
        update_with_minimap);
    folder_circ.add(view.angle, "min", -180, 180).name("angle min").onChange(
        update_with_minimap);
    folder_circ.add(view.angle, "max", -180, 180).name("angle max").onChange(
        update_with_minimap);

    folder_repr.add(view, "min_size", 1, 100).name("collapse at").onChange(
        update);
}


function add_menu_searches(dgui) {
    const folder_searches = dgui.addFolder("searches");

    folder_searches.add(view, "search").name("new search");
}


function add_menu_info(dgui) {
    const folder_info = dgui.addFolder("info");

    folder_info.add(view, "nnodes").name("visible nodes").listen();
    folder_info.add(view.pos, "cx").step(0.001).listen();
    folder_info.add(view.pos, "cy").step(0.001).listen();
    folder_info.add(view, "show_tree_info").name("show details");
}


function add_menu_view(dgui) {
    const folder_view = dgui.addFolder("view");

    folder_view.add(view, "reset_view").name("reset view");

    const folder_tl = folder_view.addFolder("top-left");
    folder_tl.add(view.tl, "x").step(0.001).onChange(update);
    folder_tl.add(view.tl, "y").step(0.001).onChange(update);

    const folder_zoom = folder_view.addFolder("zoom");
    folder_zoom.add(view.zoom, "x").step(0.001).onChange(update);
    folder_zoom.add(view.zoom, "y").step(0.001).onChange(update);

    folder_view.add(view, "select_text").name("select text").onChange(() => {
        style("font").userSelect = (view.select_text ? "text" : "none");
        div_tree.style.cursor = (view.select_text ? "text" : "auto");
        div_aligned.style.cursor = (view.select_text ? "text" : "ew-resize");
        set_boxes_clickable(!view.select_text);
    });
}

function set_boxes_clickable(clickable) {
    const value = clickable ? "auto" : "none";
    Array.from(div_tree.getElementsByClassName("box")).forEach(
        e => e.style.pointerEvents = value);
}


function add_menu_style(dgui) {
    const folder_style = dgui.addFolder("style");

    const folder_node = folder_style.addFolder("node");

    folder_node.add(view.node, "opacity", 0, 0.2).step(0.001).onChange(
        () => style("node").opacity = view.node.opacity);
    folder_node.addColor(view.node, "color").onChange(
        () => style("node").fill = view.node.color);

    const folder_outline = folder_style.addFolder("outline");

    folder_outline.add(view.outline, "opacity", 0, 1).step(0.1).onChange(
        () => style("outline").fillOpacity = view.outline.opacity);
    folder_outline.addColor(view.outline, "color").onChange(
        () => style("outline").fill = view.outline.color);
    folder_outline.add(view.outline, "width", 0.1, 10).onChange(
        () => style("outline").strokeWidth = view.outline.width);

    const folder_line = folder_style.addFolder("line");

    folder_line.addColor(view.line, "color").onChange(
        () => style("line").stroke = view.line.color);
    folder_line.add(view.line, "width", 0.1, 10).onChange(
        () => style("line").strokeWidth = view.line.width);

    const folder_text = folder_style.addFolder("text");

    const folder_name = folder_text.addFolder("name");

    folder_name.addColor(view.name, "color").onChange(
        () => style("name").fill = view.name.color);

    const folder_padding = folder_name.addFolder("padding");

    folder_padding.add(view.name.padding, "left", -20, 200).onChange(() => {
        update();

        // TODO: avoid the api call by using something like the code below
        //   which needs fixing for the case of inverted texts in circular rep.
        // const padding = view.name.padding.left / 100;
        // Array.from(div_tree.getElementsByClassName("name")).forEach(t => {
        //     const fs = Number(t.getAttribute("font-size").slice(0, -2));
        //     const x0 = Number(t.getAttribute("data-x0"));
        //     t.setAttribute("x", x0 + padding * fs);
    });
    folder_padding.add(view.name.padding, "vertical", 0, 1).step(0.01).onChange(
        () => {
            update();

            // TODO: avoid the api call by using something like the code below:
            // Array.from(div_tree.getElementsByClassName("name")).forEach(t => {
            // const box = t.getAttribute("data-box").split(",").map(Number);
            // const anchor = t.getAttribute("data-anchor").split(",").map(Number);
    });
    folder_name.add(view.name, "font", ["sans-serif", "serif", "monospace"])
        .onChange(() => style("name").fontFamily = view.name.font);
    folder_name.add(view.name, "max_size", 1, 200).name("max size").onChange(
        () => {
            // TODO: avoid the api call.
            update();
    });

    const properties = ['length', 'support'];
    properties.forEach(p => {
        const folder = folder_text.addFolder(p);

        folder.addColor(view[p], "color").onChange(
            () => style(p).fill = view[p].color);
        folder.add(view[p], "font", ["sans-serif", "serif", "monospace"])
            .onChange(() => style(p).fontFamily = view[p].font);
        folder.add(view[p], "max_size", 1, 100).name("max size").onChange(
            () => {
                // TODO: avoid the api call.
                update();
        });
    })
    folder_text.add(view.font_sizes, "auto").name("automatic size").onChange(
        () => {
            style("font").fontSize =
                view.font_sizes.auto ? "" : `${view.font_sizes.fixed}px`;

            if (view.font_sizes.auto && view.font_sizes.scroller)
                view.font_sizes.scroller.remove();
            else
                view.font_sizes.scroller = create_font_size_scroller();
    });

    function create_font_size_scroller() {
        return folder_text.add(view.font_sizes, "fixed", 0.1, 50).onChange(
            () => style("font").fontSize = `${view.font_sizes.fixed}px`);
    }

    const folder_array = folder_style.addFolder("array");

    folder_array.add(view.array, "padding", 0, 1).step(0.01).onChange(
        update);
}


function style(name) {
    const pos = {
        "line": 1,
        "font": 3,
        "name": 4,
        "length": 5,
        "support": 6,
        "node": 7,
        "outline": 8,
    };
    return document.styleSheets[0].cssRules[pos[name]].style;
}


function add_menu_minimap(dgui) {
    const folder_minimap = dgui.addFolder("minimap");

    folder_minimap.add(view.minimap, "width", 0, 100).onChange(() => {
        if (view.drawer.type === "circ") {
            view.minimap.height = view.minimap.width * div_tree.offsetWidth
                                                     / div_tree.offsetHeight;
            dgui.updateDisplay();
        }
        draw_minimap();
    });
    folder_minimap.add(view.minimap, "height", 0, 100).onChange(() => {
        if (view.drawer.type === "circ") {
            view.minimap.width = view.minimap.height * div_tree.offsetHeight
                                                     / div_tree.offsetWidth;
            dgui.updateDisplay();
        }
        draw_minimap();
    });
    folder_minimap.add(view.minimap, "show").onChange(show_minimap);
}
