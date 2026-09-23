import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SettingsPage from "./page";

const user = {
  id: 1, username: "pat", email: "pat@example.com", phone_number: "+1", first_name: "Pat", last_name: "P",
  role: "worker", is_active: true, farm_name: "Sunny Farms", is_superuser: false,
};
const sessions = [
  { id: 10, channel: "cookie", user_agent: "Mozilla/5.0 (X11; Linux) Chrome/120", client_ip: "10.0.0.1", created_date: "2026-09-23T10:00:00+00:00", last_seen: "2026-09-23T10:05:00+00:00", expires_at: "2026-09-23T22:00:00+00:00", current: true },
  { id: 11, channel: "header", user_agent: "curl/8", client_ip: "10.0.0.2", created_date: "2026-09-23T09:00:00+00:00", last_seen: "2026-09-23T09:30:00+00:00", expires_at: "2026-09-23T21:00:00+00:00", current: false },
];
const updateProfile = vi.fn();
const revoke = vi.fn();
const revokeOthers = vi.fn();
vi.mock("@/api/account", () => ({
  useProfile: () => ({ data: user, isPending: false, isError: false, error: null }),
  useUpdateProfile: () => ({ mutateAsync: updateProfile, isPending: false }),
  useChangePassword: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useSessions: () => ({ data: sessions, isPending: false, isError: false }),
  useRevokeSession: () => ({ mutateAsync: revoke, isPending: false }),
  useRevokeOtherSessions: () => ({ mutateAsync: revokeOthers, isPending: false }),
}));
const toast = { success: vi.fn(), error: vi.fn() };
vi.mock("sonner", () => ({ toast: { success: (...a: unknown[]) => toast.success(...a), error: (...a: unknown[]) => toast.error(...a) } }));

beforeEach(() => {
  updateProfile.mockReset();
  revoke.mockReset();
  revokeOthers.mockReset();
  toast.success.mockClear();
  toast.error.mockClear();
});

describe("SettingsPage", () => {
  it("asks for the current password only when the email changes, and sends it along", async () => {
    updateProfile.mockResolvedValue({ ...user, email: "pat2@example.com" });
    render(<SettingsPage />);
    // The password card has its own "Current password"; the profile card's appears only on an email change.
    expect(screen.queryByText(/Required to change the email/)).toBeNull();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "pat2@example.com" } });
    const hint = await screen.findByText(/Required to change the email/);
    const password = hint.closest("[data-slot=form-item]")!.querySelector("input")!;
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Enter your password to change the email")).toBeInTheDocument();
    expect(updateProfile).not.toHaveBeenCalled();
    fireEvent.change(password, { target: { value: "Passw0rd-Test!" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() =>
      expect(updateProfile).toHaveBeenCalledWith(expect.objectContaining({ email: "pat2@example.com", current_password: "Passw0rd-Test!" })),
    );
  });

  it("lists the sessions, flags this device, and signs the others out", async () => {
    revokeOthers.mockResolvedValue(1);
    revoke.mockResolvedValue(undefined);
    render(<SettingsPage />);
    expect(screen.getByText("Chrome on Linux")).toBeInTheDocument();
    expect(screen.getByText("This device")).toBeInTheDocument();
    expect(screen.getByText("API client")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign out device" }));
    await waitFor(() => expect(revoke).toHaveBeenCalledWith(11));
    fireEvent.click(screen.getByRole("button", { name: "Sign out everywhere else" }));
    await waitFor(() => expect(revokeOthers).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalledWith("1 other device signed out");
  });
});
