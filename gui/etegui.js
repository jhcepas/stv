'use strict';


// Variables shown with dat.gui.
const scene = {
  x: 0,
  y: 0,
  zoom: 10
};
const gui = new dat.GUI();
gui.add(scene, "x").onChange(() => update_tree());
gui.add(scene, "y").onChange(() => update_tree());
gui.add(scene, "zoom", 1, 100).onChange(() => update_tree());


// Use the mouse wheel to zoom in/out (instead of scrolling).
document.body.addEventListener("wheel", event => {
  event.preventDefault();
  const dz = (event.deltaY > 0 ? 1 : -1);
  if ((scene.zoom < 100 && dz > 0) || (scene.zoom > 1 && dz < 0)) {
    const zoom_old = scene.zoom, zoom_new = zoom_old + dz;
    scene.zoom = zoom_new;
    // scene.x = event.clientX - (zoom_new / zoom_old) * (event.clientX - scene.x);
    // scene.y = event.clientY - (zoom_new / zoom_old) * (event.clientY - scene.y);
    // scene.x += (1 / zoom_old - 1 / zoom_new) * event.clientX;
    // scene.y += (1 / zoom_old - 1 / zoom_new) * event.clientY;
    gui.updateDisplay();
    update_tree();
  }
}, {passive: false});  // chrome now uses passive=true otherwise


// Ask the server for a tree in the new defined region, and draw it.
function update_tree() {
  const width = window.innerWidth;
  const height = window.innerHeight;

  fetch(`/get_scene_region/${scene.zoom},${scene.x},${scene.y},${width},${height}/`)
    .then(response => response.json())
    .then(resp_data => draw(resp_data.items))
    .catch(error => console.log(error));
}

function draw(items) {
  const w = window.innerWidth - 10, h = window.innerHeight - 10;
  let svg = `<svg width="${w}" height="${h}">`;
  items.forEach(d => {
    switch (d[0]) {
      case 'r':
        svg += `<rect x="${d[1]}" y="${d[2]}" width="${d[3]}" height="${d[4]}"
                      fill="none" stroke="blue"/>`;
        break;
      case 'l':
        svg += `<line x1="${d[1]}" y1="${d[2]}" x2="${d[3]}" y2="${d[4]}"
                      stroke="red"/>`;
        break;
    }
  });
  svg += '</svg>';
  document.getElementById('div_svg').innerHTML = svg;
}


update_tree();
