tree_scene_w = 1000;
tree_scene_h = 900;
const app = new PIXI.Application({
  antialias: false,
  resolution: 1,
  width: tree_scene_w,
  height: tree_scene_h,
  forceCanvas: false,
});

function test() {
  console.log("TEST");
}

document.onkeydown = function (evt) {
  evt = evt || window.event;
  // if (evt.ctrlKey && evt.keyCode == 90) {
  //   alert("Ctrl-Z");
  // }
  console.log(evt.keyCode);
  if (evt.keyCode == 90) {
    console.log("Zoom");
    zoom_under_mouse(1.2);

    draw_scene();
  }
  if (evt.keyCode == 88) {
    console.log("Zoom out");
    zoom_under_mouse(0.8);
    draw_scene();
  }
};
// app.renderer.plugins.interaction
//   .on("pointerdown", mousedown)
//   .on("mousemove", mousemove)
//   .on("pointerup", mouseup);

app.renderer.backgroundColor = 0xffffff;

var cont = new PIXI.Container();

document.getElementById("canvas-placeholder").appendChild(app.view);

const graphics = new PIXI.Graphics();
tree_scene = new PIXI.Container();
tree_scene.addChild(graphics);
app.stage.addChild(tree_scene);

tree_scene.interactive = true;
tree_scene.buttonMode = true;

console.log(tree_scene);
//tree_scene.on("mouseover", test);
tree_scene
  .on("pointerdown", mousedown)
  .on("mousemove", mousemove)
  .on("pointerup", mouseup);

// alg_scene = new PIXI.Container();
// const alg_graphics = new PIXI.Graphics();
// alg_scene.addChild(alg_graphics);
// app.stage.addChild(alg_scene);

// alg_graphics.lineStyle(1, 0x0000ff, 1, 0.5, false);
// alg_graphics.beginFill(0xaa00bb);
// alg_graphics.drawRect(0, 0, 20, 20);
// alg_graphics.endFill(0xaa00bb);

var Data = function () {
  this.hello = "texto";
  this.draw = draw_scene;
  this.zoom_factor = 2;
};
mydata = new Data();

var click_pos = { x: undefined, y: undefined };
var zoom_factor = 1.0;

function zoom_under_mouse(zoom_factor) {
  mydata.zoom_factor *= zoom_factor;
  mouse_pos = app.renderer.plugins.interaction.mouse.global;
  offset_x = (mouse_pos.x - tree_scene.x) * (zoom_factor - 1);
  offset_y = (mouse_pos.y - tree_scene.y) * (zoom_factor - 1);
  tree_scene.x -= offset_x;
  tree_scene.y -= offset_y;
}

function get_tree_scene_rect() {
  if (tree_scene.x >= 0) {
    xstart = 0;
    tree_rect_width = tree_scene_w - tree_scene.x;
  } else {
    xstart = -1 * tree_scene.x;
    tree_rect_width = tree_scene_w;
  }
  if (tree_scene.y >= 0) {
    ystart = 0;
    tree_rect_height = tree_scene_h - tree_scene.y;
  } else {
    ystart = -1 * tree_scene.y;
    tree_rect_height = tree_scene_h;
  }
  tree_scene.hitArea = new PIXI.Rectangle(
    xstart,
    ystart,
    tree_rect_width,
    tree_rect_height
  );
  console.log("RECT", tree_scene.hitArea);
  return [xstart, ystart, tree_rect_width, tree_rect_height];
}

function mousedown(e) {
  m = app.renderer.plugins.interaction.mouse.global;
  //console.log("Mouse down", m.global, m);
  click_pos.x = m.x;
  click_pos.y = m.y;
  console.log(click_pos);
}

function mousemove(e) {
  m = app.renderer.plugins.interaction.mouse.global;
  if (click_pos.x != undefined && m.x != click_pos.x && m.y != click_pos.y) {
    diffx = click_pos.x - m.x;
    diffy = click_pos.y - m.y;
    tree_scene.x -= diffx;
    tree_scene.y -= diffy;
    click_pos.x = m.x;
    click_pos.y = m.y;
  }
}

function mouseup(e) {
  m = app.renderer.plugins.interaction.mouse.global;
  console.log("Mouse up", m, click_pos);
  if (m.x != click_pos.x && m.y != click_pos.y) {
    diffx = click_pos.x - m.x;
    diffy = click_pos.y - m.y;
    tree_scene.x -= diffx;
    tree_scene.y -= diffy;
    console.log("tree_scene", tree_scene);
  }
  click_pos.x = undefined;
  click_pos.y = undefined;
  draw_scene();
}


document.body.addEventListener("wheel", function(event) {
  event.preventDefault();
  if (event.deltaY > 0)
    zoom_under_mouse(0.8);
  else
    zoom_under_mouse(1.2);

  draw_scene();
});


function draw_scene() {
  for (var i in gui.__controllers) {
    gui.__controllers[i].updateDisplay();
  }

  r = get_tree_scene_rect();
  var query =
    "" + mydata.zoom_factor + "," + r[0] + "," + r[1] + "," + r[2] + "," + r[3];

  console.log(query);
  axios
    .get("/get_scene_region/" + query + "/")
    .then(function (response) {
      console.log("drawn");
      items = response["data"]["items"];
      graphics.clear();

      for (var i = 0; i < items.length; i++) {
        item = items[i];
        //item[1] += Math.random() * 50;
        stroke = 1; //+ Math.random() * 20;
        if (item["0"] == "r") {
          graphics.lineStyle(stroke, 0xc1d6f7, 1, 0, false, "square");
          graphics.drawRect(item[1], item[2], item[3], item[4]);
          // ycenter = item[2] + item[4] / 2;
          // graphics.moveTo(item[1], ycenter);
          // graphics.lineTo(item[1] + item[3], item[2]);
          // graphics.lineTo(item[1] + item[3], item[2] + item[4]);
          // graphics.lineTo(item[1], ycenter);
        } else if (item["0"] == "l") {
          graphics.lineStyle(stroke, 0x000000, 1, 1, false, "square");
          graphics.moveTo(item[1], item[2]);
          graphics.lineTo(item[3], item[4]);
        }
      }
    })
    .catch(function (error) {
      // handle error
      console.log(error);
    })
    .then(function () {
      // always executed
    });
}

var gui = new dat.GUI();
gui.add(mydata, "hello");
gui.add(mydata, "draw");
gui.add(mydata, "zoom_factor");
//gui.add(app, "antialias");

const gra = new PIXI.Graphics();
gra.lineStyle(1, 0x0000ff, 1, 0.5, false);
gra.moveTo(50, 50);
gra.lineTo(200, 25);
gra.lineTo(200, 75);
gra.lineTo(50, 50);
gra.drawCircle(100, 100, 50);
const texture = gra.generateCanvasTexture(PIXI.SCALE_MODES.LINEAR);
const sprite = new PIXI.Sprite();
sprite.texture = texture;
sprite.x = 100;
sprite.y = 1000;
console.log(sprite);
app.stage.addChild(sprite);
//app.stage.addChild(gra);
draw_scene();

// app.ticker.add(() => {
//   draw_scene();
// });
