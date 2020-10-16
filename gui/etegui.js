'use strict';


// Variables shown with dat.gui.
const data = {
  zoom: 10
};
const gui = new dat.GUI();
gui.add(data, "zoom", 1, 100).onChange(() => update_tree(0, 0));


// Use the mouse wheel to zoom in/out (instead of scrolling).
document.body.addEventListener("wheel", event => {
  event.preventDefault();
  const dz = (event.deltaY > 0 ? 1 : -1);
  if ((data.zoom < 100 && dz > 0) || (data.zoom > 1 && dz < 0)) {
    data.zoom += dz;
    gui.updateDisplay();
    update_tree(0, 0);
  }
}, {passive: false});  // chrome now uses passive=true otherwise


// Ask the server for a tree in the new defined region, and draw it.
function update_tree(x, y, width, height) {
  width = width || window.innerWidth - 10;
  height = height || window.innerHeight - 10;

  fetch(`/get_scene_region/${data.zoom},${x},${y},${width},${height}/`)
    .then(response => response.json())
    .then(resp_data => draw(resp_data.items, width, height))
    .catch(error => console.log(error));
}

function draw(items, width, height) {
  let svg = `<svg width="${width}" height="${height}">`;
  items.forEach(item => {
    switch (item[0]) {
      case 'r':
        svg += `<rect x="${item[1]}" y="${item[2]}"
                width="${item[3]}" height="${item[4]}"
                fill="none" stroke="blue"/>`;
        break;
      case 'l':
        svg += `<line x1="${item[1]}" y1="${item[2]}"
                x2="${item[3]}" y2="${item[4]}" stroke="red"/>`;
        break;
    }
  });
  svg += '</svg>';
  document.getElementById('div_svg').innerHTML = svg;
}


update_tree(0, 0);