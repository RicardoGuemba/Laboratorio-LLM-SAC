import { describe, it, expect } from "vitest";
import {
  inferAvatarMood,
  inferClienteMood,
  inferSacMood,
  avatarAriaLabel,
} from "./avatarMood";

describe("avatarMood", () => {
  it("returns speaking when cliente is active", () => {
    expect(inferClienteMood("qualquer texto", true)).toBe("speaking");
  });

  it("detects frustrated cliente mood from text", () => {
    expect(inferClienteMood("Isso é um absurdo, não aguento mais!", false)).toBe("frustrated");
  });

  it("detects anxious cliente mood from text", () => {
    expect(inferClienteMood("Desenvolvi coceira e vermelhidão na pele", false)).toBe("anxious");
  });

  it("detects empathetic SAC mood from text", () => {
    expect(inferSacMood("Pedimos sinceras desculpas e lamentamos o transtorno", false)).toBe(
      "empathetic",
    );
  });

  it("returns speaking for SAC when streaming", () => {
    expect(inferSacMood("", true)).toBe("speaking");
  });

  it("inferAvatarMood routes by role", () => {
    expect(inferAvatarMood("cliente", "estou preocupado com alergia", false)).toBe("anxious");
    expect(inferAvatarMood("sac", "entendemos sua situação", false)).toBe("empathetic");
  });

  it("builds accessible aria labels", () => {
    expect(avatarAriaLabel("cliente", "frustrated")).toContain("Cliente TRUEPALEO");
    expect(avatarAriaLabel("sac", "empathetic")).toContain("empático");
  });
});
