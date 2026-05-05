const allowedEmail = process.env.NEXT_PUBLIC_ALLOWED_USER_EMAIL?.trim().toLowerCase();

export function isAllowedUser(email: string | null | undefined): boolean {
  if (!allowedEmail) {
    return true;
  }
  return (email ?? "").trim().toLowerCase() === allowedEmail;
}

