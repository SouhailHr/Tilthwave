import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ForgotPasswordPage from "./page";

// eslint-disable-next-line @next/next/no-img-element
vi.mock("next/image", () => ({ default: (props: Record<string, unknown>) => <img alt="" {...props} /> }));
const mutateAsync = vi.fn();
vi.mock("@/api/auth", () => ({ useForgotPassword: () => ({ mutateAsync, isPending: false }) }));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

beforeEach(() => mutateAsync.mockReset());

describe("ForgotPasswordPage", () => {
  it("sends the identifier and answers the same whether or not the account exists", async () => {
    mutateAsync.mockResolvedValue(undefined);
    render(<ForgotPasswordPage />);
    fireEvent.change(screen.getByLabelText("Username or email"), { target: { value: "  pat@example.com " } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith("pat@example.com"));
    expect(await screen.findByText(/If an account exists for/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try another username or email" }));
    expect(screen.getByLabelText("Username or email")).toBeInTheDocument();
  });
});
