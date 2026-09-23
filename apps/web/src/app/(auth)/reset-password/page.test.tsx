import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ResetPasswordPage from "./page";

const replace = vi.fn();
let search = new URLSearchParams();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }), useSearchParams: () => search }));
// eslint-disable-next-line @next/next/no-img-element
vi.mock("next/image", () => ({ default: (props: Record<string, unknown>) => <img alt="" {...props} /> }));
const mutateAsync = vi.fn();
vi.mock("@/api/auth", () => ({ useResetPassword: () => ({ mutateAsync, isPending: false }) }));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

beforeEach(() => {
  replace.mockClear();
  mutateAsync.mockReset();
  window.history.replaceState({}, "", "/reset-password?token=t0k3n");
  search = new URLSearchParams({ token: "t0k3n" });
});

describe("ResetPasswordPage", () => {
  it("reads the token once, scrubs it from the URL, and sends it with the new password", async () => {
    mutateAsync.mockResolvedValue(undefined);
    render(<ResetPasswordPage />);
    await waitFor(() => expect(window.location.search).toBe(""));
    expect(window.location.pathname).toBe("/reset-password");
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "Another-Passw0rd" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "Another-Passw0rd" } });
    fireEvent.click(screen.getByRole("button", { name: "Set new password" }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ token: "t0k3n", newPassword: "Another-Passw0rd" }));
    expect(replace).toHaveBeenCalledWith("/login?reset=1");
  });

  it("explains a link without a token instead of showing the form", () => {
    search = new URLSearchParams();
    render(<ResetPasswordPage />);
    expect(screen.getByText(/missing its token/)).toBeInTheDocument();
    expect(screen.queryByLabelText("New password")).toBeNull();
  });
});
