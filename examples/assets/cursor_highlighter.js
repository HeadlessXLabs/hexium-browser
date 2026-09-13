(() => {
  if (document.getElementById("hexium-cursor-highlighter")) return;

  const BLUE = "59, 130, 246";
  const el = document.createElement("div");
  el.id = "hexium-cursor-highlighter";
  el.style.cssText = [
    "position:fixed",
    "left:0",
    "top:0",
    "width:10px",
    "height:10px",
    `background-color:rgba(${BLUE},0.9)`,
    "border-radius:50%",
    "pointer-events:none",
    "z-index:2147483647",
    "transform:translate(-50%,-50%)",
    `box-shadow:0 0 0 5px rgba(${BLUE},0.5),0 0 0 10px rgba(${BLUE},0.3),0 0 0 15px rgba(${BLUE},0.12)`,
  ].join(";");

  function mount() {
    const root = document.body || document.documentElement;
    if (root && !document.getElementById("hexium-cursor-highlighter")) {
      root.appendChild(el);
    }
  }

  function onMove(e) {
    mount();
    el.style.left = e.clientX + "px";
    el.style.top = e.clientY + "px";
  }

  window.addEventListener("mousemove", onMove, true);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
  } else {
    mount();
  }
})();
