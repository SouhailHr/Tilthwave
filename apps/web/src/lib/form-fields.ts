import * as z from "zod";

/** A required number greater than zero, with the messages every numeric form field uses. */
export const positiveNumber = (label: string) =>
  z.number({ error: `${label} is required` }).positive(`${label} must be greater than 0`);
