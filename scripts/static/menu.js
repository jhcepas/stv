import { update, on_tree_change, on_drawer_change, show_minimap, draw_minimap }
  from "./gui.js";

export { create_datgui };


// Create the top-right box ("gui") with all the options we can see and change.
function create_datgui(view, trees, drawers) {
  // Shortcut for getting the styles.
  const [style_line, style_font, style_name, style_length,
    style_node, style_outline] =
    [1, 3, 4, 5, 6, 7].map(i => document.styleSheets[0].cssRules[i].style);

  const dgui = new dat.GUI({autoPlace: false});
  div_datgui.appendChild(dgui.domElement);

  dgui.add(view.pos, "x").step(0.001).listen();
  dgui.add(view.pos, "y").step(0.001).listen();

  const dgui_tree = dgui.addFolder("tree");

  dgui_tree.add(view, "tree", trees).onChange(on_tree_change);
  dgui_tree.add(view, "drawer", drawers).onChange(on_drawer_change);
  dgui_tree.add(view, "show_tree_info").name("info");
  dgui_tree.add(view, "upload_tree").name("upload");
  const dgui_download = dgui_tree.addFolder("download");
  dgui_download.add(view, "download_newick").name("newick");
  dgui_download.add(view, "download_svg").name("svg");
  dgui_download.add(view, "download_image").name("image");

  const dgui_ctl = dgui.addFolder("control");

  dgui_ctl.add(view, "reset_view").name("reset view");
  dgui_ctl.add(view, "search");
  const dgui_ctl_tl = dgui_ctl.addFolder("top-left");
  dgui_ctl_tl.add(view.tl, "x").onChange(update);
  dgui_ctl_tl.add(view.tl, "y").onChange(update);
  const dgui_ctl_zoom = dgui_ctl.addFolder("zoom");
  dgui_ctl_zoom.add(view.zoom, "x").onChange(update);
  dgui_ctl_zoom.add(view.zoom, "y").onChange(update);
  dgui_ctl.add(view, "align_bar", 0, 100).name("align bar").onChange((value) =>
    div_aligned.style.width = `${100 - value}%`);
  const dgui_ctl_circ = dgui_ctl.addFolder("circular");
  dgui_ctl_circ.add(view, "rmin").name("radius min").onChange(
    () => update_with_minimap(view.minimap_show));
  dgui_ctl_circ.add(view.angle, "min", -180, 180).name("angle min").onChange(
    () => update_with_minimap(view.minimap_show));
  dgui_ctl_circ.add(view.angle, "max", -180, 180).name("angle max").onChange(
    () => update_with_minimap(view.minimap_show));
  dgui_ctl.add(view, "min_size", 1, 100).name("collapse at").onChange(update);
  dgui_ctl.add(view, "update_on_drag").name("update on drag");
  dgui_ctl.add(view, "select_text").name("select text").onChange(() => {
    style_font.userSelect = (view.select_text ? "text" : "none");
    div_tree.style.cursor = (view.select_text ? "text" : "auto");
    Array.from(div_tree.getElementsByClassName("box")).forEach(
      e => e.style.pointerEvents = (view.select_text ? "none" : "auto"));
  });

  const dgui_style = dgui.addFolder("style");

  const dgui_style_node = dgui_style.addFolder("node");

  dgui_style_node.add(view, "node_opacity", 0, 0.2).step(0.001).name("opacity")
    .onChange(() => style_node.opacity = view.node_opacity);
  dgui_style_node.addColor(view, "node_color").name("color").onChange(() =>
    style_node.fill = view.node_color);

  const dgui_style_line = dgui_style.addFolder("line");

  dgui_style_line.addColor(view, "line_color").name("color").onChange(() =>
    style_line.stroke = view.line_color);
  dgui_style_line.add(view, "line_width", 0.1, 10).name("width").onChange(() =>
    style_line.strokeWidth = view.line_width);

  const dgui_style_text = dgui_style.addFolder("text");

  dgui_style_text.addColor(view, "names_color").name("names").onChange(() =>
    style_name.fill = view.names_color);
  dgui_style_text.addColor(view, "lengths_color").name("lengths").onChange(() =>
    style_length.fill = view.lengths_color);
  dgui_style_text.add(view, "font_family", ["sans-serif", "serif", "monospace"])
    .name("font").onChange(() => style_font.fontFamily = view.font_family);
  dgui_style_text.add(view, "font_size_auto").name("automatic size").onChange(() => {
    style_font.fontSize = (view.font_size_auto ? "" : `${view.font_size}px`);
    if (view.font_size_auto && view.font_size_scroller)
      view.font_size_scroller.remove();
    else
      view.font_size_scroller = create_font_size_scroller();
  });
  dgui_style_text.add(view, "font_size_max", 1, 100).name("max size")
    .onChange(update);

  function create_font_size_scroller() {
    return dgui_style_text.add(view, "font_size", 0.1, 50).name("font size")
      .onChange(() => style_font.fontSize = `${view.font_size}px`);
  }

  const dgui_style_collapsed = dgui_style.addFolder("collapsed");

  dgui_style_collapsed.add(view, "outline_opacity", 0, 1).step(0.1).name("opacity")
    .onChange(() => style_outline.fillOpacity = view.outline_opacity);
  dgui_style_collapsed.addColor(view, "outline_color").name("color").onChange(
    () => style_outline.fill = view.outline_color);

  dgui.add(view, "minimap_show").name("minimap").onChange(show_minimap);

  return dgui;
}


function update_with_minimap(minimap_show) {
  if (minimap_show)
    draw_minimap();
  update();
}
