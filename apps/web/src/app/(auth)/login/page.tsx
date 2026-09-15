"use client";

import { Suspense, useEffect, useState } from "react";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { login } from "@/api/auth";
import { toApiError } from "@/api/errors";
import { safeRedirect } from "@/utils/safeRedirect";
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

  useEffect(() => {
    if (searchParams.get("expired") === "1") {
      toast.info("Session expired. Please sign in again.");
    }
  }, [searchParams]);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  async function onSubmit(values: LoginValues) {
    setSubmitting(true);
    try {
      await login(values);
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
      <CardHeader className="items-center text-center">
        <div className="mb-2 flex flex-col items-center gap-2">
          <Image
            src="/brand/tilthwave-mark.svg"
            alt="tilthwave"
            width={40}
            height={40}
            priority
          />
          <div className="flex items-baseline gap-2">
            <span className="font-heading text-xl font-semibold tracking-tight text-foreground">
              tilthwave
            </span>
            <span className="text-xs text-muted-foreground">· farm watch</span>
          </div>
        </div>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>Where farms speak. Fields listen.</CardDescription>
      </CardHeader>
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
                  <FormLabel>Password</FormLabel>
                  <FormControl>
                    <Input
                      type="password"
                      autoComplete="current-password"
                      {...field}
                    />
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
    <div className="relative flex flex-1 items-center justify-center overflow-hidden p-6">
      {/* Animated brand SVG kept as a plain img so the embedded SMIL/CSS
          animations actually play and so we don't need next.config's
          dangerouslyAllowSVG escape hatch. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/brand/tilthwave-bg-hero-animated.svg"
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 size-full object-cover"
      />
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </div>
  );
}