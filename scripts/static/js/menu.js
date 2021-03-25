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

    add_menu_info(dgui);

    add_menu_view(dgui);

    add_menu_style(dgui);

    dgui.add(view, "minimap_show").name("minimap").onChange(show_minimap);

    dgui.add(view, "share_view").name("share view");

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

    folder_repr.add(view, "drawer", drawers).onChange(on_drawer_change);
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

    folder_searches.add(view, "search_nmax").name("max results");
    folder_searches.add(view, "search").name("new search");
}


function add_menu_info(dgui) {
    const folder_info = dgui.addFolder("info");

    folder_info.add(view.nodes, "n").name("visible nodes").listen();
    folder_info.add(view.pos, "cx").step(0.001).listen();
    folder_info.add(view.pos, "cy").step(0.001).listen();
    folder_info.add(view, "show_tree_info").name("show details");
    folder_info.add(view, "show_help").name("help");
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

    folder_view.add(view, "smart_zoom").name("smart zoom");

    folder_view.add(view, "select_text").name("select text").onChange(() => {
        style("font").userSelect = (view.select_text ? "text" : "none");
        div_tree.style.cursor = (view.select_text ? "text" : "auto");
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

    folder_text.addColor(view, "names_color").name("names").onChange(
        () => style("name").fill = view.names_color);
    folder_text.addColor(view, "lengths_color").name("lengths").onChange(
        () => style("length").fill = view.lengths_color);
    folder_text.add(view, "font_family", ["sans-serif", "serif", "monospace"])
        .name("font").onChange(() => style("font").fontFamily = view.font_family);
    folder_text.add(view, "font_size_auto").name("automatic size").onChange(
        () => {
            style("font").fontSize =
                view.font_size_auto ? "" : `${view.font_size}px`;

            if (view.font_size_auto && view.font_size_scroller)
                view.font_size_scroller.remove();
            else
                view.font_size_scroller = create_font_size_scroller();
    });
    folder_text.add(view, "font_size_max", 1, 100).name("max size").onChange(
        update);
    folder_text.add(view, "text_padding", -20, 200).name("padding").onChange(
        update);

    function create_font_size_scroller() {
        return folder_text.add(view, "font_size", 0.1, 50).name("font size")
            .onChange(() => style("font").fontSize = `${view.font_size}px`);
    }
}


function style(name) {
    const pos = {
        "line": 1, "font": 3, "name": 4, "length": 5, "node": 6, "outline": 7,
    };
    return document.styleSheets[0].cssRules[pos[name]].style;
}
