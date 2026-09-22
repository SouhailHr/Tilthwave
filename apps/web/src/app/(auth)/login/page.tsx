"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { useLogin } from "@/api/auth";
import { toApiError } from "@/api/errors";
import { safeRedirect } from "@/utils/safeRedirect";
import { AuthCardHeader, AuthPage } from "@/components/auth-page";
import { PasswordInput } from "@/components/password-input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

const loginSchema = z.object({
  username: z.string().min(1, "Username is required").max(256),
  password: z.string().min(1, "Password is required").max(256),
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
    defaultValues: { username: "", password: "" },
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
    <Card className="w-full max-w-sm">
      <AuthCardHeader title="Sign in" description="Where farms speak. Fields listen." />
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4">
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Username</FormLabel>
                  <FormControl>
                    <Input autoComplete="username" {...field} />
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
                  <div className="flex items-center justify-between">
                    <FormLabel>Password</FormLabel>
                    <Link
                      href="/forgot-password"
                      className="text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                    >
                      Forgot password?
                    </Link>
                  </div>
                  <FormControl>
                    <PasswordInput autoComplete="current-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <AuthPage>
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </AuthPage>
  );
}
