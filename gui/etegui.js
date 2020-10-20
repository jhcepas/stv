'use strict';

document.addEventListener("DOMContentLoaded", () => {
  const div_tree = document.getElementById('div_tree');
  update();
});


// Variables shown on the top-right gui (using dat.gui).
const view = {
  x: 0,
  y: 0,
  zoom: 10,
  update_on_drag: true,
  drag: {x0: 0, y0: 0, active: false},  // used when dragging the image
  line_color: "#000",
  rect_color: "#00F",
  font_family: "sans-serif"
};
const dgui = new dat.GUI();
dgui.add(view, "x").onChange(update);
dgui.add(view, "y").onChange(update);
dgui.add(view, "zoom", 1, 100).onChange(update);
dgui.add(view, "update_on_drag").name("continuous dragging");
const dgui_style = dgui.addFolder("style");
dgui_style.addColor(view, "line_color").name("line color").onChange(update);
dgui_style.addColor(view, "rect_color").name("rectangle color").onChange(update);
dgui_style.add(view, "font_family",
  ["sans-serif", "serif", "cursive", "monospace"]).name("font").onChange(update);


// Use the mouse wheel to zoom in/out (instead of scrolling).
document.body.addEventListener("wheel", event => {
  event.preventDefault();
  const zr = (event.deltaY > 0 ? 1.25 : 0.8);  // zoom change (ratio)
  if (valid_zoom_change(zr)) {
    const zoom_new = view.zoom * zr,
          ppix = 1 / view.zoom - 1 / zoom_new;  // points per pixel
    view.x += ppix * event.pageX;
    view.y += ppix * event.pageY;
    view.zoom = zoom_new;
    update();
  }
}, {passive: false});  // chrome now uses passive=true otherwise

function valid_zoom_change(zr) {
  return (view.zoom < 100 && zr > 1) || (view.zoom > 1 && zr < 1);
}


// Move the tree.
document.addEventListener("mousedown", event => {
  if (event.target.id === "tree" || event.target.parentNode.id === "tree") {
    view.drag.x0 = event.pageX;
    view.drag.y0 = event.pageY;
    view.drag.active = true;
  }
});
document.addEventListener("mouseup", event => {
  if (view.drag.active) {
    const dx = event.pageX - view.drag.x0,
          dy = event.pageY - view.drag.y0;
    if (dx != 0 || dy != 0) {
      view.x -= dx / view.zoom;
      view.y -= dy / view.zoom;
      update();
    }
    view.drag.active = false;
  }
});
document.addEventListener("mousemove", event => {
  if (view.drag.active && view.update_on_drag) {
    const dx = event.pageX - view.drag.x0,
          dy = event.pageY - view.drag.y0;
    view.x -= dx / view.zoom;
    view.y -= dy / view.zoom;
    view.drag.x0 = event.pageX;
    view.drag.y0 = event.pageY;
    update();
  }
});


// Ask the server for a tree in the new defined region, and draw it.
function update() {
  dgui.updateDisplay();  // updates the info box on the top-right gui

  const x = view.zoom * Math.max(0, view.x), y = view.zoom * Math.max(0, view.y),
        w = window.innerWidth - Math.max(0, - view.zoom * view.x),
        h = window.innerHeight - Math.max(0, - view.zoom * view.y);

  fetch(`/get_scene_region/${view.zoom},${x},${y},${w},${h}/`)
    .then(response => response.json())
    .then(resp_data => draw(resp_data.items))
    .catch(error => console.log(error));
}


// Draw all the items in the list (rectangles and lines) by creating a svg.
function draw(items) {
  const width = window.innerWidth - 10, height = window.innerHeight - 10;
  let svg = `<svg id="tree" width="${width}" height="${height}">`;
  const x0 = view.zoom * view.x,
        y0 = view.zoom * view.y;
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
