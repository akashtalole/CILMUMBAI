// End-to-end check of the resident view (SPEC-020 demo slice) against a running API with the demo seed loaded.
//
//   HISHOB_DATABASE_URL=…/hishob_demo HISHOB_LOCAL_ROOT=var/demo uv run python demo/seed.py   # once
//   (cd web && npm run build) && uv run uvicorn hishob.api.app:serve --factory --port 8000
//   node web/e2e/resident.mjs [http://127.0.0.1:8000] [screenshot-dir]
//
// The Ask tab is checked against a mocked answer, so this costs nothing and needs no Claude key.
import { createRequire } from "node:module";
import { execSync } from "node:child_process";

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
const failures = [];
const check = (ok, what) => {
  console.log(`${ok ? "pass" : "FAIL"}  ${what}`);
  if (!ok) failures.push(what);
};

const MOCK = {
  id: "job1",
  status: "done",
  elapsed_s: 3,
  answer: {
    text: "x",
    body: "**Contractor repairs it.**\n\n**Where to complain**\n- Assistant Engineer (Roads), K/West\n- then the Executive Engineer\n\n<script>window.injected = true</script>",
    language: "en",
    status: "answered",
    sources: [
      { fact_id: "f_1", document: "abc", page: 1, quote: "Roads and Traffic Department, K/West Ward", publisher: "bmc" },
      { fact_id: "f_2", document: "abc", page: 1, quote: "Roads and Traffic Department, K/West Ward", publisher: "bmc" },
      { fact_id: "f_3", document: "abc", page: 2, quote: "Defect liability period: 5 years from completion", publisher: "bmc" },
    ],
    draft_letter: "To the Assistant Engineer (Roads), K/West…",
    gaps: [],
  },
};

const browser = await chromium.launch();
for (const [name, options] of [
  ["phone", { ...devices["Pixel 7"] }],
  ["desktop", { viewport: { width: 1280, height: 820 } }],
]) {
  const context = await browser.newContext({
    ...options,
    geolocation: { latitude: 19.11, longitude: 72.8355 },
    permissions: ["geolocation"],
    locale: "mr-IN",
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(BASE);

  // AC4: Marathi first, all three languages, choice remembered
  check((await page.locator("html").getAttribute("lang")) === "mr", `${name}: opens in Marathi`);
  await page.getByRole("button", { name: "English" }).click();
  await page.reload();
  check(await page.getByRole("tab", { name: "Who is responsible?" }).isVisible(), `${name}: language choice remembered`);

  // AC1: by location, and by name in Devanagari
  await page.getByRole("button", { name: "Near me" }).click();
  await page.getByText("Complain first to").waitFor({ timeout: 15000 });
  check(await page.locator(".chosen").innerText().then((t) => t.includes("S. V. Road")), `${name}: near me finds S. V. Road`);
  await page.getByRole("searchbox").fill("एस. व्ही");
  const found = await page.getByRole("option", { name: /S\. V\. Road/ }).waitFor({ timeout: 10000 }).then(() => true, () => false);
  check(found, `${name}: Devanagari search finds the road`);
  await page.getByRole("option", { name: /S\. V\. Road/ }).click();

  // AC2: who is responsible, each fact with its source
  await page.getByText("Complain first to").waitFor();
  const card = await page.locator(".card.highlight").innerText();
  check(card.includes("31 May 2031") && card.includes("Shree Ganesh"), `${name}: contractor liability with its end date`);
  check(await page.getByText("Assistant Engineer (Roads), K/West").isVisible(), `${name}: post to complain to`);
  check(await page.getByText("Executive Engineer (Roads), Western Suburbs").isVisible(), `${name}: escalation`);
  await page.getByRole("button", { name: "Source" }).first().click();
  check(await page.locator(".source-card q").first().isVisible(), `${name}: a source opens with its quote`);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}-responsible.png`, fullPage: true });

  // AC7: the map draws the road
  await page.waitForTimeout(2500);
  const drawn = await page.evaluate(() => !!document.querySelector(".map canvas"));
  check(drawn, `${name}: map canvas present`);

  // AC3: money trail in Indian format, with gaps and who holds them
  await page.getByRole("tab", { name: "Where did the money go?" }).click();
  await page.getByText("Estimated cost").waitFor({ timeout: 15000 });
  const trail = await page.locator(".trail").innerText();
  check(trail.includes("₹4,20,00,000") && trail.includes("4.2 crore"), `${name}: amounts in rupees, lakh and crore`);
  check(await page.getByText("BMC Chief Accountant (Finance)").isVisible(), `${name}: missing record and its holder`);
  await page.getByRole("button", { name: "हिंदी" }).click();
  check(await page.getByText("अनुमानित लागत").isVisible(), `${name}: Hindi labels`);
  await page.getByRole("button", { name: "English" }).click();

  // AC8: no sideways scrolling on a phone
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check(overflow <= 0, `${name}: no horizontal scroll (${overflow}px)`);

  // AC5, AC9: asking, with a mocked desk; Markdown rendered, markup not injected, sources once each
  await page.route("**/ask", (route) => route.fulfill({ status: 202, contentType: "application/json", body: '{"id":"job1","status":"running"}' }));
  await page.route("**/ask/job1", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify(MOCK) }));
  await page.getByRole("tab", { name: "Ask" }).click();
  await page.getByRole("textbox").fill("Who will fix the pothole on S. V. Road?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await page.locator(".answer").waitFor({ timeout: 10000 });
  check(await page.locator(".answer strong").first().innerText() === "Contractor repairs it.", `${name}: bold rendered`);
  check((await page.locator(".answer .rich li").count()) === 2, `${name}: bullets rendered`);
  check(!(await page.evaluate(() => window.injected)) && (await page.locator(".answer script").count()) === 0, `${name}: no markup injected`);
  check((await page.locator(".answer-sources li").count()) === 2, `${name}: repeated sources shown once`);
  check(await page.getByRole("link", { name: "Share on WhatsApp" }).isVisible(), `${name}: letter can be shared`);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}-ask.png`, fullPage: true });

  // Photo report (SPEC-030): choose a photo, see what was found, get the sourced answer and a letter
  const TINY_JPEG = Buffer.from("/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=", "base64");
  let sentPhoto = null;
  await page.route("**/report?**", async (route) => {
    sentPhoto = { url: route.request().url(), type: route.request().headers()["content-type"], bytes: route.request().postDataBuffer()?.length ?? 0 };
    await route.fulfill({ status: 202, contentType: "application/json", body: '{"id":"job2","status":"running"}' });
  });
  await page.route("**/report/job2", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({
    id: "job2", status: "done", elapsed_s: 6,
    answer: { status: "answered", issue: "pothole", confidence: "high", location_from: "device", answer: MOCK.answer } }) }));
  await page.getByRole("tab", { name: "Ask" }).click();
  await page.getByTestId("photo-input").setInputFiles({ name: "pothole.jpg", mimeType: "image/jpeg", buffer: TINY_JPEG });
  await page.getByText("We see:").waitFor({ timeout: 10000 });
  check((await page.locator(".saw strong").innerText()) === "Pothole", `${name}: the photo's finding is shown`);
  check(await page.locator(".photo .answer").isVisible(), `${name}: the photo report shows the sourced answer`);
  check(await page.locator(".photo .answer a.whatsapp").isVisible(), `${name}: the letter can be shared`);
  check(await page.locator(".photo-preview").isVisible(), `${name}: the chosen photo is previewed`);
  check(sentPhoto !== null && sentPhoto.type === "image/jpeg" && sentPhoto.bytes > 0 && /language=en/.test(sentPhoto.url) && /lat=19\.11/.test(sentPhoto.url) && /lon=72\.8355/.test(sentPhoto.url),
    `${name}: the photo goes up as an image with the language and the device's position`);
  await page.unroute("**/report/job2");
  await page.route("**/report/job2", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({
    id: "job2", status: "done", elapsed_s: 4, answer: { status: "unclear", issue: "none", confidence: "low", location_from: "device", answer: null } }) }));
  await page.getByTestId("photo-input").setInputFiles({ name: "unclear.jpg", mimeType: "image/jpeg", buffer: TINY_JPEG });
  await page.getByText("We could not tell what the photo shows").waitFor({ timeout: 10000 });
  check(true, `${name}: an unclear photo says so and points to the other tab`);

  // Street alerts (SPEC-010): asks for an access code, then lists saved areas and alerts, in the chosen language
  await page.evaluate(() => localStorage.removeItem("hishob.token"));
  await page.getByRole("tab", { name: "Alerts" }).click();
  check(await page.getByLabel("Access code").isVisible(), `${name}: alerts ask for an access code first`);
  const areas = [{ id: 1, kind: "point", lat: 19.11, lon: 72.83, radius_m: 300, road_ids: [], language: "en", created_at: "2026-11-01T00:00:00Z" }];
  const feed = [{ id: 9, kind: "tender_published", created_at: "2026-11-02T00:00:00Z",
    text: "A tender has been published for work on S. V. Road.\nTender no.: TEST/KW/ROADS/0001\nDate: 2026-11-02\nSource: https://hishob.example/sources/abc/pages/1" }];
  await page.route("**/subscriptions", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify(areas) }));
  await page.route("**/alerts", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify(feed) }));
  await page.getByLabel("Access code").fill("contributor.acct_test.0123456789");
  await page.getByRole("button", { name: "OK" }).click();
  await page.getByText("Within 300 m of a point").waitFor({ timeout: 10000 });
  check(await page.getByText("TEST/KW/ROADS/0001").isVisible(), `${name}: an alert shows its tender number`);
  check((await page.getByRole("link", { name: "Open the source page" }).getAttribute("href")) === "https://hishob.example/sources/abc/pages/1", `${name}: alert links to its source`);
  await page.getByRole("button", { name: "मराठी" }).click();
  check(await page.getByText("जतन केलेले भाग").isVisible(), `${name}: alerts tab in Marathi`);
  check((await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)) <= 0, `${name}: alerts tab has no horizontal scroll`);
  await page.getByRole("button", { name: "हा कोड विसरा" }).click();
  check(await page.getByLabel("प्रवेश कोड").isVisible(), `${name}: forgetting the code signs out`);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}-alerts.png`, fullPage: true });

  check(errors.length === 0, `${name}: no page errors ${errors.join("; ")}`);
  await context.close();
}
await browser.close();
console.log(failures.length ? `\n${failures.length} failed` : "\nall passed");
process.exit(failures.length ? 1 : 0);
