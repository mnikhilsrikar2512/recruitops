/* Build-time Tailwind config. The theme lives in shared/tailwind.config.js
   (it used to configure the Play CDN in the browser); it is read here so
   there is one source of truth. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const sandbox = { tailwind: {} };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "shared/tailwind.config.js"), "utf8"), sandbox);
const theme = sandbox.tailwind.config;

module.exports = {
  ...theme,
  content: [
    path.join(__dirname, "index.html"),
    path.join(__dirname, "pages/*.html"),
    path.join(__dirname, "shared/*.js"),
  ],
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/container-queries")],
};
