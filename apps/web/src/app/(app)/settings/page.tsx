"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";


import { useChangePassword, useProfile, useUpdateProfile } from "@/api/account";
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
import type { User } from "@/types/user";

const profileSchema = z.object({
  email: z.email("Invalid email"),
  phone_number: z.string().min(1, "Phone number is required").max(50),
  first_name: z.string().min(1, "First name is required").max(50),
  last_name: z.string().min(1, "Last name is required").max(50),
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
  };
}

function ProfileCard({ user }: { user: User }) {
  const update = useUpdateProfile();
  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: toProfileValues(user),
    values: toProfileValues(user), // re-syncs if the record changes underneath
  });

  async function onSubmit(values: ProfileValues) {
    try {
      const saved = await update.mutateAsync(values);
      form.reset(toProfileValues(saved));
      toast.success("Profile updated");
    } catch (err) {
      toast.error(toApiError(err, "Could not update the profile").message);
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

export default function SettingsPage() {
  const profile = useProfile();

  return (
    <div className="grid max-w-3xl gap-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Your account, your details, your password.</p>
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
        </>
      )}
    </div>
  );
}
