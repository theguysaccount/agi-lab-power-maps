// End-to-end check, run by scripts/e2e.sh on the home page with ?selftest=1. Verifies that every lab page repeats the
// essays' own words (from data/essays.json), carries its sources and a "last verified" box.
const strip = (s) => String(s).replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
export async function run() {
  const log = [];
  try {
    const content = await (await fetch(new URL("../data/essays.json", import.meta.url))).json();
    const cards = document.querySelectorAll(".cards .card");
    if (cards.length !== content.labs.length || cards.length !== 6) throw new Error(`home shows ${cards.length} labs`);
    log.push(`home lists all ${cards.length} labs`);
    for (const lab of content.labs) {
      const html = await (await fetch(new URL(`../labs/${lab.slug}/`, import.meta.url))).text();
      const doc = new DOMParser().parseFromString(html, "text/html");
      const text = doc.body.textContent.replace(/\s+/g, " ");
      if (!text.includes(strip(lab.who))) throw new Error(`${lab.nm}: page does not repeat the essay's control statement`);
      for (const c of lab.chain) if (!text.includes(strip(c.d))) throw new Error(`${lab.nm}: chain step "${c.role}" missing or altered`);
      if (doc.querySelectorAll("ol.sources li").length < 1) throw new Error(`${lab.nm}: no sources`);
      if (!doc.querySelector(".verify")) throw new Error(`${lab.nm}: no "last verified" box`);
    }
    log.push("every lab page repeats the essays verbatim, with sources and a last-verified box");
    document.body.dataset.selftest = "pass";
  } catch (err) {
    log.push("FAIL: " + err.message);
    document.body.dataset.selftest = "fail: " + err.message;
  }
  const pre = document.createElement("pre");
  pre.id = "selftest";
  pre.textContent = log.join("\n");
  document.body.appendChild(pre);
}
