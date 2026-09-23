import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "./page";

const push = vi.fn();
let search = new URLSearchParams();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }), useSearchParams: () => search }));
// eslint-disable-next-line @next/next/no-img-element
vi.mock("next/image", () => ({ default: (props: Record<string, unknown>) => <img alt="" {...props} /> }));
const mutateAsync = vi.fn();
vi.mock("@/api/auth", () => ({ useLogin: () => ({ mutateAsync }) }));
const toast = { info: vi.fn(), success: vi.fn(), error: vi.fn() };
vi.mock("sonner", () => ({ toast: { info: (...a: unknown[]) => toast.info(...a), success: (...a: unknown[]) => toast.success(...a), error: (...a: unknown[]) => toast.error(...a) } }));

function signIn(username = "admin", password = "Passw0rd-Test!") {
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: username } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

beforeEach(() => {
  push.mockClear();
  mutateAsync.mockReset();
  Object.values(toast).forEach((fn) => fn.mockClear());
  search = new URLSearchParams();
});

describe("LoginPage", () => {
  it("signs in and goes home", async () => {
    mutateAsync.mockResolvedValue({});
    render(<LoginPage />);
    signIn();
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ username: "admin", password: "Passw0rd-Test!", remember: false }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
  });

  it("honours a same-origin redirect and refuses an external one", async () => {
    mutateAsync.mockResolvedValue({});
    search = new URLSearchParams({ redirect: "/zones?page=2" });
    render(<LoginPage />);
    signIn();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/zones?page=2"));

    push.mockClear();
    search = new URLSearchParams({ redirect: "//evil.example" });
    render(<LoginPage />);
    fireEvent.change(screen.getAllByLabelText("Username")[1], { target: { value: "admin" } });
    fireEvent.change(screen.getAllByLabelText("Password")[1], { target: { value: "x" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Sign in" })[1]);
    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
  });

  it("shows the API's message on a bad password and stays on the page", async () => {
    mutateAsync.mockRejectedValue({ status: 400, message: "Incorrect username or password" });
    render(<LoginPage />);
    signIn("admin", "nope");
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Incorrect username or password"));
    expect(push).not.toHaveBeenCalled();
  });

  it("does not submit empty fields", async () => {
    render(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Username is required")).toBeInTheDocument();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("leaves Keep me signed in unticked by default and sends remember: true once ticked", async () => {
    mutateAsync.mockResolvedValue({});
    render(<LoginPage />);
    const box = screen.getByLabelText("Keep me signed in") as HTMLInputElement;
    expect(box.checked).toBe(false);
    fireEvent.click(box);
    signIn();
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith(expect.objectContaining({ remember: true })));
  });

  it("shows the brand, the slogan and no dead sign-up link", () => {
    render(<LoginPage />);
    expect(screen.getByText("tilthwave")).toBeInTheDocument();
    expect(screen.getByText("The field\u2019s true voice")).toBeInTheDocument();
    expect(screen.queryByText(/farm watch/)).toBeNull();
    expect(screen.queryByRole("link", { name: /create an account/i })).toBeNull();
  });

  it("tells an expired session apart from a fresh password", () => {
    search = new URLSearchParams({ expired: "1" });
    render(<LoginPage />);
    expect(toast.info).toHaveBeenCalledWith("Session expired. Please sign in again.");
  });
});
