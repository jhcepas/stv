'use strict';

document.addEventListener("DOMContentLoaded", () => {
  const div_tree = document.getElementById('div_tree');
  update();
});


// Variables shown on the top-right gui (using dat.gui).
const view = {
  tl: {x: 0, y: 0},  // in-tree coordinates of the top-left corner of the view
  pos: {x: 0, y: 0},  // in-tree current pointer position
  zoom: 10,
  update_on_drag: true,
  drag: {x0: 0, y0: 0, active: false},  // used when dragging the image
  line_color: "#000",
  rect_color: "#00F",
  font_family: "sans-serif"
};
const dgui = new dat.GUI();
dgui.add(view.pos, "x").listen();
dgui.add(view.pos, "y").listen();
const dgui_ctl = dgui.addFolder("control");
dgui_ctl.add(view.tl, "x").name("top-left x").onChange(update);
dgui_ctl.add(view.tl, "y").name("top-left y").onChange(update);
dgui_ctl.add(view, "zoom", 1, 100).onChange(update);
dgui_ctl.add(view, "update_on_drag").name("continuous dragging");
const dgui_style = dgui.addFolder("style");
dgui_style.addColor(view, "line_color").name("line color").onChange(update);
dgui_style.addColor(view, "rect_color").name("rectangle color").onChange(update);
dgui_style.add(view, "font_family",
  ["sans-serif", "serif", "cursive", "monospace"]).name("font").onChange(update);


// Use the mouse wheel to zoom in/out (instead of scrolling).
document.body.addEventListener("wheel", event => {
  event.preventDefault();
  const zr = (event.deltaY > 0 ? 1.25 : 0.8);  // zoom change (ratio)
  if (is_valid_zoom_change(zr)) {
    const zoom_new = view.zoom * zr,
          tppix = 1 / view.zoom - 1 / zoom_new;  // tree coordinates per pixel
    view.tl.x += tppix * event.pageX;
    view.tl.y += tppix * event.pageY;
    view.zoom = zoom_new;
    update();
  }
}, {passive: false});  // chrome now uses passive=true otherwise

function is_valid_zoom_change(zr) {
  return (zr > 1 && view.zoom < 100) || (zr < 1 && view.zoom > 1);
}


// Drag the tree around (by changing the top-left corner of the view).
document.addEventListener("mousedown", event => {
  if (is_tree(event.target))
    drag_start(event);
});

function is_tree(elem) {
  return elem.id === "tree" || elem.parentNode.id === "tree";
}

document.addEventListener("mouseup", event => {
  if (view.drag.active)
    drag_stop(event);
});

document.addEventListener("mousemove", event => {
  if (view.drag.active && view.update_on_drag) {
    drag_stop(event);
    drag_start(event);
  }

  update_pos(event);
});

function drag_start(event) {
  view.drag.x0 = event.pageX;
  view.drag.y0 = event.pageY;
  view.drag.active = true;
}

function drag_stop(event) {
  const dx = event.pageX - view.drag.x0,  // mouse position increment
        dy = event.pageY - view.drag.y0;
  if (dx != 0 || dy != 0) {
    view.tl.x -= dx / view.zoom;
    view.tl.y -= dy / view.zoom;
    update();
  }
  view.drag.active = false;
}

function update_pos(event) {
  view.pos.x = view.tl.x + event.pageX / view.zoom;
  view.pos.y = view.tl.y + event.pageY / view.zoom;
}


// Ask the server for a tree in the new defined region, and draw it.
function update() {
  dgui.updateDisplay();  // updates the info box on the top-right gui

  const x = view.zoom * Math.max(0, view.tl.x),
        y = view.zoom * Math.max(0, view.tl.y),
        w = window.innerWidth - Math.max(0, - view.zoom * view.tl.x),
        h = window.innerHeight - Math.max(0, - view.zoom * view.tl.y);

  fetch(`/get_scene_region/${view.zoom},${x},${y},${w},${h}/`)
    .then(response => response.json())
    .then(resp_data => draw(resp_data.items))
    .catch(error => console.log(error));
}


// Draw all the items in the list (rectangles and lines) by creating a svg.
function draw(items) {
  const width = window.innerWidth - 10, height = window.innerHeight - 10;
  let svg = `<svg id="tree" width="${width}" height="${height}">`;
  const x0 = view.zoom * view.tl.x,
        y0 = view.zoom * view.tl.y;
  items.forEach(d => {
    switch (d[0]) {
      case 'r':
        const x = d[1] - x0, y = d[2] - y0, w = d[3], h = d[4];
        svg += `<rect x="${x}" y="${y}" width="${w}" height="${h}"
                      fill="none" stroke="${view.rect_color}"/>`;
        break;
      case 'l':
        const x1 = d[1] - x0, y1 = d[2] - y0,
              x2 = d[3] - x0, y2 = d[4] - y0;
        svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
                      stroke="${view.line_color}"/>`;
        break;
    }
  });
  svg += '</svg>';
  div_tree.innerHTML = svg;
}
