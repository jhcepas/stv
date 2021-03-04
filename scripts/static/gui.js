import { create_datgui } from "./menu.js";

export { update, on_tree_change, on_drawer_change, show_minimap, draw_minimap };


// Global variables related to the current view on the tree.
// Most will be shown on the top-right gui (using dat.gui).
const view = {
  // tree
  tree: "",
  subtree: "",
  upload_tree: () => window.location.href = "upload_tree.html",
  download_newick: () => download_newick(),
  download_svg: () => download_svg(),
  download_image: () => download_image(),

  // representation
  drawer: "Full",
  align_bar: 80,
  is_circular: false,
  rmin: 0,
  angle: {min: -180, max: 180},
  min_size: 6,

  // search
  search: () => search(),
  searches: {},  // will contain the searches done and their results

  // info
  nodes: {boxes: {}, n: 0},  // will contain the visible nodeboxes
  pos: {x: 0, y: 0},  // in-tree current pointer position
  show_tree_info: () => show_tree_info(),

  // view
  reset_view: () => reset_view(),
  tl: {x: 0, y: 0},  // in-tree coordinates of the top-left of the view
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

// Used when dragging and zooming.
const dragging = {x0: 0, y0: 0, element: undefined, moved: false};
const zooming = {qz: {x: 1, y: 1}, timeout: undefined};

const trees = {};  // will contain trees[tree_name] = tree_id
let datgui = undefined;



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


// Run when the page is loaded (the "main" function).
document.addEventListener("DOMContentLoaded", async () => {
  await init_trees();
  const drawers = await api("/trees/drawers");
  datgui = create_datgui(view, Object.keys(trees), drawers);

  set_query_string_values();

  await reset_zoom(view.zoom.x === 0, view.zoom.y === 0);
  draw_minimap();
  update();
});


// Update when the window is resized too.
window.addEventListener("resize", update);  // we could also draw_minimap()


// Hotkeys.
document.addEventListener("keydown", event => {
  if (event.key === "/" || event.key === "F1") {
    event.preventDefault();
    search();
  }
  else if (event.key === "r") {
    event.preventDefault();
    reset_view();
  }
  else if (event.key === "m") {
    event.preventDefault();
    view.minimap_show = !view.minimap_show;
    show_minimap(view.minimap_show);
    datgui.updateDisplay();  // update the info box on the top-right
  }
  else if (event.key === "+") {
    event.preventDefault();
    const center = [div_tree.offsetWidth / 2, div_tree.offsetHeight / 2];
    zoom_around(center, 1.25);
  }
  else if (event.key === "-") {
    event.preventDefault();
    const center = [div_tree.offsetWidth / 2, div_tree.offsetHeight / 2];
    zoom_around(center, 0.8);
  }
});


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
  div_aligned.style.display = view.drawer.startsWith("Align") ? "initial" : "none";

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

  div_aligned.style.display = view.drawer.startsWith("Align") ? "initial" : "none";

  if (unknown_params.length != 0)
    Swal.fire("Oops!",
      "There were unknown parameters passed: " + unknown_params.join(", "),
      "warning");
}


function show_minimap(show) {
  const status = (show ? "visible" : "hidden");
  div_minimap.style.visibility = div_visible_rect.style.visibility = status;
  if (show)
    update_minimap_visible_rect();
}


function get_tid() {
  return trees[view.tree] + (view.subtree ? "," + view.subtree : "");
}


// Set the zoom so the full tree fits comfortably on the screen.
async function reset_zoom(reset_zx=true, reset_zy=true) {
  if (reset_zx || reset_zy) {
    const size = await api(`/trees/${get_tid()}/size`);
    if (view.is_circular) {
      const smaller_dim = Math.min(div_tree.offsetWidth, div_tree.offsetHeight);
      view.zoom.x = view.zoom.y = smaller_dim / (view.rmin + size.width) / 2;
    }
    else {
      if (reset_zx)
        view.zoom.x = 0.5 * div_tree.offsetWidth / size.width;
      if (reset_zy)
        view.zoom.y = div_tree.offsetHeight / size.height;
    }
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
  const qs = new URLSearchParams({x: x, y: y, w: w, h: h,
    tree: view.tree, subtree: view.subtree, drawer: view.drawer}).toString();
  return window.location.origin + window.location.pathname + "?" + qs;
}


// Show an alert with information about the current tree and view.
async function show_tree_info() {
  const info = await api(`/trees/${get_tid()}`);
  const url = get_url_view(view.tl.x, view.tl.y,
    div_tree.offsetWidth / view.zoom.x, div_tree.offsetHeight / view.zoom.y);

  const result = await Swal.fire({
    title: "Tree Information",
    icon: "info",
    html: `${info.name} (<a href="/trees/${info.id}">${info.id}</a>)<br><br>` +
    (info.description ? `${info.description}<br><br>` : "") +
    `(<a href="${url}">current view</a>)`,
    confirmButtonText: navigator.clipboard ? "Copy view to clipboard" : "Ok",
    showCancelButton: true,
  });

  if (result.isConfirmed && navigator.clipboard)
    navigator.clipboard.writeText(url);
}


// Download a file with the newick representation of the tree.
async function download_newick() {
  const newick = await api(`/trees/${get_tid()}/newick`);
  download(view.tree + ".tree", "data:text/plain;charset=utf-8," + newick);
}


// Download a file with the current view of the tree as a svg.
function download_svg() {
  const svg = div_tree.children[0].cloneNode(true);
  Array.from(svg.getElementsByClassName("node")).forEach(e => e.remove());
  const svg_xml = (new XMLSerializer()).serializeToString(svg);
  const content = "data:image/svg+xml;base64," + btoa(svg_xml);
  download(view.tree + ".svg", content);
}


// Download a file with the current view of the tree as a png.
function download_image() {
  const canvas = document.createElement("canvas");
  canvas.width = div_tree.offsetWidth;
  canvas.height = div_tree.offsetHeight;
  const svg = div_tree.children[0].cloneNode(true);
  Array.from(svg.getElementsByClassName("node")).forEach(e => e.remove());
  const svg_xml = (new XMLSerializer()).serializeToString(svg);
  const ctx = canvas.getContext("2d");
  const img = new Image();
  img.src = "data:image/svg+xml;base64," + btoa(svg_xml);
  img.addEventListener("load", () => {
    ctx.drawImage(img, 0, 0);
    download(view.tree + ".png", canvas.toDataURL("image/png"));
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

      let qs = `text=${encodeURIComponent(text)}&drawer=${view.drawer}`;
      if (view.is_circular)
        qs += `&rmin=${view.rmin}&amin=${view.angle.min}&amax=${view.angle.max}`;

      return api(`/trees/${get_tid()}/search?${qs}`);
    }});

  if (result.isConfirmed) {
    if (result.value.message === 'ok') {
      show_search_results(search_text, result.value.nodes, result.value.max);

      if (result.value.nodes.length > 0) {
        const colors = ["#FF0", "#F0F", "#0FF", "#F00", "#0F0", "#00F"];
        view.searches[search_text] = {
          nodes: result.value.nodes,
          max: result.value.max,
          color: colors[Object.keys(view.searches).length % colors.length],
        };

        add_search_boxes(search_text);

        add_search_to_datgui(search_text);
      }
    }
    else {
      Swal.fire({
        position: "bottom-start",
        showConfirmButton: false,
        text: result.value.message,
        icon: "error"});
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
    const coordinates = `${box[0].toPrecision(4)} : ${box[1].toPrecision(4)}`;
    return `<a href="#" title="Coordinates: ${coordinates}" ` +
      `onclick="zoom_into_box([${box}]); return false;">` +
      `${node_id.length > 0 ? node_id : "root"}</a>`;
  }

  if (n > 0)
    Swal.fire({
      position: "bottom-start",
      html: info + nodes.map(link).join("<br>")});
  else
    Swal.fire({
      position: "bottom-start",
      text: "No nodes found for search: " + search_text,
      icon: "warning"});
}


// Add boxes to the tree view that represent the visible nodes matched by
// the given search text.
function add_search_boxes(search_text) {
  const cname = get_search_class(search_text);
  const color = view.searches[search_text].color;
  const g = div_tree.children[0].children[0];

  view.searches[search_text].nodes.forEach(node => {
    let [node_id, box] = node;

    if (node_id in view.nodes.boxes)
      box = view.nodes.boxes[node_id];  // so we get a nicer surrounding box
    else
      return;  // NOTE: we could leave it and still add it, but what for?

    const b = view.is_circular ?
      create_asec(box, view.tl, view.zoom.x, "search " + cname) :
      create_rect(box, view.tl, view.zoom.x, view.zoom.y, "search " + cname);

    b.addEventListener("click", event => on_box_click(event, box, node_id));

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


// Zoom the current view into the area defined by the given box, with a border
// marking the fraction of zoom-out (to see a bit the surroundings).
function zoom_into_box(box, border=0.10) {
  if (!view.is_circular) {
    const [x, y, w, h] = box;
    view.tl.x = x - border * w;
    view.tl.y = y - border * h;
    view.zoom.x = div_tree.offsetWidth / (w * (1 + 2 * border));
    view.zoom.y = div_tree.offsetHeight / (h * (1 + 2 * border));
  }
  else {
    const [r, a, dr, da] = box;
    const points = [[r, a], [r, a+da], [r+dr, a], [r+dr, a+da]];
    const xs = points.map(([r, a]) => r * Math.cos(a)),
          ys = points.map(([r, a]) => r * Math.sin(a));
    const [x, y] = [Math.min(...xs), Math.min(...ys)];
    const [w, h] = [Math.max(...xs) - x, Math.max(...ys) - y];
    const [zx, zy] = [div_tree.offsetWidth / w, div_tree.offsetHeight / h];
    if (zx < zy) {
      view.tl.x = x - border * w;
      view.zoom.x = view.zoom.y = zx / (1 + 2 * border);
      view.tl.y = y - (div_tree.offsetHeight / zx - h) / 2 - border * h;
    }
    else {
      view.tl.y = y - border * h;
      view.zoom.x = view.zoom.y = zy / (1 + 2 * border);
      view.tl.x = x - (div_tree.offsetWidth / zy - w) / 2 - border * w;
    }
  }
  update();
}

window.zoom_into_box = zoom_into_box;  // exposed so it can be called in onclick


// Use the mouse wheel to zoom in/out (instead of scrolling).
document.addEventListener("wheel", event => {
  event.preventDefault();
  const qz = (event.deltaY < 0 ? 1.25 : 0.8);  // zoom change (quotient)

  if (event.ctrlKey && view.is_circular) {
    const x = view.tl.x + event.pageX / view.zoom.x,
          y = view.tl.y + event.pageY / view.zoom.y;
    const angle = Math.atan2(y, x) * 180 / Math.PI;

    view.angle.min = angle + qz * (view.angle.min - angle);
    view.angle.max = angle + qz * (view.angle.max - angle);

    if (zooming.timeout)
      window.clearTimeout(zooming.timeout);

    zooming.timeout = window.setTimeout(() => {
      zooming.timeout = undefined;
      if (view.minimap_show)
        draw_minimap();
      update();
    }, 200);  // 200 ms until we try to actually update (if not cancelled before!)
  }
  else {
    let [do_zoom_x, do_zoom_y] = [!event.ctrlKey, !event.altKey];
    zoom_around([event.pageX, event.pageY], qz, do_zoom_x, do_zoom_y);
  }
}, {passive: false});  // chrome now uses passive=true otherwise


// Zoom by a factor qz maintaining the given point on the screen.
function zoom_around(point, qz, do_zoom_x=true, do_zoom_y=true) {
  const [x, y] = point;

  if (view.is_circular)
    do_zoom_x = do_zoom_y = (do_zoom_x || do_zoom_y);  // all together

  if (do_zoom_x) {
    const zoom_new = qz * view.zoom.x;
    view.tl.x += (1 / view.zoom.x - 1 / zoom_new) * x;
    view.zoom.x = zoom_new;
    zooming.qz.x *= qz;
  }

  if (do_zoom_y) {
    const zoom_new = qz * view.zoom.y;
    view.tl.y += (1 / view.zoom.y - 1 / zoom_new) * y;
    view.zoom.y = zoom_new;
    zooming.qz.y *= qz;
  }

  if (do_zoom_x || do_zoom_y)
    smooth_zoom(point);
}


// Perform zoom by scaling the svg, and really update it only after a timeout.
function smooth_zoom(point) {
  const [x, y] = point;

  if (zooming.timeout)
    window.clearTimeout(zooming.timeout);

  const g = div_tree.children[0].children[0];
  g.setAttribute("transform",
    `scale(${zooming.qz.x}, ${zooming.qz.y}) ` +
    `translate(${(1 / zooming.qz.x - 1) * x} ${(1 / zooming.qz.y - 1) * y})`);

  if (view.minimap_show)
    update_minimap_visible_rect();

  zooming.timeout = window.setTimeout(() => {
    zooming.qz.x = zooming.qz.y = 1;
    zooming.timeout = undefined;
    update();
  }, 200);  // 200 ms until we try to actually update (if not cancelled before!)
}


// Mouse down -- select text, or move in minimap, or start dragging.
document.addEventListener("mousedown", event => {
  if (view.select_text) {
    ;  // if by clicking we can select text, don't do anything else
  }
  else if (div_visible_rect.contains(event.target)) {
    dragging.element = div_visible_rect;
    drag_start(event);
  }
  else if (div_minimap.contains(event.target)) {
    move_minimap_view(event);
  }
  else if (div_tree.contains(event.target)) {
    dragging.element = div_tree;
    drag_start(event);
  }
});


document.addEventListener("mouseup", event => {
  if (dragging.element) {
    drag_stop(event);
    if (dragging.moved)
      update_tree();
    dragging.moved = false;
  }

  dragging.element = undefined;
});


document.addEventListener("mousemove", event => {
  update_pointer_pos(event);

  if (dragging.element) {
    dragging.moved = true;

    if (view.update_on_drag)
      update_tree();

    const [scale_x, scale_y] = get_drag_scale();
    view.tl.x += scale_x * event.movementX;
    view.tl.y += scale_y * event.movementY;

    let dx = event.pageX - dragging.x0,
        dy = event.pageY - dragging.y0;

    if (dragging.element === div_visible_rect) {
      dx *= -view.zoom.x / view.minimap_zoom.x;
      dy *= -view.zoom.y / view.minimap_zoom.y;
    }

    const g = div_tree.children[0].children[0];
    g.setAttribute("transform", `translate(${dx} ${dy})`);

    datgui.updateDisplay();  // update the info box on the top-right

    if (view.minimap_show)
      update_minimap_visible_rect();
  }
});


function drag_start(event) {
  div_tree.style.cursor = div_visible_rect.style.cursor = "grabbing";

  dragging.x0 = event.pageX;
  dragging.y0 = event.pageY;
}


function drag_stop(event) {
  div_tree.style.cursor = "auto";
  div_visible_rect.style.cursor = "grab";
}


function get_drag_scale() {
  if (dragging.element === div_tree)
    return [-1 / view.zoom.x, -1 / view.zoom.y];
  else if (dragging.element === div_visible_rect)
    return [1 / view.minimap_zoom.x, 1 / view.minimap_zoom.y];
  else
    console.log(`Cannot find dragging scale for ${dragging.element}.`);
}


// Move the current tree view to the given mouse position in the minimap.
function move_minimap_view(event) {
  const mbw = 3;  // border-width from .minimap css

  // Top-left pixel coordinates of the tree (0, 0) position in the minimap.
  let [x0, y0] = [div_minimap.offsetLeft + mbw, div_minimap.offsetTop + mbw];
  if (view.is_circular) {
    x0 += (div_minimap.offsetWidth - 2 * mbw) / 2;
    y0 += (div_minimap.offsetHeight - 2 * mbw) / 2;
  }

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
  datgui.updateDisplay();  // update the info box on the top-right

  update_tree();

  if (view.minimap_show)
    update_minimap_visible_rect();
}


// Ask the server for a tree in the new defined region, and draw it.
async function update_tree() {
  const [zx, zy] = [view.zoom.x, view.zoom.y];
  const [x, y] = [view.tl.x, view.tl.y];
  const [w, h] = [div_tree.offsetWidth / zx, div_tree.offsetHeight / zy];

  div_tree.style.cursor = "wait";

  let qs = `drawer=${view.drawer}&min_size=${view.min_size}&` +
    `zx=${zx}&zy=${zy}&x=${x}&y=${y}&w=${w}&h=${h}`;
  if (view.is_circular)
    qs += `&rmin=${view.rmin}&amin=${view.angle.min}&amax=${view.angle.max}`;
  const items = await api(`/trees/${get_tid()}/draw?${qs}`);

  save_nodeboxes(items);

  draw(div_tree, items, view.tl, view.zoom);

  if (view.drawer.startsWith("Align")) {
    const aitems = await api(`/trees/${get_tid()}/draw?${qs}&aligned`);
    draw(div_aligned, aitems, {x: 0, y: view.tl.y}, view.zoom);
  }

  for (let search_text in view.searches)
    add_search_boxes(search_text);

  div_tree.style.cursor = "auto";
}


// From all the graphic items received, save the nodeboxes in the global
// variable view.nodes. We can use them later to count the total number of
// nodes shown, and to color the searched nodes that are currently visible.
function save_nodeboxes(items) {
  view.nodes.boxes = {};
  view.nodes.n = 0;
  items.forEach(item => {
    if (is_nodebox(item)) {
      const [shape, box, type, name, properties, node_id] = item;
      view.nodes.boxes[node_id] = box;
      view.nodes.n += 1;
    }
  });
}

function is_nodebox(item) {
  return (is_rect(item) || is_asec(item)) && item[2] === "node";
}

const is_rect = item => item[0] === 'r';  // is it a rectangle?
const is_asec = item => item[0] === 's';  // is it an annular sector?


// Drawing.

function create_svg_element(name, attrs) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [attr, value] of Object.entries(attrs))
    element.setAttributeNS(null, attr, value);
  return element;
}


function create_rect(box, tl, zx=1, zy=1, type="") {
  const [x, y, w, h] = box;

  return create_svg_element("rect", {
    "class": "box " + type,
    "x": zx * (x - tl.x), "y": zy * (y - tl.y),
    "width": zx * w, "height": zy * h,
    "stroke": view.rect_color});
}


// Return a newly-created svg annular sector, described by box and with zoom z.
function create_asec(box, tl, z=1, type="") {
  const [r, a, dr, da] = box;
  const large = da > Math.PI ? 1 : 0;
  const p00 = cartesian_shifted(r, a, tl, z),
        p01 = cartesian_shifted(r, a + da, tl, z),
        p10 = cartesian_shifted(r + dr, a, tl, z),
        p11 = cartesian_shifted(r + dr, a + da, tl, z);

  return create_svg_element("path", {
    "class": "box " + type,
    "d": `M ${p00.x} ${p00.y}
          L ${p10.x} ${p10.y}
          A ${z * (r + dr)} ${z * (r + dr)} 0 ${large} 1 ${p11.x} ${p11.y}
          L ${p01.x} ${p01.y}
          A ${z * r} ${z * r} 0 ${large} 0 ${p00.x} ${p00.y}`,
    "fill": view.box_color});
}

function cartesian_shifted(r, a, tl, z) {
  return {x: z * (r * Math.cos(a) - tl.x),
          y: z * (r * Math.sin(a) - tl.y)};
}


function create_line(p1, p2, tl, zx, zy) {
  const [x1, y1] = [zx * (p1[0] - tl.x), zy * (p1[1] - tl.y)],
        [x2, y2] = [zx * (p2[0] - tl.x), zy * (p2[1] - tl.y)];

  return create_svg_element("line", {
    "class": "line",
    "x1": x1, "y1": y1,
    "x2": x2, "y2": y2,
    "stroke": view.line.color});
}


function create_arc(p1, p2, large, tl, z=1) {
  const [x1, y1] = p1,
        [x2, y2] = p2;
  const r = z * Math.sqrt(x1*x1 + y1*y1);
  const n1 = {x: z * (x1 - tl.x), y: z * (y1 - tl.y)},
        n2 = {x: z * (x2 - tl.x), y: z * (y2 - tl.y)};

  return create_svg_element("path", {
    "class": "line",
    "d": `M ${n1.x} ${n1.y} A ${r} ${r} 0 ${large} 1 ${n2.x} ${n2.y}`,
    "stroke": view.line.color});
}


function create_text(text, fs, point, tl, zx, zy, type) {
  const [x, y] = [zx * (point[0] - tl.x), zy * (point[1] - tl.y)];

  const t = create_svg_element("text", {
    "class": "text " + type,
    "x": x, "y": y,
    "font-size": `${fs}px`});

  t.appendChild(document.createTextNode(text));

  return t;
}


// Return svg transformation to flip the given text.
function flip(text) {
  const bbox = text.getBBox();  // NOTE: text must be already in the DOM
  return ` rotate(180, ${bbox.x + bbox.width/2}, ${bbox.y + bbox.height/2})`;
}


// Append a svg to the given element, with all the items in the list drawn.
function draw(element, items, tl, zoom) {
  const svg = create_svg_element("svg", {
    "width": element.offsetWidth, "height": element.offsetHeight});

  if (element.children.length > 0)
    element.children[0].replaceWith(svg);
  else
    element.appendChild(svg);

  const g = create_svg_element("g", {});

  svg.appendChild(g);

  items.forEach(item => append_item(g, item, tl, zoom));
}


// Append to g the graphical (svg) element corresponding to a drawer item.
function append_item(g, item, tl, zoom) {
  // item looks like ['r', ...] for a rectangle, etc.

  const [zx, zy] = [zoom.x, zoom.y];  // shortcut

  if (item[0] === 'r' || item[0] === 's') {  // rectangle or annular sector
    const [shape, box, type, name, properties, node_id] = item;

    const b = shape === 'r' ?
      create_rect(box, tl, zx, zy, type) :
      create_asec(box, tl, zx, type);

    g.appendChild(b);

    b.addEventListener("click", event => on_box_click(event, box, node_id));

    if (name.length > 0 || Object.entries(properties).length > 0)
      b.appendChild(create_tooltip(name, properties));
  }
  else if (item[0] === 'l') {  // line
    const [ , p1, p2] = item;

    g.appendChild(create_line(p1, p2, tl, zx, zy));
  }
  else if (item[0] === 'c') {  // arc (part of a circle)
    const [ , p1, p2, large] = item;

    g.appendChild(create_arc(p1, p2, large, tl, zx));
  }
  else if (item[0] === 't') {  // text
    const [ , text, point, fs, type] = item;
    const font_size = font_adjust(type, zy * fs);

    const t = create_text(text, font_size, point, tl, zx, zy, type);

    g.appendChild(t);

    if (view.is_circular) {
      const [x, y] = point;
      const angle = Math.atan2(y, x) * 180 / Math.PI;

      t.setAttributeNS(null, "transform",
        `rotate(${angle}, ${zx * (x - tl.x)}, ${zy * (y - tl.y)})` +
        ((angle < -90 || angle > 90) ? flip(t) : ""));
    }
  }
  else if (item[0] === 'a') {  // array
    const [ , box, a] = item;
    const [x0, y0, dx0, dy0] = box;
    const dx = dx0 / a.length / zx;

    for (let i = 0, x = 0; i < a.length; i++, x+=dx) {
      const r = create_rect([x, y0, dx, dy0], tl, zx, zy, "array");
      r.style.stroke = `hsl(${a[i]}, 100%, 50%)`;
      g.appendChild(r);
    }
  }
}


// Return the font size adjusted for the given type of text.
function font_adjust(type, fs) {
  if (type === "name")
    return fs;  // no adjustments
  else
    return Math.min(view.font_size_max, fs);
  // NOTE: we could modify the font size depending on other kinds of text
  // (limiting their minimum and maximum sizes if appropriate, for example).
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


function create_tooltip(name, properties) {
  const title = create_svg_element("title", {});
  const text = name + "\n" +
    Object.entries(properties).map(x => x[0] + ": " + x[1]).join("\n");
  title.appendChild(document.createTextNode(text));
  return title;
}


// Minimap.

// Draw the full tree on a small div on the bottom-right ("minimap").
async function draw_minimap() {
  const size = await api(`/trees/${get_tid()}/size`);
  const mbw = 3;  // border-width from .minimap css
  if (view.is_circular) {
    if (div_minimap.offsetWidth < div_minimap.offsetHeight)
      div_minimap.style.height = `${div_minimap.offsetWidth - 2 * mbw}px`;
    else
      div_minimap.style.width = `${div_minimap.offsetHeight - 2 * mbw}px`;

    view.minimap_zoom.x = view.minimap_zoom.y =
      (div_minimap.offsetWidth - 2 * mbw) / (view.rmin + size.width) / 2;
  }
  else {
    div_minimap.style.width = "10%";
    div_minimap.style.height = "60%";
    view.minimap_zoom.x = (div_minimap.offsetWidth - 2 * mbw) / size.width;
    view.minimap_zoom.y = (div_minimap.offsetHeight - 2 * mbw) / size.height;
  }

  let qs = `zx=${view.minimap_zoom.x}&zy=${view.minimap_zoom.y}`;
  if (view.is_circular)
    qs += `&drawer=CircSimple&rmin=${view.rmin}` +
      `&amin=${view.angle.min}&amax=${view.angle.max}`;
  else
    qs += "&drawer=Simple";

  const items = await api(`/trees/${get_tid()}/draw?${qs}`);

  const offset = -(div_minimap.offsetWidth - 2 * mbw) / view.minimap_zoom.x / 2;
  const tl = view.is_circular ? {x: offset, y: offset} : {x: 0, y: 0};

  draw(div_minimap, items, tl, view.minimap_zoom);

  Array.from(div_minimap.getElementsByClassName("node")).forEach(
    e => e.remove());

  view.minimap_uptodate = true;

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
  let tx = round(mz.x * view.tl.x),  // top-left corner of visible area
      ty = round(mz.y * view.tl.y);  //   in tree coordinates (scaled)

  if (view.is_circular) {
    tx += mw / 2;
    ty += mh / 2;
  }

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
