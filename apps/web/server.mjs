import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "dist");
const port = Number(process.env.PORT || 3000);
const backend = process.env.API_INTERNAL_URL || "http://api.railway.internal:8000";
const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};
const server = http.createServer(async (req, res) => {
  try {
    const uri = new URL(req.url || "/", "http://localhost");
    const isApi = uri.pathname === "/auth" || uri.pathname.startsWith("/auth/") ||
      uri.pathname === "/api" || uri.pathname.startsWith("/api/") ||
      uri.pathname === "/health";
    if (isApi) {
      const target = new URL(uri.pathname + uri.search, backend);
      const response = await fetch(target, {
        method: req.method,
        headers: Object.fromEntries(Object.entries(req.headers).filter(([key]) =>
          !["host", "connection", "content-length", "transfer-encoding"].includes(key))),
        body: ["GET", "HEAD"].includes(req.method || "GET")
          ? undefined
          : await (async () => {
              const chunks = [];
              for await (const chunk of req) chunks.push(chunk);
              return Buffer.concat(chunks);
            })(),
        redirect: "manual",
      });
      res.writeHead(response.status, Object.fromEntries(response.headers.entries()));
      res.end(Buffer.from(await response.arrayBuffer()));
      return;
    }
    const relative = decodeURIComponent(uri.pathname).replace(/^\/+/, "");
    const candidate = path.resolve(root, relative || "index.html");
    if (!candidate.startsWith(root + path.sep) && candidate !== root) {
      res.writeHead(403); res.end("Forbidden"); return;
    }
    let file = candidate;
    try {
      if (!(await stat(file)).isFile()) file = path.join(root, "index.html");
    } catch {
      if (path.extname(file)) {
        res.writeHead(404); res.end("Not found"); return;
      }
      file = path.join(root, "index.html");
    }
    const bytes = await readFile(file);
    res.writeHead(200, {"content-type": types[path.extname(file)] || "application/octet-stream", "cache-control": "no-store"});
    res.end(bytes);
  } catch (error) {
    console.error("Request failed", error);
    res.writeHead(502); res.end("Service unavailable");
  }
});
server.listen(port, "0.0.0.0", () => console.log("ApplyWise frontend listening", port));
