// End-to-end check of the review screen against a running API with a run waiting at the release gate (SPEC-021).
//
//   uv run python demo/seed_review.py                       # a run waiting at the release gate in the demo database
//   HISHOB_TOKEN_SECRET=… uv run uvicorn hishob.api.app:serve --factory --port 8000
//   REVIEWER=<reviewer token> CONTRIBUTOR=<contributor token> PUBLIC_DIR=var/demo/public [VIEWPORT=desktop] \
//     node web/e2e/review.mjs [url] [shots]
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import fs from "node:fs";

const require = createRequire(import.meta.url);
let playwright;
try {
  playwright = require("playwright");
} catch {
  playwright = require(execSync("npm root -g").toString().trim() + "/playwright");
}
const { chromium, devices } = playwright;
const BASE = process.argv[2] ?? "http://127.0.0.1:8000";
const SHOTS = process.argv[3];
const { REVIEWER, CONTRIBUTOR, PUBLIC_DIR } = process.env;
if (!REVIEWER || !CONTRIBUTOR) throw new Error("set REVIEWER and CONTRIBUTOR to signed access codes");
const failures = [];
const check = (ok, what) => {
  console.log(`${ok ? "pass" : "FAIL"}  ${what}`);
  if (!ok) failures.push(what);
};

const browser = await chromium.launch();
{
  // One viewport per run, because each run decides the staged run it is given: VIEWPORT=desktop for the wide layout.
  const [name, options] = process.env.VIEWPORT === "desktop" ? ["desktop", { viewport: { width: 1280, height: 900 } }] : ["phone", { ...devices["Pixel 7"] }];
  const context = await browser.newContext(options);
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));

  // residents never see the tab; a #review link shows it
  await page.goto(BASE);
  check((await page.getByRole("tab", { name: /Review|तपासणी|समीक्षा/ }).count()) === 0, `${name}: no Review tab for an ordinary visitor`);
  await page.goto(`${BASE}/#review`);
  await page.reload();
  await page.getByRole("button", { name: "English" }).click();
  await page.getByRole("tab", { name: "Review" }).click();

  // a code that is not a reviewer's is refused, and forgotten
  await page.getByLabel("Reviewer access code").fill(CONTRIBUTOR);
  await page.getByRole("button", { name: "OK" }).click();
  await page.getByText("This code is not a reviewer’s.").waitFor({ timeout: 10000 });
  check(true, `${name}: a contributor's code is refused`);

  await page.getByLabel("Reviewer access code").fill(REVIEWER);
  await page.getByRole("button", { name: "OK" }).click();
  const run = page.locator(".run").filter({ hasText: "Waiting to release" }).first();
  await run.waitFor({ timeout: 15000 });
  check(true, `${name}: a reviewer sees a run waiting to release`);
  check((await run.getByText("Held back, whatever you decide").count()) === 2, `${name}: held cases are shown, with a reason, for each ward`);
  check((await run.getByText("the Challenger held it").count()) === 2, `${name}: the reason a case was held is shown`);

  // read a staged file
  await run.locator("details summary", { hasText: "ward-brief.md" }).first().click();
  await run.locator("pre.file").first().waitFor({ timeout: 10000 });
  check((await run.locator("pre.file").first().innerText()).includes("missing from the graph"), `${name}: a staged file can be read before releasing it`);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}-review.png`, fullPage: true });

  // nothing can be decided without a ward and a reason
  const release = run.getByRole("button", { name: /^Release/ });
  check(await release.isDisabled(), `${name}: releasing is disabled until a ward and a reason are given`);
  await run.getByLabel("Release ward K/W").check();
  check(await release.isDisabled(), `${name}: still disabled without a reason`);
  await run.getByLabel(/Reason/).fill("K/W checked against its sources; H/W needs rework");
  check(await release.isEnabled(), `${name}: enabled once a ward and a reason are given`);
  check((await release.innerText()) === "Release 1 of 2", `${name}: the button says what it will do`);
  await release.click();
  await page.locator(".run").filter({ hasText: "Finished" }).first().waitFor({ timeout: 20000 });
  check(true, `${name}: the run finishes after the decision`);
  await page.locator(".run details.history summary").first().click();
  const history = await page.locator(".run details.history").first().innerText();
  check(history.includes("K/W") && history.includes("H/W needs rework"), `${name}: the decision is recorded with its reason`);

  if (PUBLIC_DIR) {
    const published = fs.readdirSync(`${PUBLIC_DIR}/published`);
    check(published.includes("k-w"), `${name}: the approved ward was published`);
    check(!published.includes("h-w"), `${name}: the ward that was not released was not published`);
    check(!fs.readdirSync(`${PUBLIC_DIR}/published/k-w`, { recursive: true }).some((f) => String(f).includes("held")), `${name}: the held case was not published`);
  }
  check(errors.length === 0, `${name}: no page errors ${errors.join("; ")}`);
  await context.close();
}
await browser.close();
console.log(failures.length ? `\n${failures.length} failed` : "\nall passed");
process.exit(failures.length ? 1 : 0);
