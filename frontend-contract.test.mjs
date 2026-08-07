import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("contains every required dashboard route", async () => {
  for (const path of [
    "app/page.tsx",
    "app/funds/page.tsx",
    "app/allocation/page.tsx",
    "app/status/page.tsx",
  ]) {
    assert.ok((await read(path)).length > 200, `${path} should be implemented`);
  }
});

test("uses a runtime API variable and no direct Fipiran browser request", async () => {
  const proxy = await read("app/api/proxy/[...path]/route.ts");
  const client = await read("lib/api.ts");
  assert.match(proxy, /process\.env\.VITE_API_URL/);
  assert.match(client, /\/api\/proxy/);
  assert.doesNotMatch(client, /fipiran\.com/i);
});

test("allocation uses the required exposure formula without fallback records", async () => {
  const allocation = await read("app/allocation/page.tsx");
  assert.match(allocation, /stock \+ equityFund/);
  assert.match(allocation, /API فعلی داده Exposure ارائه نمی‌کند/);
  assert.doesNotMatch(allocation, /sampleData|demoData|mockData/);
});

test("frontend Dockerfile exposes the production port and healthcheck", async () => {
  const dockerfile = await read("Dockerfile");
  assert.match(dockerfile, /FROM node:22\.13-alpine/);
  assert.match(dockerfile, /EXPOSE 80/);
  assert.match(dockerfile, /HEALTHCHECK/);
});
