import { readFileSync } from "node:fs";
import { expect, it } from "vitest";

const styles = readFileSync("src/styles.css", "utf8");

it.each(["warning", "ready", "danger", "neutral"])("preserves the %s badge color inside delivery facts", (tone) => {
  const style = document.createElement("style");
  style.textContent = styles;
  const container = document.createElement("div");
  container.innerHTML = `
    <div class="delivery-facts"><div>
      <span>Status</span><span class="status-pill status-${tone}">Status value</span>
    </div></div>
    <details class="delivery-activity-details"><summary>
      View activity <span class="status-pill status-${tone}">Live</span>
    </summary></details>`;
  document.head.appendChild(style);
  document.body.appendChild(container);
  try {
    const badge = container.querySelector(".delivery-facts .status-pill")!;
    const reference = container.querySelector("summary .status-pill")!;
    const label = container.querySelector(".delivery-facts span:first-child")!;
    expect(getComputedStyle(reference).color).not.toBe("");
    expect(getComputedStyle(badge).color).toBe(getComputedStyle(reference).color);
    expect(getComputedStyle(badge).fontSize).toBe(getComputedStyle(reference).fontSize);
    expect(getComputedStyle(label).fontSize).toBe("11px");
  } finally {
    container.remove();
    style.remove();
  }
});
