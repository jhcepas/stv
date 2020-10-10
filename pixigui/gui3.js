const app = new PIXI.Application({
  antialias: false,
  width: 1800,
  height: 900,

  forceCanvas: false,
});
app.stage.interactive = true;
app.stage.x = 0;
app.stage.skewX = 300;
app.renderer.plugins.interaction.on("pointerdown", hello);
app.renderer.backgroundColor = 0xffffff;

var cont = new PIXI.Container();

document.getElementById("canvas-placeholder").appendChild(app.view);

cont.interactive = true;
cont.on("pointerdown", hello);

const graphics = new PIXI.Graphics();
app.stage.addChild(graphics);

function hello() {
  console.log("UP", app.renderer.plugins.interaction.mouse);
  start();
}

function start() {
  //graphics.clear();
  app.stage.x = Math.random() * 500;
  draw_scene();
}

function draw_scene() {
  // Make a request for a user with a given ID
  axios
    .get("/get_scene_region")
    .then(function (response) {
      items = response["data"]["items"];
      console.log("loaded");
      graphics.lineStyle(1, 0x000000, 1, 0.5, false);
      for (var i = 0; i < items.length; i++) {
        item = items[i];
        if (item["0"] == "r") {
          graphics.drawRect(item[1], item[2], item[3], item[4]);
        } else if (item["0"] == "l") {
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

// app.ticker.add(() => {
//   start();
// });
start();
