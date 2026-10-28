import assert from "node:assert/strict";
import { chromium } from "playwright";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1450, height: 1000 } });
page.setDefaultTimeout(20000);
const errors = [],
  reads = [],
  writes = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("dialog", async (dialog) => {
  console.error("Unexpected dialog:", dialog.message());
  await dialog.dismiss();
});
page.on("request", (request) => {
  if (!request.url().endsWith("/admin/rpc") || request.method() !== "POST")
    return;
  const args = request.postDataJSON()?.args;
  if (
    args?.[1]?.endsWith("NestedTableReadCmd") &&
    args[2].view === "continuous_example"
  )
    reads.push(args[2]);
  if (args?.[1]?.endsWith("DashboardFormCmd") && args[2].action === "save")
    writes.push(args[2]);
});
const control = (id) => page.locator('[data-frame="' + id + '"]:visible');
const name = () => control("customLayoutDetails_2_field_name");
const select = async (code) => {
  const row = page.locator(
    '[data-result-key="contract/entity?project=one&code=' + code + '"]:visible',
  );
  await row.waitFor();
  await row.click({ position: { x: 150, y: 25 } });
  await name().waitFor();
};
try {
  await page.goto(process.argv[2] + "/projects/one/dashboard/record_browser");
  await page.getByLabel("Login", { exact: true }).fill("admin");
  await page
    .getByLabel("Password", { exact: true })
    .fill("private-test-password");
  await control("signInSubmit").click();
  await select("A");
  await page.waitForFunction(
    (initial) =>
      document.querySelector('[data-frame="customLayoutDetails_2_field_name"]')
        ?.value === initial,
    process.argv[4],
  );
  const initialReads = reads.length;
  await name().fill("Draft A");
  await select("B");
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="customLayoutDetails_2_field_name"]')
        ?.value === "O'Reilly",
  );
  await select("A");
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="customLayoutDetails_2_field_name"]')
        ?.value === "Draft A",
  );
  await control("customLayoutDetails_2_cancel").click();
  assert.equal(await name().inputValue(), process.argv[4]);
  await name().fill("Saved from dashboard");
  await control("customLayoutDetails_2_field_amount").fill("37");
  await control("customLayoutDetails_2_save").click();
  await control("customLayoutDetails_1")
    .getByText("37", { exact: true })
    .waitFor();
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="customLayoutDetails_2_field_name"]')
        ?.value === "Saved from dashboard" &&
      document.querySelector('[data-frame="customLayoutDetails_2_save"]')
        ?.disabled,
  );
  assert.equal(
    reads.length,
    initialReads,
    "Save and selection preserve the existing item tree",
  );
  await page.screenshot({ path: process.argv[3] + "/saved.png" });
  let dropped = false;
  await page.route("**/admin/rpc", async (route) => {
    const args = route.request().postDataJSON()?.args;
    if (
      !dropped &&
      args?.[1]?.endsWith("DashboardFormCmd") &&
      args[2].action === "save"
    ) {
      dropped = true;
      await route.fetch();
      await route.abort("failed");
    } else await route.continue();
  });
  await name().fill("Saved after lost reply");
  await control("customLayoutDetails_2_save").click();
  await page.waitForFunction(() =>
    document
      .querySelector('[data-frame="customLayoutDetails_2_save"]')
      ?.textContent.includes("Check saved state"),
  );
  assert.equal(writes.length, 2, "No automatic retry of the lost response");
  await control("customLayoutDetails_2_save").click();
  await page.waitForFunction(
    () =>
      document.querySelector('[data-frame="customLayoutDetails_2_field_name"]')
        ?.value === "Saved after lost reply" &&
      document.querySelector('[data-frame="customLayoutDetails_2_save"]')
        ?.disabled,
  );
  await control("customLayoutDetails_0")
    .getByText("Saved after lost reply", { exact: true })
    .waitFor();
  assert.equal(writes.length, 2);
  assert.equal(reads.length, initialReads);
  await control("customLayoutDetails_3").click();
  await page
    .getByRole("dialog")
    .filter({ has: page.getByText("Edit record", { exact: true }) })
    .waitFor();
  await page.keyboard.press("Escape");
  assert.deepEqual(errors, []);
  console.log(
    "Record workspace: existing tree retained, selection drafts, Save, lost-response Check and full native editor pass",
  );
} catch (error) {
  console.error(error, errors);
  await page
    .screenshot({ path: process.argv[3] + "/failure.png", timeout: 4000 })
    .catch(() => {});
  throw error;
} finally {
  await browser.close();
}
