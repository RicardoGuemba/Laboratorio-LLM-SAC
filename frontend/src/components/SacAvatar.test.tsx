import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SacAvatar } from "./SacAvatar";

describe("SacAvatar", () => {
  it("renders cliente avatar with role-specific label", () => {
    render(<SacAvatar role="cliente" mood="frustrated" />);
    expect(screen.getByRole("img", { name: /Cliente TRUEPALEO.*frustrado/i })).toBeInTheDocument();
  });

  it("renders SAC avatar with empathetic label", () => {
    render(<SacAvatar role="sac" mood="empathetic" />);
    expect(screen.getByRole("img", { name: /Atendente SAC TRUEPALEO.*empático/i })).toBeInTheDocument();
  });

  it("shows pulse indicator when speaking", () => {
    const { container } = render(<SacAvatar role="cliente" mood="speaking" />);
    expect(container.querySelector(".sac-avatar__pulse")).toBeTruthy();
    expect(container.querySelector(".sac-avatar--speaking")).toBeTruthy();
  });

  it("applies custom size", () => {
    const { container } = render(<SacAvatar role="sac" mood="idle" size={96} />);
    const wrapper = container.querySelector(".sac-avatar") as HTMLElement;
    expect(wrapper.style.width).toBe("96px");
    expect(wrapper.style.height).toBe("96px");
  });

  it("includes SVG portrait for each role", () => {
    const { rerender, container } = render(<SacAvatar role="cliente" mood="idle" />);
    expect(container.querySelector(".sac-avatar--cliente svg")).toBeTruthy();

    rerender(<SacAvatar role="sac" mood="idle" />);
    expect(container.querySelector(".sac-avatar--sac svg")).toBeTruthy();
  });
});
