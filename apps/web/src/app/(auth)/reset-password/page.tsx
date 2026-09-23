"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { useResetPassword } from "@/api/auth";
import { toApiError } from "@/api/errors";
import { AuthCardHeader, AuthPage } from "@/components/auth-page";
import { PasswordInput } from "@/components/password-input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { PASSWORDS_MUST_MATCH, passwordSchema, passwordsMatch } from "@/lib/password-schema";

export const newPasswordSchema = z
  .object({
    new_password: passwordSchema,
    confirm_password: z.string(),
  })
  .refine(passwordsMatch, PASSWORDS_MUST_MATCH);
type Values = z.infer<typeof newPasswordSchema>;

function ResetPasswordForm() {
  const router = useRouter();
  const token = useSearchParams().get("token");
  const reset = useResetPassword();
  const form = useForm<Values>({
    resolver: zodResolver(newPasswordSchema),
    defaultValues: { new_password: "", confirm_password: "" },
  });

  if (!token) {
    return (
      <div className="grid gap-4 text-center text-sm">
        <p>This link is missing its token. Open the link from the email, or request a new one.</p>
        <Button variant="outline" onClick={() => router.push("/forgot-password")}>
          Request a new link
        </Button>
      </div>
    );
  }

  async function onSubmit(values: Values) {
    try {
      await reset.mutateAsync({ token: token as string, newPassword: values.new_password });
      router.replace("/login?reset=1");
    } catch (err) {
      toast.error(toApiError(err, "Could not reset the password").message);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4">
        <FormField
          control={form.control}
          name="new_password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>New password</FormLabel>
              <FormControl>
                <PasswordInput autoComplete="new-password" autoFocus {...field} />
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
        <Button type="submit" disabled={reset.isPending} className="w-full">
          {reset.isPending ? "Saving…" : "Set new password"}
        </Button>
      </form>
    </Form>
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthPage>
      <Card className="w-full max-w-sm">
        <AuthCardHeader title="Choose a new password" description="The link works once, for 30 minutes." />
        <CardContent>
          <Suspense fallback={null}>
            <ResetPasswordForm />
          </Suspense>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            <Link href="/login" className="underline-offset-4 hover:text-foreground hover:underline">
              Back to sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </AuthPage>
  );
}
