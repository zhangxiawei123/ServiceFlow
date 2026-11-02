"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const app = fs.readFileSync(path.join(__dirname, "../frontend/app.js"), "utf8");
const start = app.indexOf("function getUserId() {");
const end = app.indexOf("\nfunction setServiceState(", start);
assert.ok(start >= 0 && end > start, "getUserId must remain independently testable");
const source = app.slice(start, end);

function resolveUserId(entries = []) {
  const storage = new Map(entries);
  const reads = [];
  let generated = 0;
  const userId = vm.runInNewContext(`${source}\ngetUserId();`, {
    localStorage: {
      getItem(key) {
        reads.push(key);
        return storage.get(key) ?? null;
      },
      setItem(key, value) {
        storage.set(key, value);
      },
    },
    crypto: {
      randomUUID() {
        generated += 1;
        return "test-uuid";
      },
    },
  });
  return { userId, storage, reads, generated };
}

test("ServiceFlow reuses its existing user ID", () => {
  const result = resolveUserId([["serviceflow-user-id", "web-existing"]]);
  assert.equal(result.userId, "web-existing");
  assert.equal(result.generated, 0);
  assert.deepEqual(result.reads, ["serviceflow-user-id"]);
});

test("ServiceFlow creates and stores a new user ID", () => {
  const result = resolveUserId();
  assert.equal(result.userId, "web-test-uuid");
  assert.equal(result.storage.get("serviceflow-user-id"), result.userId);
  assert.equal(result.generated, 1);
});

test("ServiceFlow ignores unrelated storage without deleting it", () => {
  const result = resolveUserId([["other-project-user-id", "unrelated-user"]]);
  assert.equal(result.userId, "web-test-uuid");
  assert.equal(result.storage.get("other-project-user-id"), "unrelated-user");
  assert.deepEqual(result.reads, ["serviceflow-user-id"]);
});
