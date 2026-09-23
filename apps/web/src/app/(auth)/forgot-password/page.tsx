"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { MailCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import * as z from "zod";

import { useForgotPassword } from "@/api/auth";
import { toApiError } from "@/api/errors";
import { AuthCardHeader, AuthPage } from "@/components/auth-page";
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
import { Input } from "@/components/ui/input";

const schema = z.object({
  identifier: z.string().trim().min(1, "Enter your username or email").max(256),
});
type Values = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const forgot = useForgotPassword();
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { identifier: "" } });

  async function onSubmit(values: Values) {
    try {
      await forgot.mutateAsync(values.identifier);
      setSent(true);
    } catch (err) {
      toast.error(toApiError(err, "Could not send the reset link").message);
    }
  }

  return (
    <AuthPage>
      <Card className="w-full max-w-sm">
        <AuthCardHeader
          title="Forgot your password?"
          description="We'll email you a link to choose a new one."
        />
        <CardContent>
          {sent ? (
            // Same message whether or not the account exists: the API answers identically, and
            // so should the page, or it would be telling anyone which usernames are real.
            <div className="grid gap-4 text-center text-sm">
              <MailCheck className="mx-auto size-8 text-furrow" aria-hidden="true" />
              <p>
                If an account exists for <span className="font-medium">{form.getValues("identifier")}</span>,
                a reset link is on its way. It works for 30 minutes.
              </p>
              <p className="text-muted-foreground">
                Nothing arrived? Check your spam folder, or try again with the email address on the
                account.
              </p>
              <Button variant="outline" onClick={() => setSent(false)}>
                Try another username or email
              </Button>
            </div>
          ) : (
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4">
                <FormField
                  control={form.control}
                  name="identifier"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Username or email</FormLabel>
                      <FormControl>
                        <Input autoComplete="username" autoFocus {...field} />
                      </FormControl>
                      <FormDescription>The one you sign in with.</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="submit" disabled={forgot.isPending} className="w-full">
                  {forgot.isPending ? "Sending…" : "Send reset link"}
                </Button>
              </form>
            </Form>
          )}
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
