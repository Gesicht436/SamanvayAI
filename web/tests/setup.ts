import "@testing-library/jest-dom";
import { vi } from "vitest";

if (!global.fetch) {
  global.fetch = vi.fn().mockImplementation(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve([]),
      text: () => Promise.resolve(""),
    })
  ) as unknown as typeof fetch;
}
