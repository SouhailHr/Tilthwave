import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "./dropdown-menu";

// Regression for the user menu taking the whole page to the error boundary the first time it
// opened: DropdownMenuLabel is base-ui's Menu.GroupLabel and must be inside a DropdownMenuGroup.
// This test pins that contract at the wrapper, so the mistake fails here, not in a browser.
function menu(children: React.ReactNode) {
  return (
    <DropdownMenu open>
      <DropdownMenuTrigger>open</DropdownMenuTrigger>
      <DropdownMenuContent>{children}</DropdownMenuContent>
    </DropdownMenu>
  );
}

describe("DropdownMenuLabel", () => {
  it("throws when rendered bare inside the content (what the user menu used to do)", () => {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(menu(<DropdownMenuLabel>who</DropdownMenuLabel>))).toThrow();
    quiet.mockRestore();
  });

  it("renders inside a DropdownMenuGroup", () => {
    render(
      menu(
        <DropdownMenuGroup>
          <DropdownMenuLabel>who</DropdownMenuLabel>
        </DropdownMenuGroup>,
      ),
    );
    expect(screen.getByText("who")).toBeInTheDocument();
  });
});
