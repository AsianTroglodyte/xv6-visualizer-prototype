const launchLink = document.getElementById("launch-link");
const launchUrl = document.getElementById("launch-url");
const configUrl = document.getElementById("config-url");
const kernelUrl = document.getElementById("kernel-url");
const fsUrl = document.getElementById("fs-url");

const config = new URL("./xv6-jslinux.cfg", window.location.href);
const kernel = new URL("./assets/kernel", window.location.href);
const fs = new URL("./assets/fs/blk.txt", window.location.href);
const jslinux = new URL("https://bellard.org/jslinux/vm.html");

jslinux.searchParams.set("cpu", "riscv64");
jslinux.searchParams.set("url", config.href);
jslinux.searchParams.set("mem", "128");
jslinux.searchParams.set("cols", "100");
jslinux.searchParams.set("rows", "32");
jslinux.searchParams.set("net_url", "");

launchLink.href = jslinux.href;
launchUrl.textContent = jslinux.href;
configUrl.textContent = config.href;
kernelUrl.textContent = kernel.href;
fsUrl.textContent = fs.href;
