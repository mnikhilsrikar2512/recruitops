#!/usr/bin/env node
// Reports identifiers referenced but defined nowhere across frontend/shared/*.js.
// The pages load these as classic scripts that share ONE global scope, so a
// call to a function no file defines is a ReferenceError waiting to happen.
// Uses the TypeScript checker (TS2304 "Cannot find name") in plain-JS mode.
//
//   npm install --no-save typescript   (or have it globally)
//   node tools/ci/undef_check.js frontend/shared
function loadTypeScript() {
  // Needs the TypeScript 5.x JS compiler API (TS 7's native build has none).
  const usable = (ts) => ts && typeof ts.createProgram === "function" && ts.ScriptTarget;
  for (const id of ["typescript", "/opt/npm-tools/node_modules/typescript"]) {
    try { const ts = require(id); if (usable(ts)) return ts; } catch { /* try next */ }
  }
  try {
    const globalRoot = require("child_process").execSync("npm root -g").toString().trim();
    const ts = require(require("path").join(globalRoot, "typescript"));
    if (usable(ts)) return ts;
    throw new Error("unusable typescript");
  } catch {
    console.error("TypeScript 5.x compiler API not found: npm install --no-save typescript@5");
    process.exit(2);
  }
}
const ts = loadTypeScript();
const path = require("path");
const dir = process.argv[2] || path.join(__dirname, "..", "..", "frontend", "shared");
const files = ["renderers.js","api-client.js","ui-utils.js","tables.js","forms.js","sidebar.js","pipeline.js","routing.js","navigation.config.js","navigation.js","app.js"].map(f=>path.join(dir,f));
const program = ts.createProgram(files, {allowJs:true, checkJs:true, noEmit:true, lib:["lib.es2022.d.ts","lib.dom.d.ts","lib.dom.iterable.d.ts"], target: ts.ScriptTarget.ES2022, skipLibCheck:true, types: []});
const diags = ts.getPreEmitDiagnostics(program).filter(d => [2304, 2552, 2662].includes(d.code));
let n=0;
for (const d of diags) {
  if (!d.file) continue;
  const {line} = d.file.getLineAndCharacterOfPosition(d.start);
  console.log(`${path.basename(d.file.fileName)}:${line+1}  ${ts.flattenDiagnosticMessageText(d.messageText,"\n")}`); n++;
}
console.log(`TOTAL ${n}`);
process.exit(n ? 1 : 0);
