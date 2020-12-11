'use strict';


// Global variables related to the current view on the tree.
// Most will be shown on the top-right gui (using dat.gui).
const view = {
  pos: {x: 0, y: 0},  // in-tree current pointer position
  tree_name: "HmuY.aln2",
  tree_id: 4,
  show_tree_info: () => show_tree_info(),
  download_newick: () => download_newick(),
  download_svg: () => download_svg(),
  download_image: () => download_image(),
  upload_tree: () => window.location.href = "upload_tree.html",
  drawer: "Full",
  tl: {x: 0, y: 0},  // in-tree coordinates of the top-left of the view
  zoom: {x: 0, y: 0},  // initially chosen depending on the size of the tree
  update_on_drag: true,
  drag: {x0: 0, y0: 0, element: undefined},  // used when dragging
  select_text: false,
  line_color: "#000",
  rect_color: "#000",
  names_color: "#00A",
  lengths_color: "#888",
  font_family: "sans-serif",
  font_size_auto: true,
  font_size_scroller: undefined,
  font_size: 10,
  minimap_show: true,
  minimap_zoom: {x: 1, y: 1},
  datgui: undefined
};


// Run when the page is loaded (the "main" function).
document.addEventListener("DOMContentLoaded", async () => {
  set_query_string_values();
  await reset_zoom(view.zoom.x === 0, view.zoom.y === 0);
  view.datgui = create_datgui();
  draw_minimap();
  update();
});


// Set values that have been given with the query string.
function set_query_string_values() {
  const unknown_params = [];
  const params = new URLSearchParams(location.search);

  for (const [param, value] of params) {
    if (param === "id")
      view.tree_id = Number(value);
    else if (param === "name")
      view.tree_name = value;
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

  if (unknown_params.length != 0)
    swal("Oops!",
      "There were unkonwn parameters passed: " + unknown_params.join(", "),
      "warning");
}


// Update when the window is resized too.
window.addEventListener("resize", update);  // we could also draw_minimap()


// Create the top-right box ("gui") with all the options we can see and change.
function create_datgui() {
  // Shortcut for getting the styles.
  const [style_line, style_rect, style_font, style_names, style_lengths] =
    [1, 2, 3, 4, 5].map(i => document.styleSheets[0].cssRules[i].style);

  const dgui = new dat.GUI({autoPlace: false});
  div_datgui.appendChild(dgui.domElement);

  dgui.add(view.pos, "x").listen();
  dgui.add(view.pos, "y").listen();

  const dgui_tree = dgui.addFolder("tree");

  add_trees(dgui_tree).then(() => {
    dgui_tree.add(view, "show_tree_info").name("info");
    const dgui_download = dgui_tree.addFolder("download");
    dgui_download.add(view, "download_newick").name("newick");
    dgui_download.add(view, "download_svg").name("svg");
    dgui_download.add(view, "download_image").name("image");
    dgui_tree.add(view, "upload_tree").name("upload");
    add_drawers(dgui_tree);  // so they will be added in order
  });

  const dgui_ctl = dgui.addFolder("control");

  dgui_ctl.add(view.tl, "x").name("top-left x").onChange(update);
  dgui_ctl.add(view.tl, "y").name("top-left y").onChange(update);
  dgui_ctl.add(view.zoom, "x").name("zoom x").onChange(update);
  dgui_ctl.add(view.zoom, "y").name("zoom y").onChange(update);
  dgui_ctl.add(view, "update_on_drag").name("continuous dragging");
  dgui_ctl.add(view, "select_text").name("select text").onChange(() =>
    style_font.userSelect = (view.select_text ? "text" : "none"));

  const dgui_style = dgui.addFolder("style");

  dgui_style.addColor(view, "line_color").name("line color").onChange(() =>
    style_line.stroke = view.line_color);
  dgui_style.addColor(view, "rect_color").name("rectangle color").onChange(() =>
    style_rect.stroke = view.rect_color);
  dgui_style.addColor(view, "names_color").name("names color").onChange(() =>
    style_names.fill = view.names_color);
  dgui_style.addColor(view, "lengths_color").name("lengths color").onChange(() =>
    style_lengths.fill = view.lengths_color);
  dgui_style.add(view, "font_family", ["sans-serif", "serif", "monospace"])
    .name("font").onChange(() => style_font.fontFamily = view.font_family);
  dgui_style.add(view, "font_size_auto").name("automatic size").onChange(() => {
    style_font.fontSize = (view.font_size_auto ? "" : `${view.font_size}px`);
    if (view.font_size_auto && view.font_size_scroller)
      view.font_size_scroller.remove();
    else
      view.font_size_scroller = create_font_size_scroller();
  });

  function create_font_size_scroller() {
    return dgui_style.add(view, "font_size", 0.1, 50).name("font size")
      .onChange(() => style_font.fontSize = `${view.font_size}px`);
  }

  dgui.add(view, "minimap_show").name("minimap").onChange(() => {
      const status = (view.minimap_show ? "visible" : "hidden");
      div_minimap.style.visibility = div_visible_rect.style.visibility = status;
      if (view.minimap_show)
        update_minimap_visible_rect();
    });

  return dgui;
}


// Return the data coming from an api endpoint (like "/trees/<id>/size").
async function api(endpoint) {
  const response = await fetch(endpoint);
  return await response.json();
}


// Populate the trees option in dat.gui with the trees available in the server.
async function add_trees(dgui_tree) {
  const data = await api("/trees");
  const trees = {};
  data.map(t => trees[t.name] = t.id);
  dgui_tree.add(view, "tree_name", Object.keys(trees)).name("name")
    .onChange(async () => {
      view.tree_id = trees[view.tree_name];
      view.tl.x = 0;
      view.tl.y = 0;
      await reset_zoom();
      draw_minimap();
      update();
    });
}


// Set the zoom so the full tree fits comfortably on the screen.
async function reset_zoom(reset_zx=true, reset_zy=true) {
  if (reset_zx || reset_zy) {
    const size = await api(`/trees/${view.tree_id}/size`);
    if (reset_zx)
      view.zoom.x = 0.5 * div_tree.offsetWidth / size.width;
    if (reset_zy)
      view.zoom.y = div_tree.offsetHeight / size.height;
  }
}


async function add_drawers(dgui_tree) {
  const drawers = await api("/trees/drawers");
  dgui_tree.add(view, "drawer", drawers).onChange(update);
}


// Show an alert with information about the current tree and view.
async function show_tree_info() {
  const info = await api(`/trees/${view.tree_id}`);
  const params = new URLSearchParams({
    id: view.tree_id,
    name: view.tree_name,
    drawer: view.drawer,
    x: view.tl.x,
    y: view.tl.y,
    w: div_tree.offsetWidth / view.zoom.x,
    h: div_tree.offsetHeight / view.zoom.y});

  const url = window.location.origin + window.location.pathname +
    "?" + params.toString();

  swal("Tree Information",
    `Id: ${info.id}\n` +
    `Name: ${info.name}\n` +
    (info.description ? `Description: ${info.description}\n` : "") + "\n\n" +
    `URL of the current view:\n\n${url}`);
}


// Download a file with the newick representation of the tree.
async function download_newick() {
  const newick = await api(`/trees/${view.tree_id}/newick`);
  download(view.tree_name + ".tree", "data:text/plain;charset=utf-8," + newick);
}


// Download a file with the current view of the tree as a svg.
function download_svg() {
  const svg = div_tree.children[0];
  const svg_xml = (new XMLSerializer()).serializeToString(svg);
  const content = "data:image/svg+xml;base64," + btoa(svg_xml);
  download(view.tree_name + ".svg", content);
}


// Download a file with the current view of the tree as a png.
function download_image() {
  const canvas = document.createElement("canvas");
  canvas.width = div_tree.offsetWidth;
  canvas.height = div_tree.offsetHeight;
  const svg = div_tree.children[0];
  const svg_xml = (new XMLSerializer()).serializeToString(svg);
  const ctx = canvas.getContext("2d");
  const img = new Image();
  img.src = "data:image/svg+xml;base64," + btoa(svg_xml);
  img.addEventListener("load", () => {
    ctx.drawImage(img, 0, 0);
    download(view.tree_name + ".png", canvas.toDataURL("image/png"));
  });
}


// Make the browser download a file.
function download(fname, content) {
  const element = document.createElement("a");
  element.setAttribute("href", encodeURI(content));
  element.setAttribute("download", fname);
  element.style.display = "none";
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
}


// Use the mouse wheel to zoom in/out (instead of scrolling).
document.body.addEventListener("wheel", event => {
  event.preventDefault();
  const zr = (event.deltaY < 0 ? 1.25 : 0.8);  // zoom change (ratio)

  const [do_zoom_x, do_zoom_y] = [!event.altKey, !event.ctrlKey];

  if (do_zoom_x) {
    const zoom_new = zr * view.zoom.x;
    view.tl.x += (1 / view.zoom.x - 1 / zoom_new) * event.pageX;
    view.zoom.x = zoom_new;
  }

  if (do_zoom_y) {
    const zoom_new = zr * view.zoom.y;
    view.tl.y += (1 / view.zoom.y - 1 / zoom_new) * event.pageY;
    view.zoom.y = zoom_new;
  }

  if (do_zoom_x || do_zoom_y)
    update();
}, {passive: false});  // chrome now uses passive=true otherwise


// Mouse down -- select text, or move in minimap, or start dragging.
document.addEventListener("mousedown", event => {
  if (view.select_text) {
    ;  // if by clicking we can select text, don't do anything else
  }
  else if (div_visible_rect.contains(event.target)) {
    view.drag.element = div_visible_rect;
    drag_start(event);
  }
  else if (div_minimap.contains(event.target)) {
    move_minimap_view(event);
  }
  else if (div_tree.contains(event.target)) {
    view.drag.element = div_tree;
    drag_start(event);
  }
});


document.addEventListener("mouseup", event => {
  if (view.drag.element)
    drag_stop(event);

  view.drag.element = undefined;
});


document.addEventListener("mousemove", event => {
  update_pointer_pos(event);

  if (view.drag.element && view.update_on_drag) {
    drag_stop(event);
    drag_start(event);
  }
});


function drag_start(event) {
  view.drag.x0 = event.pageX;
  view.drag.y0 = event.pageY;
}


function drag_stop(event) {
  const dx = event.pageX - view.drag.x0,  // mouse position increment
        dy = event.pageY - view.drag.y0;

  if (dx != 0 || dy != 0) {
    const [scale_x, scale_y] = get_drag_scale();
    view.tl.x += scale_x * dx;
    view.tl.y += scale_y * dy;
    update();
  }
}


function get_drag_scale() {
  if (view.drag.element === div_tree)
    return [-1 / view.zoom.x, -1 / view.zoom.y];
  else if (view.drag.element === div_visible_rect)
    return [1 / view.minimap_zoom.x, 1 / view.minimap_zoom.y];
  else
    console.log(`Cannot find dragging scale for ${view.drag.element}.`);
}


// Move the current tree view to the given mouse position in the minimap.
function move_minimap_view(event) {
  // Top-left pixel coordinates of the tree (0, 0) position in the minimap.
  const [x0, y0] = [div_minimap.offsetLeft + 6, div_minimap.offsetTop + 6];

  // Size of the visible rectangle.
  const [w, h] = [div_visible_rect.offsetWidth, div_visible_rect.offsetHeight];

  view.tl.x = (event.pageX - w/2 - x0) / view.minimap_zoom.x;
  view.tl.y = (event.pageY - h/2 - y0) / view.minimap_zoom.y;
  // So the center of the visible rectangle will be where the mouse is.

  update();
}


// Update the coordinates of the pointer, as shown in the top-right gui.
function update_pointer_pos(event) {
  view.pos.x = view.tl.x + event.pageX / view.zoom.x;
  view.pos.y = view.tl.y + event.pageY / view.zoom.y;
}


// Update the view of all elements (gui, tree, minimap).
function update() {
  view.datgui.updateDisplay();  // update the info box on the top-right

  update_tree();

  if (view.minimap_show)
    update_minimap_visible_rect();
}


// Ask the server for a tree in the new defined region, and draw it.
async function update_tree() {
  const [zx, zy] = [view.zoom.x, view.zoom.y];
  const [x, y] = [view.tl.x, view.tl.y];
  const [w, h] = [div_tree.offsetWidth / zx, div_tree.offsetHeight / zy];

  const qs = `drawer=${view.drawer}&` +
    `zx=${zx}&zy=${zy}&x=${x}&y=${y}&w=${w}&h=${h}`;
  const items = await api(`/trees/${view.tree_id}/draw?${qs}`);

  draw(div_tree, items, view.tl, view.zoom);
}


// Append a svg to the given element, with all the items in the list drawn.
function draw(element, items, tl, zoom) {
  const [w, h] = [element.offsetWidth, element.offsetHeight];

  element.innerHTML = `
    <svg width="${w}" height="${h}">
      ${items.map(item => item2svg(item, tl, zoom)).join("\n")}
    </svg>`;
}


// Return the graphical (svg) element corresponding to an ete item.
function item2svg(item, tl, zoom) {
  // items look like ['r', ...] for a rectangle, etc.
  if (item[0] === 'r') {       // rectangle
    let [ , x, y, w, h] = item;
    x = zoom.x * (x - tl.x);
    y = zoom.y * (y - tl.y);
    w *= zoom.x;
    h *= zoom.y;

    return `<rect class="rect"
      x="${x}" y="${y}" width="${w}" height="${h}"
      fill="none"
      stroke-width="0.2"
      stroke="${view.rect_color}"/>`;
  }
  else if (item[0] === 'l') {  // line
    let [ , x1, y1, x2, y2] = item;
    x1 = zoom.x * (x1 - tl.x);
    y1 = zoom.y * (y1 - tl.y);
    x2 = zoom.x * (x2 - tl.x);
    y2 = zoom.y * (y2 - tl.y);

    return `<line class="line"
      x1="${x1}" y1="${y1}"
      x2="${x2}" y2="${y2}"
      stroke="${view.line_color}"/>`;
  }
  else if (item[0].startsWith('t')) {  // text
    let [text_type, x, y, w, h, txt] = item;
    x = zoom.x * (x - tl.x);
    y = zoom.y * (y - tl.y);
    w *= zoom.x;
    h *= zoom.y;
    const fs = w !== 0 ? Math.min(h, 1.5 * w / txt.length) : h;

    return `<text class="text ${get_class(text_type)}"
      x="${x}" y="${y}"
      font-size="${fs}px">${txt}</text>`;
    // NOTE: If we wanted to use the exact width of the item, we could add:
    //   textLength="${w}px"
  }
  else {
    console.log(`Got unknown item of type: ${item[0]}`);
    return "";
  }
}


function get_class(text_type) {
  if (text_type === "tn")
    return "names";
  else if (text_type === "tl")
    return "lengths";
  else if (text_type === "tt")
    return "tooltip";
  else
    return "";
}


// Draw the full tree on a small div on the bottom-right ("minimap").
async function draw_minimap() {
  const size = await api(`/trees/${view.tree_id}/size`);
  const zx = div_minimap.offsetWidth / size.width,
        zy = div_minimap.offsetHeight / size.height;

  view.minimap_zoom = {x: zx, y: zy};

  const qs = `drawer=Simple&zx=${zx}&zy=${zy}`;
  const items = await api(`/trees/${view.tree_id}/draw?${qs}`);

  draw(div_minimap, items, {x: 0, y: 0}, view.minimap_zoom);

  update_minimap_visible_rect();
}


// Update the minimap's rectangle that represents the current view of the tree.
function update_minimap_visible_rect() {
  const [w_min, h_min] = [5, 5];  // minimum size of the rectangle
  const [round, min, max] = [Math.round, Math.min, Math.max];  // shortcuts

  // Transform all measures into "minimap units" (scaling accordingly).
  const mbw = 3, rbw = 1;  // border-width from .minimap and .visible_rect css
  const mw = div_minimap.offsetWidth - 2 * (mbw + rbw),    // minimap size
        mh = div_minimap.offsetHeight - 2 * (mbw + rbw);
  const wz = view.zoom, mz = view.minimap_zoom;
  const ww = round(mz.x / wz.x * div_tree.offsetWidth),  // viewport size (scaled)
        wh = round(mz.y / wz.y * div_tree.offsetHeight);
  const tx = round(mz.x * view.tl.x),  // top-left corner of visible area
        ty = round(mz.y * view.tl.y);  //   in tree coordinates (scaled)

  const x = max(0, min(tx, mw)),  // clip tx to the interval [0, mw]
        y = max(0, min(ty, mh)),
        w = max(w_min, ww) + min(tx, 0),
        h = max(h_min, wh) + min(ty, 0);

  const rs = div_visible_rect.style;
  rs.left = `${div_minimap.offsetLeft + mbw + x}px`;
  rs.top = `${div_minimap.offsetTop + mbw + y}px`;
  rs.width = `${max(1, min(w, mw - x))}px`;
  rs.height = `${max(1, min(h, mh - y))}px`;
}
