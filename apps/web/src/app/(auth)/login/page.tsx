"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import * as z from "zod";

import { useLogin } from "@/api/auth";
import { toApiError } from "@/api/errors";
import { AuthCard, AuthCardHeader, AuthPage } from "@/components/auth-page";
import { PasswordInput } from "@/components/password-input";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { safeRedirect } from "@/utils/safeRedirect";

const loginSchema = z.object({
  username: z.string().min(1, "Username is required").max(256),
  password: z.string().min(1, "Password is required").max(256),
  remember: z.boolean(),
});

type LoginValues = z.infer<typeof loginSchema>;

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [submitting, setSubmitting] = useState(false);
  const loginMutation = useLogin();

  useEffect(() => {
    if (searchParams.get("expired") === "1") {
      toast.info("Session expired. Please sign in again.");
    }
    if (searchParams.get("reset") === "1") {
      toast.success("Password updated. Sign in with your new password.");
    }
  }, [searchParams]);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    // Unticked by default: a shared farm-office computer should not keep a session unless asked.
    defaultValues: { username: "", password: "", remember: false },
  });

  async function onSubmit(values: LoginValues) {
    setSubmitting(true);
    try {
      await loginMutation.mutateAsync(values);
      router.push(safeRedirect(searchParams.get("redirect")));
    } catch (err) {
      const apiError = toApiError(err, "Invalid credentials");
      toast.error(apiError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4" noValidate>
        <FormField
          control={form.control}
          name="username"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input autoComplete="username" placeholder="your username" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <PasswordInput autoComplete="current-password" placeholder="••••••••" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="auth-meta flex items-center justify-between gap-3">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              className="size-4 accent-[var(--tw-shoot)]"
              {...form.register("remember")}
            />
            Keep me signed in
          </label>
          <Link href="/forgot-password">Forgot password?</Link>
        </div>
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </Form>
  );
}

export default function LoginPage() {
  return (
    <AuthPage>
      <AuthCard>
        <AuthCardHeader title="Welcome back" description="Sign in to see what your fields are saying." />
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
        {/* No self-service sign-up: accounts are created by the farm's owner or an admin. */}
        <p className="auth-foot">
          New to Tilthwave? <strong>Ask your farm&rsquo;s owner for an account.</strong>
        </p>
      </AuthCard>
    </AuthPage>
  );
}
