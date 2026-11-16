import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
export type LoginInput = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    email: z.string().email("Enter a valid email address"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });
export type RegisterInput = z.infer<typeof registerSchema>;

export const cabinTypeEnum = z.enum([
  "interior",
  "oceanview",
  "balcony",
  "suite",
]);
export const triggerTypeEnum = z.enum([
  "price_drop",
  "back_in_stock",
  "availability_threshold",
]);

export const alertFormSchema = z
  .object({
    cabin_type: cabinTypeEnum,
    trigger_type: triggerTypeEnum,
    threshold_pct: z
      .union([z.coerce.number().min(0).max(100), z.nan()])
      .optional(),
    threshold_count: z
      .union([z.coerce.number().int().min(0), z.nan()])
      .optional(),
    email_enabled: z.boolean(),
    sms_enabled: z.boolean(),
  })
  .refine(
    (d) =>
      d.trigger_type !== "availability_threshold" ||
      (d.threshold_count !== undefined && !Number.isNaN(d.threshold_count)),
    {
      message: "A cabin count is required for availability warnings",
      path: ["threshold_count"],
    }
  );
export type AlertFormInput = z.infer<typeof alertFormSchema>;

export const phoneSchema = z.object({
  phone: z
    .string()
    .regex(/^\+[1-9]\d{6,14}$/, "Enter a valid E.164 number, e.g. +14155552671"),
});
export type PhoneInput = z.infer<typeof phoneSchema>;

export const verifyCodeSchema = z.object({
  code: z.string().regex(/^\d{4,8}$/, "Enter the code you received"),
});
export type VerifyCodeInput = z.infer<typeof verifyCodeSchema>;
