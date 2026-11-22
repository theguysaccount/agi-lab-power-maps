// The only script on the site: it loads the end-to-end self-test when the page is opened with ?selftest=1.
if (new URLSearchParams(location.search).has("selftest")) import("./selftest.js").then((m) => m.run());
