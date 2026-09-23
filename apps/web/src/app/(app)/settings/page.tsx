"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import {
  useChangePassword,
  useProfile,
  useRevokeOtherSessions,
  useRevokeSession,
  useSessions,
  useUpdateProfile,
} from "@/api/account";
import { toApiError } from "@/api/errors";
import { PasswordInput } from "@/components/password-input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { PASSWORDS_MUST_MATCH, passwordSchema, passwordsMatch } from "@/lib/password-schema";
import type { UserSession } from "@/types/account";
import type { User } from "@/types/user";
import { formatDateTime, formatRelative } from "@/utils/dates";

const profileSchema = z.object({
  email: z.email("Invalid email"),
  phone_number: z.string().min(1, "Phone number is required").max(50),
  first_name: z.string().min(1, "First name is required").max(50),
  last_name: z.string().min(1, "Last name is required").max(50),
  current_password: z.string().max(72),
});
type ProfileValues = z.infer<typeof profileSchema>;

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: passwordSchema,
    confirm_password: z.string(),
  })
  .refine(passwordsMatch, PASSWORDS_MUST_MATCH)
  .refine((v) => v.new_password !== v.current_password, {
    message: "Choose a password you are not already using",
    path: ["new_password"],
  });
type PasswordValues = z.infer<typeof changePasswordSchema>;

function toProfileValues(user: User): ProfileValues {
  return {
    email: user.email,
    phone_number: user.phone_number,
    first_name: user.first_name,
    last_name: user.last_name,
    current_password: "",
  };
}

function ProfileCard({ user }: { user: User }) {
  const update = useUpdateProfile();
  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: toProfileValues(user),
    values: toProfileValues(user), // re-syncs if the record changes underneath
  });

  const emailChanged = useWatch({ control: form.control, name: "email" }) !== user.email;

  async function onSubmit(values: ProfileValues) {
    const { current_password, ...profile } = values;
    if (emailChanged && !current_password) {
      form.setError("current_password", { message: "Enter your password to change the email" });
      return;
    }
    try {
      const saved = await update.mutateAsync(
        emailChanged ? { ...profile, current_password } : profile,
      );
      form.reset(toProfileValues(saved));
      toast.success("Profile updated");
    } catch (err) {
      const apiError = toApiError(err, "Could not update the profile");
      if (apiError.status === 422 && /password/i.test(apiError.message)) {
        form.setError("current_password", { message: apiError.message });
      } else {
        toast.error(apiError.message);
      }
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile</CardTitle>
        <CardDescription>How the team reaches you.</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="first_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>First name</FormLabel>
                    <FormControl>
                      <Input autoComplete="given-name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="last_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Last name</FormLabel>
                    <FormControl>
                      <Input autoComplete="family-name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input type="email" autoComplete="email" {...field} />
                  </FormControl>
                  <FormDescription>Password reset links are sent here.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            {emailChanged && (
              <FormField
                control={form.control}
                name="current_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Current password</FormLabel>
                    <FormControl>
                      <PasswordInput autoComplete="current-password" {...field} />
                    </FormControl>
                    <FormDescription>Required to change the email.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
            <FormField
              control={form.control}
              name="phone_number"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Phone number</FormLabel>
                  <FormControl>
                    <Input type="tel" autoComplete="tel" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex justify-end">
              <Button type="submit" disabled={update.isPending || !form.formState.isDirty}>
                {update.isPending ? "Saving…" : "Save changes"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

function PasswordCard() {
  const change = useChangePassword();
  const form = useForm<PasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  async function onSubmit(values: PasswordValues) {
    try {
      await change.mutateAsync({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      form.reset();
      toast.success("Password changed. Your other devices have been signed out.");
    } catch (err) {
      const apiError = toApiError(err, "Could not change the password");
      if (apiError.status === 422 && /current password/i.test(apiError.message)) {
        form.setError("current_password", { message: apiError.message });
      } else {
        toast.error(apiError.message);
      }
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Password</CardTitle>
        <CardDescription>
          Changing it signs you out everywhere else. This device stays signed in.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4">
            <FormField
              control={form.control}
              name="current_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Current password</FormLabel>
                  <FormControl>
                    <PasswordInput autoComplete="current-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="new_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>New password</FormLabel>
                    <FormControl>
                      <PasswordInput autoComplete="new-password" {...field} />
                    </FormControl>
                    <FormDescription>At least 8 characters.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm new password</FormLabel>
                    <FormControl>
                      <PasswordInput autoComplete="new-password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <div className="flex justify-end">
              <Button type="submit" disabled={change.isPending}>
                {change.isPending ? "Changing…" : "Change password"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

function AccountCard({ user }: { user: User }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Account</CardTitle>
        <CardDescription>Set by an administrator. Ask one to change these.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm sm:grid-cols-3">
        <div className="grid gap-0.5">
          <span className="text-xs uppercase tracking-wide text-muted-foreground">Username</span>
          <span className="font-medium">{user.username}</span>
        </div>
        <div className="grid gap-0.5">
          <span className="text-xs uppercase tracking-wide text-muted-foreground">Role</span>
          <span>
            <Badge variant="secondary" className="capitalize">{user.role}</Badge>
          </span>
        </div>
        <div className="grid gap-0.5">
          <span className="text-xs uppercase tracking-wide text-muted-foreground">Farm</span>
          <span className="font-medium">{user.farm_name ?? "—"}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function describeSession(session: UserSession): string {
  const ua = session.user_agent ?? "";
  const browser =
    /Edg\//.test(ua) ? "Edge"
    : /OPR\//.test(ua) ? "Opera"
    : /Firefox\//.test(ua) ? "Firefox"
    : /Chrome\//.test(ua) ? "Chrome"
    : /Safari\//.test(ua) ? "Safari"
    : null;
  const os =
    /Windows/.test(ua) ? "Windows"
    : /Android/.test(ua) ? "Android"
    : /iPhone|iPad/.test(ua) ? "iOS"
    : /Mac OS/.test(ua) ? "macOS"
    : /Linux/.test(ua) ? "Linux"
    : null;
  if (session.channel === "header") return browser ? `API client (${browser})` : "API client";
  if (browser && os) return `${browser} on ${os}`;
  return browser ?? os ?? "Browser";
}

function SessionsCard() {
  const sessions = useSessions();
  const revoke = useRevokeSession();
  const revokeOthers = useRevokeOtherSessions();
  const others = sessions.data?.filter((s) => !s.current).length ?? 0;

  async function endSession(session: UserSession) {
    try {
      await revoke.mutateAsync(session.id);
      toast.success(session.current ? "Signed out" : "Device signed out");
    } catch (err) {
      toast.error(toApiError(err, "Could not sign that device out").message);
    }
  }

  async function endOthers() {
    try {
      const revoked = await revokeOthers.mutateAsync();
      toast.success(revoked === 1 ? "1 other device signed out" : `${revoked} other devices signed out`);
    } catch (err) {
      toast.error(toApiError(err, "Could not sign the other devices out").message);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sessions</CardTitle>
        <CardDescription>
          Where you are signed in. A session ends after an hour without activity, twelve hours after
          signing in, or when you end it here. Ending one signs that device out at its next request.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {sessions.isPending ? (
          <Skeleton className="h-16 w-full" />
        ) : sessions.isError ? (
          <p className="text-sm text-muted-foreground">{sessions.error.message}</p>
        ) : (
          <ul className="grid gap-2">
            {sessions.data.map((session) => (
              <li
                key={session.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border/60 px-3 py-2 text-sm"
              >
                <div className="grid gap-0.5">
                  <span className="flex items-center gap-2 font-medium">
                    {describeSession(session)}
                    {session.current && <Badge variant="secondary">This device</Badge>}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {session.client_ip ? `${session.client_ip} · ` : ""}
                    signed in {formatDateTime(session.created_date)} · last seen{" "}
                    {formatRelative(session.last_seen)}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={revoke.isPending}
                  onClick={() => endSession(session)}
                >
                  {session.current ? "Sign out" : "Sign out device"}
                </Button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex justify-end">
          <Button variant="destructive" disabled={others === 0 || revokeOthers.isPending} onClick={endOthers}>
            {revokeOthers.isPending ? "Signing out…" : "Sign out everywhere else"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const profile = useProfile();

  return (
    <div className="grid max-w-3xl gap-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Your account, your details, your password, your sessions.</p>
      </div>
      {profile.isPending ? (
        <div className="grid gap-6">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-80 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : profile.isError || !profile.data ? (
        <div className="rounded-md border border-harvest/40 bg-harvest/10 px-4 py-3 text-sm text-loam">
          <span className="font-medium">Could not load your account.</span>{" "}
          {profile.error?.message}
        </div>
      ) : (
        <>
          <AccountCard user={profile.data} />
          <ProfileCard user={profile.data} />
          <PasswordCard />
          <SessionsCard />
        </>
      )}
    </div>
  );
}
